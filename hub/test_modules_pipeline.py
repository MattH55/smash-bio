"""Offline unit tests for the technique-module framework. No network access."""
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hub"))

from modules import MODULES, get_module  # noqa: E402
from modules import build_outputs as outputs  # noqa: E402
from modules import build_records as records  # noqa: E402
from modules import classify  # noqa: E402
from modules import crossrefs  # noqa: E402
from modules import extract  # noqa: E402
from modules import fulltext  # noqa: E402
from modules import gazetteer_ext  # noqa: E402
from modules import harvest  # noqa: E402


FRET_ARTICLE = {
    "epmc_id": "1", "source": "MED", "doi": "10.1/a",
    "title": "Single-molecule FRET of a DNA Holliday junction using Cy3 and Cy5",
    "abstract": "We measured a FRET efficiency of 0.72 for the folded state. "
                "Analysis used FRETBursts.",
    "pub_types": ["research-article"], "keywords": [], "mesh": [],
}
FRET_ENSEMBLE = {
    "epmc_id": "2", "source": "MED", "doi": "10.1/b",
    "title": "A bulk FRET biosensor for calcium imaging",
    "abstract": "Ensemble FRET read out in bulk; no single molecules were resolved.",
    "pub_types": ["research-article"], "keywords": [], "mesh": [],
}
FRET_METHODS = {
    "epmc_id": "3", "source": "MED", "doi": "10.1/c",
    "title": "An open-source software framework for smFRET analysis",
    "abstract": "We benchmark single-molecule FRET analysis algorithms.",
    "pub_types": ["research-article"], "keywords": [], "mesh": [],
}
SPT_ARTICLE = {
    "epmc_id": "4", "source": "MED", "doi": "10.1/d",
    "title": "Single-particle tracking of kinesin-1 with a diffusion coefficient of 0.12 um2/s",
    "abstract": "Individual kinesin-1 motors were tracked; the diffusion coefficient of 0.12 um2/s.",
    "pub_types": ["research-article"], "keywords": [], "mesh": [],
}
FRET_ARTICLE2 = {
    "epmc_id": "5", "source": "MED", "doi": "10.1/e",
    "title": "smFRET of a SAM riboswitch using Cy3 and Cy5",
    "abstract": "The riboswitch folded with a FRET efficiency of 0.61.",
    "pub_types": ["research-article"], "keywords": [], "mesh": [],
}

# a parsed s05_fulltext result, as modules.fulltext hands it to build_record
FULLTEXT = {
    "pmcid": "PMC1", "ok": True,
    "methods_text": "Samples were labelled with Cy3 and Cy5 maleimide. Analysis used FRETBursts.",
    "data_availability": [{"title": "Data availability", "text": "Raw data are in Zenodo."}],
    "repo_links": ["10.5281/zenodo.12345"],
    "supplementary": [],
}


class RegistryTests(unittest.TestCase):
    def test_registry_is_consistent(self):
        self.assertEqual(sorted(MODULES), ["channel", "fret", "mp", "spt"])
        prefixes = {spec.record_prefix for spec in MODULES.values()}
        self.assertEqual(len(prefixes), len(MODULES))
        for slug, spec in MODULES.items():
            self.assertEqual(spec.slug, slug)
            self.assertTrue(spec.schema_file.endswith(".schema.json"))
            self.assertTrue(spec.page_path().startswith("/"))

    def test_record_ids_are_zero_padded(self):
        spec = get_module("fret")
        self.assertEqual(spec.record_id(7), "FRET-000007")
        self.assertRegex(spec.record_id(7), spec.record_id_pattern)

    def test_unknown_module_raises(self):
        with self.assertRaises(KeyError):
            get_module("nope")


class ClassifyTests(unittest.TestCase):
    def test_core_methods_and_exclusions(self):
        fret = get_module("fret")
        tier, _tech, _r, _rev = classify.classify(FRET_ARTICLE, fret)
        self.assertEqual(tier, "core")
        self.assertEqual(classify.classify(FRET_METHODS, fret)[0], "methods")
        self.assertEqual(classify.classify(FRET_ENSEMBLE, fret)[0], "out")

    def test_classify_all_counts_tiers(self):
        fret = get_module("fret")
        kept, tiers = classify.classify_all([FRET_ARTICLE, FRET_ENSEMBLE, FRET_METHODS], fret)
        self.assertEqual(len(kept), 2)
        self.assertEqual(tiers["out"], 1)


class ExtractTests(unittest.TestCase):
    def test_results_are_grounded_with_provenance_and_unit(self):
        fret = get_module("fret")
        results = extract.extract_results(FRET_ARTICLE["abstract"], fret)
        by_q = {r["quantity"]: r for r in results}
        self.assertEqual(by_q["fret_efficiency_apparent"]["value"], 0.72)
        self.assertEqual(by_q["fret_efficiency_apparent"]["unit"], "1")
        self.assertEqual(by_q["fret_efficiency_apparent"]["provenance"][0]["method"], "regex_title_abstract")

    def test_software_is_only_reported_when_named(self):
        self.assertIn("FRETBursts", extract.extract_software(FRET_ARTICLE["abstract"]))
        self.assertEqual(extract.extract_software("no tool mentioned here"), [])

    def test_known_dye_pair_assigns_roles(self):
        pair = records.detect_fluorophores("labelled with Cy3 and Cy5")
        self.assertEqual([p["role"] for p in pair], ["donor", "acceptor"])

    def test_unknown_text_yields_no_fluorophores(self):
        self.assertEqual(records.detect_fluorophores("no dyes named"), [])


