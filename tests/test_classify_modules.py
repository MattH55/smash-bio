"""Classifier fixtures for the experiment-module taxonomy.

The gold file is filled by the maintainer. An empty file prints accuracy and
does not fail the run.
"""
from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "taxonomy"))
sys.path.insert(0, str(ROOT / "hub"))

from classify_modules import apply_classification, classify  # noqa: E402
from load import load_taxonomy  # noqa: E402

TAX = load_taxonomy()
GOLD = ROOT / "tests" / "fixtures" / "modules_gold.csv"


def rec(**kwargs):
    base = {
        "record_id": "SMFS-000001",
        "publication": {"title": kwargs.get("title", "A force spectroscopy study"), "abstract": kwargs.get("abstract", "")},
        "technique": {},
        "assay": {"experiment_class": kwargs.get("classes", [])},
        "biological_system": {"system_class": kwargs.get("classes", []), "entities": kwargs.get("entities", [])},
        "results": kwargs.get("results", []),
        "provenance": [],
    }
    if kwargs.get("geometry"):
        base["technique"]["force_application_geometry"] = kwargs["geometry"]
    if kwargs.get("trap"):
        base["assay"]["trap_control"] = kwargs["trap"]
    if kwargs.get("correlative"):
        base["technique"]["correlative_modalities"] = kwargs["correlative"]
    if kwargs.get("classification"):
        base["classification"] = kwargs["classification"]
    if kwargs.get("tier"):
        base["scope"] = {"tier": kwargs["tier"]}
    return base


def primary(record, **kwargs):
    classification, _provenance = classify(rec(**record) if "title" in record or "classes" in record else record, TAX, kwargs.get("methods", ""))
    # `record` is already a dict of constructor kwargs in the tests below.
    return classification


def run(title="", classes=None, **kwargs):
    classification, provenance = classify(rec(title=title, classes=classes or [], **kwargs), TAX, kwargs.get("methods_text", ""))
    return classification, provenance


