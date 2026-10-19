"""Published SMFS corpus after the schema 3.2.0 module stamp.

Full-record JSON Schema validation is not required: some records already used
vocabulary the 3.1.0 schema rejected. This check covers the module contract.
"""
import gzip
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
GZ = ROOT / "website" / "downloads" / "smash-smfs-records.jsonl.gz"
SCHEMA = ROOT / "website" / "schema" / "smash-smfs-record.schema.json"
MODULES = ROOT / "website" / "modules"


class CorpusModules(unittest.TestCase):
    def test_every_record_has_one_primary_module(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "3.2.0")
        validator = Draft202012Validator(schema["properties"]["classification"])
        ids = []
        with gzip.open(GZ, "rt", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                ids.append(record["record_id"])
                self.assertEqual(record["schema_version"], "3.2.0")
                classification = record["classification"]
                validator.validate(classification)
                primaries = [m for m in classification["modules"] if m["role"] == "primary"]
                self.assertEqual(len(primaries), 1, record["record_id"])
        self.assertEqual(len(ids), 7694)
        self.assertEqual(len(ids), len(set(ids)))

    def test_thirteen_module_pages_link_into_explore(self):
        index = (ROOT / "website" / "modules.html").read_text(encoding="utf-8")
        pages = list(MODULES.glob("*.html"))
        self.assertEqual(len(pages), 13)
        for page in pages:
            self.assertIn(f"modules/{page.name}", index)
            text = page.read_text(encoding="utf-8")
            self.assertIn("../explore.html?module=", text)
            self.assertNotIn('href="explore.html', text)


if __name__ == "__main__":
    unittest.main()
