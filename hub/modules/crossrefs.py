"""Publication-level cross-references between modules and the SMFS index.

Writes `website/data/modules/crossrefs.jsonl` as
`{"doi": ..., "modules": [...], "smfs_record_id": ...}`. SMFS records are never
edited: the link is stored here, not inside them.
"""
import json
from pathlib import Path

from common import load_jsonl, norm_doi
from modules.base import hub_dir


def _doi(record):
    return norm_doi((record.get("publication") or {}).get("doi"))


def build_index(smfs_records, module_records):
    """Map DOI -> {modules:set, smfs_record_id} from SMFS and module records."""
    smfs_by_doi = {}
    for record in smfs_records:
        doi = _doi(record)
        if doi:
            smfs_by_doi.setdefault(doi, record.get("record_id"))
    by_doi = {}
    for slug, records in module_records.items():
        for record in records:
            doi = _doi(record)
            if not doi:
                continue
            entry = by_doi.setdefault(doi, {"modules": set()})
            entry["modules"].add(slug)
            if doi in smfs_by_doi:
                entry["smfs_record_id"] = smfs_by_doi[doi]
    return by_doi


def compute_crossrefs(by_doi):
    """Return sorted rows for DOIs found in more than one place."""
    rows = []
    for doi in sorted(by_doi):
        entry = by_doi[doi]
        modules = sorted(entry["modules"])
        if len(modules) < 2 and not entry.get("smfs_record_id"):
            continue
        row = {"doi": doi, "modules": modules}
        if entry.get("smfs_record_id"):
            row["smfs_record_id"] = entry["smfs_record_id"]
        rows.append(row)
    return rows


def write_crossrefs(rows, path=None):
    path = Path(path or (hub_dir().parent / "website" / "data" / "modules" / "crossrefs.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def collect_all(smfs_path=None, out_dir=None, out_path=None):
    """Convenience: load SMFS records plus every module's records and write crossrefs."""
    out_dir = Path(out_dir or (hub_dir() / "out"))
    smfs = load_jsonl(smfs_path or (out_dir / "records.jsonl"))
    module_records = {}
    for slug in ("fret", "spt", "mp", "channel"):
        path = out_dir / f"{slug}_records.jsonl"
        if path.exists():
            module_records[slug] = load_jsonl(path)
    rows = compute_crossrefs(build_index(smfs, module_records))
    write_crossrefs(rows, out_path)
    return rows