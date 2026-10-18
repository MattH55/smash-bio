# REPORT — Simulations category (SMASH-SIM v1.0.0)

Agent brief: `smash-simulations-category-agent-brief.md`.
Everything in this report is reproducible from the repository; the commands are
at the end.

---

## Status

| item | value |
|---|---|
| branch / PR | **not possible**: this workspace has no `.git` (plain OneDrive files), so there is no worktree, branch or PR. The work is left in place, local only, and every new file is listed below. |
| new files | **59** — 43 authored (16 pipeline modules, 2 schemas, 6 examples, 6 pages, 1 css, 5 js, 4 docs, 2 tests, this report) and 16 generated (3 downloads, 3 site data files, `verified_identifiers.json`, 9 dataset/match outputs). See *File inventory*. |
| existing files edited | **none** |
| tests | `python -m pytest -q` → **107 passed, 281 subtests**. The pre-existing suite was 66 tests / 188 subtests; this work adds 41 tests (`test_sim_schema.py`, `test_sim_pipeline.py`) and 93 subtests. |
| records built | **123** (109 from publications, 14 from MechanoProDB) |
| schema failures | **0** — the validation gate in `sim/build_outputs.py` would have excluded them |
| verification | `python -m sim.verify` → 0 grounding failures, 0 unit violations, 0 unverified identifiers, 0 missing site assets (`docs/sim/verification.md`) |
| SMFS artifacts | byte-for-byte unchanged (SHA-256 asserted in `hub/test_sim_schema.py`) |

## What was built

```
docs/sim/ARCHITECTURE_NOTES.md      how the category plugs in
docs/sim/INTEGRATION.md             ready-to-apply owner steps (nothing applied)
docs/sim/scope_audit_sample.csv     45-paper stratified sample, empty human_label
docs/sim/verification.md            Phase 6 verification output
website/schema/sim/smash-sim-record.schema.json     record schema, v1.0.0
website/schema/sim/smash-sim-results.schema.json    results vocabulary (adds toughness)
website/schema/sim/examples/*.json                  6 hand-made example records
hub/sim/                            pipeline (spec, harvest, classify, extract, build_records,
                                    identifiers, gazetteer_sim, fulltext, ingest, match,
                                    build_outputs, audit, verify, schema, run)
hub/data/sim/                       ingested dataset provenance + matches.parquet + coverage.csv
hub/sim/verified_identifiers.json   category identifier table (resolver-checked)
website/sim/                        6 pages + css + js
website/downloads/sim/              3 downloads
hub/test_sim_schema.py, hub/test_sim_pipeline.py   tests
REPORT-sim.md                       this report
```

### Deviation from the brief's paths (the only one)

The brief was written against a layout with `schema/` at the repository root.
In this repository the schemas live in `website/schema/`, so:

| brief | here |
|---|---|
| `schema/sim/…` | `website/schema/sim/…` |
| `downloads/sim/…` | `website/downloads/sim/…` |
| `data/sim/…` | `hub/data/sim/…` |
| `.cache/sim/` | `hub/out/sim/` plus the shared HTTP cache in `hub/common.py` |
| site pages `/sim/` | `website/sim/` |

No `schema/sim/_shared-pending.schema.json` was created: the published SMFS 3.1.0
`$defs` already carry every definition the sim schema needs, so it references them
directly. The only published definition that could **not** be reused is the
`Result.quantity` vocabulary, because it has no `toughness`; the sim `Result`
therefore mirrors the published field set exactly (a test asserts property-by-property
compatibility) and adds `unit_system`. See `docs/sim/ARCHITECTURE_NOTES.md`.

---

## Datasets ingested

`python -m sim.run --step datasets` writes one provenance file per dataset under
`hub/data/sim/datasets/`, with licence, retrieval date and SHA-256.

