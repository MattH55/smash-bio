"""Gate X2: OpenMM port of the Cα model vs the engine, protocol G1, 1UBQ chain A,
20 replicas each. Pass: KS p > 0.05 on peak tension and Spearman ρ >= 0.9
between per-contact mean break steps. Writes tests/pull/results/gateX2.json.
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.stats import ks_2samp, spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "website", "pull", "export"))
import openmm as mm  # noqa: E402
import openmm_go as og  # noqa: E402
import smashpull as sp  # noqa: E402

G1 = dict(speed=2.0, spring_k=0.1, n_steps=6000, dt=0.005, kT=0.5, gamma=1.0)
SEEDS = list(range(1, 21))
pdb_path = os.path.join(REPO, "pull-engine", "fixtures", "1UBQ.pdb")
text = open(pdb_path, encoding="latin-1").read()
atoms, _, _ = sp.parse_atoms(text, "A", None)
res, xyz, _ = sp.ca_trace(atoms)
contacts = sp.native_contacts(xyz)
n, nsteps = len(xyz), G1["n_steps"]
plat = mm.Platform.getPlatformByName("CPU")

omm_peaks, omm_breaks = [], []
with tempfile.TemporaryDirectory() as td:
    cfg = dict(mode="velocity", speed=G1["speed"], spring_k=G1["spring_k"], dt=G1["dt"], kT=G1["kT"], gamma=G1["gamma"],
               n_steps=nsteps, sample_every=1, contact_every=25, lj_10_12=False)
    for s in SEEDS:
        r = og.run_one(xyz, contacts, 0, n - 1, cfg, s, plat, td, f"s{s}")
        omm_peaks.append(r["peak_tension_eps_per_A"])
        omm_breaks.append([nsteps if b is None else b for b in r["contact_break_step"]])
    exe = os.path.join(REPO, "pull-engine", "target", "release", "examples", "api_call.exe")
    eng_peaks, eng_breaks = [], []
    for s in SEEDS:
        req = {"op": "protein_run", "pdb": text, "chain": "A", "speed": G1["speed"], "spring_k": G1["spring_k"], "n_steps": nsteps,
               "dt": G1["dt"], "temperature": G1["kT"], "friction": G1["gamma"], "seed": s, "max_samples": nsteps, "contact_every": 25}
        rp, op = os.path.join(td, "r.json"), os.path.join(td, "o.json")
        json.dump(req, open(rp, "w"))
        subprocess.run([exe, rp, op], check=True, capture_output=True)
        r = json.load(open(op))
        t = np.array(r["tension"])
        eng_peaks.append(float(np.convolve(t, np.ones(5) / 5, mode="same").max()))
        eng_breaks.append([nsteps if b[2] is None else b[2] for b in r["contact_breaks"]])
        assert [[b[0], b[1]] for b in r["contact_breaks"]] == [[c[0], c[1]] for c in contacts], "contact maps differ"
ks = ks_2samp(omm_peaks, eng_peaks)
rho = float(spearmanr(np.mean(omm_breaks, 0), np.mean(eng_breaks, 0)).statistic)
ok = bool(ks.pvalue > 0.05 and rho >= 0.9)
res_ = {"gate": "X2", "protocol": G1, "seeds": SEEDS, "peak_openmm": omm_peaks, "peak_engine": eng_peaks,
        "mean_openmm": float(np.mean(omm_peaks)), "mean_engine": float(np.mean(eng_peaks)),
        "ks_p": float(ks.pvalue), "spearman_rho": rho, "pass": ok}
json.dump(res_, open(os.path.join(HERE, "results", "gateX2.json"), "w"), indent=1)
print(f"peak OpenMM {np.mean(omm_peaks):.3f}±{np.std(omm_peaks):.3f}  engine {np.mean(eng_peaks):.3f}±{np.std(eng_peaks):.3f}  "
      f"KS p={ks.pvalue:.3f}  rho={rho:.3f}  -> {'PASS' if ok else 'FAIL'}")
