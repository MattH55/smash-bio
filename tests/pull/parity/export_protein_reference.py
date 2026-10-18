"""Export golden protein numbers from the reference smash-sim pipeline.

The reference tree is imported strictly read-only: nothing under
`Meeta Analysis/Simulation Comparison/smash-sim` is written or edited here. It
provides `go_model`/`pull`, which take **coordinates**, not PDB files, so this
script also re-implements the Ca selection rules of `pull-engine/src/protein.rs`
in Python and records what they chose. That is deliberate: there is no Python PDB
parser to agree with, so parser "parity" means "the Rust engine's choices are
written down and tested", and the only trustworthy way to write them down is to
apply the same rules here and let the two independent implementations disagree
loudly if one of them drifts.

Why the trajectories are deterministic
--------------------------------------
`pull-engine` draws its Langevin noise from sfc64 (`rng.rs`) and the reference
draws from NumPy's generator, so the two noisy walks cannot be compared: any
difference would be the RNG, not the physics, and the test would prove nothing.
Every trajectory exported here is therefore either

  * `temperature = 0`, where `noise_scale = sqrt(2*friction*T*dt)` is exactly 0
    and both engines integrate the same deterministic Langevin step, or
  * driven by a noise array drawn *here* and written into the fixture, so the
    Rust engine consumes the reference's own `rng.normal(size = x.shape)` values
    in the reference's own order (`simulate_with_injected_noise`).

Whatever divergence remains after that is pure floating-point ordering, which is
the thing a parity gate is supposed to bound.

Run:
    python tests/pull/parity/export_protein_reference.py
from the repo root, with numpy installed.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SMSIM_SRC = os.path.join(
    REPO, "Meeta Analysis", "Simulation Comparison", "smash-sim", "src"
)
if not os.path.isdir(SMSIM_SRC):
    sys.exit(f"reference not found at {SMSIM_SRC}")
sys.path.insert(0, SMSIM_SRC)

from smashsim.go_model import (  # noqa: E402
    ANGLE_K,
    BOND_K,
    CONTACT_CUTOFF,
    NONNATIVE_SIGMA,
    SEQ_SEP,
    build_model,
    energy_and_force,
)
from smashsim.pull import ANCHOR_K, _contacts_remaining, _peaks  # noqa: E402

PDB_DIR = os.path.join(
    REPO, "Meeta Analysis", "mechanoprodb-reanalysis", "data", "raw", "pdb"
)
FIX_DIR = os.path.join(HERE, "fixtures")

# One-letter mapping of `protein.rs::one_letter`; anything unmapped (MSE, SEP,
# modified residues) becomes X because the Hamiltonian never reads the code.
THREE_TO_ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q",
    "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
    "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
    "TYR": "Y", "VAL": "V",
}


def _col(field) -> str:
    """`protein.rs::col` - strip spaces and tabs only, not all whitespace."""
    if isinstance(field, bytes):
        return field.decode("latin-1").strip(" \t")
    return field.strip(" \t")

# ---PARSING---

def _pdb_ca(line: str):
    """`protein.rs::pdb_ca`: an ATOM/CA row -> (chain, resi, code, xyz).

    Lines are read as latin-1, so a Python string index *is* a PDB column: the
    slicing below is the Rust column arithmetic, not whitespace splitting.
    """
    if len(line) < 54 or line[0:4] != "ATOM":
        return None
    if _col(line[12:16]) != "CA":
        return None
    chain = line[21]
    try:
        resi = int(_col(line[22:26]))
        px = float(_col(line[30:38]))
        py = float(_col(line[38:46]))
        pz = float(_col(line[46:54]))
    except ValueError:
        return None
    if not (px == px and py == py and pz == pz):
        return None
    name = _col(line[17:20]).upper()
    return chain, resi, THREE_TO_ONE.get(name, "X"), (px, py, pz)


def parse_pdb(text: str, chain: str | None = None,
              window: tuple[int, int] | None = None) -> dict:
    """`protein.rs::parse_pdb`, in Python, rule for rule.

    Returns the trace plus the provenance notes the Rust engine emits, so a drift
    in either implementation shows up as a fixture mismatch instead of as two
    engines silently pulling two different structures.
    """
    rows: list = []
    het_cys_sg = 0
    het_other = 0
    for line in text.splitlines():
        if len(line) >= 6 and line[0:6] == "HETATM":
            if len(line) >= 54 and _col(line[12:16]) == "SG" \
               and _col(line[17:20]) == "CYS":
                het_cys_sg += 1
            else:
                het_other += 1
            continue
        row = _pdb_ca(line)
        if row is None:
            continue
        # First occurrence of a residue wins: altloc rows share chain + number and
        # both cannot be modelled.
        if any(r[0] == row[0] and r[1] == row[1] for r in rows):
            continue
        rows.append(row)
    if not rows:
        raise ValueError("no ATOM records with a CA atom")

    notes: list[str] = []
    if het_cys_sg:
        notes.append(f"{het_cys_sg} disulfide sulfur(s) (SG) ignored")
    if het_other:
        notes.append(f"{het_other} HETATM record(s) (metal, ligand or water) ignored")

    if chain is None:
        counts: dict[str, int] = {}
        for r in rows:
            counts[r[0]] = counts.get(r[0], 0) + 1
        # Rust: sort_by_key((Reverse(n), chain)). A dict built in first-appearance
        # order plus this key reproduces the tie-breaking exactly.
        pick = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        if len(counts) > 1:
            notes.append(
                f"{len(counts)} chains present; modelled the largest, '{pick}', alone"
            )
    else:
        pick = chain

    residues, codes, xyz = [], [], []
    skipped = 0
    for r in rows:
        if r[0] != pick:
            continue
        if window is not None and (r[1] < window[0] or r[1] > window[1]):
            skipped += 1
            continue
        residues.append(r[1])
        codes.append(r[2])
        xyz.extend(r[3])
    if skipped:
        notes.append(
            f"domain slice {window[0]}..{window[1]}: {skipped} residue(s) dropped"
        )
    if not xyz:
        raise ValueError(f"chain {pick} has no CA in the selection")

    gaps = sum(1 for a, b in zip(residues, residues[1:]) if b - a != 1)
    if gaps:
        notes.append(f"{gaps} chain break(s) in the numbering")

    pdb_id = None
    for line in text.splitlines():
        if line.startswith("HEADER") and len(line) >= 62:
            # Columns 63-66 (1-based) per the PDB format spec, byte 62 onward:
            # `protein.rs::pdb_id`, including its widened-then-trimmed slice.
            ident = line[62:68].strip()
            pdb_id = ident.upper() if ident else None
        if not line.startswith(("HEADER", "OBSLT", "TITLE", "COMPND", "SOURCE", "REMARK")):
            break

    return {
        "label": f"{pdb_id or 'upload'}:{pick} {residues[0]}-{residues[-1]}",
        "pdb_id": pdb_id,
        "chain": pick,
        "residues": residues,
        "codes": "".join(codes),
        "coords": xyz,
        "n": len(residues),
        "notes": notes,
        "n_gaps": gaps,
        "n_chains_seen": len({r[0] for r in rows}),
    }

# ---PULLING---

def pull_deterministic(coords: np.ndarray, model: dict, *, speed: float,
                       spring_k: float, n_steps: int, dt: float,
                       temperature: float, friction: float,
                       noise: np.ndarray | None = None,
                       anchor_i: int = 0, pull_i: int = -1) -> dict:
    """`smashsim.pull.simulate` with the noise stream supplied by the caller.

    Line-for-line the reference loop (`pull.py:29-45`), including the two details
    a port tends to "fix" and thereby break: the moving anchor is advanced
    *before* the second spring is evaluated, and the reported force is
    `dot(-spring, direction)`, not the spring itself.
    """
    x = np.array(coords, dtype=float, copy=True)
    v = np.zeros_like(x)
    origin = x[anchor_i].copy()
    direction = x[pull_i] - x[anchor_i]
    direction = direction / max(np.linalg.norm(direction), 1e-8)
    anchor = x[pull_i].copy()
    extension = np.empty(n_steps)
    force_trace = np.empty(n_steps)
    noise_scale = np.sqrt(2.0 * friction * temperature * dt)
    for step in range(n_steps):
        f = energy_and_force(x, model)[1]
        f[anchor_i] += -ANCHOR_K * (x[anchor_i] - origin)
        spring = -spring_k * (x[pull_i] - anchor)
        f[pull_i] += spring
        v += 0.5 * dt * f
        x += dt * v
        draw = np.zeros(x.shape) if noise is None else noise[step]
        v += -friction * v * dt + noise_scale * draw
        f = energy_and_force(x, model)[1]
        f[anchor_i] += -ANCHOR_K * (x[anchor_i] - origin)
        anchor = anchor + direction * speed * dt
        spring = -spring_k * (x[pull_i] - anchor)
        f[pull_i] += spring
        v += 0.5 * dt * f
        extension[step] = np.linalg.norm(x[pull_i] - x[anchor_i])
        force_trace[step] = float(np.dot(-spring, direction))
    hits = _peaks(force_trace)
    peak_force = float(force_trace[hits].max()) if len(hits) else float(np.max(force_trace))
    # `peak.py` reports the peak *value* only, so this index is the port's
    # extension of it. Pinned with np.argmax's first-wins convention so both
    # engines must point their marker at the same sample.
    if len(hits):
        peak_step = int(hits[int(np.argmax(force_trace[hits]))])
    else:
        peak_step = int(np.argmax(force_trace))
    return {
        "extension_A": extension,
        "force_reduced": force_trace,
        "peak_force_reduced": peak_force,
        "n_force_peaks": int(len(hits)),
        "peak_step": peak_step,
        "peaks": [int(i) for i in hits],
        "final": x,
        "native_contacts_remaining": _contacts_remaining(x, model),
    }


def model_arrays(coords: np.ndarray, contact: str = "lj12-6") -> dict:
    """`build_model`'s dict, as plain lists: the geometry a port must reproduce."""
    m = build_model(np.array(coords, dtype=float), contact=contact)
    ci = [int(i) for i in m["ci"]]
    cj = [int(i) for i in m["cj"]]
    seps = [j - i for i, j in zip(ci, cj)]
    return {
        "n": int(m["n"]),
        "bond0": [float(b) for b in m["bond0"]],
        "angle0": [float(a) for a in m["angle0"]],
        "dihedral0": [float(d) for d in m["dihedral0"]],
        "ci": ci,
        "cj": cj,
        "contact0": [float(r) for r in m["contact0"]],
        # (i << 32 | j), sorted: protein.rs::native_pairs, the membership test the
        # non-native scan runs against. Exported so the packed form is checked too.
        "native_pairs": sorted(i * 2**32 + j for i, j in zip(ci, cj)),
        "min_seq_sep": min(seps, default=0),
        "max_seq_sep": max(seps, default=0),
    }