class BuildRecordTests(unittest.TestCase):
    def test_fret_record_validates_and_is_grounded(self):
        fret = get_module("fret")
        record = records.build_record(FRET_ARTICLE, fret, 1)
        self.assertIsNotNone(record)
        self.assertEqual(record["record_id"], "FRET-000001")
        self.assertEqual(record["fret_assays"][0]["fluorophores"][0]["role"], "donor")
        self.assertEqual(record["data_availability"]["status"], "unknown_no_fulltext")
        outputs.validator_for(fret).validate(record)

    def test_fret_record_skipped_without_dye_pair(self):
        fret = get_module("fret")
        no_dyes = dict(FRET_ARTICLE, title="Structural study of a Holliday junction",
                       abstract="We solved the structure; no dyes were used.")
        self.assertIsNone(records.build_record(no_dyes, fret, 1))

    def test_spt_record_validates(self):
        spt = get_module("spt")
        record = records.build_record(SPT_ARTICLE, spt, 1)
        self.assertIsNotNone(record)
        outputs.validator_for(spt).validate(record)

    def test_build_records_skips_ungrounded_and_numbers_kept(self):
        fret = get_module("fret")
        kept, skipped = records.build_records(
            [FRET_ARTICLE, FRET_ARTICLE2, FRET_METHODS, FRET_ENSEMBLE], fret)
        # METHODS has no grounded entity; ENSEMBLE has no named dye pair.
        self.assertEqual(skipped, 2)
        self.assertEqual([r["record_id"] for r in kept], ["FRET-000001", "FRET-000002"])

    def test_every_hand_written_example_validates_through_framework(self):
        for slug, spec in MODULES.items():
            example_dir = ROOT / "website" / "schema" / "modules" / "examples"
            ent_files = sorted(example_dir.glob(f"{slug}-*.json")) if spec.slug != "fret" else \
                sorted((ROOT / "website" / "schema" / "examples").glob("fret-*.json"))
            self.assertTrue(ent_files, f"no examples for {slug}")
            for path in ent_files:
                with self.subTest(module=slug, example=path.name):
                    outputs.validator_for(spec).validate(json.loads(path.read_text(encoding="utf-8")))


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.fret = get_module("fret")
        self.good = records.build_record(FRET_ARTICLE, self.fret, 1)
        bad = json.loads(json.dumps(self.good))
        bad["record_id"] = "XX-0001"
        self.bad = bad

    def test_outputs_write_downloads_and_report_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            report = outputs.write_outputs(
                [self.good, self.bad], self.fret,
                downloads_dir=temporary / "downloads", data_dir=temporary / "data",
            )
            self.assertEqual(report["n_valid"], 1)
            self.assertEqual(report["n_failed"], 1)
            self.assertEqual(report["failures"][0][0], "XX-0001")
            gz = temporary / "downloads" / "smash-fret-records.jsonl.gz"
            self.assertTrue(gz.exists())
            self.assertTrue((temporary / "downloads" / "smash-fret-summary.csv").exists())
            self.assertTrue((temporary / "data" / "fret" / "index.js").exists())


class CrossrefTests(unittest.TestCase):
    def test_crossref_rows_include_modules_and_smfs_link(self):
        smfs = [{"record_id": "SMFS-000123", "publication": {"doi": "10.1/shared"}}]
        module_records = {
            "fret": [{"record_id": "FRET-000001", "publication": {"doi": "10.1/shared"}}],
            "spt": [
                {"record_id": "SPT-000001", "publication": {"doi": "10.1/shared"}},
                {"record_id": "SPT-000002", "publication": {"doi": "10.1/only-spt"}},
            ],
        }
        rows = crossrefs.compute_crossrefs(crossrefs.build_index(smfs, module_records))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["modules"], ["fret", "spt"])
        self.assertEqual(rows[0]["smfs_record_id"], "SMFS-000123")


class HarvestTests(unittest.TestCase):
    def test_slim_maps_core_fields(self):
        row = harvest.slim({"id": "9", "source": "MED", "pmid": "1", "doi": "https://doi.org/10.1/x",
                            "title": "T", "pubYear": "2020", "abstractText": "A"})
        self.assertEqual(row["epmc_id"], "9")
        self.assertEqual(row["doi"], "10.1/x")
        self.assertEqual(row["year"], 2020)

    def test_dedupe_prefers_med_and_merges_tags(self):
        rows = [
            {"epmc_id": "1", "source": "PPR", "doi": "10.1/x", "query_tags": ["a"]},
            {"epmc_id": "2", "source": "MED", "doi": "10.1/x", "query_tags": ["b"]},
            {"epmc_id": "3", "source": "MED", "doi": "10.1/y", "query_tags": ["a"]},
        ]
        merged = harvest._dedupe(rows)
        self.assertEqual(len(merged), 2)
        kept = next(r for r in merged if r["doi"] == "10.1/x")
        self.assertEqual(kept["source"], "MED")
        self.assertEqual(sorted(kept["query_tags"]), ["a", "b"])

    def test_rate_factor_halves_the_request_rate(self):
        self.assertEqual(harvest.RATE_FACTOR, 2.0)


