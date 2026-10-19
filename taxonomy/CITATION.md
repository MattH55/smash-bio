# Taxonomy sources (taxonomy 1.0.0)

The module tree and the facets are a crosswalk of three published descriptions of
optical-tweezers experiments, plus the SMASH-BIO extensions for classes Table 3
does not cover (receptor–ligand, molecular tension sensors, methods).

## Halma 2025 — Table 3 types, bead geometry, trap control

Halma MTJ, Kumar S, van Eck J, Abeln S, Gates A, Wuite GJL. FAIR data for
optical tweezers experiments. *Biophysical Journal*. 2025;124(8):1255–1272.
doi:10.1016/j.bpj.2025.03.001

Contributes the four Table 3 columns (`unfolding`, `dna_protein`,
`force_generation`, `rheology`), the bead-geometry and trap-control vocabulary
that `bead_geometry` and `measurement_modes` are mapped from, and the
one-bead / three-bead distinction used for processivity. Processive motors stay
under `force_generation` even when the track is DNA or RNA, because the
observables and the assay match that column. The module pages for
`processive_motors` and `force_generation` state that a one-bead run length and
a three-bead stroke are not the same measurement.

## Haghizadeh 2023 — biological questions (Simpson and colleagues)

Haghizadeh A, Iftikhar M, Dandpat SS, Simpson T. Looking at biomolecular
interactions through the lens of correlated fluorescence microscopy and optical
tweezers. *International Journal of Molecular Sciences*. 2023;24(3):2668.
doi:10.3390/ijms24032668

Contributes the biological-question sections that the sub-modules follow:
nucleic-acid–protein interactions, RNA structure, condensates, protein folding,
cellular transport, and molecular tension. `correlative_fluorescence` records
the fluorescence channel this paper treats as part of the measurement.

## Malinowska 2024 — measurement modes and assay types

Malinowska AM, van Mameren J, Peterman EJG, Wuite GJL, Heller I. Introduction
to optical tweezers: background, system designs, and applications. *Methods in
Molecular Biology*. 2024;2694:3–28. doi:10.1007/978-1-0716-3377-9_1

Contributes `measurement_modes` (§4.1: force–extension, distance clamp, force
clamp, force ramp, force jump, oscillatory microrheology, passive equilibrium)
and `assay_type` (§4.2: translocation, mechanical change, unfolding, dual
tether, large object, and the related in-vivo / polymerisation / passive-tether
cases SMASH-BIO keeps as separate values).

## What SMASH-BIO adds

`extended` holds three modules Table 3 does not column: `receptor_ligand`,
`mechanobiology`, and `methods`. Those modules are SMASH-BIO's, not a claim
that the three papers define them.
