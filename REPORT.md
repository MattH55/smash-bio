# smFRET module — report

## Status

- **Branch / PR:** not created. This workspace is **not a Git repository**
  (`c:\Users\matth\OneDrive\Documents\PhD\SMASH-BIO` has no `.git`), so no
  branch could be made and no remote/credentials are available. All work is
  present as files; create `feature/smfret-module` and commit when a repository
  with a remote is available.
- **Build / tests:** `python -m pytest hub -q` -> **56 passed, 58 subtests
  passed**. `python -m py_compile` clean on every new `hub/modules/*.py`.
- **SMFS non-regression:** the three published download artifacts are byte
  identical (SHA-256 asserted in `hub/test_smfret_schema.py` and
  `hub/test_modules_schema.py`); no SMFS schema or pipeline file was edited.

## What was implemented

| phase | deliverable | state |
|---|---|---|
| 0 orient | `docs/smfret/ARCHITECTURE_NOTES.md` (pipeline map + module plug-in) | done |
| 1 schema | `smash-fret-record.schema.json` v1.0.0, `smash-fret-results.schema.json`, `smash-common.schema.json`, `VERSION`, `CHANGELOG.md`, 7 example records | done, validates |
| 2 harvest / scope | FRET spec + `modules/harvest.py`, `modules/classify.py` (per brief queries, core/methods/out) | code done, **harvest not run** (see below) |
| 3 annotate / extract | `modules/gazetteer_ext.py` (FRET systems), `modules/extract.py` (grounded results, named tools), `modules/build_records.py`, `modules/crossrefs.py` | done; grounded-record tests pass |
| 4 site integration | ready-to-apply steps in `docs/modules/INTEGRATION.md` | **deferred (documented)** |
| 5 verify | schema/example/negative/prefix tests; SMFS hash guard | done |

## Counts

The live Europe PMC harvest was **not run** in this session (see "Not done").
Consequently: papers harvested **0**, in scope `core` **0** / `methods` **0**,
with a linked dataset **0**, with raw photon data or movies **0**, cross-links to
the SMFS index **0**, results extracted **0**. The 7 schema example records are
hand-written and labelled as examples (`10.0000/...`), not harvested data.

## Quality

- Every auto-extracted result carries `provenance` (`method`, `snippet`,
  `confidence`); `build_record` returns no record when a donor/acceptor pair or a
  biological entity cannot be grounded.
- Identifiers in `modules/gazetteer_ext.py` were restricted to UniProt/Rfam
  entries; unresolvable terms carry no identifier.
- No 20-record spot-check was possible because no records were harvested.

## Decisions taken

- **Schema vocabulary follows the brief** (`technique.primary` in the six
  `smfret_*` values); `geometry`/`excitation_scheme` keep the extra detail, and
  `correlative` + `cross_ref_smfs_record` represent hybrid force/FRET studies.
- **Shared definitions in `smash-common.schema.json`, SMFS schemas untouched.**
  The alternative (making v3 reference the common file) would change published
  bytes and validation behaviour.
- **Module engine, not a fork.** smFRET runs on `hub/modules/`, so SPT/MP/SC can
  reuse it. FRET gazetteer terms live in `modules/gazetteer_ext.py` rather than
  the shared `gazetteer.py`, to keep the change purely additive.
- **Site integration deferred.** Editing the shared header/templates while a
  second module branch is in flight risks the existing site; exact steps are in
  `docs/modules/INTEGRATION.md`.
- **Grounding over recall** in the auto-builder: a conservative rule set yields
  fewer records rather than plausible-but-unsupported ones.

## Not done / stopped at

- **Live harvest (time-boxed).** No Europe PMC/DataCite/ScholeXplorer requests
  were issued. Resume with:
  ```
  cd hub
  python -m modules.run fret --step harvest --min-year 2015   # then backfill
  python -m modules.run fret --step all
  ```
- **Scope audit sample** `docs/smfret/scope_audit_sample.csv` (needs the harvest).
- **Site pages / nav switch / downloads** (see `docs/modules/INTEGRATION.md`).
- **Reverse links** on SMFS records (by design additive; stored in
  `crossrefs.jsonl`, not written into SMFS records).

## Open questions for the owner

1. **Branding:** stay "SMASH-BIO: Force Spectroscopy Data Hub" or broaden to a
   single-molecule data hub? (No hero or title change was made.)
2. Should **in-cell smFRET** stay in scope? It is modelled
   (`smfret_in_cell`, `construct.immobilization: in_cell`) but is a scope call.
3. Is the **scope audit** to be labelled and used for classifier tuning?
4. Should we contact the **FRET-IDP** project to set up mutual linking?
5. **Git remote:** how should this work be committed (the workspace is not a repo)?