"""Schema and non-regression tests for the SMASH-BIO smFRET module.

These tests are offline: they read the published schema files, the hand-written
FRET example records, and the frozen SMFS download artifacts. They never touch
the network and never rewrite the SMFS artifacts.
"""
import gzip
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "website" / "schema"
DOWNLOAD_DIR = ROOT / "website" / "downloads"
FORCE_HASHES = {
    "smash-smfs-records.jsonl.gz": "800de229e15efa01bfcaf1e690cf166c13c4e35a968357fb297ad0cbed72f059",
    "smash-smfs-summary.csv": "f18c03dca722b72785a32dacbab90911703ded99a9b916ab6b82c0c5eaa14a99",
    "smash-smfs-datasets.csv": "59ff377d08f64f313c27b9c193abede5179e80c9fafdde7a870585835db6b3ef",
}


def load_schema(name):
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def schema_registry(schemas):
    resources = [(schema["$id"], Resource.from_contents(schema)) for schema in schemas]
    return Registry().with_resources(resources)


class SmFretSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names = [
            "smash-common.schema.json",
            "smash-fret-results.schema.json",
            "smash-fret-record.schema.json",
            "smash-smfs-results.schema.json",
            "smash-smfs-record.schema.json",
        ]
        cls.schemas = {name: load_schema(name) for name in names}
        cls.registry = schema_registry(cls.schemas.values())
        cls.fret_validator = Draft202012Validator(
            cls.schemas["smash-fret-record.schema.json"], registry=cls.registry
        )

    def test_schema_documents_are_valid_draft_2020_12(self):
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(schema)

    def test_all_fret_examples_validate(self):
        paths = sorted((SCHEMA_DIR / "examples").glob("fret-*.json"))
        self.assertGreaterEqual(len(paths), 5)
        for path in paths:
            with self.subTest(example=path.name):
                self.fret_validator.validate(json.loads(path.read_text(encoding="utf-8")))

    def test_hybrid_example_links_force_record_and_channels(self):
        record = json.loads((SCHEMA_DIR / "examples" / "fret-hybrid-force.json").read_text(encoding="utf-8"))
        self.assertEqual(record["technique"]["geometry"], "hybrid_force_fret")
        self.assertTrue(record["related_force_records"][0].startswith("SMFS-"))
        self.assertEqual(record["cross_ref_smfs_record"], record["related_force_records"][0])
        self.assertIn("optical_tweezers", record["correlative"])
        channels = record["fret_assays"][0]["trace_sets"][0]["channels"]
        self.assertIn("force", channels)
        self.assertIn("fret_efficiency", channels)

    def test_missing_acceptor_is_rejected(self):
        record = json.loads((SCHEMA_DIR / "examples" / "fret-confocal-dna.json").read_text(encoding="utf-8"))
        donor = record["fret_assays"][0]["fluorophores"][0]
        record["fret_assays"][0]["fluorophores"] = [donor, donor]
        self.assertFalse(self.fret_validator.is_valid(record))

    def test_wrong_record_prefix_is_rejected(self):
        record = json.loads((SCHEMA_DIR / "examples" / "fret-confocal-dna.json").read_text(encoding="utf-8"))
        record["record_id"] = "SMFS-000001"
        self.assertFalse(self.fret_validator.is_valid(record))

    def test_unknown_technique_primary_is_rejected(self):
        record = json.loads((SCHEMA_DIR / "examples" / "fret-confocal-dna.json").read_text(encoding="utf-8"))
        record["technique"]["primary"] = "smFRET"
        self.assertFalse(self.fret_validator.is_valid(record))

    def test_unknown_observable_is_rejected(self):
        record = json.loads((SCHEMA_DIR / "examples" / "fret-confocal-dna.json").read_text(encoding="utf-8"))
        record["results"][0]["quantity"] = "not_an_observable"
        self.assertFalse(self.fret_validator.is_valid(record))

    def test_partial_record_without_corrections_validates(self):
        record = json.loads((SCHEMA_DIR / "examples" / "fret-partial-no-corrections.json").read_text(encoding="utf-8"))
        self.fret_validator.validate(record)
        self.assertFalse(record["fret_assays"][0]["corrections"]["gamma"]["reported"])

    def test_existing_force_corpus_is_readable_and_versioned(self):
        """Exercise every preserved record without asserting a false legacy invariant.

        The published corpus predates this test and contains vocabulary values that
        are not accepted by the published 3.1.0 schema (for example, ``scaffold``
        and ``axoneme`` in SMFS-000096). Byte hashes below are the non-regression
        contract for these artifacts; smFRET support must not silently rewrite them.
        """
        path = DOWNLOAD_DIR / "smash-smfs-records.jsonl.gz"
        count = 0
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for count, line in enumerate(handle, start=1):
                record = json.loads(line)
                self.assertRegex(record["record_id"], r"^SMFS-[0-9]{6}$")
                self.assertEqual(record["schema_version"], "3.1.0")
        self.assertEqual(count, 7694)

    def test_force_downloads_are_byte_unchanged(self):
        for name, expected in FORCE_HASHES.items():
            with self.subTest(artifact=name):
                actual = hashlib.sha256((DOWNLOAD_DIR / name).read_bytes()).hexdigest()
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()