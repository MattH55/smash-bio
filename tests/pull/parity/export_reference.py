"""Export golden numbers from the reference nucleic pipeline into expected.json.

The reference tree is imported strictly read-only: nothing under
`Meeta Analysis/Simulation Comparison/smash-sim` is written or edited by this
script. It exists so the Rust engine can be pinned to the Python numbers with a
real tolerance check instead of a hand-written guess.

Run:
    python tests/pull/parity/export_reference.py
from the repo root, with smash-sim/nucleic/src importable (the script adds it).
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
NASIM_SRC = os.path.join(
    REPO, "Meeta Analysis", "Simulation Comparison", "smash-sim", "nucleic", "src"
)
if not os.path.isdir(NASIM_SRC):
    sys.exit(f"reference not found at {NASIM_SRC}")
sys.path.insert(0, NASIM_SRC)

from nasim import params  # noqa: E402
from nasim.hairpin import contour_nm, half_force, hairpin_stem, occupancy  # noqa: E402
from nasim.thermo import stem_delta_g  # noqa: E402
from nasim.wlc import extension_nm, integrated_work, kT  # noqa: E402

STEMS = [
    "ATATATATATATATATATAT",
    "ATGCATGCATGCATGCATGC",
    "GCGCGCGCGCGCGCGCGCGC",
    "GCGCGC",
    "GCGCGCGCGC",
]
SALTS = [1.0, 0.15, 0.01]
FORCES = [0.05, 1.0, 5.0, 20.0, 80.0]

out: dict = {"constants": {}, "extension": [], "work": [], "thermo": [],
             "half_force": [], "mean_open": [], "contour": [], "hairpin_stem": []}

out["constants"] = {
    "T_NN_K": params.T_NN_K,
    "SALT_N_PHOSPHATE_SLOPE": params.SALT_N_PHOSPHATE_SLOPE,
    "SS_RISE_NM": params.SS_RISE_NM,
    "SS_LP_NM": params.SS_LP_NM,
    "DS_RISE_NM": params.DS_RISE_NM,
    "KT_PN_NM_298": params.KT_PN_NM_298,
    "dna_nn": {k: list(v) for k, v in params.DNA_NN.items()},
    "rna_nn": {k: list(v) for k, v in params.RNA_NN.items()},
}

for t in (298.15, 310.15):
    for f in FORCES:
        out["extension"].append(
            {"temperature_k": t, "force_pn": f,
             "extension_nm": extension_nm(f, 20.0 * params.SS_RISE_NM, params.SS_LP_NM, t)}
        )

# The 1600-point 0.05-80 pN grid, at the two temperatures the engine uses.
import numpy as np  # noqa: E402

for t in (298.15, 310.15):
    forces = np.linspace(0.05, 80.0, 1600)
    ext = extension_nm(forces, 20.0 * params.SS_RISE_NM, params.SS_LP_NM, t)
    work = integrated_work(forces, ext)
    out["work"].append({
        "temperature_k": t,
        "grid_force_at_1": float(forces[1]),
        "first": float(work[0]),
        "middle": float(work[800]),
        "last": float(work[-1]),
    })

for stem in STEMS:
    for salt in SALTS:
        for poly in ("DNA", "RNA"):
            out["thermo"].append({"stem": stem, "polymer": poly, "na_molar": salt,
                                  **stem_delta_g(stem, polymer=poly, na_molar=salt)})
            hf = half_force(stem, polymer=poly, na_molar=salt,
                            geometry="hairpin", temperature_k=298.15)
            out["half_force"].append({
                "stem": stem, "polymer": poly, "na_molar": salt, "geometry": "hairpin",
                "temperature_k": 298.15, "F_half_pN": hf["F_half_pN"],
                "unfold_cost_pNnm": hf["unfold_cost_pNnm"], "deltaLc_nm": hf["deltaLc_nm"],
            })
            z = half_force(stem, polymer=poly, na_molar=salt,
                           geometry="duplex_unzip", temperature_k=298.15)
            out["half_force"].append({
                "stem": stem, "polymer": poly, "na_molar": salt, "geometry": "duplex_unzip",
                "temperature_k": 298.15, "F_half_pN": z["F_half_pN"],
                "unfold_cost_pNnm": z["unfold_cost_pNnm"], "deltaLc_nm": z["deltaLc_nm"],
            })

for stem in STEMS:
    for geo in ("hairpin", "duplex_unzip"):
        out["contour"].append({"n_open": len(stem), "geometry": geo,
                               "deltaLc_nm": contour_nm(len(stem), geo)})
    for f in (1.0, 5.0, 10.0, 20.0, 40.0):
        # The reference exposes the Boltzmann weights; the engine exposes their
        # mean. Export both so the comparison is unambiguous.
        w = occupancy(stem, f)
        n = np.arange(len(w))
        out["mean_open"].append({
            "stem": stem, "force_pn": f,
            "mean_open": float((w * n).sum()),
            "p_closed": float(w[0]),
            "p_fully_open": float(w[-1]),
            "n_states": len(w),
        })

for t in (298.15, 310.15):
    out["constants"].setdefault("kT", {})[str(t)] = kT(t)

structures = [
    ("GGCCTTTGGCC", "((((...))))"),
    ("GGCATTTGGCC", "((((...))))"),
    ("GGCCTTTGGCCGG", "((((...)))).."),
    ("AGGCTTTGGCT", ".(((...)))"),
    ("GGCTTTGCC", "(((...))"),
    ("AGCT", "(..)"),
]
for seq, dot in structures:
    out["hairpin_stem"].append({"sequence": seq, "dot_bracket": dot,
                                "stem": hairpin_stem(seq, dot)})

path = os.path.join(HERE, "expected.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, sort_keys=True, allow_nan=True)
print(f"wrote {path}")
print(f"cases: extension={len(out['extension'])} thermo={len(out['thermo'])} "
      f"half_force={len(out['half_force'])} mean_open={len(out['mean_open'])}")
