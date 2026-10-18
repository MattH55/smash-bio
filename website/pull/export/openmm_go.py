#!/usr/bin/env python3
"""SMASH-Pull Cα structure-based (Gō) pulling model in OpenMM.

The same Hamiltonian as the SMASH-Pull browser engine (and the smash-sim
reference), so runs can go to GPUs, slower speeds and more replicas.

Unit map (model → OpenMM): 1 Å = 0.1 nm, ε = 1 kJ/mol, bead mass 1 u. Hence
τ = 0.1 ps and kT = 0.5 ε ↔ 60.14 K; a speed of 1 Å/τ = 1 nm/ps. Outputs are
reported back in MODEL units (Å, τ, ε/Å). They are not piconewtons: the model
has no force calibration (see https://smash-bio.org/pull/about.html).

Integrator: an OpenMM CustomIntegrator that reproduces the engine's step
(velocity Verlet, friction + noise between the half kicks, pulling anchor moved
before the second force evaluation), so trajectories differ from the browser
engine only through the random numbers (validation gate X2).

Usage:
    python prepare.py pull_setup.json         # once: fetch + align structure
    python openmm_go.py pull_setup.json [--platform CUDA] [--replicas 10]
                                        [--speeds 0.05,0.1] [--forces 5,6]
                                        [--dcd-every 2000] [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashpull as sp  # noqa: E402

try:
    import openmm as mm
    from openmm import app
except ImportError:
    raise SystemExit("OpenMM is required: pip install openmm   (or conda install -c conda-forge openmm)")

A2NM = 0.1          # Å → nm
EPS = 1.0           # ε in kJ/mol
TAU_PS = 0.1        # τ in ps
EPS_PER_A_TO_KJ_NM = 10.0  # 1 ε/Å = 10 kJ/mol/nm


def build(xyz_A, *, lj_10_12=False, exclude_res=None):
    """OpenMM System for the Cα Gō model of native coordinates xyz_A (list of (x,y,z) in Å).

    exclude_res: optional boolean mask; native contacts touching those residues
    are dropped (pLDDT mask) but stay excluded from the non-native repulsion,
    exactly as in the engine.
    """
    G = sp.GO
    n = len(xyz_A)
    sysm = mm.System()
    for _ in range(n):
        sysm.addParticle(1.0)
    # bonds: engine V = K (r-r0)^2  ↔  OpenMM ½ k (r-r0)^2 with k = 2K, in kJ/mol/nm²
    bonds = mm.HarmonicBondForce()
    for i in range(n - 1):
        r0 = math.dist(xyz_A[i], xyz_A[i + 1]) * A2NM
        bonds.addBond(i, i + 1, r0, 2 * G["BOND_K"] * EPS / A2NM ** 2)
    angles = mm.HarmonicAngleForce()
    for i in range(n - 2):
        angles.addAngle(i, i + 1, i + 2, sp.angle(xyz_A[i], xyz_A[i + 1], xyz_A[i + 2]), 2 * G["ANGLE_K"] * EPS)
    # dihedrals: (1 - cos d) + ½(1 - cos 3d), d = φ - φ0  ↔  k (1 + cos(nφ - θ)) with θ = nφ0 + π
    tors = mm.PeriodicTorsionForce()
    for i in range(n - 3):
        phi0 = sp.dihedral(xyz_A[i], xyz_A[i + 1], xyz_A[i + 2], xyz_A[i + 3])
        tors.addTorsion(i, i + 1, i + 2, i + 3, 1, phi0 + math.pi, 1.0 * EPS)
        tors.addTorsion(i, i + 1, i + 2, i + 3, 3, 3 * phi0 + math.pi, 0.5 * EPS)
    contacts = sp.native_contacts(xyz_A)
    expr = "eps*(5*(r0/r)^12 - 6*(r0/r)^10)" if lj_10_12 else "eps*((r0/r)^12 - 2*(r0/r)^6)"
    nat = mm.CustomBondForce(expr)
    nat.addGlobalParameter("eps", EPS)
    nat.addPerBondParameter("r0")
    kept = []
    for i, j, d in contacts:
        if exclude_res is not None and (exclude_res[i] or exclude_res[j]):
            continue
        nat.addBond(i, j, [d * A2NM])
        kept.append((i, j, d))
    rep = mm.CustomNonbondedForce("eps*(sig/r)^12")
    rep.addGlobalParameter("eps", EPS)
    rep.addGlobalParameter("sig", G["NONNATIVE_SIGMA"] * A2NM)
    rep.setNonbondedMethod(mm.CustomNonbondedForce.CutoffNonPeriodic)
    rep.setCutoffDistance(G["NONNATIVE_CUTOFF"] * A2NM)
    rep.setUseSwitchingFunction(False)
    rep.setUseLongRangeCorrection(False)
    for _ in range(n):
        rep.addParticle([])
    for i in range(n):  # engine evaluates non-native pairs only for j - i >= SEQ_SEP
        for j in range(i + 1, min(n, i + G["SEQ_SEP"])):
            rep.addExclusion(i, j)
    for i, j, _ in contacts:  # all native pairs, including pLDDT-masked ones
        rep.addExclusion(i, j)
    for k, f in enumerate([bonds, angles, tors, nat, rep]):
        f.setForceGroup(0)
        sysm.addForce(f)
    return sysm, kept


def add_pulling(sysm, xyz_A, ia, ip, mode, *, spring_k=0.1, force=0.0):
    """Anchor restraint (group 1) and pulling (group 2). Returns the unit pull direction."""
    G = sp.GO
    p0 = np.array(xyz_A[ia]) * A2NM
    p1 = np.array(xyz_A[ip]) * A2NM
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    anc = mm.CustomExternalForce("0.5*ka*((x-x0)^2+(y-y0)^2+(z-z0)^2)")
    anc.addGlobalParameter("ka", G["ANCHOR_K"] * EPS / A2NM ** 2)
    for nm_ in ("x0", "y0", "z0"):
        anc.addPerParticleParameter(nm_)
    anc.addParticle(ia, list(p0))
    anc.setForceGroup(1)
    sysm.addForce(anc)
    if mode == "velocity":
        f = mm.CustomExternalForce("0.5*kp*((x-px-dx*s)^2+(y-py-dy*s)^2+(z-pz-dz*s)^2)")
        f.addGlobalParameter("kp", spring_k * EPS / A2NM ** 2)
        f.addGlobalParameter("s", 0.0)
    else:
        f = mm.CustomExternalForce("-fc*(dx*x+dy*y+dz*z)")
        f.addGlobalParameter("fc", force * EPS_PER_A_TO_KJ_NM)
    for nm_, v in zip(("px", "py", "pz"), p1):
        f.addGlobalParameter(nm_, float(v))
    for nm_, v in zip(("dx", "dy", "dz"), d):
        f.addGlobalParameter(nm_, float(v))
    f.addParticle(ip, [])
    f.setForceGroup(2)
    sysm.addForce(f)
    return d


def engine_integrator(dt_tau, kT_eps, gamma_per_tau, speed_A_per_tau, seed):
    """The engine's step, as a CustomIntegrator (OpenMM units: ps, kJ/mol, nm)."""
    dt = dt_tau * TAU_PS
    it = mm.CustomIntegrator(dt)
    it.addGlobalVariable("gam", gamma_per_tau / TAU_PS)
    it.addGlobalVariable("kTv", kT_eps * EPS)
    it.addGlobalVariable("vpull", speed_A_per_tau * A2NM / TAU_PS)  # nm/ps
    it.addComputePerDof("v", "v + 0.5*dt*f/m")
    it.addComputePerDof("x", "x + dt*v")
    it.addComputePerDof("v", "v - gam*v*dt + sqrt(2*gam*kTv*dt/m)*gaussian")
    if speed_A_per_tau:
        it.addComputeGlobal("s", "s + vpull*dt")
    it.addComputePerDof("v", "v + 0.5*dt*f/m")
    it.setRandomNumberSeed(seed)
    return it


