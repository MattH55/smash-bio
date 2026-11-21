#!/usr/bin/env python3
"""Generate Tables S1 and S2 (BRIEF.md section 4) into out/supplementary.md.

S1  Table 3 field -> schema path. The mapping itself is the `T3` array the site renders on schema.html
    (website/js/schema.js); the script parses that array and then checks every path against
    website/schema/smash-smfs-record.schema.json, so a stale or misspelt path fails the build.
S2  Observable vocabulary with canonical units, from website/schema/smash-smfs-results.schema.json.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
SITE = PAPER.parent / "website"
RECORD = json.loads((SITE / "schema" / "smash-smfs-record.schema.json").read_text(encoding="utf-8"))
RESULTS = json.loads((SITE / "schema" / "smash-smfs-results.schema.json").read_text(encoding="utf-8"))


def deref(node: dict, root: dict) -> dict:
    while "$ref" in node:
        ref = node["$ref"]
        if not ref.startswith("#/"):
            return {}
        cur = root
        for part in ref[2:].split("/"):
            cur = cur[part]
        node = cur
    return node


def resolve(path: str) -> str:
    """'ok' if every segment exists, 'partial' if the schema stops describing properties part-way, else 'missing'."""
    path = re.sub(r"\s*\(.*?\)", "", path).replace("[]", "").strip(". *")
    segs = [s for s in path.split(".") if s]
    node: dict = RECORD
    if segs and segs[0] not in RECORD["properties"]:
        segs = ["biological_system"] + segs  # shorthand such as entities[].sequence, cytoskeleton.*
    for i, seg in enumerate(segs):
        node = deref(node, RECORD)
        if "items" in node:
            node = deref(node["items"], RECORD)
        props = node.get("properties")
        if props is None:
            return "partial" if i > 0 else "missing"
        if seg.startswith("_at_") or seg.startswith("/"):
            return "ok"
        if seg not in props:
            return "missing"
        node = props[seg]
    return "ok"


def parse_t3() -> list[list[str]]:
    js = (SITE / "js" / "schema.js").read_text(encoding="utf-8")
    block = re.search(r"const T3 = (\[.*?\n  \]);", js, re.S).group(1)
    return ast.literal_eval(block)


def table_s1() -> tuple[str, dict]:
    rows = parse_t3()
    status = {"ok": 0, "partial": 0, "missing": 0}
    lines = ["**Table S1.** Mapping from the fields of Table 3 of Halma et al. (2025) to SMASH-BIO schema paths "
             "(schema v3.1.0). *Schema check*: yes = every path segment exists in the record schema; partial = the path is valid down "
             "to a free-form object whose inner keys the schema does not enumerate. Generated from "
             "`website/js/schema.js` and validated against `smash-smfs-record.schema.json`.", "",
             "| Table 3 section | Table 3 field | Schema path | Applies to | Schema check |",
             "| --- | --- | --- | --- | :-: |"]
    for sec, field, path, applies in rows:
        # one cell may hold several comma- or slash-separated paths; the cell passes if all of them do
        parts = [p for p in re.split(r",\s*|\s+/\s+", path) if p and not p.startswith(("→", "(")) and "TraceSet" not in p]
        full: list[str] = []
        for p in parts:  # shorthand: "a.b.x_at_source / _at_objective" and "a.b.c / d" mean sibling keys
            if full and "." not in p:
                parent, _, last = full[-1].rpartition(".")
                p = f"{parent}.{last.split('_at_')[0]}{p}" if p.startswith("_at_") else f"{parent}.{p}"
            full.append(p)
        results = [resolve(p) for p in full] or ["ok"]
        worst = "missing" if "missing" in results else ("partial" if "partial" in results else "ok")
        status[worst] += 1
        mark = {"ok": "yes", "partial": "partial", "missing": "NO"}[worst]
        lines.append(f"| {sec} | {field} | `{path}` | {applies} | {mark} |")
    return "\n".join(lines), status


def table_s2() -> str:
    units = RESULTS["$defs"]["ObservableUnits"]["const"]
    enum = RESULTS["$defs"]["Observable"]["enum"]
    lines = ["**Table S2.** Observable vocabulary of the results schema (`Result.quantity`) with canonical units. "
             "Values are stored in the canonical unit; `other` carries a free-text label.", "",
             "| Observable | Canonical unit |", "| --- | --- |"]
    for q in enum:
        lines.append(f"| `{q}` | {units.get(q, '— (no fixed unit)')} |")
    missing = set(units) - set(enum)
    assert not missing, f"units defined for observables not in the enum: {missing}"
    return "\n".join(lines)


def main() -> int:
    s1, status = table_s1()
    out = PAPER / "out" / "supplementary.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("# Supplementary tables\n\n" + s1 + "\n\n" + table_s2() + "\n", encoding="utf-8", newline="\n")
    print(f"make_supplementary: S1 {len(parse_t3())} rows (schema check {status}); S2 "
          f"{len(RESULTS['$defs']['Observable']['enum'])} observables -> {out.relative_to(PAPER.parent)}")
    return 1 if status["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
