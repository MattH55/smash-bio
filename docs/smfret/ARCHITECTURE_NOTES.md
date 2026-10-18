# smFRET architecture notes

## Phase 1 schema decision

The existing SMFS 3.1.0 record and results schemas are published artifacts and remain byte-for-byte unchanged. Replacing their local definitions with cross-file references would be logically equivalent in many cases, but would change public bytes and reference-resolution requirements. The new `smash-common.schema.json` is therefore consumed by smFRET v1 first; a future SMFS major version may adopt it.

The common layer contains only modality-neutral definitions: quantities, identifiers, evidence/provenance, data availability, FAIR completeness, observer effects, result metadata, and trace-set metadata. FRET vocabularies and constraints remain in `smash-fret-record.schema.json` and `smash-fret-results.schema.json`.

FRET records use identifiers of the form `FRET-000001` and schema version `1.0.0`. Hybrid force/FRET publications are represented as a FRET record with `technique.geometry` set to `hybrid_force_fret` and `related_force_records` containing one or more existing `SMFS-*` identifiers. This avoids duplicating the force record while retaining a navigable cross-modality relationship.

## Phase boundaries

Phase 1 adds and validates schemas and examples only. It intentionally does not alter harvesting, classification, record generation, site generation, or force downloads. Pipeline integration begins only after these contracts pass validation.

## Pipeline integration (Phases 2-3)

smFRET runs on the shared machinery in `hub/modules/` rather than a fork of the
SMFS pipeline:

| concern | existing SMFS | smFRET (this branch) |
|---|---|---|
| HTTP (cache, throttle, User-Agent `mhalma@opensourcemed.info`) | `hub/common.py` | reused unchanged |
| harvest | `s01_harvest_articles.py` | `modules/harvest.py` (`FRET.harvest_queries`) |
| scope classification | `s03_classify.py` | `modules/classify.py` (`FRET.technique_patterns` etc.) |
| annotation/extraction | `gazetteer.py`, `extract.py` | `modules/gazetteer_ext.py`, `modules/extract.py` |
| records / downloads / site data | `s06`, `s07` | `modules/build_records.py`, `modules/build_outputs.py` |
| cross-links to force records | n/a | `modules/crossrefs.py` -> `cross_ref_smfs_record` |

The shared gazetteer and extractor are left untouched. smFRET systems (Holliday
junctions, Rev/RRE, riboswitches, SNAREs, LacY, and IDPs such as
alpha-synuclein, tau and p53) live in `modules/gazetteer_ext.py`; dye pairs and
named analysis tools live in `modules/build_records.py` and
`modules/extract.py`. This keeps the change purely additive, so the SMFS
pipeline and its outputs are byte-identical.

Run it with:

```
cd hub
python -m modules.run fret --step classify    # offline, cached
python -m modules.run fret --step all         # harvest -> classify -> records -> outputs
```

### Decisions taken

- **Shared schema, published bytes preserved.** `smash-common.schema.json`
  holds the modality-neutral definitions; the SMFS 3.1.0 schemas are not edited.
- **Technique vocabulary follows the brief.** `technique.primary` is one of
  `smfret_confocal_burst`, `smfret_tirf_widefield`,
  `smfret_confocal_scanning_immobilized`, `smfret_in_cell`,
  `smfret_nanopore_or_zmw`, `smfret_methods`; `geometry` and
  `excitation_scheme` carry the extra detail.
- **Hybrid studies.** `correlative` + `geometry: hybrid_force_fret` +
  `cross_ref_smfs_record` / `related_force_records`; the SMFS side is never
  edited, the link is stored on the FRET record and in `crossrefs.jsonl`.
- **Grounding over recall.** A FRET record is only emitted when a donor/acceptor
  dye pair and a biological entity are present in the text; otherwise no record
  is produced (no fabricated labels).
- **Site integration is documented, not applied.** The navigation switch,
  `/fret/` pages and downloads require shared templates; ready-to-apply steps
  are in `docs/modules/INTEGRATION.md`. See `REPORT.md`.