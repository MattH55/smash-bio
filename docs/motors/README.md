# SMASH-MOTOR (processive motors module)

Build brief: `website/BRIEF_MOTORS.md`. Pipeline map: `PIPELINE_MAP.md`. Gate reports: `GATE1_REPORT.md`.

SMASH-MOTOR is a **separate module**, like SMASH-SIM (author decision at Gate 1): its own record type `MOTOR-######`,
its own schemas under `website/schema/motor/`, its own downloads (Phase 4). Each MOTOR record links the SMASH-BIO study
it was derived from (`smfs_record_id`). The SMASH-BIO schemas, build (`s06`, `s07`) and release are not changed.

## 1a + 1b. Schemas (SMASH-MOTOR v1.0.0)

- Generated from `hub/motors/spec.py` (`python hub/motors/spec.py`); a test checks the committed files match it.
- `smash-motor-record.schema.json`: identity (`record_id`, `smfs_record_id`, `category: processive_motor`), the study's
  `publication`, `technique` and `data_availability` (shared SMFS `$defs`, by reference), `assay_type`
  (`single_molecule` / `gliding_or_ensemble`), `family`, `isoform`, `uniprot`, `construct`, `oligomeric_state`,
  `adaptors`, `track`, `probe_link`, `load`, `feedback`, `chemistry`, `reporting`, `results`, `evidence` (a map keyed by
  field path; values are the SMFS `Evidence` object), `classification` (route, certainty, family hits, gazetteer hash)
  and `curation`. Closed objects; every motor field optional; enums closed with `other` plus `<field>_other`.
- `smash-motor-results.schema.json`: `MotorResult` with the motor vocabulary. Quantities that also exist in SMASH-BIO
  (`step_size`, `stall_force`, `velocity`, `processivity_run_length`, `dwell_time`, ...) keep the same names and
  canonical units; new ones: `force_velocity_curve` (value = array of `{force_pN, velocity_nm_s, force_err,
  velocity_err}`, hindering positive), `load_distance_parameter`, `substep_size`, `coupling_ratio`,
  `randomness_parameter`, `backstep_ratio`, `kcat`, `km`, `rotation_per_step`, `number_of_rate_limiting_steps`.
  Conditions: `load_pN`, `load_direction`, `atp_uM`, `feedback_mode`, `temperature_K`, `rise_per_unit_nm`,
  `rise_assumed` (0.34 nm/bp B-DNA default, flagged), `construct`. `source.unit_as_reported` keeps nt / bp units.
- Validators: `hub/motors/schema.py` (registers the SMFS schemas the refs point to).

## 1c. Classifier and records

- `hub/data/motor_gazetteer.yaml`: canonical entity names of `hub/gazetteer.py` → family, title regexes as fallback,
  exclusions (myosin II / muscle; generic "Myosin").
- `hub/motors/classify.py`: entities first, titles only when no entity resolves. No SMASH-BIO experiment class is
  required. Gliding / ensemble assays are kept and labelled `assay_type: gliding_or_ensemble`.
- `python hub/motors/build_records.py`: reads the SMASH-BIO release, writes `hub/out/motor/smash-motor-records.jsonl.gz`
  (validated; exit 1 on any invalid record). IDs are stable through `hub/motors/id_map.json`. Motor fields and results
  stay empty until Phase 2 extraction or curation; nothing is guessed.
- Counts: `python -I paper/scripts/motor_stats.py`. Review list: `python hub/motors/review_list.py`.

## 1d. Gold-set tooling

- `python hub/motors/sample_gold.py`: up to 50 MOTOR records per family, strata technique × decade, seed 20261019.
  Annotation order: kinesin, dynein, myosin_processive, helicase_translocase, then the other families in a seeded
  random order (stored in `sample.json`). Stubs carry record IDs, DOI and title only; existing stubs are never overwritten.
- `docs/motors/gold/TEMPLATE.yaml` and `python hub/motors/validate_gold.py [files]`.
- Annotations come from the author and annotators; the tooling never fills or infers a label.

Tests: `python -m pytest hub/motors`.
