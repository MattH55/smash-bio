"""Gate X4 static check (does not count as a pass; GROMACS is not installed):
every key in the generated .mdp files must be a GROMACS 2024 mdp option.
The option list below is transcribed from the GROMACS 2024 "Molecular dynamics
parameters (.mdp options)" reference for the keys this generator may emit.
"""
import json
import os
import re
import sys

KNOWN = {
    "integrator", "dt", "nsteps", "emtol", "emstep", "cutoff-scheme", "nstlist", "pbc", "coulombtype", "rcoulomb",
    "rvdw", "DispCorr", "tcoupl", "tc-grps", "tau-t", "ref-t", "constraints", "constraint-algorithm", "define",
    "nstxout-compressed", "compressed-x-grps", "nstenergy", "nstlog", "gen-vel", "gen-temp", "gen-seed", "pcoupl",
    "pcoupltype", "tau-p", "ref-p", "compressibility", "refcoord-scaling", "continuation", "pull", "pull-ncoords",
    "pull-ngroups", "pull-group1-name", "pull-group2-name", "pull-coord1-type", "pull-coord1-geometry",
    "pull-coord1-vec", "pull-coord1-groups", "pull-coord1-start", "pull-coord1-rate", "pull-coord1-k",
    "pull-nstxout", "pull-nstfout",
}
ENUMS = {
    "pull-coord1-geometry": {"distance", "direction", "direction-periodic", "direction-relative", "cylinder", "angle", "dihedral", "angle-axis", "transformation"},
    "pull-coord1-type": {"umbrella", "constraint", "constant-force", "flat-bottom", "flat-bottom-high", "external"},
    "pcoupl": {"no", "Berendsen", "C-rescale", "Parrinello-Rahman", "MTTK"},
    "tcoupl": {"no", "berendsen", "nose-hoover", "andersen", "andersen-massive", "V-rescale"},
}
d = sys.argv[1]
bad, keys = [], 0
for f in sorted(os.listdir(d)):
    if not f.endswith(".mdp"):
        continue
    for line in open(os.path.join(d, f), encoding="utf-8"):
        line = line.split(";")[0].strip()
        if not line:
            continue
        k, _, v = (s.strip() for s in line.partition("="))
        keys += 1
        if k not in KNOWN:
            bad.append(f"{f}: unknown key {k}")
        elif k in ENUMS and v not in ENUMS[k]:
            bad.append(f"{f}: {k} = {v} not an allowed value")
res = {"gate": "X4", "status": "not_run", "static_check": {"keys_checked": keys, "problems": bad, "clean": not bad},
       "note": "GROMACS not installed on the test machine; static check only, does not count as a pass"}
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "gateX4.json"), "w"), indent=1)
print(json.dumps(res["static_check"]))
