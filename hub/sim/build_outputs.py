"""Validate and write the Simulations category's downloads and site data.

Every record is validated against ``smash-sim-record.schema.json`` first;
records that fail are excluded and returned so the run report can list them.
Downloads contain only records whose source licence allows redistribution: a
publication's metadata and our own annotations always qualify, a
`dataset`/`database` record only when the licence is explicit (for example
MechanoProDB's MIT terms).
"""
import csv
import gzip
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from modules.base import hub_dir
from sim import schema


SUMMARY_HEADER = [
    "record_id", "source_kind", "redistributable", "doi", "pmid", "year", "title",
    "journal", "molecule_type", "system_name", "model_family", "model_group", "software",
    "unit_system", "protocol_mode", "pulling_speed", "n_results", "data_status",
    "has_linked_dataset", "n_experimental_matches", "match_levels", "fair_overall",
]


def _quality(record):
    speed = record["protocol"].get("pulling_speed") or {}
    return f"{speed.get('value', '')} {speed.get('unit', '')}".strip()


def _summary_row(record):
    source = record["source"]
    return [
        record["record_id"], source["kind"], bool(source.get("redistributable", True)),
        source.get("doi", ""), source.get("pmid", ""), source.get("year", ""),
        (source.get("title") or "").replace("\n", " "), source.get("journal", ""),
        record["system"].get("molecule_type", ""), record["system"].get("name", ""),
        record["model"].get("family", ""), record["model"].get("family_group", ""),
        ";".join(item.get("name", "") for item in record["model"].get("software") or []),
        record["model"].get("unit_system", ""), record["protocol"].get("mode", ""),
        _quality(record), len(record.get("results") or []),
        record["data_availability"].get("status", ""),
        record["data_availability"].get("has_linked_dataset", ""),
        len((record.get("links") or {}).get("experimental_matches") or []),
        ";".join(sorted({m["match_level"] for m in
                         (record.get("links") or {}).get("experimental_matches") or []})),
        (record.get("fair_completeness") or {}).get("overall", ""),
    ]


def _compact(record):
    matches = (record.get("links") or {}).get("experimental_matches") or []
    return {
        "id": record["record_id"],
        "title": record["source"].get("title"),
        "doi": record["source"].get("doi"),
        "year": record["source"].get("year"),
        "journal": record["source"].get("journal"),
        "kind": record["source"]["kind"],
        "system": record["system"].get("name"),
        "molecule_type": record["system"].get("molecule_type"),
        "family": record["model"].get("family"),
        "family_group": record["model"].get("family_group"),
        "software": [item.get("name") for item in record["model"].get("software") or []],
        "unit_system": record["model"].get("unit_system"),
        "mode": record["protocol"].get("mode"),
        "data": record["data_availability"].get("status"),
        "nres": len(record.get("results") or []),
        "fair": (record.get("fair_completeness") or {}).get("overall"),
        "matches": len(matches),
        "match_levels": sorted({m["match_level"] for m in matches}),
        "trajectories": bool((record["data_availability"].get("trajectories") or {}).get("available")),
        "force_curves": bool((record["data_availability"].get("force_extension_curves")
                              or {}).get("available")),
        "input_files": bool((record["data_availability"].get("input_files") or {}).get("available")),
        "scripts": bool((record["data_availability"].get("scripts") or {}).get("available")),
    }


def _match_levels(record):
    levels = sorted({match["match_level"] for match in
                     (record.get("links") or {}).get("experimental_matches") or []})
    return ";".join(levels) or "none"


