# Agent brief: add a single-molecule FRET module to smash-bio.org

You are extending SMASH-BIO (https://smash-bio.org), an open, annotated index of single-molecule force spectroscopy (SMFS) studies. Your task is to add a **single-molecule FRET (smFRET) module** that brings the same treatment to smFRET studies: harvest the literature, annotate each study with FAIR metadata, extract reported results with evidence, link deposited datasets, and flag data availability.

You will run unattended overnight. Work in phases, commit after each phase, and leave a clear morning report. When a decision is ambiguous, make the most reasonable choice, record it in `REPORT.md` under "Decisions taken", and keep going. Stop and leave a note only for things that can't be undone (see "Hard rules").

---

## Hard rules

1. **Do not deploy to production and do not push to `main`.** Work on a branch named `feature/smfret-module`. Push the branch and open a PR (or leave it local with a note if no remote or no credentials are available). The owner reviews and deploys.
2. **Do not break the existing SMFS site.** Existing URLs, downloads, the v3 record schema, and the existing JSONL/CSV outputs must be byte-compatible or strictly additive. Run the existing test suite and build before and after your changes. If tests were failing before you started, record that and leave them as they were.
3. **No fabricated data.** Every auto-extracted value carries an `evidence` object (method, snippet, confidence), exactly as the existing pipeline does. If a value cannot be grounded in text, leave it null. Never invent DOIs, accessions, or dataset links. Before writing any identifier to a record, check that it resolves.
4. **Respect external APIs.** Throttle requests and cache all responses to disk. The harvest must be resumable, so a crash mid-run resumes rather than restarts. Set a descriptive User-Agent with the contact email `mhalma@opensourcemed.info`.
5. **Time-box.** If any single phase exceeds roughly 2.5 hours of wall-clock time, commit what works, write down where you stopped, and move on to the next phase on a reduced scope.

---

## Phase 0: Orient (do not skip)

1. Locate the repository and read it end to end before changing anything. Identify:
   - the site generator and stack (static HTML? which build tool?)
   - the harvest/annotation pipeline (Europe PMC + DataCite + OpenAIRE ScholeXplorer + gazetteer + extraction, described at https://smash-bio.org/schema.html#pipeline)
   - the schema files: `schema/smash-smfs-record.schema.json` and `schema/smash-smfs-results.schema.json`
   - the system gazetteer and identifier resolvers (UniProt, Rfam, ChEBI, and the others)
   - the download outputs (`downloads/smash-smfs-records.jsonl.gz`, `smash-smfs-summary.csv`, `smash-smfs-datasets.csv`)
   - page templates: home, explore, systems, stats, schema, submit
2. Write `docs/smfret/ARCHITECTURE_NOTES.md` summarizing what you found and how the smFRET module will slot in. **Reuse the existing pipeline modules wherever possible.** The FRET module should be a new technique family that runs on the same machinery, not a fork.
3. Run the existing build and tests, and record the baseline in `REPORT.md`.

## Phase 1: Schema (`smash-fret` v1.0.0)

Create `schema/smash-fret-record.schema.json` (JSON Schema Draft 2020-12). It must **reuse the shared definitions** from the SMFS schema by `$ref`: identifiers with the `verified` flag, `evidence`, data-availability block, provenance and curation level, `fair_completeness`, and the `Result` structure. If shared definitions aren't currently factored out, move them into `schema/smash-common.schema.json` and make the v3 SMFS schema reference it. The SMFS schema's validation behaviour must not change; add a test that proves this by re-validating every existing record.

Keep the same four-section backbone as Table 3 (hardware, assay, construct, solution) so cross-technique pages work. FRET-specific content:

**`technique`**
- `primary`: one of `smfret_confocal_burst`, `smfret_tirf_widefield`, `smfret_confocal_scanning_immobilized`, `smfret_in_cell`, `smfret_nanopore_or_zmw`, `smfret_methods`
- `excitation_scheme`: `continuous`, `ALEX`, `nsALEX`, `PIE`, `MFD`, `msALEX`, `other`
- `correlative`: array of other modalities, reusing the SMFS correlative vocabulary. Include force techniques here so hybrid force-plus-FRET studies (e.g., optical tweezers with confocal FRET) are captured.
- `cross_ref_smfs_record`: the SMASH-BIO SMFS record ID when the same publication is also in the force index

**`hardware`**
- shared: temperature (K), detection type
- `confocal` block: laser lines (nm) and powers (µW), pulse repetition rate (MHz), objective NA, pinhole (µm), detectors (SPAD / HyD / PMT), TCSPC resolution (ps), polarization-resolved (bool)
- `widefield` block: illumination (TIRF / HILO / epi), camera model and type (EMCCD / sCMOS), frame time (ms), pixel size (nm), emission splitter
- `zmw_or_nanopore` block: aperture or pore type and diameter (nm)

**`construct`**
- the biological system, using the existing gazetteer and identifiers
- `labels[]`: dye name (with ChEBI where resolvable), role (donor / acceptor / acceptor2), labelling site (residue number or nucleotide position), labelling chemistry (maleimide-Cys, click/UAA, NHS, enzymatic, hybridization), labelling efficiency (fraction)
- `forster_radius_nm` and its source (calculated / literature / measured)
- `immobilization`: `freely_diffusing`, `PEG_biotin_streptavidin`, `vesicle_encapsulation`, `nanodisc`, `in_cell`, `other`

**`solution`**
- buffer, salts, pH, ligands (ChEBI), and denaturant (type and molar concentration; this matters for IDP studies)
- `photostabilization`: oxygen scavenger (`GODCAT`, `PCA_PCD`, `none`, `other`), triplet-state quencher or ROXS components (Trolox, COT, NBA, others)

**`analysis`**
- `correction_factors`: alpha (leakage), beta, gamma, delta (direct excitation), each with a value and whether it was reported
- `accurate_vs_apparent_E`: `accurate`, `apparent`, `unreported`
- `software[]`: named tools with versions and a URL when given (e.g., FRETbursts, PAM, tMAVEN, Deep-LASI, SPARTAN, iSMS, MASH-FRET, FRETboard, ebFRET, HaMMy, vbFRET, SMART). Name a tool only when the text names it.
- `kinetic_model`: `HMM`, `dwell_time`, `FCS`, `BVA`, `dynamic_PDA`, `H2MM`, `other`, `none`

**Observable vocabulary** (add to the results schema, with canonical units):
`fret_efficiency_apparent` (dimensionless), `fret_efficiency_accurate`, `stoichiometry`, `interdye_distance_mean_nm`, `interdye_distance_R_E_nm`, `donor_lifetime_ns`, `acceptor_lifetime_ns`, `anisotropy`, `population_fraction`, `n_states`, `transition_rate_s-1`, `dwell_time_ms`, `radius_of_gyration_nm`, `end_to_end_distance_nm`, `scaling_exponent_nu`, `dissociation_constant_M`, `forster_radius_nm`. Each result records the states or transition it refers to and the conditions under which it was measured. Use the existing `Result` shape.

**`TraceSet` extension** (raw data)
Extend the existing TraceSet sidecar to cover two kinds of raw data:
- photon streams: Photon-HDF5, PicoQuant `.ptu/.pt3/.ht3`, Becker & Hickl `.spc`, with channel mapping (donor/acceptor, parallel/perpendicular, excitation period)
- intensity time traces: SMART `.smd`, `.traces`, and generic HDF5/CSV/NumPy

Add `has_raw_photon_data` and `has_raw_movies` alongside the existing `has_raw_traces` flag.

Add a schema version file, a changelog entry, and validation tests using at least five hand-written example records. One of them must be a hybrid force-plus-FRET study.

## Phase 2: Harvest and scope

1. **Europe PMC queries**, using the existing harvester. Search for `"single-molecule FRET"`, `smFRET`, `"single molecule FRET"`, `"single-pair FRET"`, `"spFRET"`, `"FRET" AND ("single molecule" OR "single-molecule") AND (burst OR TIRF OR ALEX OR PIE OR "multiparameter fluorescence")`, and `"smFRET" AND ("optical tweezers" OR "magnetic tweezers")`.
   - Run a full harvest if the existing pipeline handles volume comfortably. Otherwise run it for 2015 to the present first, then backfill earlier years.
2. **DataCite and repository search** for deposits with FRET vocabulary in Zenodo, Figshare, OSF, Dryad, and institutional repositories. Also check PDB-IHM entries that use FRET restraints. Link those as related structural models, not as datasets.
3. **Scope classifier.** Write a rule-based classifier, like the existing one, that marks each paper as `core`, `methods`, or `out_of_scope`.
   - `core`: the paper measures single molecules with FRET and studies a biological system.
   - `methods`: the paper develops smFRET instruments, analysis, or benchmarks (e.g., multi-lab blind studies).
   - `out_of_scope`: ensemble FRET; FRET biosensors read out in bulk or by FLIM-FRET imaging in cells, unless the analysis is per-molecule; and non-biological FRET (materials or photophysics only).
4. **Quality audit.** Draw a random sample of 60 classified papers, stratified across the three labels. Write their titles, abstract snippets, and assigned labels to `docs/smfret/scope_audit_sample.csv` with an empty `human_label` column for the owner. Also report your own best estimate of precision, but label it clearly as a self-assessment.

## Phase 3: Annotate and extract

1. Run the existing system gazetteer and identifier resolvers on the smFRET corpus. When common smFRET systems are missing from the gazetteer, add them with resolvable identifiers. Examples: DNA Holliday junctions, Rev/RRE, the riboswitch families, the ribosome and its translation factors, SNAREs, LacY, LeuT, GltPh, BetP, Hsp90, Hsp70, PBP/SBP domains, and IDPs such as α-synuclein, tau, ProTα, H1, NLS/importin, and the p53 TAD. Verify every identifier you add.
2. Extract the hardware, construct, solution, and analysis fields from Methods text where open-access full text exists, and from abstracts otherwise, using the same methods as the existing extractor. Each value needs evidence, and confidence must be calibrated. Dye names and labelling sites are high-value; prioritize them.
3. Extract results from abstracts, and from full-text results sections where available, into the new observable vocabulary. Only extract a number when the text gives the number, the unit, and the entity or transition it refers to.
4. Compute `fair_completeness` for each record, using the same definition as the SMFS records.
5. **Cross-linking.** For every publication that appears in both the SMFS index and the FRET index, set `cross_ref_smfs_record` and add the reverse link on the SMFS side. The reverse link must be additive and optional, so the v3 SMFS schema still validates.

## Phase 4: Site integration

Follow the existing visual design and templates exactly. Don't introduce new frameworks.

1. **Navigation.** Add a technique-family switch (Force spectroscopy | smFRET) to the header and to the explore page. The default remains force spectroscopy. FRET pages live under `/fret/`, e.g. `/fret/explore.html`, `/fret/stats.html`, `/fret/schema.html`, and `/fret/submit.html`.
2. **Explore.** Mirror the existing filters (has public dataset, raw data, class, technique) and add filters for excitation scheme, immobilization, accurate vs. apparent E, and dye pair.
3. **System pages.** Unify them. Each system page shows its force studies and its FRET studies in separate sections, and a combined panel when both exist (e.g., "measured by both"). This cross-technique view is the main payoff of the module, so make it work well.
4. **Stats.** Show data-availability rates, raw-data rates, correction-factor reporting rates, and completeness by year for FRET. Put a side-by-side comparison with the force spectroscopy rates where the metrics are comparable.
5. **Schema page.** Document `smash-fret` v1.0.0 in the same style as the existing schema page, with downloads.
6. **Submit.** Accept FRET records that validate against the new schema.
7. **Home page.** Add a short block announcing the smFRET index, with live counts. Leave the hero untouched; changing it is a branding decision for the owner (see "Open questions").
8. **Downloads.** Add `downloads/smash-fret-records.jsonl.gz`, `smash-fret-summary.csv`, and `smash-fret-datasets.csv`.
9. **Attribution.** On the FRET schema page, cite the community standards work: Lerner et al., eLife 2021, doi:10.7554/eLife.60416; Hellenkamp et al., Nat Methods 2018, doi:10.1038/s41592-018-0085-0; and Photon-HDF5, Ingargiola et al., Biophys J 2016, doi:10.1016/j.bpj.2015.11.013. Verify each DOI before you publish it. Also note that the ELIXIR FRET-IDP Community Resource (2026–2027) is developing a dedicated registry and the MIADE-FRET reporting standard for disordered-protein FRET data, and state that SMASH-BIO aims to link to it rather than duplicate it.

## Phase 5: Verify

1. Validate every generated FRET record against the schema. Records that fail must not be published; list them in the report.
2. Re-validate every SMFS record against v3. There must be zero regressions.
3. Build the site, serve it locally, and check every new page and a sample of existing pages: no console errors, no broken links (run a link checker), and the mobile layout at 375 px width works.
4. **Spot-check 20 random FRET records by hand.** Confirm that the evidence snippets actually support each extracted value, that the identifiers resolve, and that the dataset links open and contain what the record says. Log the results.

## Morning report (`REPORT.md` at the repository root)

Keep it short and scannable:
- **Status:** the branch, the PR link, and whether the build and tests pass
- **Counts:** papers harvested, in scope (`core` / `methods`), with a linked dataset, with raw photon data or movies, with cross-links to the SMFS index, and results extracted
- **Quality:** the scope self-assessment, the 20-record spot-check outcome, and a list of known weak extractors
- **Decisions taken:** each ambiguous call you made, with a one-line rationale
- **Not done / stopped at:** anything time-boxed out, and how to resume
- **Open questions for the owner**, including at least:
  - Branding: does the site stay "SMASH-BIO: Force Spectroscopy Data Hub", or become a broader single-molecule data hub? (You made no hero or title change.)
  - Should in-cell smFRET stay in scope?
  - Is the scope audit labelled and ready for classifier tuning?
  - Should the site reach out to the FRET-IDP project to set up mutual linking?
