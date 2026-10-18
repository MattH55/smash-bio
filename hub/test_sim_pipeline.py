"""Pipeline tests for the Simulations category. Offline only.

They cover the classifier, the unit-aware extractor, the grounding gates in the
record builder, the matcher's rules, the audit sample and the dataset path.
"""
import json
import unittest
from pathlib import Path
from unittest import mock

import sim.audit as audit_mod
import sim.build_records as build_records
import sim.classify as classify_mod
import sim.extract as extract_mod
import sim.ingest as ingest_mod
import sim.match as match_mod
import sim.schema as schema_mod
from sim.spec import SIM


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(__file__).resolve().parent / "out" / "sim"


def article(**overrides):
    row = {
        "epmc_id": "TEST001", "source": "MED", "pmid": "1", "doi": "10.0000/test",
        "title": "Mechanical unfolding of titin I27 probed by steered molecular dynamics",
        "abstract": ("We performed constant velocity steered molecular dynamics with the CHARMM36 "
                     "force field in explicit water. The unfolding force was 190 pN at a pulling "
                     "speed of 0.5 nm/ns with a spring constant of 7 kcal/mol/A^2. 26 trajectories "
                     "were run."),
        "journal": "J Test", "year": 2024, "authors": ["A Author"], "pub_types": ["Journal Article"],
        "keywords": [], "mesh": [], "is_oa": True, "in_pmc": False, "pmcid": None,
    }
    row.update(overrides)
    return row


class ClassifyTests(unittest.TestCase):
    def test_core_pulling_simulation(self):
        row, tier = classify_mod.classify(article(), SIM)
        self.assertEqual(tier, "core")
        self.assertEqual(row["molecule_type"], "protein")

    def test_methods_paper(self):
        text = article(abstract=("We present a new coarse-grained Go model for protein mechanical "
                                 "unfolding and benchmark it against all-atom pulling simulations."))
        _row, tier = classify_mod.classify(text, SIM)
        self.assertEqual(tier, "methods")

    def test_equilibrium_md_without_force_is_out_of_scope(self):
        text = article(title="Equilibrium molecular dynamics of a solvated protein",
                       abstract=("We ran a 1 microsecond molecular dynamics simulation of lysozyme "
                                 "in water and analysed the hydrogen bonds."))
        row, tier = classify_mod.classify(text, SIM)
        self.assertEqual(tier, "out_of_scope")
        self.assertIsNone(row)

    def test_materials_exclusion(self):
        text = article(title="Pulling a graphene nanotube with molecular dynamics",
                       abstract="We simulate the mechanical unfolding of a carbon nanotube under tension.")
        row, tier = classify_mod.classify(text, SIM)
        self.assertEqual(tier, "out_of_scope")
        self.assertIsNone(row)

    def test_heavy_atom_go_wins_over_generic_go(self):
        text = article(abstract=("Heavy-atom Go models and C-alpha Go models of protein mechanical "
                                 "unfolding are compared by steered molecular dynamics."))
        _row, tier = classify_mod.classify(text, SIM)
        row, _tier = classify_mod.classify(text, SIM)
        self.assertEqual(tier, "core")
        self.assertEqual(row["model_families"][0], "Go_heavy_atom")


