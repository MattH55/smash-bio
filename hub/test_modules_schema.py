"""Schema tests for the SPT, mass-photometry and single-channel modules.

Offline only: reads schema files, example records and the frozen SMFS artifacts.
"""
import hashlib
import json
import re
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_ROOT = ROOT / "website" / "schema"
MODULE_DIR = SCHEMA_ROOT / "modules"
EXAMPLE_DIR = MODULE_DIR / "examples"
DOWNLOAD_DIR = ROOT / "website" / "downloads"

MODULE_SCHEMAS = {
    "spt": ("smash-spt-record.schema.json", "smash-spt-results.schema.json", "SPT"),
    "mp": ("smash-mp-record.schema.json", "smash-mp-results.schema.json", "MP"),
    "channel": ("smash-channel-record.schema.json", "smash-channel-results.schema.json", "SC"),
}
FORCE_HASHES = {
    "smash-smfs-records.jsonl.gz": "800de229e15efa01bfcaf1e690cf166c13c4e35a968357fb297ad0cbed72f059",
    "smash-smfs-summary.csv": "f18c03dca722b72785a32dacbab90911703ded99a9b916ab6b82c0c5eaa14a99",
    "smash-smfs-datasets.csv": "59ff377d08f64f313c27b9c193abede5179e80c9fafdde7a870585835db6b3ef",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ModuleSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = {"smash-common.schema.json": load(SCHEMA_ROOT / "smash-common.schema.json")}
        cls.shared = cls.schemas["smash-common.schema.json"]
        for slug, (record, results, _prefix) in MODULE_SCHEMAS.items():
            cls.schemas[record] = load(MODULE_DIR / record)
            cls.schemas[results] = load(MODULE_DIR / results)
        resources = [(s["$id"], Resource.from_contents(s)) for s in cls.schemas.values()]
        cls.registry = Registry().with_resources(resources)
        cls.validators = {
            slug: Draft202012Validator(cls.schemas[record], registry=cls.registry)
            for slug, (record, _r, _p) in MODULE_SCHEMAS.items()
        }

    def test_staging_schema_is_gone(self):
        """The staging copy was retired once the shared defs landed upstream."""
        self.assertFalse((MODULE_DIR / "_shared-pending.schema.json").exists())

    def test_module_schemas_reference_the_shared_defs(self):
        common_defs = set(self.shared["$defs"])
        for slug, (record, results, _p) in MODULE_SCHEMAS.items():
            for name in (record, results):
                text = (MODULE_DIR / name).read_text(encoding="utf-8")
                with self.subTest(schema=name):
                    self.assertNotIn("_shared-pending", text)
                    for ref in re.findall(r"\.\./smash-common\.schema\.json#/\$defs/(\w+)", text):
                        self.assertIn(ref, common_defs)

    def test_all_module_documents_are_valid_draft_2020_12(self):
        for slug, (record, results, _p) in MODULE_SCHEMAS.items():
            for name in (record, results):
                with self.subTest(schema=name):
                    Draft202012Validator.check_schema(self.schemas[name])

    def test_every_module_has_at_least_four_examples_that_validate(self):
        for slug, prefix in (("spt", "SPT"), ("mp", "MP"), ("channel", "SC")):
            paths = sorted(EXAMPLE_DIR.glob(f"{slug}-*.json"))
            with self.subTest(module=slug):
                self.assertGreaterEqual(len(paths), 4)
            for path in paths:
                record = load(path)
                with self.subTest(module=slug, example=path.name):
                    self.validators[slug].validate(record)
                    self.assertTrue(record["record_id"].startswith(prefix + "-"))

    def test_record_prefixes_are_unique(self):
        prefixes = [p for (_r, _s, p) in MODULE_SCHEMAS.values()] + ["SMFS", "FRET"]
        self.assertEqual(len(prefixes), len(set(prefixes)))

    def test_spt_missing_sample_is_rejected(self):
        record = load(EXAMPLE_DIR / "spt-membrane-receptor.json")
        del record["sample"]
        self.assertFalse(self.validators["spt"].is_valid(record))

    def test_spt_unknown_observable_is_rejected(self):
        record = load(EXAMPLE_DIR / "spt-membrane-receptor.json")
        record["results"][0]["quantity"] = "fret_efficiency_accurate"
        self.assertFalse(self.validators["spt"].is_valid(record))

    def test_mp_wrong_prefix_is_rejected(self):
        record = load(EXAMPLE_DIR / "mp-oligomerization.json")
        record["record_id"] = "SPT-000001"
        self.assertFalse(self.validators["mp"].is_valid(record))

    def test_channel_unknown_configuration_is_rejected(self):
        record = load(EXAMPLE_DIR / "channel-patch-hek.json")
        record["technique"]["configuration"] = "whole_cell"
        self.assertFalse(self.validators["channel"].is_valid(record))

    def test_channel_acceptable_trace_format(self):
        record = load(EXAMPLE_DIR / "channel-patch-hek.json")
        self.assertEqual(record["current_trace_sets"][0]["format"], "abf")
        record["current_trace_sets"][0]["format"] = "unknown_vendor"
        self.assertFalse(self.validators["channel"].is_valid(record))

    def test_force_downloads_are_byte_unchanged(self):
        for name, expected in FORCE_HASHES.items():
            with self.subTest(artifact=name):
                actual = hashlib.sha256((DOWNLOAD_DIR / name).read_bytes()).hexdigest()
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()