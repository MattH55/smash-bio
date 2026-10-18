"""Gate X1: the OpenMM port (website/pull/export/openmm_go.py) reproduces the
engine's Cα Gō energy and forces. Run with the OpenMM environment's python:
    python tests/pull/gateX1.py
Writes tests/pull/results/gateX1.json.
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "website", "pull", "export"))
import openmm as mm  # noqa: E402
import openmm_go as og  # noqa: E402

EXE = os.path.join(REPO, "pull-engine", "target", "release", "examples", "energy_dump.exe")
out = {"gate": "X1", "proteins": {}}
ok_all = True
for pid in ("1TIT", "1UBQ", "2GB1"):
    ref = json.loads(subprocess.run([EXE, os.path.join(REPO, "pull-engine", "fixtures", pid + ".pdb"), "A"], capture_output=True, text=True, check=True).stdout)
    nat = np.array(ref["native"]).reshape(-1, 3)
    sysm, _ = og.build([tuple(p) for p in nat])
    ctx = mm.Context(sysm, mm.VerletIntegrator(0.001), mm.Platform.getPlatformByName("Reference"))
    worst_e, worst_f = 0.0, 0.0
    for c in ref["confs"]:
        x = np.array(c["coords"]).reshape(-1, 3)
        ctx.setPositions([mm.Vec3(*(p * 0.1)) for p in x])
        st = ctx.getState(getEnergy=True, getForces=True, groups={0})
        e = st.getPotentialEnergy().value_in_unit(mm.unit.kilojoule_per_mole)  # = ε
        f = st.getForces(asNumpy=True).value_in_unit(mm.unit.kilojoule_per_mole / mm.unit.nanometer) / 10.0  # → ε/Å
        fe = np.array(c["force"]).reshape(-1, 3)
        rel_e = abs(e - c["energy"]) / max(1.0, abs(c["energy"]))
        rel_f = float(np.abs(f - fe).max() / max(1e-12, np.abs(fe).max()))
        worst_e, worst_f = max(worst_e, rel_e), max(worst_f, rel_f)
    ok = worst_e <= 1e-6 and worst_f <= 1e-4
    ok_all &= ok
    out["proteins"][pid] = {"conformations": len(ref["confs"]), "max_rel_energy_err": worst_e, "max_rel_force_err": worst_f, "pass": ok}
    print(f"{pid}: {len(ref['confs'])} conformations, energy rel err {worst_e:.2e}, force rel err {worst_f:.2e} -> {'PASS' if ok else 'FAIL'}")
out["pass"] = ok_all
with open(os.path.join(HERE, "results", "gateX1.json"), "w") as fh:
    json.dump(out, fh, indent=1)