class GroundingTests(unittest.TestCase):
    """The gazetteer merges the shared vocabulary with module-local systems."""

    def test_every_declared_identifier_is_resolver_verified(self):
        for slug, terms in gazetteer_ext.BY_MODULE.items():
            for term in terms:
                for item in term["identifiers"]:
                    with self.subTest(module=slug, system=term["name"], scheme=item["scheme"]):
                        self.assertTrue(item["verified"], f"{term['name']} {item['scheme']}:{item['id']}")

    def test_all_module_system_types_are_in_the_schema_vocabulary(self):
        vocab = {"fret": ("DNA", "RNA", "protein", "complex", "ligand", "other"),
                 "spt": ("protein", "DNA", "RNA", "complex", "vesicle", "virus", "receptor", "other"),
                 "mp": ("protein", "protein_complex", "DNA", "RNA", "virus", "AAV",
                        "membrane_protein", "other"),
                 "channel": ("ion_channel", "transporter", "pore_forming_toxin", "receptor", "other")}
        for slug, allowed in vocab.items():
            for term in gazetteer_ext.BY_MODULE[slug]:
                with self.subTest(module=slug, system=term["name"]):
                    self.assertIn(term["type"], allowed)

    def test_shared_gazetteer_systems_are_reused(self):
        names = {e["name"] for e in gazetteer_ext.match_entities("microtubules were tracked", get_module("spt"))}
        self.assertTrue(any("Microtubule" in n for n in names), names)

    def test_channel_does_not_inherit_force_spectroscopy_proteins(self):
        channel_systems = gazetteer_ext.match_entities("microtubules and actin were imaged", get_module("channel"))
        self.assertEqual(channel_systems, [])

    def test_ferritin_chains_are_labelled_correctly(self):
        systems = {e["name"]: e for e in gazetteer_ext.match_entities(
            "ferritin heavy chain and ferritin light chain", get_module("mp"))}
        self.assertEqual(systems["Ferritin heavy chain"]["identifiers"][0]["id"], "P02794")
        self.assertEqual(systems["Ferritin light chain"]["identifiers"][0]["id"], "P02792")


class FulltextTests(unittest.TestCase):
    """Methods text grounds records the abstract alone cannot."""

    def test_abstract_only_availability_is_unknown(self):
        self.assertEqual(fulltext.data_availability(None), {"status": "unknown_no_fulltext"})

    def test_availability_reports_only_what_the_full_text_shows(self):
        row = fulltext.data_availability(FULLTEXT)
        self.assertEqual(row["status"], "public_repository")
        self.assertTrue(row["has_linked_dataset"])
        self.assertIn("Zenodo", row["statement"])
        code = fulltext.data_availability({"ok": True, "repo_links": ["github.com/a/b"],
                                           "data_availability": [], "supplementary": []})
        self.assertEqual(code["status"], "code_only")
        request = fulltext.data_availability(
            {"ok": True, "repo_links": [], "supplementary": [],
             "data_availability": [{"text": "Data are available upon reasonable request."}]})
        self.assertEqual(request["status"], "on_request")

    def test_parsed_for_ignores_a_missing_index(self):
        self.assertIsNone(fulltext.parsed_for("1", None))
        self.assertIsNone(fulltext.parsed_for("1", {}))

    def test_methods_text_grounds_a_record_the_abstract_cannot(self):
        fret = get_module("fret")
        article = dict(FRET_ARTICLE, title="FRET study of a DNA Holliday junction",
                       abstract="We measured a FRET efficiency of 0.72 for the folded state.")
        self.assertIsNone(records.build_record(article, fret, 1))
        record = records.build_record(article, fret, 1, fulltext=FULLTEXT)
        self.assertIsNotNone(record)
        roles = [p["role"] for p in record["fret_assays"][0]["fluorophores"]]
        self.assertEqual(roles, ["donor", "acceptor"])
        self.assertIn("FRETBursts", record["fret_assays"][0]["analysis"]["software"])
        self.assertEqual(record["data_availability"]["status"], "public_repository")
        self.assertEqual(record["provenance"][-1]["method"], "regex_fulltext_methods")
        outputs.validator_for(fret).validate(record)

    def test_channel_configuration_tags_map_to_schema_values(self):
        channel = get_module("channel")
        for tag, expected in (("planar_bilayer", "planar_lipid_bilayer"),
                              ("droplet_interface", "droplet_interface_bilayer"),
                              ("cell_attached", "cell_attached")):
            block = records.technique_block({"tier": "core", "techniques_detected": [tag]}, channel)
            with self.subTest(tag=tag):
                self.assertEqual(block["configuration"], expected)


if __name__ == "__main__":
    unittest.main()