#!/usr/bin/env python3
"""Build SMASH-MOTOR records from a SMASH-BIO release (BRIEF_MOTORS.md 1c, separate-module design).

One MOTOR record per SMASH-BIO record whose motor family resolves (hub/motors/classify.py). Each record copies the
study's publication, technique and data-availability blocks from the SMASH-BIO record it links (`smfs_record_id`), and
adds the family, assay type, classification and evidence. Motor fields and results are left out until extraction
(Phase 2) or curation fills them; nothing is guessed. IDs are stable: hub/motors/id_map.json maps SMFS -> MOTOR.
The SMASH-BIO release is only read, never changed.

    python hub/motors/build_records.py [--smfs PATH] [--out-dir DIR]
Writes <out-dir>/smash-motor-records.jsonl.gz (default hub/out/motor/) and prints a summary; exit 1 if any record
fails schema validation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motors.classify import GAZ_PATH, classify  # noqa: E402
from motors.schema import validate  # noqa: E402
from motors.spec import VERSION  # noqa: E402

HUB = Path(__file__).resolve().parents[1]
ROOT = HUB.parent
ID_MAP = HUB / "motors" / "id_map.json"
PUB_KEYS = ("doi", "pmid", "pmcid", "title", "authors", "journal", "year", "publication_date", "open_access", "license")


def read_jsonl_gz(path: Path) -> list[dict]:
    # split on "\n" only: str.splitlines() also breaks on U+2028, which occurs inside abstracts
    return [json.loads(x) for x in gzip.decompress(path.read_bytes()).decode("utf-8").split("\n") if x.strip()]


def gazetteer_tag() -> str:
    return f"{GAZ_PATH.name}@sha256:{hashlib.sha256(GAZ_PATH.read_bytes()).hexdigest()[:12]}"


def build(smfs: list[dict], id_map: dict) -> tuple[list[dict], Counter]:
    reasons: Counter = Counter()
    out = []
    tag = gazetteer_tag()
    today = dt.date.today().isoformat()
    for r in sorted(smfs, key=lambda r: r["record_id"]):
        bs = r["biological_system"]
        c = classify(r["publication"].get("title", ""), r["publication"].get("abstract", ""), bs.get("entities") or [])
        reasons[c.reason] += 1
        if not c.family:
            continue
        mid = id_map.get(r["record_id"])
        if mid is None:
            mid = id_map[r["record_id"]] = f"MOTOR-{max([int(v[6:]) for v in id_map.values()] + [0]) + 1:06d}"
        tech = r["technique"]
        out.append({
            "record_id": mid, "schema_version": VERSION, "category": "processive_motor", "smfs_record_id": r["record_id"],
            "publication": {k: r["publication"][k] for k in PUB_KEYS if r["publication"].get(k) not in (None, "", [])},
            "technique": {"primary": tech["primary"], "force_application_geometry": tech.get("force_application_geometry", "other")},
            "assay_type": c.assay_type, "family": c.family,
            "evidence": {"family": c.evidence},
            "classification": {"route": c.route, "certainty": c.certainty, "family_hits": c.scores, "gazetteer": tag},
            "data_availability": r["data_availability"],
            "curation": {"level": "auto", "last_updated": today},
        })
    return out, reasons


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smfs", type=Path, default=ROOT / "website" / "downloads" / "smash-smfs-records.jsonl.gz")
    ap.add_argument("--out-dir", type=Path, default=HUB / "out" / "motor")
    a = ap.parse_args()
    smfs = read_jsonl_gz(a.smfs)
    id_map = json.loads(ID_MAP.read_text(encoding="utf-8")) if ID_MAP.exists() else {}
    recs, reasons = build(smfs, id_map)
    good, bad = validate(recs)
    ID_MAP.write_text(json.dumps(id_map, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in recs).encode("utf-8")
    (a.out_dir / "smash-motor-records.jsonl.gz").write_bytes(gzip.compress(payload, mtime=0))
    print(json.dumps({"smfs_records_read": len(smfs), "smfs_sha256": hashlib.sha256(a.smfs.read_bytes()).hexdigest(),
                      "motor_records": len(recs), "valid": len(good), "invalid": len(bad), "invalid_examples": bad[:5],
                      "families": dict(Counter(r["family"] for r in recs).most_common()),
                      "assay_type": dict(Counter(r["assay_type"] for r in recs)), "classifier_reasons": dict(reasons.most_common()),
                      "out": str(a.out_dir / "smash-motor-records.jsonl.gz")}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
