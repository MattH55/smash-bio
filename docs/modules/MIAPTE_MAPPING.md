# Positioning the SPT schema against MIAPTE

MIAPTE — the **M**inimum **I**nformation **A**bout a **P**article **T**racking
**E**xperiment — is a community reporting guideline for particle-tracking
studies, analogous to the SMASH-BIO Table 3 baseline for force spectroscopy.
SMASH-BIO does not try to replace it: `smash-spt-record.schema.json` is designed
so that a record *is* a MIAPTE-shaped report, with the SMASH-BIO additions that
make records machine-actionable (identifiers, evidence, data availability,
completeness).

> Note: the exact MIAPTE checklist wording is owned by the MIAPTE authors. The
> table below maps the SMASH-BIO SPT fields to the MIAPTE reporting categories;
> confirm the exact field names before claiming conformance. See the open
> question in `REPORT-modules.md`.

| MIAPTE reporting category | SMASH-BIO SPT field |
|---|---|
| Sample / biological system | `biological_system.entities[]` (+ `identifiers[]` UniProt, `evidence`) |
| Probe / label | `probe.type`, `probe.name`, `probe.labeling_strategy`, `probe.labeling_density` |
| Sample environment / context | `sample.context`, `sample.cell_line` (Cellosaurus), `sample.organism` |
| Imaging / acquisition | `hardware.illumination`, `hardware.camera_model`, `hardware.camera_type`, `hardware.frame_rate`, `hardware.pixel_size`, `hardware.objective_na` |
| Tracking parameters | `tracking.software`, `tracking.max_jump`, `tracking.gap_frames`, `tracking.min_track_length` |
| Analysis model | `results[].model` and `technique.variant`, `technique.dimensions` |
| Derived measurements | `results[]` (`diffusion_coefficient_um2_s-1`, `bound_fraction`, `residence_time_s`, ...) with units and `provenance` |
| Raw data | `trajectory_sets[]` (`TrajectorySet`: columns -> standard names, movie files/formats) and `data_flags` |
| Data availability | `data_availability` (status, repository, license, `has_linked_dataset`) |
| Provenance / curation | `provenance[]`, `fair_completeness` |

## Why this shape is MIAPTE-friendly

- **A `TrajectorySet` maps columns to standard names and units**, which is the
  part MIAPTE cares about most: a reader can load the file without guessing what
  `col3` means.
- **Movies and trajectories are both first-class** (`movie_files`, `movie_format`,
  `has_trajectories`, `has_raw_movies`), matching studies that publish either or
  both.
- **No invented identifiers.** Terms without a checked UniProt/Cellosaurus ID
  carry no ID rather than a plausible-looking one.

## Cross-module reuse

`diffusion_coefficient_um2_s-1` is deliberately identical (name and unit) in the
SPT and mass-photometry results schemas, so MSPT values are directly comparable
across the two module pages.