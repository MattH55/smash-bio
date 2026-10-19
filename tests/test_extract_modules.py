"""Module-profile results stay optional for the historical extractor."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hub"))

from extract import extract_results  # noqa: E402


class ExtractModuleObservables(unittest.TestCase):
    def test_historical_call_ignores_fusion_time(self):
        text = "The fusion time of 2 s was measured in a force-extension cycle."
        self.assertEqual(extract_results(text), [])

    def test_profile_reads_fusion_time_and_the_mode_in_the_same_sentence(self):
        text = "The fusion time of 2 s was measured in a force-extension cycle."
        rows = extract_results(text, quantities=["fusion_time"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], "fusion_time")
        self.assertEqual(rows[0]["value"], 2)
        self.assertEqual(rows[0]["unit"], "s")
        self.assertEqual(rows[0]["measurement_mode"], "force_extension")


if __name__ == "__main__":
    unittest.main()
