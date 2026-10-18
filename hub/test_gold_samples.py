import csv
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import s10_prepare_gold_samples as gold


class GoldSampleTests(unittest.TestCase):
    def test_family_members_are_expanded_without_predictions(self):
        families = [{
            "canonical_doi": "10.1/item",
            "version_dois": ["10.1/item.v1"],
            "family_id": "machine-family",
            "relevance": "in_scope",
            "repository": "Example",
            "linked_records": ["SMFS-2", "SMFS-1"],
        }]
        rows = gold.expand_deposit_members(families)
        self.assertEqual([r["source_deposit_id"] for r in rows], ["10.1/item", "10.1/item.v1"])
        self.assertEqual(rows[0]["linked_study_record_id"], "SMFS-1;SMFS-2")
        self.assertNotIn("family_id", rows[0])
        self.assertNotIn("relevance", rows[0])

    def test_sampling_is_deterministic(self):
        rows = [{"value": i, "group": i % 4} for i in range(20)]
        one = gold.stratified_sample(rows, 10, lambda r: r["group"], random.Random(7))
        two = gold.stratified_sample(rows, 10, lambda r: r["group"], random.Random(7))
        self.assertEqual([r["value"] for r in one], [r["value"] for r in two])

    def test_writer_matches_template_and_blanks_human_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            (temporary / "studies.template.csv").write_text(
                "source_record_id,human_data_status,annotator,adjudication_notes\n", encoding="utf-8"
            )
            with patch.object(gold, "GOLD", temporary):
                path = gold.write_rows("studies", [{"source_record_id": "SMFS-1"}])
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows, [{
                "source_record_id": "SMFS-1",
                "human_data_status": "",
                "annotator": "",
                "adjudication_notes": "",
            }])

    def test_writer_refuses_to_overwrite_annotations(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            (temporary / "files.template.csv").write_text("source_file_id,human_content_tier\n", encoding="utf-8")
            (temporary / "files.csv").write_text("existing annotation\n", encoding="utf-8")
            with patch.object(gold, "GOLD", temporary):
                with self.assertRaises(FileExistsError):
                    gold.write_rows("files", [])

    def test_source_digest_ignores_annotation_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "studies.csv"
            path.write_text("source_record_id,human_data_status\nSMFS-1,\n", encoding="utf-8")
            before = gold.source_digest(path, ["source_record_id"])
            path.write_text("source_record_id,human_data_status\nSMFS-1,public_repository\n", encoding="utf-8")
            self.assertEqual(gold.source_digest(path, ["source_record_id"]), before)


if __name__ == "__main__":
    unittest.main()