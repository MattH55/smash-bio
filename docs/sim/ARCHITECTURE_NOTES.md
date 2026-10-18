# Simulations-category architecture

How the **Simulations** category plugs into SMASH-BIO alongside the single-molecule
force-spectroscopy (SMFS) corpus and the four technique modules (smFRET, SPT, mass
photometry, single channel).

The brief for this work is `smash-simulations-category-agent-brief.md`. It was
written against a repository layout where the schemas sit at `schema/`; in this
repository they sit at `website/schema/`, so the brief's `schema/sim/` maps to
`website/schema/sim/` and `downloads/sim/` maps to `website/downloads/sim/`. That
path mapping is the only deviation and it is recorded in `REPORT-sim.md`.

## Isolation

Simulations are a separate category, never an experiment. They get their own
record type (`SIM-######`), their own pages (`/sim/`), their own downloads
(`website/downloads/sim/`), and a visible label everywhere they appear.

| the brief says | this repository |
|---|---|
| `schema/sim/smash-sim-record.schema.json` | `website/schema/sim/smash-sim-record.schema.json` |
| `schema/sim/_shared-pending.schema.json` | not needed (see below) |
| `data/sim/` | `hub/data/sim/` (ingested datasets + `matches.parquet`) |
| `.cache/sim/` | `hub/out/sim/` intermediates + the shared HTTP cache in `hub/common.py` |
| `downloads/sim/` | `website/downloads/sim/` |
| site pages `/sim/` | `website/sim/` |

Nothing existing is edited. The category is new files only, and every shared
helper is *called*, never copied.

## The plug-in contract

There is one `SimSpec` (`hub/sim/spec.py`), one classifier, one extractor and one
record builder. Unlike the technique modules (four specs), the Simulations
category is a single spec because the brief defines one pipeline for proteins,
nucleic acids and their complexes.

```
sim/spec.py            SimSpec: harvest queries, model families, geometry, observables
sim/harvest.py         Europe PMC harvest (reuses modules.harvest -> half-rate, cached)
sim/fulltext.py        Methods text (reuses modules.fulltext: shared fetcher + cache)
sim/classify.py        core / methods / out_of_scope tiering + model family + molecule type
sim/extract.py         grounded model/protocol/results extraction, with unit_system
sim/gazetteer_sim.py   entity grounding (category-local systems + the shared gazetteer)
sim/identifiers.py     PDB verification on top of the shared resolver table
sim/ingest.py          dataset ingestion with licence + SHA-256 provenance
sim/build_records.py   assemble schema-shaped SIM records; skip anything ungrounded
sim/match.py           SIM <-> experimental matching, match levels, coverage
sim/build_outputs.py   validate, then write downloads/sim/* and sim/data/*.js
sim/audit.py           the 45-paper stratified scope-audit sample
sim/verify.py          Phase 6 checks -> docs/sim/verification.md
sim/schema.py          JSON Schema registry/validator for the sim schemas
sim/run.py             python -m sim.run --step ...
```

`harvest` imports `modules.harvest.harvest` unchanged: a `SimSpec` only has to
expose `.slug` and `.harvest_queries` for it to work, and `modules.harvest`
already paces requests at `RATE_FACTOR = 2.0` (half the SMFS rate) with every
response cached on disk by `common.get`. The same shared layer is used for the
open-access Methods text (`modules.fulltext`). Identifier grounding reuses the
shared resolver table for UniProt/Rfam/ChEBI/GO/CL/GenBank and adds a PDB check;
the codes confirmed for this category are kept in `hub/sim/verified_identifiers.json`
rather than in the modules branch's table, and a code is only ever written into a
record when a resolver confirmed it.

## Schema strategy: reference the v3 `$defs`, do not stage a copy

The brief allows `$ref` into the existing v3 schema's `$defs`, and only asks for
`_shared-pending.schema.json` when a definition is **not** factored out there.
The published v3 schemas already carry what is needed:

| sim needs | source |
|---|---|
| `Quantity` | `../smash-smfs-record.schema.json#/$defs/Quantity` |
| `Identifier` | `../smash-smfs-record.schema.json#/$defs/Identifier` |
| `Evidence` (provenance arrays are arrays of `Evidence`) | `../smash-smfs-record.schema.json#/$defs/Evidence` |
| `MolecularEntity` | `../smash-smfs-record.schema.json#/$defs/MolecularEntity` |
| `DatasetLink` | `../smash-smfs-record.schema.json#/$defs/DatasetLink` |
| `DataAvailability.status` | `../smash-smfs-record.schema.json#/$defs/DataAvailability/properties/status` |
| `force_application_geometry` | `../smash-smfs-record.schema.json#/$defs/Technique/properties/force_application_geometry` |
| `Observable` (the sim vocabulary is the SMFS vocabulary plus `toughness`) | `../smash-smfs-results.schema.json#/$defs/Observable` |

