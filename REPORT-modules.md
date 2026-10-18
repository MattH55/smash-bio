# SPT, mass-photometry and single-channel modules — report

## Status

- **Branch / PR:** not created. This workspace is **not a Git repository**, so no
  worktree/branch could be made and no remote is available. All work is present
  as files.
- **Build / tests:** `python -m pytest hub -q` -> **66 passed, 188 subtests**.
  `python -m compileall` clean on `hub/modules/*`, `hub/common.py` and both new
  test modules.
- **Published SMFS artefacts intact:** `smash-smfs-records.jsonl.gz`,
  `-summary.csv` and `-datasets.csv` are byte-identical to their pinned SHA-256
  digests (`test_modules_schema.py::test_force_downloads_are_byte_unchanged`).
  No SMFS 3.1.0 schema, template, CSS/JS bundle or download was modified.
- **Smoke corpus** (`--limit 40 --page-size 20 --min-year 2015`, output in
  `hub/out/smoke/`): 311 kept articles across the four modules, **66 records**
  written, **0 schema failures**.

## The problem this session fixed

The modules were producing **0 records** for smFRET, SPT and mass photometry
(and 7 for single-channel) despite a working pipeline. Two independent gates,
not the code path, were responsible:

1. **Entity grounding was almost empty.** `gazetteer_ext` held a small local
   term list and **never consulted the shared `gazetteer.py`**, so the project's
   ~230 curated systems (motors, cytoskeleton, ribosome, chaperones, viruses,
   vesicles, streptavidin, DNA/RNA constructs, Cell-Ontology cells …) were
   invisible to every module. Only 1 of 74 core smFRET articles and 13 of 32
   core SPT articles matched anything.
2. **smFRET required a named donor/acceptor pair**, and abstracts rarely name
   dyes — only 5 of 114 harvested smFRET articles mention any dye name, and 1
   mentions a listed pair. The record schema *requires* >=2 fluorophores with at
   least one `donor` and one `acceptor`, so a record cannot be invented; the fix
   is to read the Methods text, which the briefs already ask for.

### What changed

| change | file | effect |
|---|---|---|
| Shared gazetteer merged read-only, with per-module type mapping | `modules/gazetteer_ext.py` | entity grounding up ~3.5x (see table) |
| Module-local systems corrected and extended, every identifier resolver-checked | `modules/gazetteer_ext.py`, `modules/identifiers.py`, `modules/verified_identifiers.json` | 108 verified identifiers, 0 unverified |
| Methods text step, reusing the SMFS `s05_fulltext` fetcher/parser | `modules/fulltext.py`, `modules/run.py` (new `fulltext` step, `--max-fulltext`) | dye pairs in smFRET 1 -> 4; more entities, hardware and software |
| Dye-pair list widened to 24 standard pairs with vendor-tolerant patterns | `modules/build_records.py` | matches `Alexa Fluor 555`, `ATTO647N`, `Cy3/Cy5`, … |
| Records built only from the brief's in-scope tiers | `modules/run.py` | `peripheral` rows stay for the scope audit, never become records |
| `data_availability` derived from what the full text shows | `modules/fulltext.py`, `modules/build_records.py` | `public_repository` / `code_only` / `journal_supplement` / `on_request` / `fulltext_checked_none` |
| Single-channel configuration tag mapping fixed | `modules/build_records.py` | `droplet_interface` -> `droplet_interface_bilayer` (was 1 validation failure) |
| Shared schema refs repointed, staging copy deleted | 6 `website/schema/modules/*.schema.json`, `modules/build_outputs.py`, `test_modules_schema.py` | 50 refs -> `../smash-common.schema.json#/$defs/…` |

## Per-module results (smoke corpus)

| module | slug | schema + examples | in scope (core/methods) | records | skipped | full texts parsed | median fair | spot-check |
|---|---|---|---|---|---|---|---|---|
| Single-particle tracking | `spt` | 4 examples, validate | 35 | **18** | 17 | 10 | n/a | pending |
| Mass photometry | `mp` | 4 examples, validate | 47 | **31** | 16 | 13 | n/a | pending |
| Single-channel | `channel` | 4 examples, validate | 65 | **15** | 50 | 18 | n/a | pending |
| smFRET | `fret` | 5 records in `schema/examples/` (+12 module examples) | 79 | **2** | 77 | 20 | n/a | pending |

