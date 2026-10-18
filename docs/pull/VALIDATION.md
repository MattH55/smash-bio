# SMASH-Pull validation gates

**Status of this file:** the criteria in sections 1–6 were written on 2026-10-14 *before* any gate was run
(brief, Phase 7). Results are appended below the lock line and never edit the criteria. If a gate fails, the
affected part ships behind an **experimental** label and the report says why (brief, hard rule 4).

Common definitions used by every protein gate:

- **Tension** is the pulling-spring force along the pull direction, positive when the molecule is stretched:
  `tension = k_spring * (anchor_position - x_pull) . direction`. The Python reference (`pull.py`) records the
  same quantity with the opposite sign (`dot(-spring, direction)`), so its trace is multiplied by -1 before any
  comparison. (Known issue in the reference, documented in `PROTOCOL.md`.)
- **Peak tension** of a trajectory = the maximum of the 5-point zero-padded running mean of tension (the
  reference's own smoothing kernel, `pull.py:_peaks`), over the whole trajectory.
- **Contact break step**: a native contact (|i-j| >= 4, Cα-Cα < 8 Å in the native structure) is *broken* when
  its distance exceeds 1.2 x its native distance (`pull.py:_contacts_remaining`). Its break step is the first
  checked step after which it stays broken until the end of the run; contacts still intact at the end get
  `n_steps`. Distances are checked every 25 steps in both engines.
- **Production engine** = `pull-engine/src/fast.rs`: the same Hamiltonian as `go_model.py` (bonds, angles,
  dihedrals, native 6–12 contacts, non-native (σ/r)^12 with σ = 4 Å and a 12 Å cut-off), with analytic dihedral
  gradients, a Verlet neighbour list (2 Å skin) for non-native pairs and one force evaluation per step. This
  is the code the browser runs.

## Gate 1 — protein engine vs reference

**1a, deterministic parity (parity path).** `cargo test --test protein_parity`: native energy and force, contact
map, PDB parsing, zero-temperature trajectories and injected-noise trajectories agree with
`expected_protein.json` (exported from `go_model.py` + `pull.py`) to relative 1e-9 on traces and 1e-7 on final
coordinates. Pass = every test passes.

**1b, production force field equals the reference force field.** On the native structure and on 20 thermally
perturbed copies (Gaussian displacement σ = 0.3 Å, fixed seed) of 1TIT, 1UBQ and 2GB1, the production force
agrees with `energy_and_force` (parity path, itself bit-matched to the reference) to relative 1e-5 per atom
(central-difference truncation of the reference's dihedral gradient is O(h²) with h = 1e-5 Å) and the energy to
relative 1e-9. Pass = all structures pass.

**1c, statistical equivalence of trajectories.** Proteins: titin I27 (1TIT chain A), ubiquitin (1UBQ chain A),
GB1 (2GB1 chain A). Protocol G1, identical in both engines: kT = 0.5, γ = 1, spring k = 0.1 ε/Å², Δt = 0.005,
speed 2.0 Å/τ, 6,000 steps, anchor = first Cα, pull = last Cα. 30 replicas per engine: reference seeds 1–30
(`numpy.random.default_rng`), production seeds 1–30 (sfc64). For each protein:
- two-sample Kolmogorov–Smirnov test on peak tension: **p > 0.05**;
- Spearman ρ between the two engines' mean break step per native contact (all native contacts): **ρ ≥ 0.9**.

Pass = all three proteins pass both tests.

## Gate 2 — protein geometry against experiment

Protocol P_std (the browser's "standard" run at its middle speed): kT = 0.5, γ = 1, k = 0.1 ε/Å², Δt = 0.005,
speed 0.5 Å/τ, travel = 0.9 x (3.8 Å x (sequence separation of the pull points) − native distance), 20 replicas,
production engine. The force compared is the peak tension.

**2a, ubiquitin.** 1UBQ chain A pulled N–C (residues 1 and 76) and K48–C (residues 48 and 76). Experiment
(Carrion-Vazquez et al. 2003): N–C is the stronger direction. Pass = mean peak tension N–C > K48–C with a
one-sided Mann–Whitney p < 0.05.

**2b, GFP.** 1EMA chain A pulled between the residue pairs measured by Dietz et al., PNAS 103:12724 (2006),
Table 1: 117–182 (548 pN), 182–212 (356 pN), 3–132 (346 pN at 2 µm/s; 407 pN at 12 µm/s), 132–212 (127 pN),
3–212 (117 pN). Pass = **both**: (i) every one of the three strong directions {117–182, 182–212, 3–132} has a
higher simulated mean peak tension than both weak directions {132–212, 3–212}; and (ii) Spearman ρ between
simulated means and the experimental forces (3–132 taken as 346 pN) ≥ 0.7.

## Gate 3 — nucleic-acid engine vs ViennaRNA

As written in the brief: MFE structures and free energies agree with ViennaRNA within 0.1 kcal/mol on 100 random
sequences. Pre-declared: this gate requires a secondary-structure folding algorithm (Zuker/McCaskill). If the
engine does not implement one, the gate is **not_run**, MFE prediction is not offered, and the page requires a
single-hairpin structure (auto-detected perfect stem or a user dot-bracket); multi-branch and pseudoknotted
inputs are refused with a message.

## Gate 4 — nucleic-acid experiments (sequence class)

The published sequences of the benchmark hairpins are not reachable from this environment (Woodside et al. 2006
supplementary tables are behind a bot check; Forns et al. 2011 give theirs only inside a figure). The gate is
therefore run on the **sequence class** of the one fully reported hairpin:

- Woodside et al., PNAS 103:6190 (2006): hairpin 20R55/4T (20-bp random stem, 55 % GC, T₄ loop), 23 °C,
  200 mM KCl: **F½ = 13.2 ± 0.7 pN, Δx = 18 ± 2 nm**.
- Test set: 30 random 20-bp stems with exactly 11 G/C (seed 20261014), loop TTTT, DNA, 296.15 K, 200 mM
  monovalent, browser thermodynamics (stacks at the measurement temperature + NNDB hairpin-loop initiation).
- Pass = **both**: median predicted F½ within ±3.0 pN of 13.2 pN, and median Δx at F½ (released single strand
  at F½ minus the 2.0 nm folded-hairpin projection) within ±20 % of 18 nm.
- Reported alongside, not gated: the same set under the reference-parity thermodynamics (37 °C tables, no loop
  term), to show what the loop and temperature terms change.

Self-consistency, also gated: class medians of F½ for 20-bp stems at 0, 25, 55, 75 and 100 % GC increase
monotonically (Woodside 2006 report increasing stability with GC content).

## Gate 5 — determinism

(a) The same inputs and seed give byte-identical result JSON from the native build (`cargo run --example`) and
the WebAssembly build in Chrome, for one protein run (1UBQ, quick) and one nucleic kinetic run. (b) Two
consecutive runs in Chrome are byte-identical. (c) Firefox and Safari: run if available. If a browser is not
available the sub-gate is **not_run** (not passed). Rationale for expecting cross-browser identity is recorded
in `ARCHITECTURE.md` (all floating-point math, including transcendental functions, is inside the wasm module).

## Gate 6 — performance

(a) Titin I27 (89 residues) "standard" run (3 speeds x 10 replicas) completes in **< 60 s** in Chrome on this
machine with `navigator.hardwareConcurrency` workers. A ~100-residue structure is timed as well and reported.
(b) Phone: not available in this environment → **not_run**; the page restricts phones (detected as < 4 cores or
touch-primary narrow screens) to quick mode with a warning.

<!-- VALIDATION_LOCK: criteria above this line are frozen. Results go below. -->

## Results

Runs of 2026-10-14. Raw outputs are in `tests/pull/results/*.json`; a summary for the site is in
`website/pull/data/validation.json` (built by `tests/pull/build_validation.mjs`). Nothing above the
lock was changed after any run.

| Gate | Result | Numbers |
|---|---|---|
| 1a | **pass** | `cargo test`: nucleic parity 9/9, protein parity 10/10 (plus 62 unit tests). |
| 1b | **pass** | `fast_force_equals_reference_force`: 1TIT/1UBQ/2GB1 × 21 conformations; energy ≤ 1e-9, force ≤ 1e-5 of scale. |
| 1c | **pending** | Harness `tests/pull/gate1c.py` is running. The Python reference costs ≈ 1 s per step at 89 residues, so 90 × 6,000-step reference trajectories take ≈ 10 h on this machine. Results cache per seed in `results/gate1c_cache/`; rerunning the script resumes and writes `results/gate1c.json`. |
| 2a | **pass** | Ubiquitin N–C 11.78 ± 0.25 vs K48–C 5.98 ± 0.16 ε/Å (20 replicas each); one-sided Mann–Whitney p = 3.4e-8. Caveat recorded with the result: N–C also spans more chain (75 vs 28 residues), so drag (PROTOCOL P4) contributes in the same direction. |
| 2b | **fail** | GFP mean peaks: 117–182 12.85, 182–212 6.46, 3–132 24.08, 132–212 15.42, 3–212 33.36 ε/Å. Strong-above-weak: false. Spearman ρ with experiment = −0.80. Peaks order by pulled span (209 > 129 > 80 > 65 > 30 residues): drag dominates at 0.5 Å/τ. |
| 3 | **not_run** | No secondary-structure folding algorithm (as pre-declared). |
| 4 | **fail** | Median F½ 18.51 pN vs 13.2 ± 3.0 → fail. Median Δx 16.39 nm vs 18 ± 20 % → pass. GC series 0/25/55/75/100 % → 12.97/15.62/18.37/19.89/22.43 pN, monotonic → pass. Reference thermodynamics (not gated): median F½ 25.52 pN. |
| 5a | **pass** | SHA-256 of the result JSON identical, native vs Chrome 155.0.8059.40, for `protein_1UBQ_quick` and `nucleic_kinetic_hp20`. Re-checked after the last engine rebuild. |
| 5b | **pass** | Two fresh Chrome workers: identical hashes. |
| 5c | **not_run** | Firefox and Safari not installed on the test machine. |
| 6a | **fail** | I27 standard (30 trajectories) 168.7 s with 12 workers in Chrome; target < 60 s. Machine: 6 cores / 12 threads, about 3 cores busy with unrelated processes during the run. Also measured: talin R3 (2L7A, 131 residues) standard 372.2 s; I27 quick 15.6 s. |
| 6b | **not_run** | No phone available. |

**Consequences (per the brief).** The protein engine (2b, 6a failed; 1c pending) and the nucleic engine
(4 failed on absolute force) both ship labelled **experimental**. The labels sit on the simulator page,
the results panels, `about.html` and `benchmarks.html`.

**Not done, deliberately.** No parameter was re-fitted after a failure: ssDNA elasticity for Gate 4, and
speed/friction for Gate 2. Doing so would turn the gates into fits. The open questions are in
REPORT-pull.md.


---

# Phase 2 gates (written 2026-10-15, before any Phase 2 code was run)

<!-- VALIDATION_LOCK_PHASE2_EXPORT -->

## Gate X — exports to standard MD programs

**X1, OpenMM port of the Cα model is the same Hamiltonian.** `openmm_go.py` builds the SMASH-Pull Cα
Gō model in OpenMM. The unit map is 1 Å = 0.1 nm and ε = 1 kJ/mol, with mass 1 u, so τ = 0.1 ps and
kT = 0.5 ε corresponds to 60.14 K. For 1TIT, 1UBQ and 2GB1 chain A, compare against the engine at the
native structure and at 5 conformations from an engine trajectory. Pass: total energy within 1e-6
relative, and every force component within 1e-4 of the largest force component. Units are converted,
so the comparison is in model units.

**X2, OpenMM port gives statistically the same pulls.** Protocol G1 (Gate 1c), 20 replicas per engine,
1UBQ chain A. The OpenMM run uses the CustomIntegrator that reproduces the engine's step order, with
OpenMM's own random numbers. Pass, with the same tests as Gate 1c: KS p > 0.05 on peak tension, and
Spearman ρ ≥ 0.9 between the per-contact mean break steps.

**X3, all-atom OpenMM script runs.** `prepare.py` then `openmm_allatom.py` on 1UBQ (N–C). Two runs:

- implicit solvent (GBn2), 0.5 ps equilibration plus 2 ps of pulling, OpenMM CPU platform;
- explicit solvent, built (solvation, ions, system creation) but run for only 50 steps.

Pass: both finish without error. The pull CSV has the expected columns and monotonically increasing
time. The reported extension at step 0 equals the native anchor–pull Cα distance within 0.05 nm.

**X4, GROMACS bundle.** GROMACS is not installed on the test machine, so this gate is **not_run** by
construction. A static check is recorded but does not count as a pass: every .mdp key appears in the
GROMACS 2024 mdp option list compiled into the test.

**X5, database pack.** Every hub system with a UniProt accession and an AlphaFold model gets a setup
file. Pass: each file validates against `pull_setup.schema.json`. Also, `prepare.py` succeeds on a
random sample of 10 setups (seed 20261015), fetching from AlphaFold DB.
