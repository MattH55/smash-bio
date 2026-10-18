"""SMASH-Pull export library: setup files, structure fetching and preparation.

Shared by prepare.py, openmm_go.py and openmm_allatom.py. Standard library
only (plus numpy where noted) so it runs anywhere Python 3.9+ runs.

Structure selection follows the SMASH-Pull browser engine rule for rule
(pull-engine/src/protein.rs): first MODEL only, the chosen chain only, the
first occurrence of each residue (altlocs), optional residue window, HETATM
records dropped. The prepared structure is rotated so that the anchor Cα sits
at the origin and the pulled Cα lies on +z.
"""
from __future__ import annotations

import json
import math
import os
import urllib.request

SCHEMA = "smash-pull-setup/1"
UA = {"User-Agent": "SMASH-Pull-export/1 (+https://smash-bio.org/pull/)"}


# ----------------------------------------------------------------- setup files
def load_setup(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        s = json.load(fh)
    if s.get("schema") != SCHEMA:
        raise SystemExit(f"{path}: not a {SCHEMA} file (schema = {s.get('schema')!r})")
    return s


def setup_dir(path: str) -> str:
    return os.path.dirname(os.path.abspath(path))


# ----------------------------------------------------------------- fetching
def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_structure(st: dict, workdir: str) -> str:
    """Return PDB-format text for setup['structure'], caching it as structure.pdb."""
    cache = os.path.join(workdir, "structure.pdb")
    if os.path.exists(cache):
        with open(cache, encoding="latin-1") as fh:
            return fh.read()
    src = st["source"]
    if src == "file":
        with open(os.path.join(workdir, st["file"]), encoding="latin-1") as fh:
            text = fh.read()
    elif src == "pdb":
        text = _get(f"https://files.rcsb.org/download/{st['id'].upper()}.pdb").decode("latin-1")
    elif src == "alphafold":
        meta = json.loads(_get(f"https://alphafold.ebi.ac.uk/api/prediction/{st['id'].upper()}"))
        m = meta[0] if isinstance(meta, list) else meta
        text = _get(m["pdbUrl"]).decode("latin-1")
    else:
        raise SystemExit(f"unknown structure source {src!r}")
    with open(cache, "w", encoding="latin-1", newline="\n") as fh:
        fh.write(text)
    return text


# ----------------------------------------------------------------- parsing
def parse_atoms(text: str, chain: str | None, window: list | None):
    """All ATOM records of the first model, one chain, first altloc.

    Returns (atoms, chain_used, notes). Each atom is a dict with the PDB fields
    needed to rewrite the record.
    """
    rows, notes = [], []
    for line in text.splitlines():
        if line.startswith("ENDMDL"):
            break
        if line.startswith("ATOM") and len(line) >= 54:
            rows.append(line)
    if not rows:
        raise SystemExit("no ATOM records in the structure")
    # chain: as requested, else the one with the most Cα (protein.rs rule)
    if not chain:
        counts = {}
        for l in rows:
            if l[12:16].strip() == "CA":
                counts[l[21]] = counts.get(l[21], 0) + 1
        chain = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        if len(counts) > 1:
            notes.append(f"{len(counts)} chains present; using the largest, {chain}")
    atoms, seen_atom, seen_res = [], set(), []
    for l in rows:
        if l[21] != chain:
            continue
        resi = int(l[22:26])
        icode = l[26]
        if window and (resi < window[0] or resi > window[1]):
            continue
        name = l[12:16].strip()
        key = (resi, icode, name)
        if key in seen_atom:  # altloc: first occurrence wins
            continue
        seen_atom.add(key)
        atoms.append({
            "name": name, "rawname": l[12:16], "resname": l[17:20].strip(), "resi": resi, "icode": icode,
            "x": float(l[30:38]), "y": float(l[38:46]), "z": float(l[46:54]),
            "bfac": float(l[60:66]) if len(l) >= 66 and l[60:66].strip() else 0.0,
            "element": l[76:78].strip() if len(l) >= 78 else name[0],
        })
        if (resi, icode) not in seen_res:
            seen_res.append((resi, icode))
    if not atoms:
        raise SystemExit(f"chain {chain} has no atoms in the selection")
    return atoms, chain, notes


def ca_trace(atoms):
    """Residue numbers, Cα coordinates (Å) and Cα B-factors, in chain order."""
    res, xyz, bf, seen = [], [], [], set()
    for a in atoms:
        if a["name"] == "CA" and a["resi"] not in seen:
            seen.add(a["resi"])
            res.append(a["resi"]); xyz.append((a["x"], a["y"], a["z"])); bf.append(a["bfac"])
    return res, xyz, bf


def is_alphafold(text: str) -> bool:
    head = "\n".join(text.splitlines()[:40]).upper()
    return "ALPHAFOLD" in head


# ----------------------------------------------------------------- geometry
def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _norm(a): return math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def rotation_to_z(u):
    """3x3 rotation matrix (rows) taking unit vector u onto +z (Rodrigues)."""
    z = (0.0, 0.0, 1.0)
    v = _cross(u, z)
    s, c = _norm(v), _dot(u, z)
    if s < 1e-12:
        return [[1, 0, 0], [0, 1, 0], [0, 0, 1]] if c > 0 else [[1, 0, 0], [0, -1, 0], [0, 0, -1]]
    k = (v[0] / s, v[1] / s, v[2] / s)
    K = [[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]]
    K2 = [[sum(K[i][m] * K[m][j] for m in range(3)) for j in range(3)] for i in range(3)]
    return [[(1 if i == j else 0) + s * K[i][j] + (1 - c) * K2[i][j] for j in range(3)] for i in range(3)]


def align(atoms, anchor_xyz, pulled_xyz):
    """Translate the anchor Cα to the origin and rotate the pull vector onto +z (in place)."""
    d = _sub(pulled_xyz, anchor_xyz)
    L = _norm(d)
    R = rotation_to_z((d[0] / L, d[1] / L, d[2] / L))
    for a in atoms:
        p = (a["x"] - anchor_xyz[0], a["y"] - anchor_xyz[1], a["z"] - anchor_xyz[2])
        a["x"], a["y"], a["z"] = (sum(R[i][j] * p[j] for j in range(3)) for i in range(3))
    return L


def write_pdb(atoms, path, chain="A", remarks=()):
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        for r in remarks:
            fh.write(f"REMARK 999 {r[:68]}\n")
        for k, a in enumerate(atoms, 1):
            name = a["rawname"] if len(a["rawname"]) == 4 else f" {a['name']:<3}"
            fh.write("ATOM  %5d %4s %3s %1s%4d%1s   %8.3f%8.3f%8.3f%6.2f%6.2f          %2s\n" % (
                k % 100000, name, a["resname"], chain, a["resi"], a["icode"] if a["icode"].strip() else " ",
                a["x"], a["y"], a["z"], 1.0, a["bfac"], a["element"][:2]))
        fh.write("TER\nEND\n")


# ----------------------------------------------------------------- Cα Gō model (SMASH-Pull engine constants)
GO = dict(BOND_K=100.0, ANGLE_K=20.0, CONTACT_CUTOFF=8.0, SEQ_SEP=4, NONNATIVE_SIGMA=4.0,
          NONNATIVE_CUTOFF=12.0, ANCHOR_K=50.0, CONTACT_INTACT_FACTOR=1.2)


def dihedral(p0, p1, p2, p3):
    """Same formula and sign convention as pull-engine protein::dihedral."""
    b0, b1, b2 = _sub(p0, p1), _sub(p2, p1), _sub(p3, p2)
    n = max(_norm(b1), 1e-12)
    u = (b1[0] / n, b1[1] / n, b1[2] / n)
    d0, d2 = _dot(b0, u), _dot(b2, u)
    v = (b0[0] - d0 * u[0], b0[1] - d0 * u[1], b0[2] - d0 * u[2])
    w = (b2[0] - d2 * u[0], b2[1] - d2 * u[1], b2[2] - d2 * u[2])
    return math.atan2(_dot(_cross(u, v), w), _dot(v, w))


def angle(p0, p1, p2):
    a, b = _sub(p0, p1), _sub(p2, p1)
    c = _dot(a, b) / (_norm(a) * _norm(b))
    return math.acos(max(-1.0, min(1.0, c)))


def native_contacts(xyz):
    n, out = len(xyz), []
    for i in range(n):
        for j in range(i + GO["SEQ_SEP"], n):
            d = _norm(_sub(xyz[i], xyz[j]))
            if d < GO["CONTACT_CUTOFF"]:
                out.append((i, j, d))
    return out
