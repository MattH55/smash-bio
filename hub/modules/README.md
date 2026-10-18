# Hub technique modules

One engine, one `ModuleSpec` per technique. Additive: nothing here edits the
SMFS pipeline or the published SMFS schemas.

```
cd hub
python -m modules.run fret    --step classify       # offline, uses the HTTP cache
python -m modules.run spt     --step fulltext --max-fulltext 200
python -m modules.run spt     --step all --limit 500 --min-year 2015
python -m modules.run mp      --step outputs
python -m modules.run channel --step crossrefs
```

Steps: `harvest` -> `classify` -> `fulltext` -> `records` -> `outputs` ->
`crossrefs`, or `all`. `fulltext` is optional: without it a record is grounded in
the title/abstract only, with it the Methods section is used too. On its own,
`records` reuses whatever index a previous `fulltext` run left behind.

Files (see `docs/modules/ARCHITECTURE_NOTES.md` for the full contract):

| file | role |
|---|---|
| `base.py` | `ModuleSpec`, `MODULES`, `get_module`, `ta` |
| `fret.py` `spt.py` `mp.py` `channel.py` | the four module specs |
| `harvest.py` | Europe PMC, resumable, cached, half-rate |
| `classify.py` | core / methods / peripheral / out |
| `extract.py` | grounded results + named software |
| `fulltext.py` | Methods text, reusing the SMFS step-5 fetcher/parser |
| `gazetteer_ext.py` | module-local entity terms + the shared gazetteer (read-only) |
| `identifiers.py` | resolver-backed identifier verification (+ the committed table) |
| `verified_identifiers.json` | the codes a resolver confirmed; rebuilt by `python -m modules.identifiers` |
| `build_records.py` | assemble records, skip anything ungrounded |
| `build_outputs.py` | validate, then write downloads and site data |
| `crossrefs.py` | publication-level overlaps with SMFS and between modules |
| `run.py` | CLI |

Tests: `python -m pytest hub/test_modules_pipeline.py hub/test_modules_schema.py -q`

## Grounding rules

- A record is only written when the module schema's required fields can be
  grounded in the text; otherwise the article is counted as skipped.
- Identifiers are attached only through `identifiers.identifier`, which reports
  `verified: true` solely for codes present in `verified_identifiers.json`.
  Refresh the table with `python -m modules.identifiers [limit]` (network; it
  checkpoints after every identifier, so it can be resumed).
- `gazetteer_ext.match_entities` matches module-local systems first and then the
  shared `gazetteer.py` vocabulary, mapping its entity types into each module's
  schema vocabulary. Types with no sensible slot are dropped, and the channel
  module deliberately opts out of the shared vocabulary (it has no channel
  targets).