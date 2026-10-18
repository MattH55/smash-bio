import unittest

from s11_evaluate_gold import pairwise_metrics


class GoldEvaluationTests(unittest.TestCase):
    def test_pairwise_metrics(self):
        rows = [
            {"source_deposit_id": "a", "adjudicated_family_id": "one"},
            {"source_deposit_id": "b", "adjudicated_family_id": "one"},
            {"source_deposit_id": "c", "adjudicated_family_id": "two"},
        ]
        metrics = pairwise_metrics(rows, {"a": "x", "b": "x", "c": "x"})
        self.assertEqual(metrics["confusion"], {"tp": 1, "tn": 0, "fp": 2, "fn": 0})
        self.assertAlmostEqual(metrics["accuracy"], 1 / 3)

    def test_pairwise_metrics_handles_no_positive_predictions(self):
        rows = [
            {"source_deposit_id": "a", "adjudicated_family_id": "one"},
            {"source_deposit_id": "b", "adjudicated_family_id": "two"},
        ]
        metrics = pairwise_metrics(rows, {"a": "x", "b": "y"})
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertIsNone(metrics["precision_same_family"])


if __name__ == "__main__":
    unittest.main()