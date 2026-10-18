"""JSON Schema registry and validator for the SMASH-SIM schemas.

The sim record schema references the **published** SMFS 3.1.0 ``$defs``
(``../smash-smfs-record.schema.json``, ``../smash-smfs-results.schema.json``)
rather than duplicating them, so every schema those refs touch has to be in the
registry. Nothing here writes to any schema file.
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from modules.base import hub_dir


def schema_root():
    return hub_dir().parent / "website" / "schema"


def sim_schema_dir():
    return schema_root() / "sim"


def schema_files():
    """Every schema the sim records reference, in a stable order."""
    root = schema_root()
    return [
        root / "smash-smfs-record.schema.json",
        root / "smash-smfs-results.schema.json",
        sim_schema_dir() / "smash-sim-record.schema.json",
        sim_schema_dir() / "smash-sim-results.schema.json",
    ]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_registry():
    documents = [load(p) for p in schema_files()]
    return Registry().with_resources(
        [(doc["$id"], Resource.from_contents(doc)) for doc in documents]
    )


def record_schema():
    return load(sim_schema_dir() / "smash-sim-record.schema.json")


def validator():
    return Draft202012Validator(record_schema(), registry=build_registry())


def validate_records(records):
    """Split records into (valid, failures), failures being (record_id, message)."""
    check = validator()
    valid, failures = [], []
    for record in records:
        error = next(check.iter_errors(record), None)
        if error is None:
            valid.append(record)
        else:
            failures.append((record.get("record_id"), error.message))
    return valid, failures