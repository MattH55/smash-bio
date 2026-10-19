#!/usr/bin/env python3
"""Gate-1 review list: the least certain SMASH-MOTOR family calls, for the author to check.

Reads the MOTOR records (their `classification.certainty` is stored on each record) and writes
docs/motors/REVIEW_CLASSIFICATION.md: per family the N records of lowest certainty, then every gliding/ensemble record.

    python hub/motors/review_list.py [--motor PATH] [-n 20]
"""
from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "hub" / "out" / "motor" / "smash-motor-records.jsonl.gz"
OUT = ROOT / "docs" / "motors" / "REVIEW_CLASSIFICATION.md"


def md(s: str) -> str:
    return (s or "").replace("|", "/").replace("\n", " ")


def row(r: dict) -> str:
    c = r["classification"]
    hits = ", ".join(f"{k} {v}" for k, v in sorted(c["family_hits"].items(), key=lambda kv: -kv[1]))
    p = r["publication"]
    return (f"| {c['certainty']:.2f} | {r['record_id']} | {r['smfs_record_id']} | {p.get('year') or ''} | {r['technique']['primary']} | "
            f"{c['route']} | {hits} | {md(p.get('title'))[:130]} |")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--motor", type=Path, default=DEFAULT)
    ap.add_argument("-n", type=int, default=20)
    a = ap.parse_args()
    recs = [json.loads(x) for x in gzip.decompress(a.motor.read_bytes()).decode("utf-8").split("\n") if x.strip()]
    by = defaultdict(list)
    for r in recs:
        by[r["family"]].append(r)
    head = "| certainty | MOTOR | SMFS | year | technique | route | family hits | title |\n| ---: | --- | --- | --- | --- | --- | --- | --- |"
    lines = ["# SMASH-MOTOR classification: records for author review (Gate 1)", "",
             f"From `{a.motor.name}`. Certainty = route weight (specific entity 1.0, generic entity 0.7, title only 0.45) x share of "
             "the top family among all family hits. It measures how unambiguously the family resolved, not whether the paper is a "
             "motor study; the gold set measures that. Lowest first.", ""]
    for fam in sorted(by, key=lambda f: -len(by[f])):
        rs = sorted(by[fam], key=lambda r: (r["classification"]["certainty"], r["record_id"]))[: a.n]
        lines += [f"## {fam} ({len(by[fam])} records; {len(rs)} least certain shown)", "", head] + [row(r) for r in rs] + [""]
    gl = [r for r in recs if r["assay_type"] == "gliding_or_ensemble"]
    lines += [f"## Gliding / ensemble assays ({len(gl)} records, included and labelled)", "", head] + [row(r) for r in gl] + [""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"review_list: {len(recs)} records in {len(by)} families -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
