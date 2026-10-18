"""Validate gold annotations and evaluate Milestone-1 gates when adjudication is complete.

The script never derives human labels.  On incomplete batches it writes a
machine-readable pending report; metrics are computed only from non-empty final
adjudicated labels.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date
from itertools import combinations
from pathlib import Path

from harvester_cleanup import COUNTED_RELEVANCE


HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
GOLD = HERE / "gold"
REPORT = GOLD / "evaluation.json"
RELEVANCE_LABELS = {"in_scope", "methods", "out_of_scope", "unsure"}
DATA_STATUS_LABELS = {
    "public_repository", "source_data_supplement", "journal_supplement", "on_request",
    "not_available", "not_stated", "unknown_no_fulltext", "code_only",
}


def load_jsonl(path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


def digest_source_columns(path, fields):
    digest = hashlib.sha256()
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            payload = json.dumps([row.get(field, "") for field in fields], ensure_ascii=False, separators=(",", ":"))
            digest.update((payload + "\n").encode("utf-8"))
    return digest.hexdigest()


def prediction_maps(families):
    family_by_id, relevance_by_id = {}, {}
    for family in families:
        identifiers = [family.get("canonical_doi"), family.get("doi"), family.get("url")]
        identifiers.extend(family.get("version_dois") or [])
        for identifier in identifiers:
            if identifier:
                key = str(identifier).strip().lower()
                family_by_id[key] = family.get("family_id")
                relevance_by_id[key] = family.get("relevance")
    return family_by_id, relevance_by_id


def pairwise_metrics(rows, predictions):
    tp = tn = fp = fn = 0
    for left, right in combinations(rows, 2):
        predicted_same = predictions[left["source_deposit_id"].lower()] == predictions[right["source_deposit_id"].lower()]
        human_same = left["adjudicated_family_id"] == right["adjudicated_family_id"]
        if predicted_same and human_same:
            tp += 1
        elif predicted_same:
            fp += 1
        elif human_same:
            fn += 1
        else:
            tn += 1
    total = tp + tn + fp + fn
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "accuracy": (tp + tn) / total if total else None,
        "precision_same_family": precision,
        "recall_same_family": recall,
        "f1_same_family": (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and precision + recall else None,
        "pairs": total,
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


def evaluate(gold=GOLD, out=OUT):
    errors, warnings = [], []
    manifest_path = gold / "sample_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    datasets = {}
    for name in ("studies", "deposits", "files"):
        path = gold / f"{name}.csv"
        template = gold / f"{name}.template.csv"
        rows, fields = read_csv(path)
        _, expected = read_csv(template)
        if fields != expected:
            errors.append(f"{name}.csv columns do not exactly match the template")
        expected_rows = manifest["requested_rows"][name]
        if len(rows) != expected_rows:
            errors.append(f"{name}.csv has {len(rows)} rows; expected {expected_rows}")
        batch = manifest["batches"][f"{name}.csv"]
        if digest_source_columns(path, batch["source_fields"]) != batch["source_sha256"]:
            errors.append(f"{name}.csv immutable source columns differ from the generated batch")
        datasets[name] = rows

    records = {row["record_id"]: row for row in load_jsonl(out / "records.jsonl")}
    families = load_jsonl(out / "datasets_hub.jsonl")
    family_predictions, relevance_predictions = prediction_maps(families)

    study_ids = [row.get("source_record_id", "") for row in datasets["studies"]]
    deposit_ids = [row.get("source_deposit_id", "").lower() for row in datasets["deposits"]]
    if len(study_ids) != len(set(study_ids)):
        errors.append("studies.csv contains duplicate source_record_id values")
    if len(deposit_ids) != len(set(deposit_ids)):
        errors.append("deposits.csv contains duplicate source_deposit_id values")
    missing_studies = sorted(set(study_ids) - records.keys())
    missing_deposits = sorted(set(deposit_ids) - family_predictions.keys())
    if missing_studies:
        errors.append(f"{len(missing_studies)} study identifiers no longer join to records.jsonl")
    if missing_deposits:
        errors.append(f"{len(missing_deposits)} deposit identifiers no longer join to datasets_hub.jsonl")

    for row in datasets["studies"]:
        for field in ("human_data_status", "adjudicated_data_status"):
            label = row.get(field, "").strip()
            if label and label not in DATA_STATUS_LABELS:
                errors.append(f"invalid {field} for {row.get('source_record_id')}: {label}")
    for row in datasets["deposits"]:
        for field in ("human_relevance", "adjudicated_relevance"):
            label = row.get(field, "").strip()
            if label and label not in RELEVANCE_LABELS:
                errors.append(f"invalid {field} for {row.get('source_deposit_id')}: {label}")
    for name in ("studies", "deposits", "files"):
        for number, row in enumerate(datasets[name], 2):
            annotation_date = row.get("annotation_date", "").strip()
            if annotation_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", annotation_date):
                errors.append(f"{name}.csv row {number} has a non-ISO annotation_date: {annotation_date}")

    required = {
        "studies": ("human_data_status", "annotator", "annotation_date", "second_reviewer", "adjudicated_data_status"),
        "deposits": ("human_relevance", "human_family_id", "annotator", "annotation_date", "second_reviewer", "adjudicated_relevance", "adjudicated_family_id"),
    }
    completion = {}
    for name, fields in required.items():
        missing = Counter(field for row in datasets[name] for field in fields if not row.get(field, "").strip())
        complete_rows = sum(all(row.get(field, "").strip() for field in fields) for row in datasets[name])
        completion[name] = {"rows": len(datasets[name]), "complete_rows": complete_rows, "missing_fields": dict(missing)}

    report = {
        "schema_version": 1,
        "evaluated": date.today().isoformat(),
        "status": "invalid" if errors else "pending_human_annotation",
        "validation": {"errors": errors, "warnings": warnings},
        "completion": completion,
        "gates": {
            "family_pairwise_accuracy": {"target": 0.98, "measured": None},
            "relevance_in_scope_precision": {"target": 0.95, "measured": None},
        },
    }
    deposits_complete = completion["deposits"]["complete_rows"] == len(datasets["deposits"])
    if not errors and deposits_complete and datasets["deposits"]:
        pairwise = pairwise_metrics(datasets["deposits"], family_predictions)
        predicted_positive = [row for row in datasets["deposits"]
                              if relevance_predictions[row["source_deposit_id"].lower()] in COUNTED_RELEVANCE]
        true_positive = sum(row["adjudicated_relevance"] in COUNTED_RELEVANCE for row in predicted_positive)
        relevance_precision = true_positive / len(predicted_positive) if predicted_positive else None
        report["status"] = "complete"
        report["gates"]["family_pairwise_accuracy"].update(
            measured=pairwise["accuracy"], passed=pairwise["accuracy"] >= 0.98, details=pairwise)
        report["gates"]["relevance_in_scope_precision"].update(
            measured=relevance_precision,
            passed=relevance_precision is not None and relevance_precision >= 0.95,
            details={"predicted_in_scope_or_methods": len(predicted_positive), "human_in_scope_or_methods": true_positive})
    else:
        reason = "invalid gold set" if errors else "adjudicated deposit labels are incomplete"
        for gate in report["gates"].values():
            gate["reason"] = reason
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate without writing gold/evaluation.json")
    args = parser.parse_args()
    report = evaluate()
    if not args.check:
        REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(REPORT)
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if report["status"] == "invalid" else 0)


if __name__ == "__main__":
    main()