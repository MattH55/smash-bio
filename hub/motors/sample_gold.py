#!/usr/bin/env python3
"""Draw the Motors gold-set sample (BRIEF_MOTORS.md 1d).

Stratified random sample of about 50 SMASH-MOTOR records per family, strata = primary technique x publication decade,
proportional allocation by largest remainder. Annotation order: kinesin, dynein, myosin_processive, helicase_translocase
first (brief), then the other families in a seeded random order (author decision at Gate 1, E), stored in sample.json.
Fixed seed; the seed, the source file's SHA-256 and the full list go to docs/motors/gold/sample.json. One annotation
stub per record is written from TEMPLATE.yaml with source fields only (record_id, DOI, title): no predicted family or
values, so annotators are not anchored on the pipeline. Existing stubs are never overwritten (they may hold annotations).

    python hub/motors/sample_gold.py [--records PATH] [--families a,b] [--per-family 50] [--seed 20261019]
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import random
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "docs" / "motors" / "gold"
DEFAULT_RECORDS = ROOT / "hub" / "out" / "motor" / "smash-motor-records.jsonl.gz"
FIRST_FAMILIES = ["kinesin", "dynein", "myosin_processive", "helicase_translocase"]


def annotation_order(present: list[str], seed: int) -> list[str]:
    """First four families as in the brief, then the rest in a seeded random order."""
    rest = sorted(f for f in present if f not in FIRST_FAMILIES)
    random.Random(f"{seed}:order").shuffle(rest)
    return [f for f in FIRST_FAMILIES if f in present] + rest


def allocate(sizes: dict, total: int) -> dict:
    """Largest-remainder proportional allocation, capped by stratum size."""
    n = sum(sizes.values())
    if n <= total:
        return dict(sizes)
    quota = {k: total * v / n for k, v in sizes.items()}
    alloc = {k: min(sizes[k], int(q)) for k, q in quota.items()}
    for k in sorted(quota, key=lambda k: (-(quota[k] - int(quota[k])), k)):
        if sum(alloc.values()) >= total:
            break
        if alloc[k] < sizes[k]:
            alloc[k] += 1
    while sum(alloc.values()) < total:  # caps can leave a shortfall: fill from strata with room, largest first
        k = max((k for k in sizes if alloc[k] < sizes[k]), key=lambda k: (sizes[k] - alloc[k], k))
        alloc[k] += 1
    return alloc


def sample(recs: list[dict], families: list[str], per_family: int, seed: int) -> dict:
    out = {}
    for fam in families:
        pool = sorted((r for r in recs if r.get("family") == fam), key=lambda r: r["record_id"])
        strata = defaultdict(list)
        for r in pool:
            y = r["publication"].get("year")
            strata[(r["technique"]["primary"], f"{(y // 10) * 10}s" if y else "unknown")].append(r)
        alloc = allocate({k: len(v) for k, v in strata.items()}, per_family)
        rng = random.Random(f"{seed}:{fam}")
        chosen = []
        for key in sorted(strata):
            chosen += rng.sample(strata[key], alloc[key])
        out[fam] = {"pool": len(pool), "sampled": len(chosen),
                    "strata": {f"{t}|{d}": {"pool": len(strata[(t, d)]), "sampled": alloc[(t, d)]} for t, d in sorted(strata)},
                    "records": [{"record_id": r["record_id"], "smfs_record_id": r.get("smfs_record_id"), "doi": r["publication"].get("doi"), "pmid": r["publication"].get("pmid"),
                                 "title": r["publication"].get("title"), "year": r["publication"].get("year"),
                                 "technique": r["technique"]["primary"]} for r in sorted(chosen, key=lambda r: r["record_id"])]}
    return out


def stub(template: str, rec: dict) -> str:
    def q(s):
        return json.dumps(s or "", ensure_ascii=False)  # a JSON string is a valid YAML scalar
    t = re.sub(r"^record_id: .*$", f"record_id: {rec['record_id']}", template, count=1, flags=re.M)
    t = re.sub(r"^smfs_record_id: .*$", f"smfs_record_id: {rec.get('smfs_record_id') or ''}", t, count=1, flags=re.M)
    t = re.sub(r'^doi: "".*$', f"doi: {q(rec['doi'])}", t, count=1, flags=re.M)
    return re.sub(r'^title: "".*$', f"title: {q(rec['title'])}", t, count=1, flags=re.M)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    ap.add_argument("--families", default="all", help="comma list, or 'all' (first four, then seeded random order)")
    ap.add_argument("--per-family", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20261019)
    a = ap.parse_args()
    raw = a.records.read_bytes()
    # split on "\n" only: str.splitlines() also breaks on U+2028, which occurs inside abstracts
    recs = [json.loads(line) for line in gzip.decompress(raw).decode("utf-8").split("\n") if line.strip()]
    present = sorted({r["family"] for r in recs})
    fams = annotation_order(present, a.seed) if a.families == "all" else [f.strip() for f in a.families.split(",") if f.strip()]
    result = sample(recs, fams, a.per_family, a.seed)
    meta = {"created": dt.date.today().isoformat(), "seed": a.seed, "per_family": a.per_family, "annotation_order": fams,
            "strata": "technique.primary x publication decade, largest-remainder proportional allocation",
            "source": {"file": a.records.name, "sha256": hashlib.sha256(raw).hexdigest(), "n_records": len(recs)},
            "note": "Annotators must not open this file while annotating: it is stratified on the pipeline's family call.",
            "by_family": result}
    GOLD.mkdir(parents=True, exist_ok=True)
    (GOLD / "sample.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    template = (GOLD / "TEMPLATE.yaml").read_text(encoding="utf-8")
    (GOLD / "records").mkdir(exist_ok=True)
    written = kept = 0
    for fam in fams:
        for r in result[fam]["records"]:
            p = GOLD / "records" / f"{r['record_id']}.yaml"
            if p.exists():
                kept += 1
                continue
            p.write_text(stub(template, r), encoding="utf-8")
            written += 1
    print("sample_gold:", {f: f"{v['sampled']}/{v['pool']}" for f, v in result.items()}, f"stubs written {written}, kept {kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