def aggregation(records):
    """Counts the site shows: by molecule type, model family, unit system, mode, match level."""
    def counts(key):
        return dict(Counter(key(record) for record in records))

    return {
        "molecule_type": counts(lambda r: r["system"].get("molecule_type")),
        "model_family": counts(lambda r: r["model"].get("family")),
        "model_group": counts(lambda r: r["model"].get("family_group")),
        "unit_system": counts(lambda r: r["model"].get("unit_system")),
        "protocol_mode": counts(lambda r: r["protocol"].get("mode")),
        "source_kind": counts(lambda r: r["source"]["kind"]),
        "data_status": counts(lambda r: r["data_availability"].get("status")),
        "match_level": counts(_match_levels),
        "has_experimental_match": counts(
            lambda r: bool((r.get("links") or {}).get("experimental_matches"))),
    }


def write_outputs(records, spec, downloads_dir=None, data_dir=None):
    """Validate, then write downloads/sim/* and sim/data/*.js."""
    website = hub_dir().parent / "website"
    downloads_dir = Path(downloads_dir or (website / "downloads" / spec.slug))
    data_dir = Path(data_dir or (website / "sim" / "data"))
    downloads_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    valid, failures = schema.validate_records(records)
    public = [record for record in valid
              if record["source"]["kind"] in ("publication", "smash_sim_generated")
              or record["source"].get("redistributable")]
    public_ids = {record["record_id"] for record in public}
    withheld = [record["record_id"] for record in valid if record["record_id"] not in public_ids]

    with gzip.open(downloads_dir / f"smash-{spec.slug}-records.jsonl.gz", "wt",
                   encoding="utf-8") as handle:
        for record in public:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    with open(downloads_dir / f"smash-{spec.slug}-summary.csv", "w", newline="",
              encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(SUMMARY_HEADER)
        for record in valid:
            writer.writerow(_summary_row(record))

    matches_parquet = hub_dir() / "data" / spec.slug / "matches.parquet"
    match_rows = []
    if matches_parquet.exists():
        import pandas as pd
        frame = pd.read_parquet(matches_parquet)
        frame.to_csv(downloads_dir / f"smash-{spec.slug}-matches.csv", index=False)
        match_rows = json.loads(frame.to_json(orient="records"))
    else:
        (downloads_dir / f"smash-{spec.slug}-matches.csv").write_text(
            "sim_record_id,experimental_record_id,experimental_source,match_level\n",
            encoding="utf-8")

    aggregation_rows = aggregation(valid)
    meta = {
        "slug": spec.slug, "name": spec.name, "short": spec.short, "prefix": spec.record_prefix,
        "version": spec.version, "category_label": spec.extra.get("category_label", "Simulation"),
        "path": spec.page_path(),
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_records": len(valid), "n_published": len(public), "n_withheld": len(withheld),
        "n_matches": len(match_rows), "aggregation": aggregation_rows,
    }
    payload = {"meta": meta, "records": [_compact(record) for record in valid],
               "full": valid}
    (data_dir / "index.js").write_text(
        "window.SMASH = window.SMASH || {};\n"
        f"SMASH.sim = {json.dumps(payload, ensure_ascii=False)};\n", encoding="utf-8")
    (data_dir / "matches.js").write_text(
        "window.SMASH = window.SMASH || {};\n"
        f"SMASH.simMatches = {json.dumps(match_rows, ensure_ascii=False)};\n", encoding="utf-8")

    systems = {}
    for record in valid:
        key = (record["system"].get("name") or "unnamed system").strip()
        systems.setdefault(key, {"system": key,
                                 "molecule_type": record["system"].get("molecule_type"),
                                 "records": []})
        systems[key]["records"].append(_compact(record))
    (data_dir / "systems.js").write_text(
        "window.SMASH = window.SMASH || {};\n"
        f"SMASH.simSystems = {json.dumps(list(systems.values()), ensure_ascii=False)};\n",
        encoding="utf-8")

    return {
        "n_valid": len(valid), "n_failed": len(failures), "failures": failures,
        "n_published": len(public), "withheld": withheld,
        "records_path": str(downloads_dir / f"smash-{spec.slug}-records.jsonl.gz"),
        "data_dir": str(data_dir),
    }