def static_energy_and_force(flat_coords: list[float]) -> dict:
    """Native-state energy and force: the term-by-term anchor of the Hamiltonian.

    `energy_and_force` perturbs its argument in place for the dihedral central
    difference (`go_model.py:110-122`), so every call here gets a private copy and
    the reported contacts are counted on the pristine native geometry. The Rust
    test mirrors that: clone the buffer, read `contacts_remaining` on the clone,
    then let `energy_and_force(&mut x, m)` drift whichever copy it likes.
    """
    coords = np.asarray(flat_coords, dtype=float).reshape(-1, 3)
    m = build_model(coords.copy(), contact="lj12-6")
    ml = build_model(coords.copy(), contact="lj10-12")
    q = float(_contacts_remaining(coords, m))
    e, f = energy_and_force(coords.copy(), m)
    e10, f10 = energy_and_force(coords.copy(), ml)
    return {
        "energy": float(e),
        "force": [float(a) for a in f.reshape(-1)],
        "energy_lj10_12": float(e10),
        "force_lj10_12": [float(a) for a in f10.reshape(-1)],
        # Contacts are intact by definition at the native state.
        "contacts_remaining": q,
    }

# ---CASES---

def helix(n: int = 12) -> np.ndarray:
    """Ideal poly-alpha-helix Ca trace: 1.5 A rise, 2.3 A radius, 100 deg/step."""
    t = np.arange(n, dtype=float)
    return np.stack([
        2.3 * np.cos(np.deg2rad(100.0) * t),
        2.3 * np.sin(np.deg2rad(100.0) * t),
        1.5 * t,
    ], axis=1)


