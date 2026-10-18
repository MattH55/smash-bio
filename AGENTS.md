# AGENTS.md — SMASH-BIO Drug-Effect Pipeline

Instructions for coding agents building the harvesting, harmonization and analysis pipeline for SMASH-BIO (smash-bio.org). Read this whole file before writing code. Work milestone by milestone; do not skip ahead.

## 1. Mission

Build an open-source pipeline that:

1. **Finds** public single-molecule force-spectroscopy datasets (starting with pulling curves recorded with and without a drug/ligand).
2. **Ingests** raw traces into one standard in-memory and on-disk representation.
3. **Analyzes** them with a uniform, versioned, reproducible workflow (force-extension fitting, rupture-force/kinetics, optionally energy-landscape reconstruction).
4. **Outputs** schema-valid SMASH-BIO records plus a harmonized "paired drug effect" table, with uncertainties and provenance.

Also usable as a standalone tool: a user uploads raw traces plus experimental metadata and gets analysis output back.

## 2. Scope and non-goals

**In scope (v1):** pulling curves (force-extension and force-time) with an apo/no-drug condition and a drug/ligand condition, from one or two techniques (start with optical tweezers; AFM second). Worm-like-chain fits, rupture/unfolding force statistics, loading-rate-dependent kinetics.

**Out of scope for v1:** magnetic/acoustic/centrifugal/nanopore data, de novo instrument calibration from raw voltages, simulations (they live in the separate `sim/` section of the site), any claim of drug potency or affinity.

## 3. Non-negotiable principles

- **Never invent data or metadata.** If a required field (trap stiffness, pulling speed, handle length, buffer, drug concentration, etc.) is missing, record it as `null` with a `missing_reason`. Do not guess, and do not fill from a paper's text unless you store the evidence snippet and source.
- **Every value carries provenance:** source dataset ID/DOI, file path inside the deposit, code version (git SHA), workflow version, parameters, and for any text-extracted value the evidence snippet.
- **Uncertainty by default:** every fitted parameter has a confidence interval (bootstrap or posterior) and a fit-quality diagnostic. No bare point estimates.
- **Reproducible:** pinned dependencies (lockfile), containerized runs, fixed random seeds recorded in output.
- **Licenses first:** before downloading or reprocessing a dataset, record its license. If the license forbids redistribution or derivatives, index and link only; do not copy raw data into our storage. Always cite and link the original authors.
- **Show disagreement, don't hide it:** when our result differs from the published one, store both side by side with a `discrepancy_note`. Never overwrite the author's reported value.
- **Conservative matching:** only produce a drug-effect delta when apo and drug conditions are matched (see section 8). Otherwise flag and skip.
- **Be honest about tiers** (section 9). Every record states how much of it was verified.

## 4. Suggested repository layout

```
smashbio-pipeline/
  AGENTS.md
  pyproject.toml            # python >=3.11, uv or pip-tools lockfile
  Dockerfile
  src/smashbio/
    harvest/                # repository crawlers + license capture
    readers/                # one module per file format, common interface
    model/                  # Trace, Condition, Dataset dataclasses/pydantic
    metadata/               # Table 3 mapping, validation, extraction w/ evidence
    pairing/                # apo/drug pair detection + match checks
    preprocess/             # drift, filtering, calibration sanity checks
    analysis/               # wlc, events, rupture_stats, kinetics, landscape
    records/                # schema-valid record builder + JSON schema validation
    report/                 # figures + discrepancy comparison
    cli.py
  workflows/                # Snakemake (or Nextflow) definitions
  schemas/                  # JSON schema(s): record, paired_effect table
  tests/
    unit/ integration/ synthetic/ golden/
  benchmarks/               # synthetic datasets with known ground truth
  docs/
```

Use Python. Use `pydantic` for models, `numpy/scipy` for numerics, `pandas`/`pyarrow` for tables, `h5py` for HDF5, `pytest` for tests, `ruff` + `mypy` for lint/types. Prefer well-maintained libraries over hand-rolled numerics; if you must implement an estimator yourself, test it against synthetic data with known answers.

## 5. Core data model (define first)

Define these in `src/smashbio/model/` and mirror them in `schemas/` as JSON Schema. Keep them small and explicit.

- `Trace`: `time` (s), `force` (pN), `extension` (nm) or `position`, optional `trap_positions`, `sampling_rate_hz`, `units` (explicit), `source_file`, `raw_format`.
- `Condition`: `label` (`apo` | `drug`), `ligand` (name, ChEMBL/PubChem/DrugBank ID if known), `concentration` (value, unit), `buffer`, `temperature_k`, `pulling_speed` or `loading_rate`, `construct` (handles, linker lengths), `instrument` (type, trap stiffness, calibration method), each field optionally `null` + `missing_reason` + `evidence`.
- `Dataset`: `source` (repo, DOI/URL, version), `license`, `authors`, `paper_doi`, `files`, `conditions`, `traces`, `tier`.
- `AnalysisRun`: `workflow_name`, `workflow_version`, `git_sha`, `params`, `seed`, `inputs` (hashes), `outputs`, `diagnostics`.
- `PairedEffect` row: see section 11.

