# Agent brief: add single-particle tracking, single-channel recording, and mass photometry modules to smash-bio.org

You are extending SMASH-BIO (https://smash-bio.org), an open, annotated index of single-molecule force spectroscopy (SMFS) studies. The site annotates each study with FAIR metadata, extracts reported results with evidence, links deposited datasets, and flags data availability. Your task is to add three new technique modules that get the same treatment:

1. **Single-particle tracking (SPT)**: path `/spt/`, slug `spt`
2. **Mass photometry (MP)**: path `/mp/`, slug `mp`
3. **Single-channel electrophysiology (SC)**: path `/channel/`, slug `channel`

Build them in that order. SPT is the highest priority, MP is the quickest build, and single-channel recording is the most specialized.

You will run unattended overnight. Make the most reasonable choice when something is ambiguous, log it under "Decisions taken", and keep going.

---

## ⚠️ Another agent is working in the same repository at the same time

A separate agent is building an **smFRET module** on branch `feature/smfret-module`. That agent has been told it may:
- factor shared schema definitions out into `schema/smash-common.schema.json` and make the v3 SMFS schema reference it
- add a technique-family switch to the site header and the explore page
- unify the system pages so force and FRET studies appear together
- add reverse links to SMFS records
- write `REPORT.md` at the repository root, plus `docs/smfret/`

To avoid merge conflicts, you must follow these rules:

1. **Work in a separate git worktree on branch `feature/sc-spt-mp-modules`**, created from the current `main`. Never check out, rebase onto, or edit the smFRET branch.
2. **Do not edit any of these:**
   - `schema/smash-smfs-record.schema.json`, `schema/smash-smfs-results.schema.json`, and any `schema/smash-common.schema.json`
   - existing site templates, partials, the header and navigation, the home page, the explore, systems, stats, schema, and submit pages, and existing CSS and JS bundles
   - existing download files
   - `REPORT.md`
3. **Shared definitions:** your module schemas need the shared definitions (identifiers with the `verified` flag, `evidence`, data availability, provenance and curation level, `fair_completeness`, and `Result`). Reference them by `$ref` to the **existing v3 schema's `$defs`** if they exist there. If they don't, copy them into `schema/modules/_shared-pending.schema.json`, mark them `TODO(integration)`, and reference that file. Never create `smash-common.schema.json` yourself.
4. **Pipeline code:** add each module as **new files** (a config, plugin, or new modules) that call the existing harvester, gazetteer, resolvers, and extractors. If a shared function genuinely must change, make the smallest **purely additive** change you can (a new optional parameter or a new function; never a changed signature or default), and list it in the report so the merge is easy.
5. **Separate outputs:** write docs under `docs/modules/`, the report to `REPORT-modules.md`, caches under `.cache/modules/`, and site pages only under `/spt/`, `/mp/`, `/channel/`.
6. **Shared API budget:** both agents query Europe PMC, DataCite, and OpenAIRE at the same time. Throttle to **half** the request rate the existing pipeline uses. Cache everything, make the harvest resumable, and set the User-Agent contact to `mhalma@opensourcemed.info`.
7. **Integration is deferred.** Anything that needs shared files (the nav entries, the technique-family switch, the unified system pages, and the shared-schema consolidation) goes into `docs/modules/INTEGRATION.md` as exact, ready-to-apply instructions. Write them as diffs or steps the owner can apply after both branches merge. Assume the smFRET branch merges first.

If your harness supports parallel subagents, you may run one per module. Only one agent may edit files outside the module directories, and every module must still follow all of the rules above.

## General hard rules

- **No deploy and no push to `main`.** Push the branch and open a PR. If no remote or no credentials are available, leave it local and say so.
- **No fabricated data.** Every auto-extracted value carries `evidence` (method, snippet, confidence). Leave a field null rather than guessing. Never invent DOIs, accessions, or dataset links. Check every identifier resolves before writing it.
- **Leave the existing site intact.** Run the existing build and tests before and after, and record any tests that were already failing.
- **Time-box.** Allow roughly 2 hours per module. If a module runs over, commit what works and record the stopping point.

---

## Phase 0: Orient (once, shared)

Read the repository: the stack, the pipeline (Europe PMC + DataCite + OpenAIRE ScholeXplorer + gazetteer + extractors; see https://smash-bio.org/schema.html#pipeline), the v3 schemas, and the page templates. Write `docs/modules/ARCHITECTURE_NOTES.md` describing how a technique module plugs in. Build all three modules on that same plug-in pattern, so a fourth module is cheap to add.

## Per-module work (do this for each module)

**A. Schema.** Create `schema/modules/smash-<slug>-record.schema.json` and `smash-<slug>-results.schema.json` (JSON Schema Draft 2020-12, version 1.0.0). Keep the Table 3 backbone (hardware, assay, construct, solution, data availability) so later cross-technique pages work. Add the module-specific fields and observables listed below. Write at least four hand-made example records and validation tests for each module.

**B. Harvest and scope.** Run Europe PMC queries and a DataCite deposit search. Write a rule-based classifier that labels each paper `core`, `methods`, or `out_of_scope`. Write a 45-paper stratified audit sample to `docs/modules/<slug>/scope_audit_sample.csv`, with an empty `human_label` column.

**C. Annotate and extract.** Use the existing gazetteer and resolvers. Where the gazetteer is missing frequent systems, add them in a **module-local gazetteer extension file**, not the shared gazetteer. Extract metadata from Methods text (open-access full text) or from abstracts. Extract a result only when the number, the unit, and the entity it refers to are all stated. Compute `fair_completeness` using the same definition as the SMFS records.

**D. Data linking.** Search DataCite, Zenodo, Figshare, Dryad, OSF, plus the module-specific repositories listed below. Record file formats and flag whether raw data is present.

**E. Pages.** Mirror the existing explore and stats pages under the module path, using the existing visual style. Use copies or new templates; do not modify the shared ones. Each module gets these pages: `index.html` (overview with live counts), `explore.html`, `stats.html`, `schema.html`, and `submit.html`. Pages may link back to the main site, but the main site doesn't link to them yet; that happens at integration.

**F. Downloads.** Write `downloads/modules/smash-<slug>-records.jsonl.gz`, `-summary.csv`, and `-datasets.csv`.

**G. Cross-references.** Record publication-level overlaps in a separate file, `data/modules/crossrefs.jsonl`, as `{doi, modules:[...], smfs_record_id?}`. Never edit SMFS records directly.

---

## Module 1: Single-particle tracking (`spt`)

**Scope.** Include single-molecule and single-particle tracking of biomolecules or biological particles: proteins (including transcription factors), mRNPs, viruses, vesicles, and membrane receptors, studied in vitro (DNA curtains, supported bilayers) or in cells or organisms. `methods` covers tracking algorithms, benchmarks (e.g., the AnDi challenge), and instrumentation such as MINFLUX tracking. Exclude whole-cell or organism tracking, PIV, colloid and soft-matter physics without a biological system, and plain microrheology beads (record those only when the probe is a biological particle).

**Standard.** Align fields with **MIAPTE** (Minimum Information About Particle Tracking Experiments; Rigano & Strambio-De-Castillia). Map each field to the corresponding MIAPTE element in `docs/modules/spt/MIAPTE_mapping.md`, and record the alignment explicitly in the schema documentation.

**Module fields:**
- imaging: modality (`TIRF`, `HILO`, `light_sheet`, `confocal`, `spinning_disk`, `MINFLUX`, `iSCAT`, `orbital_tracking`, `other`), frame time (ms), exposure (ms), stroboscopic illumination (bool), pixel size (nm), camera, excitation power density (kW/cm²), 3D method (`none`, `astigmatism`, `biplane`, `double_helix`, `other`)
- probe: label type (`HaloTag`, `SNAP`, `fluorescent_protein`, `organic_dye`, `quantum_dot`, `gold_nanoparticle`, `other`), dye name (with ChEBI where resolvable), labelling density or strategy (sparse labelling, PA/PC-FP)
- sample: context (`in_vitro_surface`, `supported_bilayer`, `DNA_curtain`, `live_cell_nucleus`, `live_cell_cytoplasm`, `live_cell_membrane`, `organism`), cell line (Cellosaurus ID), organism (NCBI Taxonomy)
- tracking: software and version (TrackMate, u-track, SMAP, Spot-On, ThunderSTORM, and others; name a tool only when the text names it), maximum jump (µm), gap frames, minimum track length
- analysis model: `MSD`, `Spot_On`, `vbSPT`, `saSPT`, `HMM`, `jump_distance`, `residence_time_survival`, `other`

**Observables:** `diffusion_coefficient_um2_s-1`, `anomalous_exponent_alpha`, `bound_fraction`, `residence_time_s`, `confinement_radius_nm`, `velocity_nm_s-1`, `run_length_nm`, `step_size_nm`, `localization_precision_nm`, `mean_track_length_frames`, `n_diffusive_states`.

**Raw data:** trajectories (CSV with id/x/y/(z)/t, TrackMate XML, Spot-On-compatible MATLAB or CSV formats) and movies (TIFF/OME-TIFF/ND2/CZI). Add the flags `has_trajectories` and `has_raw_movies`. Define a `TrajectorySet` sidecar that maps columns to standard names and units.

**Extra repositories:** the BioImage Archive and the Image Data Resource (IDR). Search both for deposits linked to included papers.

---

## Module 2: Mass photometry (`mp`)

**Scope.** Include mass photometry and iSCAT-based mass measurement of biomolecules: oligomeric state, complex assembly, binding affinity and stoichiometry, AAV full/empty characterization, membrane-protein mass photometry, and mass-sensitive particle tracking (MSPT) on bilayers. `methods` covers new instrumentation, calibration, and analysis. Exclude iSCAT imaging that doesn't measure mass (cross-reference those papers to SPT when they track particles).

**Module fields:**
- instrument: manufacturer and model (e.g., Refeyn OneMP/TwoMP/SamuxMP, or custom), field of view (µm²), frame rate (Hz), acquisition duration (s)
- calibration: standards used (e.g., BSA, β-amylase, thyroglobulin, or others named in the text), contrast-to-mass slope if reported, calibration type (`standards`, `in_situ`, `none_reported`)
- assay: surface (`glass`, `PLL_coated`, `supported_bilayer`, `other`), method (`droplet_dilution`, `buffer_free_focus`, `flow`, `MSPT`), sample concentration (nM), incubation time
- analysis software: DiscoverMP, PhotoMol, eSPC, custom

**Observables:** `molecular_mass_kDa` (one per species or peak), `relative_abundance` (fraction), `oligomeric_state`, `dissociation_constant_M`, `binding_stoichiometry`, `mass_resolution_kDa`, `event_count`, `aav_full_fraction`, `diffusion_coefficient_um2_s-1` (for MSPT; use the same name and unit as SPT, so values can be compared across modules).

**Raw data:** ratiometric movies and event lists (vendor `.mp`/`.h5`, CSV event lists). Add `has_event_lists` and `has_raw_movies`. Since no specialist repository exists, the data-availability report for this module is the main deliverable. Make the stats page lead with deposit rates.

**Extra repositories:** the generalist repositories only, plus MBDB (mbdb-data.org) in case mass photometry deposits appear there.

---

## Module 3: Single-channel electrophysiology (`channel`)

**Scope.** Include recordings that resolve single-channel events: cell-attached, inside-out, and outside-out patches; planar lipid bilayer reconstitution; and droplet interface bilayers. They can cover ion channels, transporters with channel modes, pore-forming toxins, and channel-like receptors. `methods` covers kinetic-analysis software, idealization algorithms, and instrumentation. Exclude whole-cell macroscopic-only studies (record whole-cell data alongside as `correlative` when it's in the same paper), nanopore sequencing, and nanopore analyte-sensing work where the pore is just a sensor rather than the biological subject.

**Identifiers:** in addition to UniProt, resolve channels and ligands to **IUPHAR/BPS Guide to Pharmacology (GtoPdb)** target and ligand IDs. Record mutations in HGVS-style protein notation as stated in the text. Use Cellosaurus for cell lines, and add *Xenopus* oocytes as an expression system.

**Module fields:**
- configuration: `cell_attached`, `inside_out`, `outside_out`, `planar_lipid_bilayer`, `droplet_interface_bilayer`, `other`
- hardware: amplifier, sampling rate (kHz), filter type and cutoff (kHz), pipette resistance (MΩ), holding or test potentials (mV), temperature (K)
- expression system: `HEK293`, `CHO`, `xenopus_oocyte`, `native_tissue`, `reconstituted_proteoliposome`, `other`
- solutions: pipette and bath ionic composition (mM), and ligands with concentrations (ChEBI/GtoPdb)
- analysis: software (QuB, HJCFIT/DCprogs, SCAN, Clampfit, others), idealization method, kinetic model type (number of open and closed states, model topology if stated), and dead time / resolution (µs)

**Observables:** `unitary_conductance_pS`, `unitary_current_pA`, `open_probability`, `mean_open_time_ms`, `mean_closed_time_ms`, `burst_duration_ms`, `n_open_states`, `n_closed_states`, `transition_rate_s-1`, `subconductance_level_pS`, `ec50_M`, `reversal_potential_mV`, `dwell_time_ms` (use the same name and unit as the SMFS and FRET vocabularies where they overlap).

**Raw data:** ABF (Axon), HEKA PatchMaster `.dat`, NWB, QuB `.qdf`, `.ldt`, and CSV. Add `has_raw_current_traces`. Define a `CurrentTraceSet` sidecar (channel names, units, gain, filter, sampling rate).

**Extra repositories:** DANDI (search for NWB single-channel data), plus Channelpedia as a related resource. Link to it; don't duplicate it.

---

## Phase Z: Verify (all modules)

1. Validate every module record against its schema. Records that fail are excluded from publication and listed in the report.
2. Confirm the existing SMFS records and pages are unchanged: there must be no diff to existing files, apart from any additive pipeline changes you documented.
3. Build the site and serve it locally. Check every module page for console errors, broken links (run a link checker), and the mobile layout at 375 px width.
4. **Spot-check 15 random records per module by hand:** confirm the evidence supports each value, the identifiers resolve, and the dataset links open and contain what the record says.

## Morning report (`REPORT-modules.md`)

- **Status:** the branch, the PR link, and whether the build and tests pass
- **A table per module:** papers harvested; in scope (`core` / `methods`); with linked data; with raw data; results extracted; median `fair_completeness`; spot-check pass rate
- **Cross-module overlaps:** counts from `crossrefs.jsonl`, e.g. SPT↔MP (MSPT), SPT↔SMFS (motors and DNA curtains), and channel↔SMFS (mechanosensitive channels)
- **Additive changes to shared code:** the exact files and functions
- **Decisions taken**
- **Not done / stopped at**
- **Open questions for the owner**, including at least:
  - The site's overall branding, now that it spans five techniques
  - Whether to contact the MIAPTE authors about adopting the SPT schema as a MIAPTE implementation
  - Whether single-channel data should cross-link to Channelpedia or GtoPdb on system pages
  - Merge order and integration, with a pointer to `docs/modules/INTEGRATION.md`