def sheet(n: int = 10) -> np.ndarray:
    """A flat zig-zag strand: sequence-separated pairs sit close enough to form
    beta-like contacts without any folding, so the contact rule gets exercised."""
    x = np.zeros((n, 3), dtype=float)
    for i in range(n):
        x[i, 0] = 3.8 * i
        x[i, 1] = 2.5 if i % 2 else -2.5
    return x


def collapsed(n: int = 9) -> np.ndarray:
    """A tight cluster: loads up the non-native repulsion and the small-r guards."""
    t = np.arange(n, dtype=float)
    return np.stack([
        3.1 * np.cos(1.1 * t),
        3.1 * np.sin(1.1 * t),
        2.2 * np.sin(0.55 * t),
    ], axis=1) + np.array([0.37, -1.13, 2.9])


def straight(n: int = 6) -> np.ndarray:
    """Fully extended: no contacts at all, so contacts-remaining is undefined."""
    x = np.zeros((n, 3), dtype=float)
    x[:, 0] = 9.0 * np.arange(n, dtype=float)
    return x


CFG_ZERO = dict(speed=0.2, spring_k=0.1, n_steps=240, dt=0.002,
                temperature=0.0, friction=1.0)

# The reference is pure-Python numpy per angle, per dihedral coordinate and per
# non-native pair, so a real protein costs O(n_steps * n^2) interpreter steps:
# one energy_and_force call is ~0.06 s at 53 residues and ~0.15 s at 89. 100 steps
# is still long enough for a wrong sign or a swapped ordering to compound into a
# visible mismatch, which is what a trajectory parity gate is for; the synthetic
# traces run the full 240 because they cost almost nothing.
CFG_PDB = dict(CFG_ZERO, n_steps=100)