Units are always explicit and converted to SI-ish canonical units (pN, nm, s, K, M) at ingest; keep the original values and units alongside.

## 6. Milestones

Work in order. Each milestone must end with passing tests and a short `docs/` note on what was learned. Open a PR (or commit) per milestone.

### M0 — Foundations
- Scaffold repo, tooling, CI, container.
- Implement the data model and JSON schemas.
- Acceptance: schemas validate hand-written example records; `pytest` and lint pass in CI.

### M1 — Harvester (find the data)
- Implement crawlers for Zenodo, Figshare, Dryad, OSF and (via their APIs) GitHub releases. Start with Zenodo.
- Query using keyword sets (e.g. optical tweezers, AFM force spectroscopy, single-molecule pulling, unfolding force, rupture force, force-extension, drug/inhibitor/ligand terms) and `.h5 .hdf5 .mat .csv .txt .tdms .zip` style file types. Verify real file extensions by looking at actual deposits; do not assume.
- For each candidate store: repo, ID, DOI, title, authors, license, file list with sizes and checksums, linked paper DOI, and a `relevance_score` with the matched terms.
- Respect rate limits and `robots.txt`/API terms. Cache responses. Make crawls resumable and idempotent.
- Output: `candidates.parquet` plus a human-reviewable `candidates.md` summary.
- Acceptance: a crawl of at least one repository yields a reviewable list; a report states how many candidates have usable licenses and which file formats occur. **Stop and report these coverage numbers before M2.** The format counts decide which readers to build.

### M2 — Readers (format support)
- Common interface: `read(path) -> list[Trace]` plus a `FormatInfo` describing what was and wasn't found (units, sampling rate, channel names).
- Implement readers in descending order of frequency found in M1: generic CSV/TSV (with column-mapping config), HDF5 (common force-spectroscopy layouts), MATLAB `.mat`, then one or two instrument-specific formats if prevalent. Verify each format's actual structure from sample files or public documentation; do not guess field names.
- Each reader gets tests using small real or realistic fixture files (strip/anonymize; respect licenses, prefer tiny synthetic fixtures that mimic the layout).
- Readers must fail loudly with an actionable error on unknown layouts, never return partially-guessed data silently.
- Acceptance: all M1-identified top formats either have a reader or an explicit documented reason they don't.

