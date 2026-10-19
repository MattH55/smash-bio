# SMASH-BIO hub pipeline map (for the Motors module)

Checked against the repository on 2026-10-18 (commit `02dd131`). Every Motors task names the file it changes from this map. Paths are relative to the repo root.

## Stages

| Stage | File | Inputs | Outputs |
| --- | --- | --- | --- |
| 1 Harvest articles | `hub/s01_harvest_articles.py` | Europe PMC REST search, one query set per technique (`ta(...)` phrase lists) | `hub/out/articles_raw.jsonl` |
| 2 Harvest deposits | `hub/s02_harvest_datasets.py` | DataCite search with the same technique phrases | `hub/out/datasets_raw.jsonl` |
| 3 Classify | `hub/s03_classify.py` | `articles_raw.jsonl` | `hub/out/articles_classified.jsonl` (technique tags, scope `tier`: core / methods / peripheral / out); log `classify_log.txt` |
| 4 Link data | `hub/s04_links.py` | core + methods articles | `hub/out/links.json` (EPMC data links and text-mined annotations, Scholix, DataCite related identifiers) |
| 5 Full text | `hub/s05_fulltext.py` | PMC OA JATS XML | `<cache>/fulltext/<PMCID>.json`, `hub/out/fulltext_index.json` (data statement, repo links, supplementary files, `methods_text`) |
| 6 Build records | `hub/s06_build_records.py` | outputs of 3–5, `hub/out/datasets_raw.jsonl`, curated YAML, `hub/curated_json/*.json`, `hub/id_map.json` | `hub/out/records.jsonl`, `hub/out/datasets_hub.jsonl`, `uniprot_cache.json`, `harvester_m1_metrics.json`, `harvester_review_queue.jsonl`; log `build_log.txt` |
| 7 Build site | `hub/s07_build_site.py` (calls `s09_systems.py`) | `records.jsonl`, `datasets_hub.jsonl` | `website/data/*.js` (index, record shards, datasets, `stats.js` via `build_stats()`, `schema.js`, `systems.js`), `website/downloads/*` |
| 8 Curation batches (optional) | `hub/s08_curation_batches.py` | `records.jsonl` | `hub/curation_batches/batch_NN.json` for AI-assisted review |
| 9 Systems | `hub/s09_systems.py` | records, `gazetteer.py`, UniProt / Wikipedia | `website/data/systems.js` |
| 10–11 Gold set (harvester) | `hub/s10_prepare_gold_samples.py`, `hub/s11_evaluate_gold.py` | records, deposits | `hub/gold/*.csv`, `hub/gold/evaluation.json` (status `pending_human_annotation`) |

`hub/run_all.py` runs 1–7 in order. HTTP responses are cached in `%LOCALAPPDATA%/smash-bio-hub-cache/http` (override with `SMASH_HUB_CACHE`), so steps 6–7 rebuild offline.

## Where things happen

- **Experiment-class classifier:** `hub/s06_build_records.py::experiment_classes(text, ents, tech)`. It is a set of regexes over title + abstract plus entity-type hints from the gazetteer. `force_generation_motor` is assigned by the pattern `motor|kinesin|myosin|dynein|stall force|stepping|step size|processiv|power stroke|packaging|force generation|force-generating|translocat`, or by a `force_generation` gazetteer hint. The classes go to `assay.experiment_class` and `biological_system.system_class`; `TABLE3_COLUMN` maps them to Table 3 columns. There is no sub-class level today.
- **Entities (gazetteer):** `hub/gazetteer.py` (regex → canonical name, entity type, Table 3 class, UniProt gene/taxon lookup), used by `s06::entities_for()`.
- **Results extraction:** `hub/extract.py::extract_results(text)`, called once in `s06.main()` on the **abstract only** (`"results": X.extract_results(abstract)`). Methods full text feeds only `hardware_from`, `assay_from` and `solution_from` (`s06`, evidence method `regex_fulltext_methods`).
- **Overrides:** in `s06.main()`, after the automatic record is assembled. Curated YAML (`publications_metadata/study_*.yaml`, loaded by `load_curated()`, applied by `merge_curated()`, level `curated`). JSON from `hub/curated_json/*.json` (author submissions and AI-assisted reviews; `load_submitted()` + `merge_submitted()`, level `author_verified` or `ai_assisted`, keyed by DOI). Curated and submitted values replace automatic ones section by section.
- **Completeness:** `s06::completeness(rec)` fills `fair_completeness`.
- **TraceSet sidecars:** defined in `website/schema/smash-smfs-results.schema.json#/$defs/TraceSet` (and in `smash-common.schema.json`). **Nothing in `hub/` validates them**: no TraceSet file is read during the build, and the only TraceSet checks are the module schema tests (`hub/test_modules_schema.py`, `hub/test_smfret_schema.py`). Phase 3 adds the first validator.
- **Schema page:** `website/js/schema.js` (`T3` array → `schema.html` "Mapping to Table 3"; also read by `paper/scripts/make_supplementary.py` for Table S1). `s07` copies the schema JSON into `website/data/schema.js`.
- **Release counts:** `s07::build_stats()`; the paper reproduces them with `paper/scripts/corpus_stats.py --check`.

## Where SMASH-MOTOR plugs in

SMASH-MOTOR is a separate module (like SMASH-SIM). It **reads** the SMASH-BIO release and changes none of the files above.

| Task | File(s) |
| --- | --- |
| 1a/1b schemas | `hub/motors/spec.py` → `website/schema/motor/smash-motor-{record,results}.schema.json`; `hub/motors/schema.py` |
| 1c classifier + records | `hub/data/motor_gazetteer.yaml`, `hub/motors/classify.py`, `hub/motors/build_records.py` → `hub/out/motor/`; `paper/scripts/motor_stats.py` |
| 1d gold tooling | `hub/motors/sample_gold.py`, `hub/motors/validate_gold.py`, `docs/motors/gold/` |
| 2 extraction | `hub/motors/extract.py` (new), reading SMASH-BIO abstracts and the s05 full-text cache |
| 3 traces | `website/schema/motor/traceset-motor.profile.json`, `tools/traceset/` |
| 4 site | `website/motor/` pages and `website/downloads/motor/` (own build step, like `website/sim/`) |