def _run_record(label: str, coords: np.ndarray, cfg: dict,
                noise: np.ndarray | None) -> dict:
    model = build_model(np.array(coords, dtype=float))
    res = pull_deterministic(coords, model, noise=noise, **cfg)
    final = np.array(res["final"], dtype=float)
    # Mirrors `protein.rs::finish` evaluation order, which matters: the final
    # energy is taken with energy_and_force, whose dihedral central difference
    # perturbs the buffer in place and leaves sub-ulp drift (protein.rs:1184).
    # contacts_remaining and the exported coordinates are then read from that
    # *drifted* buffer, exactly as Rust's struct literal moves it at 1194-1195.
    energy_final = float(energy_and_force(final, model)[0])
    q_final = float(_contacts_remaining(final, model))
    return {
        "label": label,
        "config": {k: v for k, v in cfg.items()},
        "extension_A": [float(a) for a in res["extension_A"]],
        "force_reduced": [float(a) for a in res["force_reduced"]],
        "final_coords": [float(a) for a in final.reshape(-1)],
        "peak_force_reduced": res["peak_force_reduced"],
        "n_force_peaks": res["n_force_peaks"],
        "peak_step": res["peak_step"],
        "peaks": res["peaks"],
        "native_contacts_remaining": q_final,
        "energy_final": energy_final,
    }