### M3 — Metadata and pairing
- Build metadata extraction from (a) structured deposit metadata, (b) README/data-description files, (c) the linked paper (only when full text is legally accessible, e.g. open access). Every extracted value stores its evidence snippet and a confidence.
- Map to Table 3 fields (see the site's schema page at https://smash-bio.org/schema.html; read it and follow it exactly rather than paraphrasing it).
- Pairing: detect apo vs drug groups from file names, folder structure, metadata and README. Output `PairCandidate` objects with confidence and the reasoning, and queue low-confidence pairs for human review (write them to `review_queue.jsonl`).
- Acceptance: on a hand-labeled set of 10+ datasets, report pairing precision and recall; no auto-accepted pair below the confidence threshold.

### M4 — Preprocessing and analysis core
Implement as separate, individually tested modules, each returning values with uncertainties and diagnostics:

1. **Sanity checks:** units, sampling rate, force baseline, drift magnitude; flag rather than silently correct.
2. **Force-extension fitting:** extensible worm-like-chain model for handles/linker; report contour length, persistence length, stretch modulus with CIs; flag poor fits.
3. **Event detection:** unfolding/rupture events (step or change-point detection); record force, extension change, and event time per event.
4. **Rupture-force statistics:** per loading rate, distributions; fit Bell-Evans and at least one more detailed model (e.g. Dudko-Hummer-Szabo) with the model name stored next to every parameter (k_off at zero force, distance to the transition state, barrier height). Compare models and report when they disagree.
5. **Energy landscape (optional, last):** nonequilibrium reconstruction for pulling data (Jarzynski/Crooks-type estimators) and, for constant-force/hopping data, an equilibrium method. Include diagnostics for violated assumptions (too fast pulling, too few events, non-equilibrium work distributions).
- Acceptance: every method recovers known parameters on synthetic benchmarks (section 10) within stated tolerances, and the benchmark report documents where each method breaks down.

### M5 — Paired drug-effect computation
- For each accepted pair, compute apo vs drug differences with propagated uncertainty (bootstrap over events or traces) for: mean/median unfolding or rupture force at matched loading rate, k_off(0), distance to the transition state, landscape barrier where available.
- Matching check (section 8) must pass; otherwise emit `status = skipped` with reasons.
- Emit the `PairedEffect` table (section 11) and per-dataset reports with figures.
- Acceptance: for datasets with published values, a comparison table shows our value, the published value, and an automatic `discrepancy_note` listing likely causes (different model, fit window, drift correction, loading-rate range).

### M6 — Records and workflow packaging
- Build the SMASH-BIO record builder that emits JSON validating against the site's schema, with evidence snippets, tier, provenance and links to the source dataset.
- Wrap M2–M5 in a Snakemake/Nextflow workflow runnable end-to-end via `smashbio run --dataset <id>` inside the container.
- Add a `smashbio analyze --input <dir> --metadata <file>` command for the standalone user-upload case.
- Acceptance: one command reproduces a full analysis from a clean checkout and produces identical outputs given the same seed.

### M7 — Pilot batch and report
- Select 20–30 public datasets with drug/no-drug pulling curves across one or two techniques. Run the full pipeline.
- Produce a report: how many datasets entered each tier, why others failed (missing metadata, unreadable format, license, unmatched conditions), agreement with published values, and a list of authors to contact for missing metadata.
- Acceptance: the report is written in plain language and states limitations. This report decides whether to expand.

### Later (do not start without approval)
Web upload front end, queued server jobs, more techniques, author-claim/verification flow, public API and bulk downloads.

## 7. Harvester details

- Use official APIs where they exist; send a descriptive User-Agent with a contact address; honor rate limits; back off on errors.
- Store raw API responses in a cache directory so analysis of a crawl is repeatable offline.
- Deduplicate across repositories using DOI, checksums and title similarity (the same data is often mirrored).
- Never download large files by default: first list sizes and ask the configured policy (`max_download_gb`). Download only datasets accepted for analysis.
- Record license text and URL for each dataset; map to an allowed-actions flag (`may_reprocess`, `may_redistribute_raw`). Unknown license means `may_redistribute_raw = false`.

## 8. Matching rules for apo vs drug

A pair is analyzable only if all of these hold, or the differences are documented and judged immaterial by a reviewer:
- Same construct (molecule, handles, linker lengths).
- Same instrument/setup class and comparable trap stiffness or cantilever.
- Overlapping loading-rate or pulling-speed range (compute the effect only inside the overlap).
- Same buffer, pH and temperature within stated tolerances (defaults in a config file; document them).
- Drug concentration known (or the condition is flagged qualitative).
Compute and store a `match_report` listing each check as pass/fail/unknown.

## 9. Tiers (store on every record)

- **Tier 1 — Re-analyzed:** readable raw data, sufficient metadata, matched pair, full pipeline run, comparison to published values.
- **Tier 2 — Assisted:** usable data but missing metadata; `needs` list of exactly what is required; no landscape/kinetic outputs that depend on missing fields.
- **Tier 3 — Indexed only:** linked and annotated without re-analysis (licensing, format or missing data).

## 10. Testing and validation

- **Unit tests** for every estimator and reader.
- **Synthetic benchmarks** in `benchmarks/`: simulate traces from known landscapes and known WLC parameters with realistic noise, drift and sampling; include conditions that should break each method. The test asserts recovery within tolerance and that diagnostics flag the broken cases.
- **Golden tests** on small public real datasets whose published values are known; tolerances documented.
- **Property tests** for unit conversion and schema round-trips.
- CI runs unit and synthetic tests on every commit; golden/integration tests on merge.

## 11. Output: paired drug-effect table (Parquet + CSV)

One row per matched pair and observable. Columns at minimum:
`pair_id, dataset_id, source_doi, target (UniProt ID if known), construct, technique, ligand_name, ligand_id, ligand_concentration, loading_rate_range, observable, model, apo_value, apo_ci_low, apo_ci_high, drug_value, drug_ci_low, drug_ci_high, delta, delta_ci_low, delta_ci_high, n_events_apo, n_events_drug, published_apo, published_drug, discrepancy_note, match_report_status, tier, workflow_version, git_sha, license, notes`.
Include a data card (`docs/DATA_CARD.md`) describing coverage, known biases (public data skews toward clean experiments) and the statement that rupture force is not affinity or potency.

## 12. How to work (agent rules)

1. Start each session by reading this file and `docs/` notes; list what you will do before doing it.
2. Do one milestone at a time. Write tests before or with the code.
3. When facts about a file format, API, or the SMASH-BIO schema are needed, look at real samples or official documentation. If you cannot verify, say so in the code comments and the PR description instead of assuming.
4. Keep functions small and typed; no hidden global state; log with structured messages.
5. Do not commit data that you are not licensed to redistribute. Use `.gitignore` for caches and downloads.
6. When something is ambiguous (scientific choice, threshold, scope), write the question in `docs/OPEN_QUESTIONS.md` with your proposed default, and proceed with that default behind a config flag.
7. At the end of every milestone, update `docs/` with what works, what does not, and the numbers (coverage, accuracy).
8. Escalate to the human maintainers before: changing the schema, adding a method not listed here, contacting dataset authors, making anything public, or spending paid compute.