| dataset | source | licence | redistributable | outcome |
|---|---|---|---|---|
| **ForceGen** (Ni, Kaplan & Buehler, arXiv:2310.10605) | `github.com/lamm-mit/ProteinMechanicsDiffusionDesign` | **MIT** (GitHub API) | yes (code) | metadata + links indexed; the ~7,000 per-protein force–extension records are **not copied** (large, and the dataset's own licence for the *data files* is not stated). 0 records. |
| **BSDB** (Sikora, Sułkowska, Witkowski & Cieplak) | `jowisz.ifpan.edu.pl/BSDB/` | **not stated** | no | host returns **404** at both published addresses; the Internet Archive snapshot of 2025-03-14 was fetched and read (11.6 kB, a Flash/JS wrapper mentioning download, mechanical clamp, protein, stretching). 0 records; metadata only. Question for the owner below. |
| **Mykuliak et al. 2020** (Biophys J, doi:10.1016/j.bpj.2020.07.030) | DataCite / Fairdata `10.23729/e4805d6f-e85e-4712-8481-948dfc7c6f0e` | **CC BY 4.0** (DataCite `rightsList`) | yes | metadata indexed with a link; files not copied yet. 0 records. |
| **MechanoProDB** (Mesbah, Habermann & Rico, *Database* 2024) | local export of `mechanoprodb-reanalysis/data/processed/entries.parquet` | **MIT** (site terms page, SHA-256 recorded) | yes | **14 steered-MD rows ingested as `database` records**, each keeping the original publication DOI and the PDB entry; the 68 experimental rows are used as match targets, not copied into records. |
| **SMASH-SIM outputs** | `smash-sim/out/harmonized.parquet` | n/a | — | **not found** in this workspace. The reader exists; nothing invented. |

Skipped and why: BSDB (licence unstated, host down), ForceGen data files (data
licence unstated beyond the repository's code licence), Mykuliak files (not needed
for the records built here), SMASH-SIM outputs (absent).

## Literature harvest

Eight Europe PMC queries, taken verbatim from the brief
(`sim/spec.py:SIM.harvest_queries`), one page each, at **half the SMFS request
rate** (`modules.harvest.RATE_FACTOR = 2.0`) with every response cached on disk.

| stage | count |
|---|---|
| hits fetched | 608 |
| unique articles after de-duplication | **542** |
| scope labels | `out_of_scope` 349 · `core` 179 · `methods` 14 |
| in scope (core + methods) | **193** |
| open-access full texts parsed (Methods text) | 111 |
| records built | **109** of 193 in-scope articles (**56 % pass rate**) |
| skipped | 84 × `no-model-evidence` |
| dataset records | 14 |

The 84 skips are the price of the grounding rule: a record is only built when the
text names a model family, software, force field or solvent. Abstracts alone
almost never do (2 of 94 named software, 6 named a family, 4 a force field), so the
**Methods text is what makes most records possible** — the same finding as in the
technique modules.

Counts by molecule type, model family and unit system (published records):

| molecule type | n | | model family | n | | unit system | n |
|---|---|---|---|---|---|---|---|
| protein | 81 | | other (unnamed) | 78 | | physical | 121 |
| DNA–protein | 13 | | Go_CA | 20 | | reduced | 2 |
| complex | 11 | | thermodynamic nearest-neighbour | 6 | | reduced_with_stated_conversion | 0 |
| DNA | 7 | | Martini | 6 | | | |
| RNA | 7 | | SOP | 5 | | | |
| RNA–protein | 4 | | all-atom explicit solvent | 5 | | | |
| | | | oxDNA | 3 | | | |

Protocol modes: `constant_velocity` 55 · `other` 21 · `equilibrium_under_force` 18 ·
`constant_force` 17 · `force_ramp` 11 · `boxed_MD` 1. Software named in 77 records.
Results extracted: **97 values**, every one with provenance — unfolding force 16,
contour length 15, x‡ 13, k0 13, ΔG‡ 10, pulling velocity 7, and the rest spread
over rupture/unbinding force, persistence length, loading rate, dwell time,
toughness-type work and intermediates. **5 of the 97 are recorded as bounds**
(`min`/`max`, for example "rupture forces > 60 pN were rare"), not as values.
Median `fair_completeness` **0.680** (range 0.345–0.945).

### What the spot-check changed

The 15-record spot-check (below) is run by `python -m sim.verify`, and the first
pass caught real false positives, all of which were fixed before publishing:

| false positive | cause | fix |
|---|---|---|
| `intermediates = 15` from "Leu15", `= 43` from "TDP-43", `= 3` from "3'-end" | the number was read out of a token | a value-boundary guard rejects a digit preceded by a letter, hyphen or apostrophe |
| `intermediates = 10000` from "minimised for 10,000 steps" | MD *integration* steps are not unfolding intermediates | the pattern now requires "intermediates" or "unfolding steps/events" |
| `velocity = 4 nm/s` from "10–4 nm/step" | `nm/s` matched the prefix of `nm/step` | a unit-boundary guard rejects a unit that is the prefix of a longer one |
| `work = 600 kJ/mol` from "in this work we chose k = 600 kJ/mol/nm" | the word "work" was matched in "in this work" | the `work` pattern now requires "mechanical work", "work done", "work performed", "work required" or "reversible work" |
| `unfolding_force = 0.1 pN` from "the difference … is less than 0.1 pN" | a difference is not a measurement | a quantifier guard rejects a value whose window contains "difference", "less than", "increases from", etc. |
| `distance_to_transition_state` read from HTML-markup text | `<sup>` next to the number | inline HTML is stripped before matching |

After the fixes, all 31 publication-derived snippets verified as substrings of
their source text (`docs/sim/verification.md`), and no bound is published as a
plain value.

Data availability: `public_repository` 71 · `journal_supplement` 29 ·
`not_stated` 15 · `fulltext_checked_none` 7 · `code_only` 1.

An audit sample of 45 papers (20 core, 10 methods, 15 out-of-scope), stratified by
molecule type, is in `docs/sim/scope_audit_sample.csv` with an **empty
`human_label` column** for the owner's labels.

## Coverage: experimental systems with a matched simulation

`hub/data/sim/matches.parquet` (complete relation) and
`hub/data/sim/coverage.csv` (the table below, rolled up by molecule type and model
family). Match rules: a shared **resolver-verified** identifier *and* molecule-name
agreement for the two strong levels, a distinctive name token for `homolog`.

| level | links | distinct experimental systems |
|---|---|---|
| `same_construct_same_geometry` | **0** | 0 |
| `same_molecule_different_geometry` | 3040 | 521 total across levels |
| `homolog` | 337 | (included above) |

Totals: **3377** links; **106 of 123** simulation records have at least one
experimental match; sources SMASH-BIO 3353 / MechanoProDB 24; **705 links agree on
the pulling geometry**; 33 links carry a force on both sides.

**Why the top level is empty, and why that is the honest answer.** The brief's
strongest rung means *same construct, same geometry*. Geometry agrees in 705
links, but a confirmed construct overlap is required on both sides, and that
evidence is thin: a residue/nucleotide range is grounded in **30 of 123**
simulation records, and the SMASH-BIO side carries a `region` for only a minority
of the matched records. Rather than label geometry-agreeing pairs as
"same construct", the matcher keeps them at level 2 and the geometry agreement is
published as a separate `geometry_match` column in `smash-sim-matches.csv`, so the
comparison is available without over-claiming. This is a coverage finding in its
own right: **construct annotation is the bottleneck for simulation↔experiment
comparison**, on both sides.

The systems where the link counts are largest are titin (Q8WZ42), ubiquitin
(P0CG48), GB1 (P06654), GFP (P42212) and calmodulin (P0DP23) — identifier-backed
matches against the existing experimental index.

---

## Decisions taken

1. **Reference the published `$defs`; no staging file.** Every shared definition
   is `$ref`'d from the SMFS 3.1.0 schemas. The sim `Result` mirrors the published
   field set because the published `quantity` enum has no `toughness`; a test
   asserts the mirror property-by-property.
2. **Geometry uses the experimental vocabulary.** `protocol.geometry.force_application_geometry`
   `$ref`s the SMFS `Technique` enum, so simulation and experiment share one
   representation. A test asserts the two enums are identical.
3. **Match levels are strict.** Level 1 needs a shared verified identifier, equal
   geometry *and* confirmed overlapping constructs; level 2 keeps everything else
   identifier-backed; level 3 is name-token-only. Construct agreement is therefore
   never assumed, which is why level 1 is currently empty.
4. **Only the primary, category-local entity is matched.** Using every entity's
   identifiers produced thousands of spurious links (a streptavidin *handle*
   accession matched ~500 unrelated experiments). Matching now uses the record's
   primary entity when it comes from the curated local list, and requires
   molecule-name agreement even for a shared identifier.
5. **`homolog` is capped** at 5 links per simulation and identifier links at 20
   per record *in the record body*; the parquet keeps the complete relation.
6. **PDB entries are verified against RCSB** (`sim/identifiers.py`) and the result
   is cached in `hub/sim/verified_identifiers.json`; UniProt/Rfam codes are
   confirmed through the shared resolver table. Nothing unverified is published
   (asserted by a test).
7. **Category-local identifier table.** `sim.identifiers.warm()` writes to
   `hub/sim/verified_identifiers.json`, never to the modules branch's table.
8. **Units.** Every value keeps its source unit; `model.unit_system` and
   `results[].unit_system` are `physical`, `reduced` or
   `reduced_with_stated_conversion`; a reduced value is never given a physical
   unit (asserted for the examples and for the whole published corpus).
9. **Downloads only carry redistributable records.** Publication metadata and our
   annotations always qualify; dataset/database records only when the licence is
   explicit (MechanoProDB MIT). 123 of 123 published here; 0 withheld.
10. **`methods` tier beats `core` when a paper develops a method or benchmark.**
    Both tiers produce records; the tier is stored and reported.
11. **Site chrome is local to `/sim/`.** The shared `app.js` builds root-relative
    navigation that would break one level down, so the category renders its own
    nav/footer (fewer shared files touched). INTEGRATION.md has the merge steps.

## Not done, or stopped at

- **No git branch/PR** — there is no repository here (see *Status*).
- **Level 1 matches: 0** — construct evidence is the limit, not the matcher.
  Improving `system.construct` extraction (and asking for construct annotations on
  the experimental side) is the single highest-value next step.
- **BSDB**: unreachable; archived copy read, no data ingested, licence unknown.
- **ForceGen and Mykuliak data files**: not copied (licence/need); metadata and
  links only.
- **SMASH-SIM outputs**: absent, reader in place.
- **Level-3 data linking for MP/SPT** (DataCite deposit search, MBDB/DANDI probes):
  out of scope for this branch; the category's `data_availability` block is ready
  for it.
- **GtoPdb / Channelpedia cross-links**: not part of the Simulations category.
- **No browser was available** in this environment, so the `/sim/` pages were
  checked structurally (assets resolve, data files parse, mobile breakpoint rules
  present) rather than by rendering. The 375 px layout is handled in
  `website/sim/css/sim.css` and needs one human look.
- **Site navigation, sitemap and submit form are not wired** — deliberately, in
  `docs/sim/INTEGRATION.md`, because they need shared files owned by other branches.

## Open questions for the owner

1. **BSDB.** The site is 404 at both published addresses; the 2025-03-14 Internet
   Archive snapshot exists (`hub/data/sim/datasets/bsdb.json`). Is BSDB still
   reachable elsewhere, and should we ask the Cieplak group to host a copy — and
   for permission to redistribute the reduced-unit peak forces?
2. **Redistribution permission.** ForceGen's repository is MIT, but the dataset
   licence is unstated; MechanoProDB is MIT. Do we ask the Buehler lab (ForceGen)
   and the BSDB authors for explicit permission before ingesting the data files?
3. **Where should the "Simulation vs experiment" panel appear** on existing system
   pages — inline under the experimental results, or as a collapsed tab? Ready-made
   markup and the merge steps are in `docs/sim/INTEGRATION.md` §2.
4. **Should level 1 require a confirmed construct, or should a geometry-only match
   get its own label?** Currently geometry agreement is a published column
   (`geometry_match`) instead of a level, because the brief's vocabulary has three
   rungs. A fourth label (`same_molecule_same_geometry_construct_unconfirmed`) would
   make the 705 geometry-agreeing links first-class.
5. **Branding across five categories.** The Simulations pages call the category
   "Simulations" and use the shared visual style with a category tag; confirm the
   label wording ("Simulation" / "Simulations" / "SMASH-SIM") for the nav entry.
6. **Path mapping.** Should the category keep `website/schema/sim/` (the repository
   layout) or move to `schema/sim/` to match the brief's wording exactly?

---

## Reproduce it

```bash
cd hub
python -m sim.run --step all --limit 100 --page-size 100   # the corpus in this report
python -m sim.identifiers                                  # warm the category identifier table
python -m sim.verify                                       # Phase 6 checks
python -m pytest -q                                        # 107 passed
```

Smaller/shorter runs (a scratch directory, nothing written to `website/`):

```bash
python -m sim.run --step all --limit 40 --page-size 20 --out-dir out/sim-smoke
python -m sim.run --step fulltext --max-fulltext 20 --out-dir out/sim-smoke
```

### File inventory (new files only)

**Pipeline** — `hub/sim/__init__.py`, `spec.py`, `schema.py`, `harvest.py`,
`classify.py`, `extract.py`, `build_records.py`, `gazetteer_sim.py`, `identifiers.py`,
`fulltext.py`, `ingest.py`, `match.py`, `build_outputs.py`, `audit.py`, `verify.py`,
`run.py`, `verified_identifiers.json`.

**Schemas** — `website/schema/sim/smash-sim-record.schema.json`,
`website/schema/sim/smash-sim-results.schema.json`, 6 files in
`website/schema/sim/examples/`.

**Site** — `website/sim/{index,explore,stats,schema,submit,system}.html`,
`website/sim/css/sim.css`, `website/sim/js/{sim,overview,explore,stats,system}.js`,
generated data `website/sim/data/{index,matches,systems}.js`.

**Downloads** — `website/downloads/sim/smash-sim-{records.jsonl.gz,summary.csv,matches.csv}`.

**Data** — `hub/data/sim/datasets_index.json`, `hub/data/sim/datasets/*.json` (5),
`hub/data/sim/mechanoprodb_entries.json`, `hub/data/sim/matches.parquet`,
`hub/data/sim/coverage.csv`.

**Docs/tests** — `docs/sim/{ARCHITECTURE_NOTES,INTEGRATION}.md`,
`docs/sim/{scope_audit_sample.csv,verification.md}`, `hub/test_sim_schema.py`,
`hub/test_sim_pipeline.py`, `REPORT-sim.md`.