def synthetic_case(name: str, xyz: np.ndarray, noise_seed: int = 1) -> dict:
    coords = np.asarray(xyz, dtype=float)
    flat = [float(a) for a in coords.reshape(-1)]
    m = model_arrays(coords)
    out = {
        "name": name,
        "coords": flat,
        "model": m,
        "static": static_energy_and_force(flat),
        "end_to_end_A": float(np.linalg.norm(coords[-1] - coords[0])),
        "runs": [],
    }
    # Tier 1: zero temperature. noise_scale is exactly 0, so the reference and the
    # Rust engine integrate the identical deterministic step.
    out["runs"].append(_run_record("zero_temperature", coords, CFG_ZERO, None))
    # Tier 2: injected noise. The reference draws them, writes them out, and the
    # Rust engine must consume the same numbers in the same order.
    n_steps = 60
    rng = np.random.default_rng(noise_seed)
    noise = rng.normal(size=(n_steps, len(coords), 3))
    cfg = dict(speed=0.2, spring_k=0.1, n_steps=n_steps, dt=0.002,
               temperature=0.5, friction=1.0)
    out["noise_seed"] = noise_seed
    out["noise"] = [float(a) for a in noise.reshape(-1)]
    out["runs"].append(_run_record("injected_noise", coords, cfg, noise))
    return out

# ---PDB AND PEAK CASES---

def pdb_case(pdb_file: str, chain: str | None, window: tuple[int, int] | None,
             cfg: dict) -> dict:
    with open(pdb_file, "r", encoding="latin-1") as fh:
        text = fh.read()
    s = parse_pdb(text, chain=chain, window=window)
    coords = np.asarray(s["coords"], dtype=float).reshape(-1, 3)
    return {
        "name": os.path.splitext(os.path.basename(pdb_file))[0],
        "file": os.path.basename(pdb_file),
        "chain_requested": chain,
        "window_requested": list(window) if window else None,
        "structure": s,
        "model": model_arrays(coords),
        "static": static_energy_and_force(s["coords"]),
        "end_to_end_A": float(np.linalg.norm(coords[-1] - coords[0])),
        "runs": [_run_record("zero_temperature", coords, cfg, None)],
    }


def peak_cases() -> list[dict]:
    """Pure synthetic force traces, so the peak rule is tested on its own.

    The engine's peak statistics fold together smooth5, median, std and the
    tie-break of argmax; mixing that into a simulation mismatch hides which of the
    four broke, so these carry no physics at all.
    """
    ramp = np.arange(12, dtype=float)
    twin = [0.0] * 40
    single = [0.0] * 30
    buried = [0.0] * 30
    # A five-sample triangular bump; the centre keeps its own height so two bumps
    # of different sizes can be compared.
    shape = ((-2, 1.0), (-1, 3.0), (0, None), (1, 3.0), (2, 1.0))

    def stamp(trace, centre, height):
        for d, h in shape:
            trace[centre + d] = height if h is None else h

    stamp(twin, 10, 5.0)
    stamp(twin, 25, 5.0)
    stamp(single, 15, 5.0)
    stamp(buried, 8, 5.0)
    stamp(buried, 20, 9.0)
    cases = [
        {"name": "monotone", "force": [float(a) for a in ramp]},
        {"name": "flat5", "force": [2.0] * 5},
        {"name": "too_short", "force": [1.0, 4.0, 2.0]},
        {"name": "twin_equal_peaks", "force": twin},
        {"name": "single_peak", "force": single},
        {"name": "two_unequal_peaks", "force": buried},
    ]
    out = []
    for c in cases:
        f = np.asarray(c["force"], dtype=float)
        hits = _peaks(f)
        peak_force = float(f[hits].max()) if len(hits) else float(np.max(f))
        peak_step = int(hits[int(np.argmax(f[hits]))]) if len(hits) else int(np.argmax(f))
        out.append({
            **c,
            "smooth5": [float(a) for a in
                        np.convolve(f, np.ones(5) / 5, mode="same")],
            "peaks": [int(i) for i in hits],
            "n_peaks": int(len(hits)),
            "peak_force": peak_force,
            "peak_step": peak_step,
        })
    return out

