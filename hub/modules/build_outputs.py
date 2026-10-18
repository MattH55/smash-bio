"""Write module downloads and site-data files, validating every record first.

Records that fail schema validation are excluded and returned so the run report
can list them. Nothing is published that does not validate.
"""
import csv
import gzip
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from common import load_jsonl
from modules.base import hub_dir


def schema_dir():
    return hub_dir().parent / "website" / "schema"


def module_schema_dir():
    return schema_dir() / "modules"


def build_registry(spec):
    schema_root = schema_dir()
    subdir = (schema_root / spec.schema_subdir) if spec.schema_subdir else schema_root
    # every module schema refs the shared defs as ../smash-common.schema.json
    documents = [
        json.loads((schema_root / "smash-common.schema.json").read_text(encoding="utf-8")),
        json.loads((subdir / spec.schema_file).read_text(encoding="utf-8")),
        json.loads((subdir / spec.results_schema_file).read_text(encoding="utf-8")),
    ]
    resources = [(doc["$id"], Resource.from_contents(doc)) for doc in documents]
    return Registry().with_resources(resources), documents[1]


def validator_for(spec):
    registry, record_schema = build_registry(spec)
    return Draft202012Validator(record_schema, registry=registry)


def validate_records(records, spec):
    """Split records into (valid, failures) where failures are (record_id, error)."""
    validator = validator_for(spec)
    valid, failures = [], []
    for record in records:
        error = next(validator.iter_errors(record), None)
        if error is None:
            valid.append(record)
        else:
            failures.append((record.get("record_id"), error.message))
    return valid, failures


def _summary_row(record):
    pub = record.get("publication", {})
    tech = record.get("technique", {})
    avail = record.get("data_availability", {})
    entities = [e.get("name") for e in record.get("biological_system", {}).get("entities", [])]
    return [
        record.get("record_id"), pub.get("doi", ""), pub.get("pmid", ""), pub.get("year", ""),
        (pub.get("title") or "").replace("\n", " "), tech.get("primary", ""),
        tech.get("configuration", tech.get("geometry", "")),
        ";".join(e for e in entities if e),
        avail.get("status", ""), avail.get("has_linked_dataset", ""),
        len(record.get("results") or []),
        (record.get("fair_completeness") or {}).get("overall", ""),
    ]


SUMMARY_HEADER = ["record_id", "doi", "pmid", "year", "title", "technique", "configuration",
                  "entities", "data_status", "has_linked_dataset", "n_results", "fair_overall"]


def write_outputs(records, spec, downloads_dir=None, data_dir=None):
    """Validate and write downloads/modules/* and data/modules/<slug>/index.js."""
    website = hub_dir().parent / "website"
    downloads_dir = Path(downloads_dir or (website / "downloads" / "modules"))
    data_dir = Path(data_dir or (website / "data" / "modules"))
    downloads_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / spec.slug).mkdir(parents=True, exist_ok=True)

    valid, failures = validate_records(records, spec)

    gz_path = downloads_dir / f"smash-{spec.slug}-records.jsonl.gz"
    with gzip.open(gz_path, "wt", encoding="utf-8") as handle:
        for record in valid:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    with open(downloads_dir / f"smash-{spec.slug}-summary.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(SUMMARY_HEADER)
        for record in valid:
            writer.writerow(_summary_row(record))

    index = [{
        "id": r["record_id"],
        "doi": r.get("publication", {}).get("doi"),
        "y": r.get("publication", {}).get("year"),
        "t": r.get("publication", {}).get("title"),
        "tech": r.get("technique", {}).get("primary"),
        "st": r.get("data_availability", {}).get("status"),
        "fair": (r.get("fair_completeness") or {}).get("overall"),
        "nres": len(r.get("results") or []),
    } for r in valid]
    (data_dir / spec.slug / "index.js").write_text(
        f"SMASH.modules = SMASH.modules || {{}}; SMASH.modules.{spec.slug} = "
        + json.dumps({"spec": {"slug": spec.slug, "name": spec.name, "prefix": spec.record_prefix},
                      "n": len(index), "records": index}, ensure_ascii=False)
        + ";\n",
        encoding="utf-8",
    )
    return {
        "n_valid": len(valid),
        "n_failed": len(failures),
        "failures": failures,
        "records_path": str(gz_path),
    }


def load_module_records(spec):
    return load_jsonl(hub_dir() / "out" / f"{spec.slug}_records.jsonl")