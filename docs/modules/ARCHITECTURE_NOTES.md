# Technique-module architecture

How a new single-molecule technique plugs into SMASH-BIO. The smFRET module
(`feature/smfret-module`) and the SPT, mass-photometry and single-channel modules
(`feature/sc-spt-mp-modules`) share this one pattern, so a fifth module is cheap.

## The plug-in contract

Everything a module needs is a single frozen `ModuleSpec`
(`hub/modules/base.py`). A module is a new file that defines one spec; the engine
does the rest.

| spec field | purpose |
|---|---|
| `slug` | cache/out prefix, page path `/slug/`, download names |
| `record_prefix` | record IDs, e.g. `SPT-000001` |
| `schema_file`, `results_schema_file`, `schema_subdir` | which JSON Schemas validate the records |
| `harvest_queries` | Europe PMC `TITLE_ABS` query fragments per technique tag |
| `technique_patterns` | tag -> regex, used by the classifier and to pick `technique.*` |
| `bio_pattern`, `single_molecule_pattern`, `methods_pattern`, `out_of_scope_pattern` | rule-based scope tiering |
| `observables`, `observable_patterns` | grounded result extraction with canonical units |
| `raw_formats`, `repositories`, `citation_dois` | data linking and attribution |

## Engine

```
modules/base.py          ModuleSpec + registry (MODULES, get_module)
modules/fret.py            \
modules/spt.py              > one ModuleSpec each
modules/mp.py              /
modules/channel.py        /
modules/harvest.py       Europe PMC harvest, resumable, cached, half-rate
modules/classify.py      core / methods / peripheral / out tiering
modules/extract.py       grounded results + named software, evidence on every value
modules/fulltext.py      Methods text via the SMFS step-5 fetcher/parser (shared cache)
modules/gazetteer_ext.py module-local systems + the shared gazetteer (read-only)
modules/identifiers.py   resolver-backed identifier verification
modules/build_records.py assemble schema-shaped records, skip anything ungrounded
modules/build_outputs.py validate, then write downloads/modules/* and data/modules/<slug>/index.js
modules/crossrefs.py     publication-level overlaps -> data/modules/crossrefs.jsonl
modules/run.py           python -m modules.run <slug> --step ...
```

The shared gazetteer is consumed, not copied: `gazetteer_ext.match_entities`
matches module-local systems first, then the shared `gazetteer.py` entries,
mapping each `entity_type` into the module's schema vocabulary through
`SHARED_TYPES`. Types with no slot in a module are dropped rather than
mis-typed, and the single-channel module opts out entirely because the shared
vocabulary holds no ion-channel targets. Generic shared names (e.g. "Kinesin"
next to "Kinesin-1") yield to the more specific sibling that already matched.

## Non-negotiable rules encoded here

- **Additive only.** No existing pipeline script, schema, template, CSS/JS or
  download is edited. Modules are new files; shared helpers are only called.
- **No fabricated data.** `build_record` returns `None` (no record) when required
  schema fields cannot be grounded in the text. Identifiers carry
  `verified: true` only when `modules/identifiers.py` finds the code in
  `verified_identifiers.json`, the committed table of codes a resolver confirmed
  (UniProt REST, EBI Search for Rfam/GO, OLS4 for Cell Ontology, NCBI for
  GenBank). Anything unconfirmed is flagged `verified: false` rather than
  silently invented.
- **Evidence everywhere.** Every extracted result carries
  `provenance: [{field, method, snippet, confidence}]` using the shared
  `Evidence` vocabulary.
- **Validation gate.** `build_outputs.validate_records` drops any record that
  fails its schema and returns the failures for the report.
- **Respect the API budget.** `harvest.RATE_FACTOR = 2.0` leaves twice the normal
  gap between requests; all responses are cached by `common.get`; the JSONL is
  rewritten after each query tag so a crash resumes.

## Schema layout

Module record and results schemas live in `website/schema/modules/`. They
reference the modality-neutral definitions as
`../smash-common.schema.json#/$defs/...`. The staging copy
(`_shared-pending.schema.json`) was retired once the shared definitions landed
upstream: all 50 references were repointed, the file was deleted, and
`test_modules_schema.py` now asserts that every referenced definition exists in
`smash-common.schema.json` and that no module schema mentions the staging file.

## Adding a fifth module

1. Copy the closest existing spec and edit it.
2. Add `smash-<slug>-{record,results}.schema.json` under
   `website/schema/modules/` and at least four example records.
3. Add `hub/test_<slug>_schema.py` following `test_modules_schema.py`.
4. Register the spec in `base._registry` and add its slug to
   `crossrefs.collect_all`.