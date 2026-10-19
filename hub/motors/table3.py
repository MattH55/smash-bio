#!/usr/bin/env python3
"""Table 3 for motor experiments: load the grid, check its paths, render it, score completeness.

The grid (hub/motors/table3_motor.yaml) follows Table 3 of the FAIR optical-tweezers guidelines: sections x fields x
experiment types, each cell R (required), O (optional) or - (not applicable). Completeness for a record is the fraction
of R fields that are filled for the record's experiment type, per section and overall, reading motor:* paths from the
MOTOR record and smfs:* paths from the linked SMASH-BIO record. Without an experiment type, only fields that are R in
every column count (basis "core").

    python hub/motors/table3.py      # writes docs/motors/TABLE3_MOTOR.md
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GRID = HERE / "table3_motor.yaml"
SECTIONS = ("hardware", "assay", "construct", "solution")


@lru_cache(maxsize=1)
def grid() -> dict:
    g = yaml.safe_load(GRID.read_text(encoding="utf-8"))
    cols = list(g["columns"])
    rows = []
    for sec in SECTIONS:
        for r in g["rows"][sec]:
            cells = r["cells"].split()
            if len(cells) != len(cols) or set(cells) - {"R", "O", "-"}:
                raise ValueError(f"bad cells for {r['label']}: {r['cells']}")
            rows.append({"section": sec, "label": r["label"], "path": r["path"], "cells": dict(zip(cols, cells))})
    obs = [{"quantity": o["quantity"], "cells": dict(zip(cols, o["cells"].split()))} for o in g.get("observables") or []]
    return {"columns": g["columns"], "rows": rows, "observables": obs}


def experiment_types() -> list[str]:
    return list(grid()["columns"])


def _get(d: dict | None, dotted: str):
    for k in dotted.split("."):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def filled(v) -> bool:
    return v not in (None, "", [], {}) and not (isinstance(v, dict) and v.get("value") is None and "unit" in v and not v.get("note"))


def value(path: str, motor: dict, smfs: dict | None):
    """First filled value among the alternatives of a path ("motor:a.b|smfs:c.d")."""
    for alt in path.split("|"):
        src, _, p = alt.partition(":")
        v = _get(motor if src == "motor" else smfs, p)
        if filled(v):
            return v
    return None


def completeness(motor: dict, smfs: dict | None) -> dict:
    et = motor.get("experiment_type")
    use = (lambda r: r["cells"].get(et) == "R") if et in grid()["columns"] else (lambda r: all(c == "R" for c in r["cells"].values()))
    out, n_all, f_all = {}, 0, 0
    for sec in SECTIONS:
        rows = [r for r in grid()["rows"] if r["section"] == sec and use(r)]
        f = sum(filled(value(r["path"], motor, smfs)) for r in rows)
        out[sec] = round(f / len(rows), 2) if rows else None
        n_all += len(rows)
        f_all += f
    out["overall"] = round(f_all / n_all, 2) if n_all else None
    out["basis"] = et if et in grid()["columns"] else "core"
    return out


def check_paths() -> list[str]:
    """Paths that do not resolve in the MOTOR or SMFS record schema."""
    schema_dir = ROOT / "website" / "schema"
    motor = json.loads((schema_dir / "motor" / "smash-motor-record.schema.json").read_text(encoding="utf-8"))
    smfs = json.loads((schema_dir / "smash-smfs-record.schema.json").read_text(encoding="utf-8"))

    def deref(schema: dict, node: dict) -> dict:
        while "$ref" in node and node["$ref"].startswith("#/"):
            cur = schema
            for part in node["$ref"][2:].split("/"):
                cur = cur[part]
            node = cur
        return node

    def resolve(schema: dict, dotted: str) -> bool:
        node = schema
        for k in dotted.split("."):
            props = deref(schema, node).get("properties")
            if not props or k not in props:
                return False
            node = props[k]
        return True

    bad = []
    for r in grid()["rows"]:
        for alt in r["path"].split("|"):
            src, _, p = alt.partition(":")
            if src not in ("motor", "smfs") or not resolve(motor if src == "motor" else smfs, p):
                bad.append(alt)
    return bad


def render() -> str:
    g = grid()
    cols = list(g["columns"])
    short = {"optical_trap_single_bead": "OT single bead", "optical_trap_three_bead": "OT three-bead",
             "optical_trap_dna_tether": "OT nucleic-acid tether", "magnetic_tweezers": "Magnetic tweezers",
             "flow_stretching": "Flow / curtains", "sm_fluorescence": "SM fluorescence", "gliding_ensemble": "Gliding / ensemble"}
    head = "| Section | Field | Path | " + " | ".join(short.get(c, c) for c in cols) + " |"
    sep = "| --- | --- | --- | " + " | ".join(":-:" for _ in cols) + " |"
    lines = ["# Table 3 for motor experiments (SMASH-MOTOR)", "",
             "Same structure as Table 3 of the FAIR optical-tweezers guidelines: metadata fields grouped as hardware, assay, "
             "construct and solution, with one column per experiment type. **R** required, **O** optional, **–** not applicable. "
             "`motor:` = SMASH-MOTOR record field, `smfs:` = field of the linked SMASH-BIO record. Generated from "
             "`hub/motors/table3_motor.yaml` (a proposal for the author to edit). Completeness scores count the R cells of a "
             "record's experiment type.", "", "Experiment types:", ""]
    lines += [f"- **{short.get(c, c)}** (`{c}`): {d}" for c, d in g["columns"].items()]
    lines += ["", head, sep]
    for r in g["rows"]:
        lines.append(f"| {r['section']} | {r['label']} | `{r['path']}` | " + " | ".join(r["cells"][c].replace("-", "–") for c in cols) + " |")
    lines += ["", "Observables each experiment type usually reports (**E**; informational, not scored):", "",
              "| Observable | " + " | ".join(short.get(c, c) for c in cols) + " |", "| --- | " + " | ".join(":-:" for _ in cols) + " |"]
    for o in g["observables"]:
        lines.append(f"| `{o['quantity']}` | " + " | ".join(o["cells"][c].replace("-", "–") for c in cols) + " |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    bad = check_paths()
    if bad:
        raise SystemExit(f"unresolved paths: {bad}")
    out = ROOT / "docs" / "motors" / "TABLE3_MOTOR.md"
    out.write_text(render(), encoding="utf-8")
    print(f"table3: {len(grid()['rows'])} fields x {len(grid()['columns'])} experiment types -> {out.relative_to(ROOT)}")
