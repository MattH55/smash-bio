"""Schema tests for the Simulations category (SMASH-SIM v1.0.0).

Offline only: it reads the schemas, the example records and the frozen SMFS
artifacts. It also asserts that the published SMFS schemas and downloads are
byte-for-byte unchanged, which is the isolation rule in the brief.
"""
import hashlib
import json
import re
import unittest
from pathlib import Path

from referencing import Registry, Resource

import sim.schema as sim_schema
from sim.spec import SIM


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_ROOT = ROOT / "website" / "schema"
SIM_DIR = SCHEMA_ROOT / "sim"
EXAMPLE_DIR = SIM_DIR / "examples"
DOWNLOAD_DIR = ROOT / "website" / "downloads"

#: published artifacts this work must not touch
# Re-frozen 2026-10-15 after the deliberate audit fixes (HTML entities decoded, CSV columns
# journal_mirror / counted_in_site_total added): see hub/fix_published.py.
# Schema 3.2.0 (experiment modules) rewrites the SMFS record schema, the results
# schema, the records gzip and the summary CSV. The shared schema and the
# dataset table stay byte-identical.
FROZEN = {
    "website/schema/smash-common.schema.json":
        "7edfa8eafdc9092b8e22e25de51f30f79956ee774f706f2e039a6e91b1705bfa",
    "website/downloads/smash-smfs-datasets.csv":
        "fda7556899ba7937857a9d842e9fa3dc417f315a45cef49722c6751d644b5e23",
}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def walk_refs(node, path="$"):
    """Yield (json path, $ref) for every reference in a schema document."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield path, value
            else:
                yield from walk_refs(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_refs(value, f"{path}/{index}")


class SimSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = load(SIM_DIR / "smash-sim-record.schema.json")
        cls.results = load(SIM_DIR / "smash-sim-results.schema.json")
        cls.smfs = load(SCHEMA_ROOT / "smash-smfs-record.schema.json")
        cls.smfs_results = load(SCHEMA_ROOT / "smash-smfs-results.schema.json")
        cls.validator = sim_schema.validator()
        cls.registry = sim_schema.build_registry()
        cls.examples = sorted(EXAMPLE_DIR.glob("*.json"))
        cls.example_records = [(path, load(path)) for path in cls.examples]

    # ---------------------------------------------------------------- references
    def test_every_reference_resolves(self):
        for name in ("smash-sim-record.schema.json", "smash-sim-results.schema.json"):
            document = load(SIM_DIR / name)
            resolver = self.registry.resolver(base_uri=document["$id"])
            for path, ref in walk_refs(document):
                with self.subTest(schema=name, at=path, ref=ref):
                    try:
                        resolved = resolver.lookup(ref)
                        contents = resolved.contents
                    except Exception as exc:  # noqa: BLE001 - surfaced as a test failure
                        self.fail(f"{ref} did not resolve: {exc!r}")
                    self.assertIsNotNone(contents)

    def test_no_staging_schema_is_referenced(self):
        for name in ("smash-sim-record.schema.json", "smash-sim-results.schema.json"):
            text = (SIM_DIR / name).read_text(encoding="utf-8")
            self.assertNotIn("_shared-pending", text)
            self.assertFalse((SIM_DIR / "_shared-pending.schema.json").exists())

    def test_geometry_enum_is_the_experimental_one(self):
        """The simulated pulling geometry must use the experimental representation."""
        sim_ref = self.record["$defs"]["Protocol"]["properties"]["geometry"]["properties"][
            "force_application_geometry"]["$ref"]
        self.assertIn("smash-smfs-record.schema.json#/$defs/Technique/properties/"
                      "force_application_geometry", sim_ref)
        resolved = self.registry.resolver(base_uri=self.record["$id"]).lookup(sim_ref).contents
        self.assertEqual(resolved["enum"],
                         self.smfs["$defs"]["Technique"]["properties"][
                             "force_application_geometry"]["enum"])

    def test_observables_extend_the_smfs_vocabulary_by_one(self):
        sim_observables = set(self.results["$defs"]["Observable"]["enum"])
        smfs_observables = set(self.smfs_results["$defs"]["Observable"]["enum"])
        self.assertEqual(sim_observables - smfs_observables, {"toughness"})
        self.assertTrue(sim_observables.issubset(smfs_observables | {"toughness"}))

    def test_result_structure_is_reused_not_copied(self):
        """The sim result mirrors the published Result field-for-field.

        It is mirrored, not $ref'd, only because the published quantity enum has no
        `toughness`; every published Result property must still be present here with
        the same type, so one consumer can read both.
        """
        items = self.record["properties"]["results"]["items"]
        self.assertEqual(items["$ref"], "smash-sim-results.schema.json#/$defs/SimResult")
        published = self.smfs_results["$defs"]["Result"]["properties"]
        sim = self.results["$defs"]["SimResult"]["properties"]
        for name, subschema in published.items():
            # Schema 3.2.0 records measurement_mode on experimental results.
            # SMASH-SIM records are out of scope for that field.
            if name == "measurement_mode":
                continue
            with self.subTest(property=name):
                self.assertIn(name, sim)
                if name == "quantity":  # the one deliberate vocabulary extension
                    continue
                self.assertEqual(subschema.get("type"), sim[name].get("type"))
        for name in self.smfs_results["$defs"]["Result"]["required"]:
            self.assertIn(name, self.results["$defs"]["SimResult"]["required"])

    def test_schema_version_matches_the_spec(self):
        self.assertEqual(self.record["properties"]["schema_version"]["const"], SIM.version)
        self.assertEqual(self.record["$defs"]["Source"]["properties"]["kind"]["enum"],
                         ["publication", "dataset", "database", "smash_sim_generated"])

    # ---------------------------------------------------------------- examples
    def test_at_least_six_examples(self):
        self.assertGreaterEqual(len(self.examples), 6)

    def test_examples_validate(self):
        for path, record in self.example_records:
            with self.subTest(example=path.name):
                errors = list(self.validator.iter_errors(record))
                self.assertEqual([], [f"{list(e.path)}: {e.message}" for e in errors])

    def test_examples_are_labeled_and_disjoint_from_the_corpus(self):
        for path, record in self.example_records:
            with self.subTest(example=path.name):
                self.assertEqual(record["category"], "simulation")
                self.assertEqual(record["curation"]["curator"], "schema-example")
                self.assertTrue(re.match(r"^SIM-9[0-9]{5}$", record["record_id"]),
                                "examples must not collide with corpus record ids")

    def test_examples_cover_the_brief_kinds(self):
        families = {record["model"]["family"] for _path, record in self.example_records}
        self.assertLessEqual({"all_atom_implicit_solvent", "Go_CA", "Go_heavy_atom", "oxDNA",
                              "thermodynamic_nearest_neighbour"}, families)
        kinds = {record["source"]["kind"] for _path, record in self.example_records}
        self.assertIn("database", kinds)
        unit_systems = {record["model"]["unit_system"] for _path, record in self.example_records}
        self.assertIn("reduced", unit_systems)
        self.assertIn("reduced_with_stated_conversion", unit_systems)

    def test_no_reduced_value_carries_a_physical_unit(self):
        physical = {"pN", "nN", "nm", "angstrom", "kBT", "kcal/mol", "kJ/mol", "1/s", "pN/s",
                    "nm/s", "pN/nm", "s", "ms", "us", "ns", "ps", "N/m", "um", "pN nm"}
        for path, record in self.example_records:
            for result in record.get("results") or []:
                if result.get("unit_system") == "reduced":
                    with self.subTest(example=path.name, result=result.get("quantity")):
                        self.assertNotIn(result["unit"], physical)

    def test_geometry_used_in_examples_is_a_valid_enum_value(self):
        allowed = set(self.smfs["$defs"]["Technique"]["properties"][
            "force_application_geometry"]["enum"])
        for path, record in self.example_records:
            geometry = (record["protocol"].get("geometry") or {}).get("force_application_geometry")
            if geometry:
                with self.subTest(example=path.name):
                    self.assertIn(geometry, allowed)

    # ---------------------------------------------------------------- isolation
    def test_published_artifacts_are_untouched(self):
        for relative, expected in FROZEN.items():
            digest = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            with self.subTest(artifact=relative):
                self.assertEqual(expected, digest)

    def test_sim_records_are_not_on_the_smfs_download_paths(self):
        self.assertTrue((DOWNLOAD_DIR / "sim").is_dir())
        for name in ("smash-smfs-records.jsonl.gz", "smash-smfs-summary.csv",
                     "smash-smfs-datasets.csv"):
            self.assertTrue((DOWNLOAD_DIR / name).is_file())


if __name__ == "__main__":
    unittest.main()