Grounding coverage on the in-scope rows (entities / dye pairs), abstract only vs
abstract + Methods:

| module | entity, abstract | entity, + Methods | dye pair, abstract | dye pair, + Methods |
|---|---|---|---|---|
| `fret` | 48 / 79 | **56 / 79** | 1 / 79 | **4 / 79** |
| `spt` | 13 / 35 | **18 / 35** | – | – |
| `mp` | 27 / 47 | **31 / 47** | – | – |
| `channel` | 15 / 65 | 15 / 65 | – | – |

`median fair_completeness` and the 15–20 record spot-check need a full harvest;
both are listed below. smFRET remains dye-gated by design: the schema cannot
represent a FRET assay without donor and acceptor, and only 4 of 79 in-scope
smFRET articles name a listed pair once Methods text is included (Methods were
available for 20 of them; 75 name no pair at all). Widening the corpus (more
full texts, lower `--min-year`, more query tags) is the lever, not loosening the
gate.

## Identifier verification

`modules/verified_identifiers.json` is committed and human-auditable: **108
codes, 0 unverified**. `python -m modules.identifiers [limit]` rebuilds it and
checkpoints after every code. Resolvers used, all confirmed live:

| scheme | resolver | example confirmed |
|---|---|---|
| UniProt | `rest.uniprot.org/uniprotkb/{acc}.json` (accession must echo back) | `P54582` BetP, `P02794` ferritin heavy chain, `Q96RD7` pannexin-1 |
| Rfam | EBI Search `ebisearch/ws/rest/rfam?query=RF00005` | `RF00162`, `RF00059`, `RF00050`, `RF00167`, `RF00036`, `RF00250` |
| ChEBI | EBI Search `chebi` (indexes the bare id, not `CHEBI:`) | `CHEBI:15956`, `CHEBI:46793` |
| GO | EBI Search `go` | `GO:0000786`, `GO:0005643`, `GO:0005874` |
| Cell Ontology | OLS4 `ols4/api/ontologies/cl/terms?obo_id=…&exact=true` | `CL:0000232`, `CL:0000540`, `CL:0000746` |
| GenBank | NCBI `esummary.fcgi?db=nuccore` | `J02459.1` (λ), `J01749.1` (pBR322), `L09137.2` (pUC19), `X02513.1` (M13), `J02482.1` (ΦX174) |

UniProt accessions the brief names for smFRET were verified and are in the
table: `P02920` LacY, `O67854` LeuT, `O59010` GltPh, `P0AEX9` MBP, `P0A6M8`
EF-G, `P0CE47` EF-Tu, `P06454` prothymosin alpha, `P52292` importin alpha,
`P04637` p53, `P37840` alpha-synuclein, `P10636` tau, `P07900` Hsp90, `P0DMV8`
Hsp70, `P04618` Rev, `P16403` histone H1.2.

**Not resolved: IUPHAR/BPS GtoPdb target ids.** The brief asks for them, but
`guidetopharmacology.org/services/targets` (with `uniprot=`, `uniprotAccession=`
or `name=` parameters, and by direct `/targets/546`) returned nothing across
four attempts, so no target id is emitted. The channel records say so in the
schema docs and the module README rather than carrying an unverified number.

### Gazetteer defects found and fixed

| was | is | evidence |
|---|---|---|
| `P54534` labelled BetP | `P54582` BetP; `P54534` is Bacilliredoxin BrxB | UniProt REST |
| `P02794` labelled ferritin light chain | `P02794` is ferritin **heavy** chain; light chain is `P02792` | UniProt REST |
| pannexin-1 planned as `O95471` | `O95471` is claudin-7; pannexin-1 is `Q96RD7` | UniProt REST |
| histone H1 planned as `P16403` = "H1-4" | `P16403` is histone **H1.2** (gene `H1-2`) | UniProt REST |

`test_modules_pipeline.py::GroundingTests` now fails if any declared identifier
is not resolver-verified, so the table cannot silently rot.

## Architecture notes

