# Harvester gold set

Milestone 1 requires independently hand-labelled data before family/relevance precision gates can pass.
Do not populate these files from classifier output: that would make the evaluation circular.

Required samples:

- `studies.csv`: 150 studies across techniques and years, including curated records; label true data status and all deposits/supplements.
- `deposits.csv`: 300 current deposits; label relevance and correct family ID.
- `files.csv`: 50 files per content tier; label content tier and raw-trace status after opening the file.

Minimum columns should include stable source ID, human label, annotator, annotation date, and notes. A second
reviewer should adjudicate disagreements. Until these files exist and are evaluated, Step 6 reports the family
and relevance gate measurements as `null` rather than claiming unverified precision.

## Templates and workflow

The `*.template.csv` files contain headers only. Copy them to `studies.csv`, `deposits.csv`, and `files.csv`
when annotation begins; do not edit the templates in place. Sample source rows independently of the classifier,
then have annotators fill the `human_*` columns after inspecting the study, deposit, or opened file. Machine
predictions may be added only after human annotation is locked and must never be copied into a `human_*` field.

Use ISO 8601 dates (`YYYY-MM-DD`). Keep stable source identifiers and DOI/URL values unchanged so evaluation can
join annotations back to harvester output. The second reviewer records the final adjudicated label and explains
disagreements in `adjudication_notes`.

Run `python s10_prepare_gold_samples.py` from `hub/` to create reproducible working samples (seed `20261010`):
150 studies stratified across primary technique and decade, including up to 15 curated/author-verified records,
and 300 deposit identifiers stratified across repository and decade. Deposit families are expanded to member DOIs
before sampling, and predicted family/relevance values are not written to the CSV. The command refuses to overwrite
working files unless `--force` is supplied, protecting annotations already in progress.

`files.csv` is currently created header-only. The current pipeline retains aggregate formats/counts for only some
deposits, not stable file IDs and downloadable file URLs, so a valid 50-files-per-content-tier sample cannot yet be
drawn. Add a file-inventory harvest step before beginning that part of annotation; do not infer tiers from filenames
or aggregate deposit metadata.

Generation also writes `sample_manifest.json` with the seed, source-file SHA-256 digests, batch digests, row counts,
and immutable source columns. Run `python s11_evaluate_gold.py` at any time to validate columns, counts, uniqueness,
joins, allowed adjudicated labels, and annotation completeness. Before adjudication it writes a pending
`evaluation.json` with `measured: null`; after every deposit row has both review metadata and final adjudicated
relevance/family labels, the same command computes the family pairwise metrics and in-scope precision gate.