def run_one(xyz_A, contacts, ia, ip, cfg, seed, platform, outdir, tag, dcd_every=0, top=None):
    n = len(xyz_A)
    sysm, _ = build(xyz_A, lj_10_12=cfg["lj_10_12"], exclude_res=cfg.get("exclude"))
    mode = cfg["mode"]
    d = add_pulling(sysm, xyz_A, ia, ip, mode, spring_k=cfg.get("spring_k", 0.1), force=cfg.get("force", 0.0))
    it = engine_integrator(cfg["dt"], cfg["kT"], cfg["gamma"], cfg["speed"] if mode == "velocity" else 0.0, seed)
    ctx = mm.Context(sysm, it, platform)
    ctx.setPositions([mm.Vec3(*(np.array(p) * A2NM)) for p in xyz_A])
    ctx.setVelocities([mm.Vec3(0, 0, 0)] * n)
    nsteps, every = cfg["n_steps"], cfg["sample_every"]
    ce = cfg.get("contact_every", 25)
    ci = np.array([c[0] for c in contacts]); cj = np.array([c[1] for c in contacts]); r0 = np.array([c[2] for c in contacts])
    last_intact = np.zeros(len(contacts), dtype=int)
    p0 = np.array(xyz_A[ip]) * A2NM
    rows = []
    dcd = None
    if dcd_every and top is not None:
        fh = open(os.path.join(outdir, f"{tag}.dcd"), "wb")
        dcd = app.DCDFile(fh, top, cfg["dt"] * TAU_PS * dcd_every)

    def sample(step):
        st = ctx.getState(getPositions=True)
        x = st.getPositions(asNumpy=True).value_in_unit(mm.unit.nanometer)
        ext = np.linalg.norm(x[ip] - x[ia]) / A2NM
        if mode == "velocity":
            s = ctx.getParameter("s")
            kp = cfg["spring_k"]  # ε/Å²
            anchor = (p0 + d * s) / A2NM
            ten = kp * float(np.dot(anchor - x[ip] / A2NM, d))
        else:
            ten = cfg["force"]
        rows.append((step, step * cfg["dt"], ext, ten))
        return x

    x = sample(0)
    step = 0
    # advance in chunks that land on every sampling/contact/frame boundary
    marks = sorted(set(list(range(every, nsteps + 1, every)) + list(range(ce, nsteps + 1, ce)) +
                       (list(range(dcd_every, nsteps + 1, dcd_every)) if dcd else []) + [nsteps]))
    for mk in marks:
        it.step(mk - step)
        step = mk
        need_pos = step % every == 0 or step % ce == 0 or (dcd and step % dcd_every == 0)
        if not need_pos:
            continue
        if step % every == 0:
            x = sample(step)
        else:
            x = ctx.getState(getPositions=True).getPositions(asNumpy=True).value_in_unit(mm.unit.nanometer)
        if step % ce == 0 and len(contacts):
            dist = np.linalg.norm(x[cj] - x[ci], axis=1) / A2NM
            last_intact[dist < sp.GO["CONTACT_INTACT_FACTOR"] * r0] = step
        if dcd and step % dcd_every == 0:
            dcd.writeModel(mm.unit.Quantity([mm.Vec3(*p) for p in x], mm.unit.nanometer))
        if not np.isfinite(x).all():
            raise RuntimeError(f"{tag}: trajectory diverged at step {step}; lower dt or speed")
    xf = x
    dist = np.linalg.norm(xf[cj] - xf[ci], axis=1) / A2NM if len(contacts) else np.array([])
    breaks = [None if dist[k] < sp.GO["CONTACT_INTACT_FACTOR"] * r0[k] else int(min(last_intact[k] + ce, nsteps)) for k in range(len(contacts))]
    with open(os.path.join(outdir, f"{tag}.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["step", "time_tau", "extension_A", "tension_eps_per_A"])
        w.writerows(rows)
    ten = np.array([r[3] for r in rows])
    sm = np.convolve(ten, np.ones(5) / 5, mode="same")
    summ = {"tag": tag, "seed": seed, "n_steps": nsteps, "peak_tension_eps_per_A": float(sm.max()),
            "contacts": [[int(a), int(b)] for a, b in zip(ci, cj)], "contact_break_step": breaks,
            "contacts_remaining": float(np.mean([b is None for b in breaks])) if breaks else None}
    with open(os.path.join(outdir, f"{tag}.json"), "w") as fh:
        json.dump(summ, fh)
    return summ


def ca_topology(residues):
    top = app.Topology()
    ch = top.addChain("A")
    prev = None
    for r in residues:
        res = top.addResidue("GLY", ch, str(r))
        a = top.addAtom("CA", app.element.carbon, res)
        if prev is not None:
            top.addBond(prev, a)
        prev = a
    return top


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("setup")
    ap.add_argument("--platform", default=None, help="OpenMM platform (CUDA, OpenCL, CPU, Reference)")
    ap.add_argument("--replicas", type=int)
    ap.add_argument("--speeds", help="comma list, Å/τ (constant velocity)")
    ap.add_argument("--forces", help="comma list, ε/Å (constant force; overrides --speeds)")
    ap.add_argument("--steps", type=int, help="override the number of steps")
    ap.add_argument("--seed0", type=int, default=1)
    ap.add_argument("--dcd-every", type=int, default=0, help="write a DCD frame every N steps (0 = none)")
    ap.add_argument("--check", action="store_true", help="print the energy of the native structure and exit")
    a = ap.parse_args()

    setup = sp.load_setup(a.setup)
    wd = sp.setup_dir(a.setup)
    prep = os.path.join(wd, "prepared_ca.pdb")
    info_p = os.path.join(wd, "prepared.json")
    if not os.path.exists(prep):
        raise SystemExit("run prepare.py first:  python prepare.py " + a.setup)
    info = json.load(open(info_p))
    atoms, _, _ = sp.parse_atoms(open(prep, encoding="latin-1").read(), "A", None)
    residues, xyz, bfac = sp.ca_trace(atoms)
    ia, ip = residues.index(info["anchor_residue"]), residues.index(info["pulled_residue"])
    g = setup.get("go_model", {})
    exclude = None
    if info.get("is_alphafold") and g.get("plddt_cutoff"):
        exclude = [b < g["plddt_cutoff"] for b in bfac]
    contacts = [(i, j, d) for i, j, d in sp.native_contacts(xyz) if not (exclude and (exclude[i] or exclude[j]))]
    platform = mm.Platform.getPlatformByName(a.platform) if a.platform else None
    if platform is None:
        names = [mm.Platform.getPlatform(i).getName() for i in range(mm.Platform.getNumPlatforms())]
        platform = mm.Platform.getPlatformByName(next(p for p in ("CUDA", "HIP", "OpenCL", "CPU", "Reference") if p in names))
    if a.check:
        sysm, kept = build(xyz, lj_10_12=g.get("contact_form") == "lj10-12", exclude_res=exclude)
        ctx = mm.Context(sysm, mm.VerletIntegrator(0.001), platform)
        ctx.setPositions([mm.Vec3(*(np.array(p) * A2NM)) for p in xyz])
        e = ctx.getState(getEnergy=True).getPotentialEnergy().value_in_unit(mm.unit.kilojoule_per_mole)
        print(f"{len(xyz)} beads, {len(kept)} native contacts, native energy {e:.6f} ε  (platform {platform.getName()})")
        return
    mode = "force" if (a.forces or g.get("protocol") == "constant_force") else "velocity"
    conds = [float(v) for v in (a.forces or a.speeds or ",".join(map(str, g.get("forces_eps_per_A" if mode == "force" else "speeds_A_per_tau", [0.1])))).split(",")]
    reps = a.replicas or g.get("replicas", 3)
    dt = g.get("dt_tau", 0.01)
    sep = abs(ip - ia)
    d0 = math.dist(xyz[ia], xyz[ip])
    out = os.path.join(wd, "openmm_go_out")
    os.makedirs(out, exist_ok=True)
    top = ca_topology(residues)
    print(f"{setup.get('name', '')}: {len(xyz)} beads, {len(contacts)} native contacts, pulling {residues[ia]} → {residues[ip]}, "
          f"{len(conds)} condition(s) × {reps} replicas on {platform.getName()}")
    summary = []
    for c in conds:
        if mode == "velocity":
            travel = max(10.0, g.get("travel_fraction", 0.9) * (3.8 * sep - d0))
            steps = a.steps or g.get("steps") or int(math.ceil(travel / (c * dt)))
        else:
            steps = a.steps or g.get("steps") or 300000
        cfg = dict(mode=mode, speed=c, force=c, spring_k=g.get("spring_k_eps_per_A2", 0.1), dt=dt,
                   kT=g.get("temperature_eps", 0.5), gamma=g.get("friction_per_tau", 1.0), n_steps=steps,
                   sample_every=max(1, steps // 2000), contact_every=25, lj_10_12=g.get("contact_form") == "lj10-12",
                   exclude=exclude)
        for r in range(reps):
            seed = a.seed0 + r
            tag = f"{'F' if mode == 'force' else 'v'}{c:g}_seed{seed}"
            t0 = time.time()
            s = run_one(xyz, contacts, ia, ip, cfg, seed, platform, out, tag, a.dcd_every, top)
            s.update(condition=c, mode=mode, seconds=round(time.time() - t0, 2))
            summary.append({k: v for k, v in s.items() if k not in ("contacts", "contact_break_step")})
            print(f"  {tag}: {steps} steps, peak tension {s['peak_tension_eps_per_A']:.3f} ε/Å, "
                  f"{s['contacts_remaining']:.2f} contacts left, {s['seconds']} s")
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"setup": setup.get("name"), "units": "model units: Å, τ (=0.1 ps in the OpenMM map), ε/Å (not pN)", "runs": summary}, fh, indent=1)
    if top is not None:
        with open(os.path.join(out, "topology_ca.pdb"), "w") as fh:
            app.PDBFile.writeFile(top, mm.unit.Quantity([mm.Vec3(*p) for p in xyz], mm.unit.angstrom), fh)
    print("wrote", out)


if __name__ == "__main__":
    main()
