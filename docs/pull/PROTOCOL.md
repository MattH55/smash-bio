# SMASH-Pull protocols

What the simulator runs, what it reports, and where it departs from the reference pipeline
(`Meeta Analysis/Simulation Comparison/smash-sim`). Every number on the page follows one of these rules.

## Protein

### P1. Model
The reference Cα structure-based Hamiltonian, unchanged (`smashsim/go_model.py`). Its terms are:

- bonds 100 (r − r₀)²;
- angles 20 (θ − θ₀)²;
- dihedrals (1 − cos Δφ) + ½(1 − cos 3Δφ);
- native contacts, for pairs with |i − j| ≥ 4 and Cα–Cα < 8 Å: LJ 12-6 with minimum −ε at r₀ (10-12 selectable);
- non-native pairs: (4 Å/r)¹² inside 12 Å.

Reduced units: ε, Å, τ; kT = 0.5 ε, γ = 1.
The fixed residue is held by a 50 ε/Å² restraint at its native position.

### P2. Integrator
The reference velocity-Verlet Langevin step (`pull.py:30-42`). Velocities get a half kick, then
positions are updated, then friction and noise are applied (√(2γkT dt) · N(0,1)), then a second half kick.

Two changes to how the step is evaluated, neither of which alters the physics:

- one force evaluation per step (the reference's second evaluation equals the next step's first);
- an analytic dihedral gradient, equal to the reference central difference to O(h²).

### P3. Reported tension
`tension = k (anchor − x_pull) · d̂`, **positive when stretched**.