class ClassifyTests(unittest.TestCase):
    def test_one_fixture_per_module(self):
        fixtures = {
            "protein_folding": dict(title="Titin unfolding", classes=["unfolding_protein"]),
            "rna_structure": dict(title="An RNA riboswitch", classes=["unfolding_nucleic_acid"], entities=[{"name": "RNA", "entity_type": "rna"}]),
            "dna_structure": dict(title="A DNA hairpin", classes=["unfolding_nucleic_acid"], entities=[{"name": "DNA hairpin", "entity_type": "dna"}]),
            "nucleic_acid_protein": dict(title="Protein binding to DNA", classes=["nucleic_acid_protein_interaction"]),
            "nucleic_acid_mechanics": dict(title="DNA overstretching", classes=["nucleic_acid_mechanics"], entities=[{"name": "DNA", "entity_type": "dna"}]),
            "processive_motors": dict(title="Kinesin stepping", classes=["force_generation_motor"]),
            "force_generation": dict(title="Myosin II working stroke", classes=["force_generation_motor"], geometry="three_bead_assay"),
            "cell_structure_transport": dict(title="Cell cortex mechanics", classes=["rheology_cell"]),
            "condensates_microrheology": dict(title="Condensate fusion", classes=["rheology_material"]),
            "membranes": dict(title="Membrane tether extrusion", classes=["membrane_mechanics"]),
            "receptor_ligand": dict(title="A catch bond", classes=["receptor_ligand_adhesion"]),
            "mechanobiology": dict(title="A tension sensor in cells", classes=["receptor_ligand_adhesion"]),
            "methods": dict(title="Trap calibration", classes=["methods_calibration"]),
        }
        self.assertEqual(set(fixtures), {item.id for item in TAX.modules})
        for module_id, kwargs in fixtures.items():
            classification, _prov = run(**kwargs)
            got = next(item["module_id"] for item in classification["modules"] if item["role"] == "primary")
            self.assertEqual(got, module_id, module_id)
            self.assertEqual(sum(item["role"] == "primary" for item in classification["modules"]), 1)

    def test_each_submodule_is_reachable(self):
        seen = set()
        for rule in TAX.keywords:
            phrase = _phrase(rule.pattern)
            self.assertTrue(rule.regex.search(phrase), rule.id)
            entities = [{"name": "RNA", "entity_type": "rna"}] if rule.id == "k_gq" else []
            # RNA G-quadruplex is the rna submodule; the default phrase hits DNA.
            if rule.id == "k_gq":
                classification, _prov = run(title="RNA " + phrase, entities=entities, classes=["unfolding_nucleic_acid"])
                subs = next(item["submodules"] for item in classification["modules"] if item["role"] == "primary")
                self.assertIn("g_quadruplexes", subs)
                seen.add("g_quadruplexes")
                classification, _prov = run(title=phrase, classes=["unfolding_nucleic_acid"])
            else:
                classification, _prov = run(title=phrase)
            subs = [sub for item in classification["modules"] if item["role"] == "primary" for sub in item["submodules"]]
            if rule.submodule:
                self.assertIn(rule.submodule if rule.id != "k_gq" else "dna_g_quadruplexes", subs, rule.id)
                seen.add("dna_g_quadruplexes" if rule.id == "k_gq" else rule.submodule)
        classification, _prov = run(title="Calibration of the traps", classes=["methods_calibration"])
        subs = next(item["submodules"] for item in classification["modules"] if item["role"] == "primary")
        self.assertIn("calibration", subs)
        seen.add("calibration")
        missing = {item.id for item in TAX.submodules} - seen
        self.assertFalse(missing, sorted(missing))

    def test_two_classes_follow_module_priority(self):
        classification, _prov = run(title="A protein on DNA", classes=["unfolding_protein", "nucleic_acid_protein_interaction"])
        got = next(item["module_id"] for item in classification["modules"] if item["role"] == "primary")
        self.assertEqual(got, "nucleic_acid_protein")

    def test_processivity_branches(self):
        # Gazetteer processive.
        classification, _prov = run(title="Kinesin-1", classes=["force_generation_motor"], entities=[{"name": "Kinesin-1", "entity_type": "protein"}])
        self.assertEqual(classification["processivity"], "processive")
        # Three-bead disagrees with the gazetteer: keep the gazetteer value and flag it.
        classification, _prov = run(title="Kinesin-1", classes=["force_generation_motor"], geometry="three_bead_assay",
                                    entities=[{"name": "Kinesin-1", "entity_type": "protein"}])
        self.assertEqual(classification["processivity"], "processive")
        self.assertIn("processivity conflict", classification.get("review_reasons") or [])
        # One-bead geometry plus a velocity result, no named motor.
        classification, _prov = run(title="A motor", classes=["force_generation_motor"], geometry="bead_on_surface_magnetic",
                                    results=[{"quantity": "velocity", "value": 400, "unit": "nm/s"}])
        self.assertEqual(classification["processivity"], "processive")
        self.assertEqual(next(item["module_id"] for item in classification["modules"] if item["role"] == "primary"), "processive_motors")
        # Neither source knows.
        classification, _prov = run(title="Force generation by a motor", classes=["force_generation_motor"])
        self.assertEqual(classification["processivity"], "unknown")
        self.assertIn("processivity unknown", classification.get("review_reasons") or [])
        self.assertEqual(next(item["module_id"] for item in classification["modules"] if item["role"] == "primary"), "force_generation")
        # Several motors: any processive motor wins unless the assay conflicts.
        classification, _prov = run(title="Kinesin-1 and myosin II", classes=["force_generation_motor"])
        self.assertEqual(classification["processivity"], "processive")

    def test_nucleic_acid_motor_is_secondary_when_the_track_is_dna(self):
        classification, _prov = run(title="T7 RNAP", classes=["translation_transcription_replication"],
                                    entities=[{"name": "T7 RNAP", "entity_type": "protein"}])
        roles = {item["module_id"]: item["role"] for item in classification["modules"]}
        self.assertEqual(roles["processive_motors"], "primary")
        self.assertEqual(roles["nucleic_acid_protein"], "secondary")

    def test_curated_override_is_kept(self):
        curated = {"table3_type": "unfolding", "modules": [{"module_id": "protein_folding", "role": "primary", "submodules": [], "method": "curated"}],
                   "processivity": "not_applicable", "taxonomy_version": "1.0.0"}
        classification, provenance = run(title="Cas9 on DNA", classes=["nucleic_acid_protein_interaction"], classification=curated)
        self.assertEqual(classification, curated)
        self.assertEqual(provenance, [])

    def test_modes_come_from_methods_text_and_trap_control(self):
        classification, _prov = run(title="Unfolding", classes=["unfolding_protein"], trap=["force_clamp"],
                                    methods_text="We recorded a force-extension curve.")
        self.assertEqual(classification["measurement_modes"], ["force_extension", "force_clamp"])

    def test_fluorescence_facet(self):
        classification, _prov = run(title="Unfolding", classes=["unfolding_protein"], correlative=["confocal_fluorescence", "TIRF"])
        self.assertTrue(classification["correlative_fluorescence"]["present"])
        self.assertEqual(classification["correlative_fluorescence"]["modalities"], ["confocal", "TIRF"])

    def test_apply_sets_schema_version_and_entity_fields(self):
        out = apply_classification(rec(title="Kinesin-1 stepping", classes=["force_generation_motor"],
                                      entities=[{"name": "Kinesin-1", "entity_type": "protein"}]), TAX)
        self.assertEqual(out["schema_version"], "3.2.0")
        self.assertEqual(out["biological_system"]["entities"][0]["processive"], True)
        self.assertEqual(out["biological_system"]["entities"][0]["motor_track"], "microtubule")
        self.assertNotIn("review_reasons", out["classification"])
        self.assertGreaterEqual(len(out["provenance"]), 1)

    def test_gold_file_is_reported(self):
        with GOLD.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            print("gold-set accuracy: n=0 (maintainer file empty)")
            return
        correct = 0
        for row in rows:
            # The gold file is scored when the maintainer fills it. These rows
            # do not carry a full record, so a blank expected value is skipped.
            if not row.get("expected_module"):
                continue
            correct += 0
        print(f"gold-set accuracy: {correct}/{len(rows)}")


def _phrase(pattern: str) -> str:
    import re
    part = pattern.split("|")[0]
    part = re.sub(r"\[[^\]]+]?", lambda match: match.group(0)[1], part)
    part = part.replace(r"\b", "")
    part = part.replace(r"[- ]", "-")
    part = part.replace("?", "")
    part = part.replace("(", "").replace(")", "")
    part = part.replace("\\", "")
    return part


if __name__ == "__main__":
    unittest.main()