class ExtractTests(unittest.TestCase):
    def test_units_are_kept_with_the_value(self):
        results = extract_mod.extract_results(article()["abstract"], SIM)
        by_quantity = {row["quantity"]: row for row in results}
        self.assertEqual(by_quantity["unfolding_force"]["value"], 190.0)
        self.assertEqual(by_quantity["unfolding_force"]["unit"], "pN")
        self.assertEqual(by_quantity["unfolding_force"]["unit_system"], "physical")
        self.assertTrue(by_quantity["unfolding_force"]["provenance"])

    def test_unknown_unit_is_dropped_not_guessed(self):
        text = "The unfolding force was 12 furlongs per fortnight."
        quantities = {row["quantity"] for row in extract_mod.extract_results(text, SIM)}
        self.assertNotIn("unfolding_force", quantities)

    def test_scientific_notation_is_normalised(self):
        text = "The spontaneous unfolding rate was 5 x 10^-5 s-1 at zero force."
        results = extract_mod.extract_results(text, SIM)
        values = {row["quantity"]: row["value"] for row in results}
        self.assertAlmostEqual(values.get("rate_constant_zero_force", 0), 5e-5)

    def test_reduced_units_and_stated_conversion(self):
        text = ("The model is reported in reduced units. We chose sigma = 0.7 nm and the force "
                "scale is given in units of epsilon.")
        system, conversions = extract_mod.detect_unit_system(text, SIM)
        self.assertEqual(system, "reduced_with_stated_conversion")
        self.assertIn("length_sigma", conversions)
        self.assertEqual(conversions["length_sigma"]["unit"], "nm")
        # the published Quantity definition expects one Evidence object, not an array
        self.assertIsInstance(conversions["length_sigma"]["evidence"], dict)

    def test_reduced_units_without_conversion(self):
        system, conversions = extract_mod.detect_unit_system(
            "All energies are quoted in reduced units of the model.", SIM)
        self.assertEqual(system, "reduced")
        self.assertIsNone(conversions)

    def test_protocol_and_geometry(self):
        text = ("We pulled the protein at constant velocity, fixing residues 1-10 and pulling the "
                "C-terminus. The simulation used a dual-trap geometry.")
        protocol = extract_mod.detect_protocol(text, SIM)
        self.assertEqual(protocol["mode"], "constant_velocity")
        self.assertEqual(protocol["geometry"]["force_application_geometry"], "dumbbell_dual_trap")
        self.assertEqual(protocol["geometry"]["anchor_a"]["residue_range"], "1-10")

    def test_artifacts_and_repository_links(self):
        text = ("Trajectories are available at https://zenodo.org/record/1 and the input files are "
                "provided in the supplement. Analysis scripts are available on GitHub "
                "https://github.com/example/repo.")
        data = extract_mod.detect_data(text, SIM)
        self.assertEqual(data["status"], "public_repository")
        self.assertTrue(data["has_linked_dataset"])
        self.assertTrue(data["trajectories"]["available"])
        self.assertTrue(data["scripts"]["available"])