The reference records `dot(−spring, d̂)`, which is negative under tension. Its "peak force" (the largest
value among peaks) therefore picks the sample *closest to zero*. Gate 1c compares against the reference
trace multiplied by −1. Peak tension is the maximum of the zero-padded 5-point running mean (the
reference's `np.convolve(…, ones(5)/5, "same")`).

### P4. Speeds, time step and drag
- dt = 0.01 τ. A single-seed check at dt = 0.02 gave I27 peaks 10–15 % lower than at 0.01, which may be
  systematic, so 0.02 was not adopted.
- Run plans:
  - Quick: 0.2 Å/τ × 3 replicas.
  - Standard: 0.05, 0.1 and 0.2 Å/τ × 10 replicas.
  - Custom: any speeds, up to 50 replicas.
- Travel: 0.9 × (3.8 Å × sequence separation − native distance). In optical-trap-like mode
  (k = 0.05 ε/Å²) a further max(0, 8/k − 80) Å is added so that the softer spring can still load the chain.
- **Drag.** With γ = 1, a chain segment of N beads dragged at speed v carries a friction force of order
  γ v N/2. At browser-affordable speeds this is comparable to the unfolding forces themselves:
  - at 0.5 Å/τ (protocol P_std, Gate 2) it dominates;
  - at 0.05–0.2 Å/τ it is still a large fraction.

  Consequences:
  - peak tensions grow with the pulled span, so directions with different spans cannot be ranked by peak;
  - Bell–Evans slopes include a viscous component.

  The pages state this next to every protein result.

### P5. Unfolding events (not the reference rule)
- **Smoothing.** The tension is smoothed with a centred running mean of w samples, where w = the largest
  odd number ≤ n/100 (minimum 5).
- **Noise and baseline.** noise_sd is the RMS of (raw − smoothed); the baseline is the 10th percentile
  of the smoothed trace.
- **Event.** An event is a local maximum of the smoothed trace followed by a drop of at least
  max(0.15 × (peak − baseline), 3 noise_sd) before the trace rises above the peak again.
- **Rip size.** This is the extension gained before the trace next regains the peak force.

The reference's `median + 0.5 sd` rule is kept only in the parity path.

### P6. Contour length released (ΔLc)
- **Effective contour.** The effective contour Lc_eff(t) is the shortest path from the fixed to the
  pulled residue in a graph with:
  - bonds weighted by their native length;
  - native contacts still intact at step t, weighted by their native Cα–Cα distance.
- **When a contact is intact.** A contact is intact at step t if its break step (the last step it was
  within 1.2 r₀, plus the 25-step check interval) is later than t, or if it never broke.
- **ΔLc of an event.** ΔLc(event k) = Lc_eff(peak of event k + 1, or end of run) − Lc_eff(peak of event k).
- **Totals.** Summed over events this is the contour released. At the slowest standard speed it is
  28.2 nm for I27 (experiment 28.1 nm), 23.7 nm for ubiquitin N–C and 16.9 nm for GB1. Faster runs
  end before the last contacts break, giving 26.8 and 23.9 nm for I27.
- **Why not a WLC fit.** A WLC fit to the simulated curve was tried first and rejected. Drag makes the
  chain look stiff, which gave about 9 nm per event and a total far below the contour.

### P7. Loading-rate fit
Bell–Evans: F* = (kT/xβ) ln(k v) + c, fitted by least squares to every replica's peak tension. The
reported quantities are xβ = kT/slope (Å) and its standard error from the slope's standard error.

In force-clamp mode the unfolding time is the first time the extension exceeds
d₀ + ½(Lc − d₀). Then ln t is fitted against F, and xβ = −kT · slope.

### P8. Unfolding order
Each native contact's break step, divided by the run length, is averaged over the replicas at the
slowest speed. A per-residue value is the mean over that residue's contacts.

### P8b. Unfolding pathways and movies
- **Contact blocks.** Native contacts are grouped into blocks: contacts between sequence segments of
  B = max(4, round(n/12)) residues. Only blocks with at least 3 contacts count.
- **When a block breaks.** A block's break time in a run is the median of its contacts' break fractions.
- **Pathway.** A run's pathway is its *initiating rupture*, the block that breaks first. Pathways with
  a single run are reported as "other".
- **Why not rank correlation.** Rank correlation over all contacts was tried first and rejected. The
  shared peel-from-the-pulled-end order puts every pair of runs at ρ > 0.85 (I27, GB1, protein L,
  ubiquitin), which hides real differences in which element lets go first.
- **Representative.** Each pathway's representative is its medoid: the run whose full contact-break
  order (Spearman ρ) agrees best with the rest of its pathway. At most 3 pathways are shown, largest first.
- **Movies.** The movie re-runs each representative with the same seed and 240 frames. The page
  checks that the tension trace is bit-identical to the original run; it relies on Gate 5 determinism.
  - Frames are interpolated for display, and the pull axis is oriented left to right.
  - Each residue is coloured by the fraction of its native contacts still within 1.2 r₀.
  - The initiating block is drawn with a yellow halo.
  - Recording uses MediaRecorder: MP4/H.264 where supported, otherwise WebM.
- **Example result.** I27 always initiates at residues 1–7 ↔ 71–77, at all three speeds. The strand
  assignment of these blocks has not been checked against DSSP.
  Ubiquitin N–C initiates at β1–β5 (1–6 ↔ 67–72) in 6–7 of 10 runs, with 2–3 alternatives.

### P9. Structure preparation
- **Chain.** The largest chain is used unless one is chosen. Altlocs keep the first copy, and a NMR
  file contributes its first model.
- **Domain.** Domains are given as residue windows of at most 400 residues.
- **AlphaFold models.** These are detected from the header. Residues with pLDDT below the cut-off
  (default 50) lose their native contacts, and the masked pairs do not become repulsive.
- **Reported, not modelled.** Disulfides (SSBOND records, or SG–SG < 2.5 Å), metal sites, ligands and
  chain breaks (a numbering gap, or a Cα gap > 4.2 Å) are reported but not modelled.

### P10. Units
- **Forces** are in ε/Å: never converted, never labelled pN. `website/pull/data/calibration.json`
  holds `null`.
- **Times** are in τ.
- **Lengths** are in Å or nm, from the structure.

## Nucleic acids

### N1. Construct and states
The construct is either a hairpin (stem of N bp plus a loop of L nt) or a duplex unzipped from one end.
The state n = 0…N counts base pairs open from the handle end. The released single strand is
m(n) = 2n nt for n < N, and 2N + L nt for the open hairpin.

The folded part projects a fixed length: D_FOLD = 2.0 nm for n < N, and 0 for the open hairpin.

### N2. Chemistry. Browser default, departing from the reference
- **Stacks.** Watson–Crick nearest-neighbour stacks are evaluated at the measurement temperature T:
  ΔG = ΔH − TΔS (SantaLucia 1998 for DNA; Xia et al. 1998 for RNA). The reference evaluates them at 37 °C
  whatever the pull temperature.
- **Salt.** −0.114 (N − 1) ln[Na⁺] kcal/mol (SantaLucia 1998), scaled by T/310.15 because the term is
  entropic. The reference applies it unscaled.
- **Mg²⁺.** [Na⁺]eq = [Na⁺] + 120 √[Mg²⁺] (mM). This is approximate and flagged in the output.
- **Hairpin-loop initiation.** NNDB values: the DNA table, and Turner 2004 for RNA, for loops of
  3–30 nt. Above 30 nt they are extrapolated as 1.75 RT ln(L/30). The temperature dependence is
  ΔG(T) = ΔH − T (ΔH − ΔG₃₇)/310.15. The reference has no loop term.
- **Reference mode.** "Reference thermodynamics" (37 °C stacks, no loop term) remains selectable for
  comparison.

**Side effect of the reference mode.** Without a loop term, the state with one base pair left is
nearly as low in energy as the open state. P(n = N) therefore reaches ½ only at a higher force. This is
why the reference-mode F½ of the Gate 4 class is *higher* (25.5 pN) than the browser's (18.5 pN), even
though its ΔG is smaller.

### N3. Mechanics
- **Single strand.** Marko–Siggia WLC with 0.59 nm/nt and Lp 0.75 nm (the reference values).
- **Handles.** dsDNA as an extensible WLC: 0.34 nm/bp, Lp 50 nm, stretch modulus 1000 pN.
- **Probe.** A trap or cantilever spring of stiffness k.
- **Free energy at fixed trap position X.** G(n, X) = G_chem(n) + F X − ∫₀^F X_n(F′) dF′, where
  X_n(F) = handles(F) + F/k + m(n) · ss(F) + D(n). It is tabulated on a 0.01 pN grid to 100 pN.

### N4. Reported quantities
- **F½** is the force at which P(n = N) = ½ in the constant-force ensemble.
- **Δx at F½** is the molecular extension change at F½ between n = N and n = 0. It includes the 2 nm
  folded projection.
- **Intermediates** are local minima of G_F(n) more than 1 kT below both neighbouring barriers.

### N5. Kinetics
- **Rates.** Hops n → n ± 1 at rate k₀ exp(−ΔG/2kT), with k₀ an input (default 10⁶ s⁻¹).
- **Simulation.** Exact Gillespie dynamics with the trap moving in 0.05 nm ticks.
- **Unfolding and refolding.** The first arrival at n = N counts as unfolding, and the first return to
  n = 0 as refolding.
- **Reported forces.** These are the forces an experimentalist would read: the folded-branch force at
  the moment of unfolding, and the open-branch force at refolding.
- **Clamp mode.** The molecule starts in the more populated basin. Dwell times are measured between
  transitions.
- **Default speeds and caps.**
  - Ramp: 100 nm/s, up to F½ + 8 pN, then back.
  - Event cap: 3 × 10⁸.
  - Construct size for kinetics: ≤ 200 bp in the UI.

### N6. Instrument presets

| Preset | Probe | Handles | Mode |
|---|---|---|---|
| Optical trap | 0.3 pN/nm | 2 kbp | ramp |
| Magnetic tweezers | 0.3 pN/nm | 2 kbp | clamp at F½ (or a set force) |
| AFM | 10 pN/nm | none | ramp |
