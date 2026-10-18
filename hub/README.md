# SMASH-BIO force-spectroscopy hub pipeline

Builds the data behind `website/` — an index of single-molecule force spectroscopy (SMFS) studies
annotated with the SMASH-BIO schema v3 (Table 3 of Halma, van Eck, Abeln et al., *Biophys J* 2025,
generalised to all force techniques), with linked datasets.

```
python s01_harvest_articles.py   # Europe PMC search per technique            -> out/articles_raw.jsonl
python s02_harvest_datasets.py   # DataCite search for deposits                 -> out/datasets_raw.jsonl
python s03_classify.py           # technique detection + scope tier              -> out/articles_classified.jsonl
python s04_links.py              # EPMC datalinks/annotations, Scholix, DataCite -> out/links.json
python s05_fulltext.py           # PMC full text: data statements, methods       -> cache + out/fulltext_index.json
python s06_build_records.py      # annotate + assemble v3.1 records/families     -> out/records.jsonl, out/datasets_hub.jsonl
python s07_build_site.py         # website/data/*.js and website/downloads/*
python s10_prepare_gold_samples.py # reproducible blinded M1 annotation batches
python s11_evaluate_gold.py      # validate batches; score only completed adjudication
```
or `python run_all.py`. Steps 4–5 accept being re-run; every HTTP response is cached
(outside OneDrive, in `%LOCALAPPDATA%/smash-bio-hub-cache`, override with `SMASH_HUB_CACHE`).
Delete the cache entries (or the whole folder) to refresh from the APIs.

## Files
| file | role |
|---|---|
| `common.py` | cached, throttled HTTP; JSONL helpers |
| `gazetteer.py` | biological systems → entity type, Table 3 class, UniProt gene/taxon or fixed IDs; organism patterns |
| `extract.py` | regexes for hardware/assay/solution fields, results (observable vocabulary) and data-statement classes |
| `../website/schema/*.schema.json` | the formal record and results/trace JSON Schemas |

Record IDs (`SMFS-000123`) are stable across rebuilds: `id_map.json` maps DOI/PMID/PMCID → id. Never delete it.

## Dataset harvester milestone 1

`harvester_cleanup.py` resolves existing repository links into DOI families and labels each family
`in_scope`, `methods`, `out_of_scope`, or `unsure`, with rule evidence. Step 6 writes one row per family,
`out/harvester_review_queue.jsonl`, and `out/harvester_m1_metrics.json`. Public deposit totals include only
`in_scope` and `methods`; the downloadable dataset CSV retains every label for audit. Gold-set gate values in
the metrics remain `null` until the required hand-labelled set has been completed; they are not inferred from
the same rules being evaluated.

## AI-assisted curation (optional)
`python s08_curation_batches.py 100 10` packages the top 100 records with a linked public dataset and open Methods
text into batches of 10 (`curation_batches/`). Reviewer agents follow `curation_brief.md` and write
`curated_json/<record_id>.json` with `curation.level = "ai_assisted"` and verbatim evidence snippets
(`evidence.method = "llm_review"`). Step 6 then lets those sections replace the regex values. Records a reviewer
flags `NOT SMFS` are removed and listed in `out/rejected_by_review.json`. AI-assisted records are shown with their
own badge and should still be spot-checked by a human before being upgraded to `curated`.

## Curating
* Hand-curated YAML in `../publications_metadata/study_*.yaml` is merged by DOI and marks a record `curated`.
* Author submissions from `submit.html` are schema v3 JSON (`curation.level = author_verified`); to merge them,
  drop the files into `curated_json/`; step 6 merges them by DOI and marks the record `author_verified`.
* Improve recall by adding patterns to `gazetteer.py` (biology) or `extract.py` (parameters), then re-run steps 6–7 (fast, cached).

## Known limitations
* Rule-based scope classification: some false positives/negatives at the boundary (e.g. AFM on materials).
* Hardware/solution values are extracted only from open-access Methods text; others carry abstract-level data only.
* Proteins without a stated organism get a default ortholog, flagged `confidence: low`.