# ---MAIN---

def _json_safe(value):
    """Replace non-finite floats with None so the fixture is strict JSON.

    `straight6` has no native contacts, so the reference returns NaN for
    contacts-remaining (pull.py:76-77). Writing `NaN` would make the fixture
    unreadable by any real JSON parser - which is exactly the trap
    `PullResult::to_json` must not fall into, so the fixture states the value as
    null and the Rust test asserts the engine agrees it is undefined.
    """
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else None
    if isinstance(value, np.floating):
        return _json_safe(float(value))
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def main() -> None:
    out: dict = {
        "constants": {
            "BOND_K": BOND_K,
            "ANGLE_K": ANGLE_K,
            "CONTACT_CUTOFF": CONTACT_CUTOFF,
            "NONNATIVE_SIGMA": NONNATIVE_SIGMA,
            "SEQ_SEP": SEQ_SEP,
            "ANCHOR_K": ANCHOR_K,
        },
        "synthetic": [],
        "pdb": [],
        "peaks": peak_cases(),
    }

    # ---- tiny synthetic traces: full Hamiltonian + trajectory parity ----
    out["synthetic"].append(synthetic_case("helix12", helix(12)))
    out["synthetic"].append(synthetic_case("sheet10", sheet(10)))
    out["synthetic"].append(synthetic_case("collapsed9", collapsed(9)))
    out["synthetic"].append(synthetic_case("straight6", straight(6)))

    # ---- real structures: parse rules, contact map, zero-temperature pull ----
    wanted = [
        ("1UBQ.pdb", None, None),
        ("1BRF.pdb", None, None),
        ("1TIT.pdb", None, None),
    ]
    for fname, chain, window in wanted:
        path = os.path.join(PDB_DIR, fname)
        if not os.path.isfile(path):
            print(f"note: {fname} not present, skipped")
            continue
        out["pdb"].append(pdb_case(path, chain, window, CFG_PDB))
        dst = os.path.join(FIX_DIR, fname)
        os.makedirs(FIX_DIR, exist_ok=True)
        with open(path, "r", encoding="latin-1") as fh:
            text = fh.read()
        with open(dst, "w", encoding="latin-1", newline="\n") as fh:
            fh.write(text)

    # ---- the domain picker and explicit chain, not just the default pick ----
    if out["pdb"]:
        base = out["pdb"][0]
        path = os.path.join(PDB_DIR, base["file"])
        lo = base["structure"]["residues"][0]
        window = (lo + 1, lo + 40)
        case = pdb_case(path, base["structure"]["chain"], window, CFG_ZERO)
        case["name"] = base["name"] + "-domain40"
        out["pdb"].append(case)

    out = _json_safe(out)
    path = os.path.join(HERE, "expected_protein.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True, allow_nan=False)
    size = os.path.getsize(path)
    print(f"wrote {path} ({size/1e6:.2f} MB)")
    for c in out["synthetic"]:
        print(f"  synthetic {c['name']}: n={c['model']['n']} "
              f"contacts={len(c['model']['ci'])} "
              f"E={c['static']['energy']:+.6f} "
              f"zeroT_peak={c['runs'][0]['peak_force_reduced']:+.6f}")
    for c in out["pdb"]:
        s = c["structure"]
        print(f"  pdb {c['name']}: {s['label']} n={s['n']} "
              f"contacts={len(c['model']['ci'])} notes={len(s['notes'])} "
              f"zeroT_peak={c['runs'][0]['peak_force_reduced']:+.6f}")


if __name__ == "__main__":
    main()
