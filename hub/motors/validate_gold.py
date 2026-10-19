#!/usr/bin/env python3
"""Validate Motors gold-set annotation files (BRIEF_MOTORS.md 1d).

Each file follows docs/motors/gold/TEMPLATE.yaml. Checks: required header fields; dates; the `motor` block against the
SMASH-MOTOR record schema; every result against the SMASH-MOTOR MotorResult; `not_reported` paths are
real motor fields and are not also filled in. null values mean "not looked at" and are dropped before schema validation.
The script never fills or derives labels.

    python hub/motors/validate_gold.py [FILES ...]       # default: docs/motors/gold/records/*.yaml
Exit code 1 if any file has an error. Prints one line per file and a completion summary.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motors.schema import record_defs, registry, result_validator  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "docs" / "motors" / "gold"
HEADER = ("record_id", "smfs_record_id", "doi", "title", "annotator", "annotation_date", "second_reviewer", "adjudicated",
          "sections_read", "full_text_available", "is_processive_motor_study", "motor", "not_reported", "results", "notes")
SECTIONS = {"abstract", "methods", "results", "figure_legends", "tables", "supplement"}
MOTOR_FIELDS = ("assay_type", "experiment_type", "family", "family_other", "isoform", "uniprot", "construct", "oligomeric_state", "adaptors",
                "track", "probe_link", "load", "feedback", "chemistry", "reporting")


def _schemas():
    """(record schema, validator for the annotation's motor block, validator for one result)."""
    rec = record_defs()
    block = {"type": "object", "additionalProperties": False,
             "properties": {k: {"$ref": f"{rec['$id']}#/properties/{k}"} for k in MOTOR_FIELDS}}
    return rec, Draft202012Validator(block, registry=registry()), result_validator()


def prune(x):
    """Drop None, empty strings and empty containers (unfilled template fields)."""
    if isinstance(x, dict):
        d = {k: prune(v) for k, v in x.items()}
        return {k: v for k, v in d.items() if v not in (None, "", [], {})}
    if isinstance(x, list):
        return [v for v in (prune(i) for i in x) if v not in (None, "", [], {})]
    return x


def field_paths(rec: dict) -> set[str]:
    """Every motor field path (resolving the record schema's local $defs), e.g. 'load.direction'."""
    def walk(node: dict, prefix: str) -> set[str]:
        if "$ref" in node and node["$ref"].startswith("#/$defs/"):
            node = rec["$defs"][node["$ref"].split("/")[-1]]
        out = set()
        for k, v in (node.get("properties") or {}).items():
            out.add(prefix + k)
            if "$ref" in v and v["$ref"].startswith("#/$defs/") or v.get("type") == "object" and "properties" in v:
                out |= walk(v, prefix + k + ".")
        return out
    return walk({"properties": {k: rec["properties"][k] for k in MOTOR_FIELDS}}, "")


def filled_paths(d: dict, prefix: str = "") -> set[str]:
    out = set()
    for k, v in d.items():
        p = f"{prefix}{k}"
        out.add(p)
        if isinstance(v, dict):
            out |= filled_paths(v, p + ".")
    return out


def check(path: Path, rec_schema: dict, motor_v, result_v) -> tuple[list[str], bool]:
    errors: list[str] = []
    try:
        a = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return [f"YAML error: {exc}"], False
    missing = [k for k in HEADER if k not in a]
    if missing:
        errors.append(f"missing keys: {missing}")
    if a.get("record_id") and path.stem != a["record_id"] and path.name != "TEMPLATE.yaml":
        errors.append(f"file name {path.stem} does not match record_id {a['record_id']}")
    if a.get("annotation_date"):
        try:
            dt.date.fromisoformat(str(a["annotation_date"]))
        except ValueError:
            errors.append(f"annotation_date not YYYY-MM-DD: {a['annotation_date']}")
    bad_sections = set(a.get("sections_read") or []) - SECTIONS
    if bad_sections:
        errors.append(f"unknown sections_read: {sorted(bad_sections)}")
    motor = prune(a.get("motor") or {})
    for e in motor_v.iter_errors(motor):
        errors.append(f"motor.{'.'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}")
    valid = field_paths(rec_schema)
    nr = set(a.get("not_reported") or [])
    for p in sorted(nr - valid):
        errors.append(f"not_reported path is not a motor field: {p}")
    for p in sorted(nr & filled_paths(motor)):
        errors.append(f"{p} is both filled and listed as not_reported")
    for i, r in enumerate(a.get("results") or []):
        for e in result_v.iter_errors(prune(r)):
            errors.append(f"results[{i}].{'.'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}")
    complete = bool(a.get("annotator") and a.get("annotation_date") and a.get("is_processive_motor_study") is not None
                    and a.get("sections_read"))
    return errors, complete


def main(argv: list[str]) -> int:
    files = [Path(p) for p in argv] or sorted((GOLD / "records").glob("*.yaml"))
    motor_def, motor_v, result_v = _schemas()
    n_err = n_complete = 0
    for f in files:
        errs, complete = check(f, motor_def, motor_v, result_v)
        n_err += bool(errs)
        n_complete += complete
        print(f"{'ERROR' if errs else 'ok   '} {f.name}{'' if complete else '  (not yet annotated)'}")
        for e in errs:
            print("      ", e)
    print(f"validate_gold: {len(files)} files, {n_err} with errors, {n_complete} annotated")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