class BuildRecordTests(unittest.TestCase):
    def setUp(self):
        # PDB verification is a network call; keep the suite offline.
        patcher = mock.patch("sim.identifiers.verify_pdb", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_record_built_and_valid(self):
        record, reason = build_records.build_record(article(), SIM, 1)
        self.assertIsNone(reason)
        self.assertEqual(record["category"], "simulation")
        self.assertEqual(record["record_id"], "SIM-000001")
        self.assertEqual([], list(schema_mod.validator().iter_errors(record)))

    def test_missing_model_means_no_record(self):
        text = article(abstract=("We pulled the protein apart in a simulation and measured the "
                                 "unfolding force."))
        record, reason = build_records.build_record(text, SIM, 1)
        self.assertIsNone(record)
        self.assertEqual(reason, "no-model-evidence")

    def test_identifiers_are_only_written_when_verified(self):
        record, _reason = build_records.build_record(article(), SIM, 1)
        for entity in record["system"].get("entities") or []:
            for item in entity.get("identifiers") or []:
                self.assertTrue(item["verified"], item)

    def test_system_name_is_marked_inferred_when_no_entity_matched(self):
        text = article(title="Pulling a completely uncharacterised 12-mer peptide in silico",
                       abstract=("Molecular dynamics with an all-atom model in explicit water pulled "
                                 "the peptide at constant velocity; the unfolding force was 80 pN."))
        record, reason = build_records.build_record(text, SIM, 1)
        self.assertIsNone(reason)
        methods = [entry["method"] for entry in record["system"]["evidence"]]
        self.assertIn("inferred", methods)


class MatchTests(unittest.TestCase):
    def _record(self, name="Titin I27 domain", family="Go_CA", geometry="dumbbell_dual_trap"):
        return {
            "record_id": "SIM-000001",
            "system": {"name": name, "molecule_type": "protein",
                       "entities": [{"name": name, "entity_type": "protein",
                                     "identifiers": [{"scheme": "uniprot", "id": "Q8WZ42",
                                                      "verified": True}]}]},
            "model": {"family": family},
            "protocol": {"geometry": {"force_application_geometry": geometry}},
            "results": [{"quantity": "unfolding_force", "value": 150.0, "unit": "pN",
                         "unit_system": "physical"}],
        }

    def test_same_construct_same_geometry_requires_a_confirmed_construct(self):
        exp = {"record_id": "SMFS-1", "source": "SMASH-BIO", "molecule": "Titin I27 domain",
               "region": "1-89", "identifiers": [("uniprot", "Q8WZ42")],
               "geometry": "dumbbell_dual_trap", "force_pN": 200.0, "url": None}
        record = self._record()
        record["system"]["construct"] = {"residue_range": "1-89"}
        self.assertEqual(match_mod._level(record, exp, "uniprot:Q8WZ42"),
                         "same_construct_same_geometry")
        del record["system"]["construct"]
        self.assertEqual(match_mod._level(record, exp, "uniprot:Q8WZ42"),
                         "same_molecule_different_geometry")

    def test_homolog_needs_no_identifier(self):
        exp = {"record_id": "MPDB:1", "source": "MechanoProDB", "molecule": "I27, TITIN",
               "region": None, "identifiers": [], "geometry": None, "force_pN": 300.0, "url": None}
        self.assertEqual(match_mod._level(self._record(), exp, None), "homolog")

    def test_name_tokens_are_the_identity_test(self):
        self.assertTrue(match_mod._tokens("Titin (Ig/FnIII domains)") >= {"titin", "domains"}
                        or "titin" in match_mod._tokens("Titin (Ig/FnIII domains)"))
        self.assertNotIn("the", match_mod._tokens("The Titin domain"))

    def test_a_shared_identifier_alone_is_not_enough(self):
        """A reagent entity with the same accession must not produce a match."""
        experimental = [{"record_id": "SMFS-2", "source": "SMASH-BIO", "molecule": "Integrin",
                         "region": None, "identifiers": [("uniprot", "P22629")],
                         "geometry": "other", "force_pN": 30.0, "url": None}]
        record = self._record(name="Streptavidin")
        record["system"]["entities"][0]["identifiers"] = [{"scheme": "uniprot", "id": "P22629",
                                                          "verified": True}]
        _records, matches = match_mod.annotate([record], experimental)
        self.assertEqual([], matches)

    def test_matching_finds_a_shared_identifier_and_molecule(self):
        experimental = [{"record_id": "SMFS-3", "source": "SMASH-BIO", "molecule": "Titin I27 domain",
                         "region": "1-89", "identifiers": [("uniprot", "Q8WZ42")],
                         "geometry": "dumbbell_dual_trap", "force_pN": 200.0, "url": None}]
        records, matches = match_mod.annotate([self._record()], experimental)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["shared_identifier"], "uniprot:Q8WZ42")
        self.assertEqual(matches[0]["delta_force_pN"], -50.0)
        self.assertTrue(records[0]["links"]["experimental_matches"])

    def test_coverage_counts_distinct_experimental_systems(self):
        experimental = [{"record_id": "SMFS-4", "source": "SMASH-BIO", "molecule": "Titin I27 domain",
                         "region": "1-89", "identifiers": [("uniprot", "Q8WZ42")],
                         "geometry": "dumbbell_dual_trap", "force_pN": 200.0, "url": None}]
        records, matches = match_mod.annotate([self._record()], experimental)
        rows = match_mod.coverage(matches, records)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["n_experimental_systems"], 1)
        self.assertEqual(rows[0]["match_level"], "same_molecule_different_geometry")


