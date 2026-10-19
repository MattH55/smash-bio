"""JSON Schema registry and validators for SMASH-MOTOR (like hub/sim/schema.py).

The motor schemas reference the published SMFS 3.1.0 `$defs`, so those files are registered too. Nothing here writes
to any schema file.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2] / "website" / "schema"
MOTOR = ROOT / "motor"
FILES = [ROOT / "smash-smfs-record.schema.json", ROOT / "smash-smfs-results.schema.json",
         MOTOR / "smash-motor-record.schema.json", MOTOR / "smash-motor-results.schema.json"]


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def registry() -> Registry:
    return Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in map(load, FILES)])


def _validator(ref: str) -> Draft202012Validator:
    return Draft202012Validator({"$ref": ref}, registry=registry())


def record_validator() -> Draft202012Validator:
    return _validator("https://smash-bio.org/schema/motor/smash-motor-record.schema.json")


def result_validator() -> Draft202012Validator:
    return _validator("https://smash-bio.org/schema/motor/smash-motor-results.schema.json#/$defs/MotorResult")


def record_defs() -> dict:
    return load(MOTOR / "smash-motor-record.schema.json")


def validate(records: list[dict]) -> tuple[list[dict], list[tuple[str, str]]]:
    """Split records into (valid, failures); a failure is (record_id, first error)."""
    v = record_validator()
    good, bad = [], []
    for r in records:
        e = next(v.iter_errors(r), None)
        if e is None:
            good.append(r)
        else:
            bad.append((r.get("record_id"), f"{'/'.join(map(str, e.absolute_path))}: {e.message[:160]}"))
    return good, bad
