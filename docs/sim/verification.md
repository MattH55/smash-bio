# Simulations category — verification

Produced by `python -m sim.verify`. Re-run it after any pipeline change.

## Summary

- records built: **123**, schema failures: **0**
- records published in the download: **123**
- evidence snippets checked against the source text: **31** (failures: **0**; records without source text: 14)
- reduced-unit violations: **0**
- unverified identifiers in published records: **0**
- missing local assets referenced by `/sim/` pages: **0**

## Spot-check sample (15 records)

| record | system | model | units | n results | results | experiment links |
|---|---|---|---|---|---|---|
| SIM-000063 | Intrinsically disordered protein | other | physical | 0 |  | 5 (homolog) |
| SIM-000045 | Combining High-Pressure Perturbation wit | other | physical | 0 |  | 0 (none) |
| SIM-000064 | Talin-1 | other | physical | 0 |  | 5 (homolog) |
| SIM-000044 | Titin I27 domain | Go_CA | physical | 0 |  | 20 (same_molecule_different_geometry) |
| SIM-000036 | Fibrinogen / fibrin | SOP | physical | 0 |  | 5 (homolog) |
| SIM-000008 | Intrinsically disordered protein | other | physical | 0 |  | 5 (homolog) |
| SIM-000006 | Ku70/80 | other | physical | 0 |  | 5 (homolog) |
| SIM-000046 | Propensity to form amyloid fibrils is en | Go_CA | physical | 0 |  | 0 (none) |
| SIM-000062 | Titin (Ig/FnIII domains) | all_atom_explicit_solvent | physical | 0 |  | 20 (same_molecule_different_geometry) |
| SIM-000005 | Green fluorescent protein (GFP) | other | physical | 1 | dwell_time=0.5 s | 20 (same_molecule_different_geometry) |
| SIM-000089 | Double-stranded DNA (overstretching) | other | physical | 1 | velocity=500.0 nm/s | 5 (homolog) |
| SIM-000002 | Ubiquitin | other | physical | 1 | distance_to_transition_state=2.7 nm | 20 (same_molecule_different_geometry) |
| SIM-000091 | Double-stranded DNA (overstretching) | oxDNA | physical | 0 |  | 5 (homolog) |
| SIM-000111 | Phytochrome carrying its covalently boun | other | physical | 2 | unfolding_force=73.0 pN; contour_length=104.0 nm | 1 (same_molecule_different_geometry) |
| SIM-000098 | Riboswitch | other | physical | 0 |  | 5 (homolog) |

## Failures

- none