None of these definitions set `additionalProperties: false`, so they can be
referenced and extended. **No staging file is created.**

### One definition is mirrored, not referenced: the result structure

`SimResult` in `website/schema/sim/smash-sim-results.schema.json` repeats the
published `Result` properties one-for-one instead of `$ref`-ing the whole
definition, for one concrete reason: the published `Result` pins `quantity` to
the SMFS `Observable` enum, which has no `toughness`, and the brief requires
toughness as a simulation observable while the published schemas must not be
modified. The mirror adds the mandatory `unit_system` plus optional pathway
fields (`unfolding_order`, `n_intermediates`) and keeps `provenance` alongside the
published `source` evidence field. `hub/test_sim_schema.py` asserts that every
published `Result` property is present with the same type and that the published
required keys are kept, so the mirror cannot drift silently.

If a future SMFS major version adds `toughness` to the observable vocabulary, the
mirror can be replaced by `allOf: [{$ref: …Result}, {unit_system …}]`.

After the sibling branches merge, `smash-common.schema.json` becomes the shared
home for the modality-neutral definitions and the sim refs can be repointed to
it — that is a ready-to-apply step in `docs/sim/INTEGRATION.md`, not something
this branch does.

### The pulling geometry is the experimental representation

The brief requires the simulated pulling geometry to use "the same
representation as the experimental records, so the two can be matched". The
sim schema therefore points `protocol.geometry.force_application_geometry` at
the **v3 enum itself** (the `$ref` above) rather than inventing a parallel
vocabulary, and adds only sim-specific detail (`pull_direction`, `anchor_a`,
`anchor_b`, `separation_axis`).

## Units are part of the data

Every value keeps its original unit. `model.unit_system` and every
`results[].unit_system` are one of `physical`, `reduced`, or
`reduced_with_stated_conversion`. A reduced value is never converted to a
physical unit unless the source states the conversion, in which case the
conversion is stored in `model.unit_conversions` with its own evidence. A
verification test asserts that no `reduced` result and no `reduced` source
record is ever labelled with a physical unit.

## Non-negotiable rules encoded here

- **No fabricated data.** `build_records` returns no record when a required
  schema field cannot be grounded; every extracted value and every inferred
  field carries `provenance`/`evidence`.
- **Identifiers are resolver-checked.** UniProt/PDB/Rfam codes come from the
  verified tables (`modules.identifiers` plus the RCSB-backed PDB check in
  `sim/identifiers.py`); an unconfirmed code is dropped from the record, never
  published, and a test asserts every published identifier is verified.
- **Licences before ingestion.** `sim/ingest.py` records a licence value for
  every dataset and only copies data whose licence allows redistribution. Where
  it does not, the record indexes metadata and links to the source.
- **Validation gate.** `sim/build_outputs.validate_records` drops any record
  that fails its schema and returns the failures for the report.
- **Additive only.** No existing schema, template, CSS/JS bundle, download or
  pipeline script is edited. The category's own nav/footer lives in
  `website/sim/js/sim.js` because the shared `app.js` builds root-relative links
  that would break one level down.
- **Matching never over-claims.** Level 1 needs a shared verified identifier,
  equal pulling geometry *and* overlapping constructs; a missing construct is not
  treated as agreement. Geometry agreement is published as its own
  `geometry_match` column so the information is not lost.

## Adding to the category later

1. Add a query fragment to `SIM.harvest_queries`, and a model family to the
   record schema if the list does not cover it.
2. Add an observable to `sim/extract.py` and to the results vocabulary (and the
   reference unit map).
3. Add a dataset reader to `sim/ingest.py` with its licence, retrieval date and
   SHA-256; only copy data whose licence allows redistribution.
4. Re-run `python -m sim.run --step all`, then `python -m sim.verify`.

## Verification

`python -m sim.verify` runs the brief's Phase 6 checks — grounding (every evidence
snippet must occur in the source text the record was built from), units (no
reduced value with a physical unit; a claimed stated conversion must be stored),
identifiers (published records carry only resolver-verified codes) and site assets
(every local file a `/sim/` page references exists) — and writes
`docs/sim/verification.md` with a deterministic 15-record spot-check sample.

1. Add a query fragment to `SIM.harvest_queries` and a model family to the
   `ModelFamily` enum in the record schema.
2. Add an observable to `sim/extract.py` and to the results vocabulary.
3. Add a dataset reader to `sim/ingest.py` with its licence and SHA-256.
4. Re-run `python -m sim.run --step all`.