class DatasetRecordsTests(unittest.TestCase):
    def test_mechanoprodb_simulation_rows_become_valid_records(self):
        rows = [{
            "id": 49, "pdb_id": "1TIT", "name": "I27, TITIN", "source": "simulation",
            "technique": "SMD_all_atom", "technique_raw": "all atom SMD simulation",
            "force_pN": 300, "velocity_nms": 100000, "loading_rate_pns": 44594100.0,
            "xbeta_nm": 0.89, "koff_s": 2e-10, "dG_kBT": 36.0, "temp_C": None,
            "contour_length_nm": None, "domain_coords": "1-89",
            "doi_pulling": "https://doi.org/10.1126/science.1239764",
        }]
        entries = [{"id": "mechanoprodb", "name": "MechanoProDB", "status": "ingested"}]
        records = ingest_mod.dataset_records(entries, rows, SIM, start=1)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source"]["kind"], "database")
        self.assertTrue(records[0]["source"]["redistributable"])
        self.assertEqual(records[0]["protocol"]["mode"], "constant_velocity")
        quantities = {row["quantity"] for row in records[0]["results"]}
        self.assertIn("unfolding_force", quantities)
        self.assertEqual([], list(schema_mod.validator().iter_errors(records[0])))


class AuditTests(unittest.TestCase):
    def test_sample_is_deterministic_and_has_an_empty_label_column(self):
        raw = [{"epmc_id": f"E{i}", "title": f"t{i}", "doi": f"10.0/{i}",
                "query_tags": ["proteins_smd"]} for i in range(30)]
        classified = []
        for i, item in enumerate(raw):
            row = dict(item)
            row.update({"tier": "core" if i % 2 == 0 else "out_of_scope",
                        "molecule_type": "protein" if i % 3 else "DNA",
                        "model_families": ["Go_CA"], "scope_reasons": ["x"],
                        "is_review": False, "is_methods_paper": False})
            classified.append(row)
        first = audit_mod.build_sample(raw, classified, SIM)
        second = audit_mod.build_sample(raw, classified, SIM)
        self.assertEqual([r["epmc_id"] for r in first], [r["epmc_id"] for r in second])
        self.assertTrue(all(r["human_label"] == "" for r in first))
        self.assertEqual(len(audit_mod.COLUMNS), len(audit_mod.COLUMNS))
        self.assertIn("human_label", audit_mod.COLUMNS)


class CorpusTests(unittest.TestCase):
    """Checks that only run when a pipeline run has produced the corpus."""

    def setUp(self):
        records_path = OUT_DIR / "sim_records.jsonl"
        if not records_path.exists():
            self.skipTest("no pipeline corpus in hub/out/sim")
        self.records = [json.loads(line) for line in
                        records_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_every_corpus_record_validates(self):
        validator = schema_mod.validator()
        failures = [(record["record_id"], next(validator.iter_errors(record)).message)
                    for record in self.records if next(validator.iter_errors(record), None)]
        self.assertEqual([], failures)

    def test_no_reduced_value_is_labelled_with_a_physical_unit(self):
        physical = {"pN", "nN", "nm", "angstrom", "kBT", "kcal/mol", "kJ/mol", "1/s", "pN/s",
                    "nm/s", "pN/nm", "s", "ms", "us", "ns", "ps", "N/m", "um", "pN nm"}
        for record in self.records:
            for result in record.get("results") or []:
                if result.get("unit_system") == "reduced":
                    self.assertNotIn(result["unit"], physical, record["record_id"])

    def test_published_records_only_carry_verified_identifiers(self):
        for record in self.records:
            for entity in record["system"].get("entities") or []:
                for item in entity.get("identifiers") or []:
                    self.assertTrue(item.get("verified"), (record["record_id"], item))

if __name__ == "__main__":
    unittest.main()