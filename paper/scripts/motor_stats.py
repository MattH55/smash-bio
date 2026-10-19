#!/usr/bin/env python3
"""SMASH-MOTOR counts from the release files (BRIEF_MOTORS.md 1c), in the style of corpus_stats.py.

Reads the MOTOR record file (default hub/out/motor/smash-motor-records.jsonl.gz until Phase 4 publishes it under
website/downloads/motor/) and prints one JSON document: records per family x technique, assay type, linked deposits,
raw traces, abstract-only share (from the linked SMASH-BIO record's curation level, via --smfs) and classification
confidence. Read-only.

    python -I paper/scripts/motor_stats.py [--motor PATH] [--smfs PATH] > paper/out/motor_stats.json
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: Path) -> list[dict]:
    # split on "\n" only: str.splitlines() also breaks on U+2028, which occurs inside abstracts
    return [json.loads(x) for x in gzip.decompress(path.read_bytes()).decode("utf-8").split("\n") if x.strip()]


def pct(n: int, d: int) -> float:
    return round(100 * n / d, 1) if d else 0.0


def stats(motor: list[dict], smfs_level: dict) -> dict:
    da = lambda r: r.get("data_availability") or {}  # noqa: E731
    abstract_only = lambda r: smfs_level.get(r["smfs_record_id"]) == "auto_abstract"  # noqa: E731
    out: dict = {
        "n_motor_records": len(motor),
        "n_distinct_smfs_records": len({r["smfs_record_id"] for r in motor}),
        "assay_type": dict(Counter(r["assay_type"] for r in motor)),
        "n_with_dataset": sum(bool(da(r).get("has_linked_dataset")) for r in motor),
        "n_with_raw_traces": sum(bool(da(r).get("raw_traces_available")) for r in motor),
        "n_abstract_only": sum(abstract_only(r) for r in motor),
        "n_no_fulltext": sum(not da(r).get("fulltext_checked") for r in motor),
        "curation_levels": dict(Counter(r["curation"]["level"] for r in motor)),
        "classification_route": dict(Counter(r["classification"]["route"] for r in motor)),
        "family_confidence": dict(Counter(r["evidence"]["family"]["confidence"] for r in motor)),
        "n_ambiguous_family": sum(len(r["classification"]["family_hits"]) > 1 for r in motor),
    }
    out["pct_abstract_only"] = pct(out["n_abstract_only"], len(motor))
    out["experiment_type"] = dict(Counter(r.get("experiment_type", "(not yet known)") for r in motor).most_common())
    by_basis = defaultdict(list)
    for r in motor:
        by_basis[r["fair_completeness"]["basis"]].append(r["fair_completeness"])
    def mean(vals: list) -> float | None:  # None when no field of that section is required for this basis
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None
    out["completeness_by_basis"] = {b: {"n": len(L), **{s: mean([x[s] for x in L]) for s in ("hardware", "assay", "construct", "solution", "overall")}}
                                    for b, L in sorted(by_basis.items())}
    fam = {}
    for f, n in Counter(r["family"] for r in motor).most_common():
        rs = [r for r in motor if r["family"] == f]
        fam[f] = {"records": n, "by_technique": dict(Counter(r["technique"]["primary"] for r in rs).most_common()),
                  "gliding_or_ensemble": sum(r["assay_type"] == "gliding_or_ensemble" for r in rs),
                  "with_dataset": sum(bool(da(r).get("has_linked_dataset")) for r in rs),
                  "raw_traces": sum(bool(da(r).get("raw_traces_available")) for r in rs),
                  "pct_abstract_only": pct(sum(abstract_only(r) for r in rs), n)}
    out["by_family"] = fam
    tx = defaultdict(Counter)
    for r in motor:
        tx[r["technique"]["primary"]][r["family"]] += 1
    out["technique_x_family"] = {t: dict(c.most_common()) for t, c in sorted(tx.items(), key=lambda kv: -sum(kv[1].values()))}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--motor", type=Path, default=ROOT / "hub" / "out" / "motor" / "smash-motor-records.jsonl.gz")
    ap.add_argument("--smfs", type=Path, default=ROOT / "website" / "downloads" / "smash-smfs-records.jsonl.gz")
    a = ap.parse_args()
    smfs_level = {r["record_id"]: r["curation"]["level"] for r in read(a.smfs)}
    s = stats(read(a.motor), smfs_level)
    s["source"] = {"motor": a.motor.name, "smfs": a.smfs.name}
    json.dump(s, sys.stdout, indent=1, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