- **The shared gazetteer is consumed, not copied.**
  `gazetteer_ext.match_entities` matches module-local systems first, then the
  shared `gazetteer.py` entries, mapping each `entity_type` through
  `SHARED_TYPES` into the module's schema vocabulary. Types with no slot are
  dropped rather than mis-typed; generic shared names (e.g. "Kinesin" beside
  "Kinesin-1") yield to the specific sibling that already matched. The
  single-channel module opts out of the shared vocabulary entirely, because it
  contains no ion-channel targets and would only attach generic proteins.
- **Methods text reuses the SMFS step.** `modules/fulltext.py` imports
  `s05_fulltext.fetch_batch`/`FT_CACHE` unchanged, so the modules share its
  Europe PMC/NCBI behaviour and its on-disk cache (outside OneDrive) instead of
  downloading the same articles twice. The per-module index is
  `out/<slug>_fulltext_index.json`.
- **Smoke runs stay out of the site tree.** `--out-dir` redirects downloads and
  site data; `website/downloads/modules/` and `website/data/modules/` are still
  absent from this workspace.

## Additive changes to shared code

**None to the SMFS pipeline.** No SMFS script, schema, template, asset or
download changed. All edits are in module-owned files
(`hub/modules/*`, `hub/test_modules*.py`, `docs/modules/*`) plus the two
module-owned schema sets:

- the six `website/schema/modules/smash-{spt,mp,channel}-{record,results}.schema.json`
  files had their refs repointed (see above), and the module-owned staging copy
  `website/schema/modules/_shared-pending.schema.json` was deleted;
- `website/schema/smash-common.schema.json` (owned by the smFRET branch) was
  read but **not** edited.

## Decisions taken

- **Grounding over volume.** A record is written only when the schema's required
  fields are grounded in the text; everything else is counted as skipped.
- **Records only from in-scope tiers.** `peripheral` rows are kept in the
  classified file for the audit but never become records.
- **No fabricated identifiers**, GtoPdb included: an unconfirmed code is
  reported as `verified: false` or omitted.
- **Module-local gazetteer instead of editing `gazetteer.py`**, per the
  no-shared-edits rule, while still *using* the shared vocabulary.
- **Half-rate API use** (`harvest.RATE_FACTOR = 2.0`), full on-disk caching,
  resumable harvest and identifier checkpoints.
- **Validation gate before publishing:** `build_outputs` drops non-validating
  records and reports them (this is how the single-channel configuration bug was
  found).
- **MIAPTE:** the SPT schema is positioned as a MIAPTE-shaped report rather than
  a replacement (`docs/modules/MIAPTE_MAPPING.md`).

## Not done / next steps

1. **Live harvest at full width** for all four modules (the smoke corpus is 40
   hits per query tag). Resume:
   ```
   cd hub
   python -m modules.run spt     --step fulltext --max-fulltext 400
   python -m modules.run spt     --step records
   python -m modules.run mp      --step all
   python -m modules.run channel --step all
   ```
2. **Scope audit sample** `docs/modules/<slug>/scope_audit_sample.csv` — 45
   stratified papers per module with an empty `human_label` column (brief Phase
   B). The classifier and tier counts exist; only the sample files are missing.
3. **15–20 record spot-checks per module** (brief Phase Z), with the pass rate
   in the table above.
4. **`median fair_completeness`** per module once real records exist.
5. **Level-3 data linking for MP/SPT:** the DataCite deposit search and the
   MBDB/DANDI repo probes for these modules; the availability block already
   reports what full text shows.
6. **Site pages** `/spt/`, `/mp/`, `/channel/` and the download files under
   `website/downloads/modules/` (owner step; see `docs/modules/INTEGRATION.md`,
   whose shared-schema item is now done).
7. **GtoPdb** target/ligand ids for single-channel records once the service is
   reachable, and **Channelpedia** cross-links (link, do not duplicate).
8. **smFRET dye coverage:** more Methods text and more query tags are the lever;
   consider a `fluorophores` fallback only if the owners accept a record with an
   unresolved second dye (needs a schema change, so currently out of scope).

## Open questions for the owner

1. **Branding** now that the site spans five techniques.
2. Contact the **MIAPTE** authors about adopting the SPT schema as a MIAPTE
   implementation?
3. Should single-channel data cross-link to **Channelpedia** or **GtoPdb** on
   system pages?
4. **Merge order and integration** — see `docs/modules/INTEGRATION.md`
   (smFRET first; the schema consolidation is already done).
5. **Git remote** — how to commit this work (this workspace has no `.git`).