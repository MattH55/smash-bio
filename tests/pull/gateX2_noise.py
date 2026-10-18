"""Diagnostic for Gate X2 (does not change its verdict): how well do two
independent 20-replica sets from the SAME engine agree on per-contact mean break
steps under protocol G1? Engine seeds 21-40 vs 1-20, OpenMM seeds 21-40 vs 1-20.
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "website", "pull", "export"))
import openmm as mm  # noqa: E402
import openmm_go as og  # noqa: E402
import smashpull as sp  # noqa: E402

N = 6000
text = open(os.path.join(REPO, "pull-engine", "fixtures", "1UBQ.pdb"), encoding="latin-1").read()
atoms, _, _ = sp.parse_atoms(text, "A", None)
_, xyz, _ = sp.ca_trace(atoms)
contacts = sp.native_contacts(xyz)
exe = os.path.join(REPO, "pull-engine", "target", "release", "examples", "api_call.exe")


def engine(seeds, td):
    out = []
    for s in seeds:
        req = {"op": "protein_run", "pdb": text, "chain": "A", "speed": 2.0, "spring_k": 0.1, "n_steps": N, "dt": 0.005,
               "temperature": 0.5, "friction": 1.0, "seed": s, "max_samples": 600, "contact_every": 25}
        json.dump(req, open(os.path.join(td, "r.json"), "w"))
        subprocess.run([exe, os.path.join(td, "r.json"), os.path.join(td, "o.json")], check=True, capture_output=True)
        out.append([N if b[2] is None else b[2] for b in json.load(open(os.path.join(td, "o.json")))["contact_breaks"]])
    return np.array(out)


def openmm(seeds, td):
    cfg = dict(mode="velocity", speed=2.0, spring_k=0.1, dt=0.005, kT=0.5, gamma=1.0, n_steps=N, sample_every=10, contact_every=25, lj_10_12=False)
    plat = mm.Platform.getPlatformByName("CPU")
    return np.array([[N if b is None else b for b in og.run_one(xyz, contacts, 0, len(xyz) - 1, cfg, s, plat, td, f"s{s}")["contact_break_step"]] for s in seeds])


with tempfile.TemporaryDirectory() as td:
    e1, e2 = engine(range(1, 21), td), engine(range(21, 41), td)
    o1, o2 = openmm(range(1, 21), td), openmm(range(21, 41), td)
r = lambda a, b: float(spearmanr(a.mean(0), b.mean(0)).statistic)
never = float(np.mean(np.concatenate([e1, e2]) == N))
res = {"engine_vs_engine": r(e1, e2), "openmm_vs_openmm": r(o1, o2), "engine_vs_openmm_40": r(np.vstack([e1, e2]), np.vstack([o1, o2])),
       "fraction_contacts_never_broken": never}
json.dump(res, open(os.path.join(HERE, "results", "gateX2_noise.json"), "w"), indent=1)
print(res)
