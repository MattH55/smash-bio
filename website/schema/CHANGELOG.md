# SMASH-BIO schema changelog

## 1.0.0 - 2026-10-10

- Added the DNA/RNA smFRET record and results schemas.
- Added modality-neutral shared definitions in `smash-common.schema.json`.
- Added explicit hybrid-study links from FRET records to `SMFS-*` records.
- Preserved the published SMFS 3.1.0 schema files unchanged to avoid a validation regression.
- Aligned the smFRET technique vocabulary with the module brief: `technique.primary`
  is one of `smfret_confocal_burst`, `smfret_tirf_widefield`,
  `smfret_confocal_scanning_immobilized`, `smfret_in_cell`,
  `smfret_nanopore_or_zmw`, `smfret_methods`, with `excitation_scheme`, `geometry`
  and `correlative` carrying the additional detail.
- Added the Table 3 blocks `construct`, `hardware` (confocal / widefield /
  zmw_or_nanopore) and `solution` (denaturant, photostabilisation), the analysis
  block (`correction_factors`, `accurate_vs_apparent_E`, `software`,
  `kinetic_model`) and the `data_flags` block (`has_raw_photon_data`,
  `has_raw_movies`, `has_raw_traces`).
- Added an SPT, a mass-photometry and a single-channel module under
  `schema/modules/` (see `docs/modules/`), staged against
  `schema/modules/_shared-pending.schema.json`.

### Modules (SPT / mass photometry / single channel) — staging retired

- The 50 module-schema references to the staging copy are now
  `../smash-common.schema.json#/$defs/...`, and
  `schema/modules/_shared-pending.schema.json` is deleted; the staging `$defs`
  were identical to `smash-common`'s (whose `Result` is a superset, adding
  `trace_set`), so no module record changes meaning.
- Module records now use the shared `DataAvailability.status`
  `fulltext_checked_none` when the full text was read and no deposit was found,
  and keep `unknown_no_fulltext` when only the abstract was available.