#!/usr/bin/env python3
"""All-atom steered-MD pull of a SMASH-Pull setup in OpenMM.

    python prepare.py pull_setup.json
    python openmm_allatom.py pull_setup.json [--implicit] [--platform CUDA]
                                             [--speed 2.0] [--distance 10]
                                             [--max-steps N] [--equil-ns 0.5]

Protocol (all values from the setup's "all_atom" block unless overridden):
  1. PDBFixer: replace non-standard residues, add missing heavy atoms and
     hydrogens at the setup pH. Missing loops are NOT modelled.
  2. Amber14 force field; explicit TIP3P-FB water and ions in a box that is
     long along z (room to pull), or GBn2 implicit solvent with --implicit.
  3. Minimise; equilibrate with heavy-atom restraints (NPT for explicit).
  4. Pull: the anchor Cα is held by a stiff harmonic restraint, and the pulled
     Cα is attached to a spring along +z whose anchor point moves at constant speed.
Output (folder openmm_allatom_out/): pull.csv with time (ps), extension (nm)
and force (pN, from the spring), and protein-only frames as pull_protein.pdb.
Forces here ARE in pN: this is a physical all-atom model.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashpull as sp  # noqa: E402

try:
    import openmm as mm
    from openmm import app, unit as u
    from pdbfixer import PDBFixer
except ImportError:
    raise SystemExit("needs OpenMM and PDBFixer: conda install -c conda-forge openmm pdbfixer")

KJ_NM_TO_PN = 1.66054


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("setup")
    ap.add_argument("--implicit", action="store_true", help="GBn2 implicit solvent instead of explicit water")
    ap.add_argument("--platform", default=None)
    ap.add_argument("--speed", type=float, help="nm/ns")
    ap.add_argument("--distance", type=float, help="pull distance, nm")
    ap.add_argument("--equil-ns", type=float)
    ap.add_argument("--max-steps", type=int, help="stop the pull after this many steps (testing)")
    ap.add_argument("--build-only", action="store_true", help="build and minimise, then stop")
    a = ap.parse_args()

    setup = sp.load_setup(a.setup)
    wd = sp.setup_dir(a.setup)
    info = json.load(open(os.path.join(wd, "prepared.json")))
    aa = setup.get("all_atom", {})
    cond = setup.get("conditions", {})
    T = cond.get("temperature_K", 300) * u.kelvin
    implicit = a.implicit or aa.get("solvent") == "implicit"
    speed = (a.speed or aa.get("speed_nm_per_ns", 2.0)) * u.nanometer / u.nanosecond
    dist = (a.distance or info["pull_distance_nm"]) * u.nanometer
    dt = aa.get("timestep_fs", 2) * u.femtosecond
    k_pull = aa.get("spring_k_kJ_mol_nm2", 1000) * u.kilojoule_per_mole / u.nanometer ** 2
    k_anc = aa.get("anchor_restraint_kJ_mol_nm2", 10000)
    out = os.path.join(wd, "openmm_allatom_out" + ("_implicit" if implicit else ""))
    os.makedirs(out, exist_ok=True)

    fixer = PDBFixer(filename=os.path.join(wd, "prepared_allatom.pdb"))
    fixer.findMissingResidues()
    fixer.missingResidues = {}
    fixer.findNonstandardResidues()
    fixer.replaceNonstandardResidues()
    fixer.findMissingAtoms()
    fixer.addMissingAtoms()
    fixer.addMissingHydrogens(cond.get("pH", 7.0))
    ff = app.ForceField("amber14-all.xml", "implicit/gbn2.xml") if implicit else app.ForceField("amber14-all.xml", "amber14/tip3pfb.xml")
    model = app.Modeller(fixer.topology, fixer.positions)
    n_protein = model.topology.getNumAtoms()
    if implicit:
        system = ff.createSystem(model.topology, nonbondedMethod=app.NoCutoff, constraints=app.HBonds)
    else:
        bx, by, bz = info["box_nm"]
        model.addSolvent(ff, boxSize=mm.Vec3(bx, by, bz) * u.nanometer,
                         ionicStrength=cond.get("ionic_strength_M", 0.15) * u.molar, positiveIon="Na+", negativeIon="Cl-")
        system = ff.createSystem(model.topology, nonbondedMethod=app.PME, nonbondedCutoff=1.0 * u.nanometer, constraints=app.HBonds)
    # locate the two Cα atoms
    def ca_index(resnum):
        for atom in model.topology.atoms():
            if atom.name == "CA" and int(atom.residue.id) == resnum:
                return atom.index
        raise SystemExit(f"Cα of residue {resnum} not found after preparation")
    ia, ip = ca_index(info["anchor_residue"]), ca_index(info["pulled_residue"])
    pos = model.positions
    pa, pp = pos[ia].value_in_unit(u.nanometer), pos[ip].value_in_unit(u.nanometer)
    # anchor restraint (all three dimensions) and the pulling spring (along z only)
    anc = mm.CustomExternalForce("0.5*ka*((x-x0)^2+(y-y0)^2+(z-z0)^2)")
    anc.addGlobalParameter("ka", k_anc)
    for p_ in ("x0", "y0", "z0"):
        anc.addPerParticleParameter(p_)
    anc.addParticle(ia, list(pa))
    system.addForce(anc)
    pull = mm.CustomExternalForce("0.5*kp*(z-zp0-s)^2")
    pull.addGlobalParameter("kp", k_pull.value_in_unit(u.kilojoule_per_mole / u.nanometer ** 2))
    pull.addGlobalParameter("zp0", pp[2])
    pull.addGlobalParameter("s", 0.0)
    pull.addParticle(ip, [])
    system.addForce(pull)
    # equilibration restraints on protein heavy atoms
    rest = mm.CustomExternalForce("0.5*kr*((x-x0)^2+(y-y0)^2+(z-z0)^2)")
    rest.addGlobalParameter("kr", 1000.0)
    for p_ in ("x0", "y0", "z0"):
        rest.addPerParticleParameter(p_)
    for atom in model.topology.atoms():
        if atom.index < n_protein and atom.element is not None and atom.element.symbol != "H":
            rest.addParticle(atom.index, list(pos[atom.index].value_in_unit(u.nanometer)))
    rest_idx = system.addForce(rest)
    baro_idx = None if implicit else system.addForce(mm.MonteCarloBarostat(1 * u.bar, T))
    integ = mm.LangevinMiddleIntegrator(T, 1 / u.picosecond, dt)
    platform = mm.Platform.getPlatformByName(a.platform) if a.platform else None
    sim = app.Simulation(model.topology, system, integ, platform) if platform else app.Simulation(model.topology, system, integ)
    sim.context.setPositions(pos)
    print(f"{setup.get('name', '')}: {n_protein} protein atoms, {model.topology.getNumAtoms()} total, "
          f"{'implicit GBn2' if implicit else 'explicit water'}, platform {sim.context.getPlatform().getName()}")
    sim.minimizeEnergy(maxIterations=2000)
    with open(os.path.join(out, "minimised.pdb"), "w") as fh:
        app.PDBFile.writeFile(sim.topology, sim.context.getState(getPositions=True).getPositions(), fh)
    if a.build_only:
        print("built and minimised:", out)
        return
    eq_ns = a.equil_ns if a.equil_ns is not None else aa.get("equilibration_ns", 0.5)
    sim.context.setVelocitiesToTemperature(T)
    sim.step(int(round(eq_ns * 1e6 / dt.value_in_unit(u.femtosecond))))
    # release equilibration restraints and the barostat; pull at constant volume
    sim.context.setParameter("kr", 0.0)
    if baro_idx is not None:
        system.removeForce(baro_idx)
        sim.context.reinitialize(preserveState=True)
    # pull: move the spring anchor every `chunk` steps
    chunk = 10
    v_nm_ps = speed.value_in_unit(u.nanometer / u.picosecond)
    total = int(round(dist.value_in_unit(u.nanometer) / v_nm_ps / dt.value_in_unit(u.picosecond)))
    if a.max_steps:
        total = min(total, a.max_steps)
    report_every = max(chunk, (total // 2000) // chunk * chunk or chunk)
    frame_every = max(report_every, (total // 200) // report_every * report_every or report_every)
    protein_atoms = list(range(n_protein))
    kp = pull.getGlobalParameterDefaultValue(0)
    t0 = time.time()
    with open(os.path.join(out, "pull.csv"), "w", encoding="utf-8", newline="") as fh, open(os.path.join(out, "pull_protein.pdb"), "w") as pf:
        w = csv.writer(fh)
        w.writerow(["step", "time_ps", "spring_nm", "extension_nm", "z_pulled_nm", "force_pN", "work_kJ_mol"])
        work = 0.0
        step = 0
        prev_f = None
        sub_top = app.Modeller(sim.topology, sim.context.getState(getPositions=True).getPositions())
        sub_top.delete([r for r in sub_top.topology.residues() if r.chain.index != 0 or r.name in ("HOH", "NA", "CL")])
        model_no = 1
        while step <= total:
            st = sim.context.getState(getPositions=True)
            x = st.getPositions(asNumpy=True).value_in_unit(u.nanometer)
            s = sim.context.getParameter("s")
            f_kj = kp * (pp[2] + s - x[ip][2])  # spring tension along +z, kJ/mol/nm
            ext = float(((x[ip] - x[ia]) ** 2).sum() ** 0.5)
            if prev_f is not None:
                work += 0.5 * (f_kj + prev_f) * v_nm_ps * dt.value_in_unit(u.picosecond) * report_every
            prev_f = f_kj
            if step % report_every == 0:
                w.writerow([step, round(step * dt.value_in_unit(u.picosecond), 4), round(s, 5), round(ext, 5), round(float(x[ip][2]), 5), round(f_kj * KJ_NM_TO_PN, 3), round(work, 3)])
            if step % frame_every == 0:
                app.PDBFile.writeModel(sub_top.topology, x[protein_atoms] * u.nanometer, pf, modelIndex=model_no)
                model_no += 1
            if step == total:
                break
            n = min(report_every, total - step)
            for _ in range(n // chunk):
                sim.step(chunk)
                sim.context.setParameter("s", sim.context.getParameter("s") + v_nm_ps * chunk * dt.value_in_unit(u.picosecond))
            if n % chunk:
                sim.step(n % chunk)
                sim.context.setParameter("s", sim.context.getParameter("s") + v_nm_ps * (n % chunk) * dt.value_in_unit(u.picosecond))
            step += n
        app.PDBFile.writeFooter(sub_top.topology, pf)
    print(f"pulled {total} steps ({total * dt.value_in_unit(u.picosecond) / 1000:.3f} ns) in {time.time() - t0:.0f} s -> {out}")


if __name__ == "__main__":
    main()
