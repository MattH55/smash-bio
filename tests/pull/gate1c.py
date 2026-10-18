"""Gate 1c (docs/pull/VALIDATION.md): reference smash-sim vs the browser engine,
statistically, under protocol G1.

G1: kT 0.5, friction 1, spring k 0.1, dt 0.005, speed 2.0 A/tau, 6000 steps,
seeds 1-30 per engine, proteins 1TIT / 1UBQ / 2GB1 chain A, termini pulled.

* Reference side: the reference Langevin loop (smashsim/pull.py:29-45, same
  order of operations, numpy default_rng(seed) noise) calling the reference
  `energy_and_force`, instrumented to record which native contacts are intact
  every 25 steps (pull.py has no break-step output). Run in a process pool.
* Engine side: `pull-engine` `api::call` op protein_run via the native
  `api_call` example (byte-identical to the wasm build, Gate 5).

Pass = KS p > 0.05 on per-replica peak tension (max of the 5-point smoothed
tension; the reference trace is multiplied by -1 because it records
dot(-spring, direction)) AND Spearman rho >= 0.9 between the two engines'
per-contact mean break steps (never-broken contacts count as 6000).

Usage (repo root): python tests/pull/gate1c.py [--procs 10]
Writes tests/pull/results/gate1c.json; reference runs are cached per seed in
tests/pull/results/gate1c_cache/ so an interrupted run resumes.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SMSIM_SRC = os.path.join(REPO, "Meeta Analysis", "Simulation Comparison", "smash-sim", "src")
sys.path.insert(0, SMSIM_SRC)
sys.path.insert(0, os.path.join(HERE, "parity"))

from smashsim.go_model import build_model, energy_and_force  # noqa: E402
from smashsim.pull import ANCHOR_K  # noqa: E402
from export_protein_reference import parse_pdb  # noqa: E402  (the Rust parser's rules)

FIX = os.path.join(REPO, "pull-engine", "fixtures")
OUT = os.path.join(HERE, "results")
CACHE = os.path.join(OUT, "gate1c_cache")
PROTEINS = ["1TIT", "1UBQ", "2GB1"]
SEEDS = list(range(1, 31))
G1 = dict(speed=2.0, spring_k=0.1, n_steps=6000, dt=0.005, temperature=0.5, friction=1.0)
CONTACT_EVERY = 25


def coords_of(pid: str) -> np.ndarray:
    with open(os.path.join(FIX, pid + ".pdb"), encoding="latin-1") as fh:
        s = parse_pdb(fh.read(), chain="A")
    return np.asarray(s["coords"], dtype=float).reshape(-1, 3)


def smooth5(y: np.ndarray) -> np.ndarray:
    return np.convolve(y, np.ones(5) / 5, mode="same")


def reference_run(args: tuple[str, int]) -> dict:
    pid, seed = args
    path = os.path.join(CACHE, f"{pid}_{seed}.json")
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    coords = coords_of(pid)
    model = build_model(coords.copy())
    ci, cj, r0 = model["ci"], model["cj"], model["contact0"]
    c = G1
    rng = np.random.default_rng(seed)
    x = coords.copy()
    v = np.zeros_like(x)
    origin = x[0].copy()
    direction = x[-1] - x[0]
    direction = direction / max(np.linalg.norm(direction), 1e-8)
    anchor = x[-1].copy()
    force_trace = np.empty(c["n_steps"])
    noise_scale = np.sqrt(2.0 * c["friction"] * c["temperature"] * c["dt"])
    last_intact = np.zeros(len(ci), dtype=int)
    for step in range(c["n_steps"]):  # pull.py:29-45, unchanged order
        f = energy_and_force(x, model)[1]
        f[0] += -ANCHOR_K * (x[0] - origin)
        spring = -c["spring_k"] * (x[-1] - anchor)
        f[-1] += spring
        v += 0.5 * c["dt"] * f
        x += c["dt"] * v
        v += -c["friction"] * v * c["dt"] + noise_scale * rng.normal(size=x.shape)
        f = energy_and_force(x, model)[1]
        f[0] += -ANCHOR_K * (x[0] - origin)
        anchor = anchor + direction * c["speed"] * c["dt"]
        spring = -c["spring_k"] * (x[-1] - anchor)
        f[-1] += spring
        v += 0.5 * c["dt"] * f
        force_trace[step] = float(np.dot(-spring, direction))
        s1 = step + 1
        if s1 % CONTACT_EVERY == 0:
            d = np.linalg.norm(x[cj] - x[ci], axis=1)
            last_intact[d < 1.2 * r0] = s1
    d = np.linalg.norm(x[cj] - x[ci], axis=1)
    intact = d < 1.2 * r0
    brk = [None if ok else int(min(li + CONTACT_EVERY, c["n_steps"])) for ok, li in zip(intact, last_intact)]
    tension = -force_trace
    res = {
        "protein": pid, "seed": seed,
        "peak_tension": float(smooth5(tension).max()),
        "break_step": brk,
        "contacts": [[int(a), int(b)] for a, b in zip(ci, cj)],
    }
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(res, fh)
    return res


def engine_runs(pid: str) -> list[dict]:
    exe = os.path.join(REPO, "pull-engine", "target", "release", "examples", "api_call.exe")
    if not os.path.exists(exe):
        exe = exe[:-4]
    with open(os.path.join(FIX, pid + ".pdb"), encoding="latin-1") as fh:
        pdb = fh.read()
    out = []
    with tempfile.TemporaryDirectory() as td:
        for seed in SEEDS:
            req = {"op": "protein_run", "pdb": pdb, "chain": "A", "mode": "velocity",
                   "speed": G1["speed"], "spring_k": G1["spring_k"], "n_steps": G1["n_steps"],
                   "dt": G1["dt"], "temperature": G1["temperature"], "friction": G1["friction"],
                   "seed": seed, "max_samples": G1["n_steps"], "contact_every": CONTACT_EVERY}
            rp, op = os.path.join(td, "req.json"), os.path.join(td, "out.json")
            with open(rp, "w") as fh:
                json.dump(req, fh)
            subprocess.run([exe, rp, op], check=True, capture_output=True)
            with open(op) as fh:
                r = json.load(fh)
            if "error" in r:
                raise RuntimeError(r["error"])
            t = np.asarray(r["tension"], dtype=float)
            out.append({
                "seed": seed,
                "peak_tension": float(smooth5(t).max()),
                "break_step": [b[2] for b in r["contact_breaks"]],
                "contacts": [[b[0], b[1]] for b in r["contact_breaks"]],
            })
    return out


def main() -> None:
    from scipy.stats import ks_2samp, spearmanr

    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=10)
    a = ap.parse_args()
    jobs = [(p, s) for p in PROTEINS for s in SEEDS]
    with ProcessPoolExecutor(a.procs) as ex:
        ref = list(ex.map(reference_run, jobs))
    summary = {"gate": "1c", "protocol": G1, "seeds": SEEDS, "proteins": {}}
    all_pass = True
    for pid in PROTEINS:
        r = [x for x in ref if x["protein"] == pid]
        e = engine_runs(pid)
        assert r[0]["contacts"] == e[0]["contacts"], "contact maps differ"
        n = G1["n_steps"]
        mean_b = lambda runs: np.mean([[n if b is None else b for b in x["break_step"]] for x in runs], axis=0)
        mr, me = mean_b(r), mean_b(e)
        rho = float(spearmanr(mr, me).statistic)
        pr = [x["peak_tension"] for x in r]
        pe = [x["peak_tension"] for x in e]
        ks = ks_2samp(pr, pe)
        ok = bool(ks.pvalue > 0.05 and rho >= 0.9)
        all_pass &= ok
        summary["proteins"][pid] = {
            "n_contacts": len(mr),
            "peak_tension_reference": pr, "peak_tension_engine": pe,
            "peak_mean_reference": float(np.mean(pr)), "peak_mean_engine": float(np.mean(pe)),
            "ks_statistic": float(ks.statistic), "ks_p": float(ks.pvalue),
            "spearman_rho_break_order": rho, "pass": ok,
        }
        print(f"{pid}: peak ref {np.mean(pr):.3f}+-{np.std(pr):.3f} eng {np.mean(pe):.3f}+-{np.std(pe):.3f} "
              f"KS p={ks.pvalue:.3f}  rho={rho:.3f}  {'PASS' if ok else 'FAIL'}")
    summary["pass"] = all_pass
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "gate1c.json"), "w") as fh:
        json.dump(summary, fh, indent=1)


if __name__ == "__main__":
    main()
