# REPORT — SMASH-Pull (browser pulling simulator)

Date: 2026-10-14. Brief: `smash-pull-browser-agent-brief (1).md`.

## Status

| Part | State |
|---|---|
| Engine (Rust → wasm, 245 KB) | Done. 81 native tests pass. |
| Simulator page `website/pull/index.html` | Done. Protein and DNA/RNA flows checked end-to-end in Chrome 155. |
| `about.html`, `benchmarks.html` | Done |
| Docs: ARCHITECTURE, PROTOCOL, VALIDATION (results appended), INTEGRATION | Done |
| Protein engine | **Live, labelled experimental** (Gate 2b failed) |
| Nucleic engine | **Live, labelled experimental** (Gate 4 absolute force failed) |
| Deployment | **Deployed 2026-10-14 at the owner's request** (https://smash-bio.org/pull/), with INTEGRATION §1b (nav entry), §2 (system-page link) and §3 (sitemap, edited directly because the hub build hit a OneDrive cloud-only file). Previously: not deployed, not pushed. There is no git repository in this workspace, so there is no PR either. Everything is local; see "How to ship". |

Written only under `website/pull/`, `pull-engine/`, `docs/pull/` and `tests/pull/`. No shared nav, template,
CSS/JS bundle, schema or existing page was edited. The integration steps are in `INTEGRATION.md`.

## Gates (criteria frozen in VALIDATION.md before the runs)

| Gate | Result | Key number |
|---|---|---|
| 1a parity with reference | pass | 19/19 parity tests |
| 1b production force = reference | pass | energy 1e-9, force 1e-5 |
| 1c trajectory statistics vs reference | **pending** | Python reference ≈ 10 h; running, resumable (python tests/pull/gate1c.py) |
| 2a ubiquitin N–C > K48–C | pass | 11.8 vs 6.0 ε/Å, p = 3e-8 (partly drag) |
| 2b GFP directions | **fail** | ρ = −0.80; peaks follow pulled span (drag) |
| 3 ViennaRNA | not_run | no folding algorithm (pre-declared) |
| 4 hairpin class (Woodside 20R55/4T) | **fail** | F½ 18.5 vs 13.2 ± 3 pN; Δx 16.4 nm pass; GC trend pass |
| 5a native = Chrome bytes | pass | identical SHA-256, protein and nucleic |
| 5b Chrome repeatable | pass | identical |
| 5c Firefox/Safari | not_run | not installed |
| 6a I27 standard < 60 s | **fail** | 168.7 s (12 workers, 6-core laptop, partly loaded) |
| 6b phone | not_run | no phone; phones limited to Quick |

Full numbers are in VALIDATION.md § Results.

## Performance

- **Engine.** Native production force call: about 14–35 µs for I27 (89 residues), folded to unfolded, on
  an unloaded machine. WASM in V8 is 1.2–2× native.
- **Chrome, through the real page.**
  - I27 Quick (3 runs): 15.6 s.
  - I27 Standard (30 runs): 168.7 s.
  - Talin R3 Standard: 372 s.
- **Nucleic.** A 20-bp hairpin pull–relax cycle at 100 nm/s takes 0.1–0.3 s (≈ 4×10⁶ Monte Carlo
  events); 20 cycles take 3.4 s in Chrome.
- **Bug found and fixed.** The JSON string reader was quadratic. A 3 MB NMR PDB (2L7A) took more than
  10 minutes per request; it now takes 25 s. A regression test was added (long_strings_parse_in_linear_time).
- **Gate 6a needs about 3× more speed.** Candidates:
  - WASM SIMD for the non-native loop;
  - fewer neighbour-list rebuilds (≈ 1 per 57 steps now);
  - or an owner decision to redefine "standard". That would mean a new pre-registered gate.

## Network and privacy (CORS checks, 2026-10-14)

The page's own files are loaded from the site. Other requests, made only on user action:

| Host | Use | CORS | Notes |
|---|---|---|---|
| files.rcsb.org | `/download/<ID>.pdb` | `Access-Control-Allow-Origin: *` | Large entries are mmCIF-only, so their 404 is explained to the user. |
| alphafold.ebi.ac.uk | `/api/prediction/<acc>` → `pdbUrl` | `*` | Model files are now `model_v6`, so the API's URL is used, not a hard-coded version. Node without a browser User-Agent gets 403; browsers get 200. |
| rest.uniprot.org | `uniprotkb/search?query=checksum:<CRC64>` | `*` | Only the CRC64 of a typed sequence is sent. Verified: ubiquitin CRC64 C42A35397FFD9B52 resolves. |

In the smoke test the only hosts contacted were the local server and files.rcsb.org. The pages carry no Google tag,
no Google Fonts and no CDN (decision D5); INTEGRATION.md §4 leaves analytics to the owner.

## Licences

| Component | Licence / status |
|---|---|
| pull-engine (all Rust), page JS/CSS | Project code; zero third-party dependencies |
| `dmath::acos` rational approximation | fdlibm, © 1993 Sun Microsystems: "Permission to use, copy, modify, and distribute this software is freely granted, provided that this notice is preserved." The notice is kept in `dmath.rs` and `about.html`. |
| DNA NN stacks | SantaLucia, PNAS 95:1460 (1998). Published measurements, transcribed. |
| RNA NN stacks | Xia et al., Biochemistry 37:14719 (1998). Published measurements. |
| Hairpin-loop initiation | NNDB (Mathews lab): DNA `dna_loop_dg/dh.txt`, RNA Turner 2004 `turner_2004_loop_dg/dh.txt`. Published values. |
| Structures | RCSB PDB (CC0), AlphaFold DB (CC BY 4.0), UniProt (CC BY 4.0). Fetched at run time, not redistributed. Test fixtures in `tests/pull/fixtures` are PDB entries (CC0). |

## Decisions (see ARCHITECTURE.md for the full list)

1. **Canvas Cα viewer instead of Mol\*** (D4): no dependency or CDN, and it is enough for a bead model.
2. **Deterministic maths in the engine** (D3). Native and Chrome were 12 bytes apart until `ln/exp/acos`
   were made platform-independent. Now byte-identical.
3. **Production run plan**: dt = 0.01 τ.
   - Quick: 0.2 Å/τ × 3.
   - Standard: 0.05, 0.1 and 0.2 Å/τ × 10.

   dt = 0.02 was rejected after a single-seed check showed 10–15 % lower peaks.
4. **ΔLc from the effective contour** (D8, PROTOCOL P6). WLC fits were biased by drag (≈9 nm vs 28 nm for I27).
5. **Gate 4 is a sequence-class benchmark.** The exact Woodside sequences were not retrievable (bot-checked
   supplement); none were reconstructed from memory.
6. **Not re-fitted after failures.** ssDNA elasticity (Gate 4) and the protein speed/friction (Gate 2) were
   left as locked. Changing them to pass would invalidate the gates.
7. **Own page chrome** (D6), because app.js cannot be edited and does not handle `/pull/`.

## Limitations

- **Protein forces are model units (ε/Å).** No calibration exists; `website/pull/data/calibration.json` is
  null on purpose.
- **Drag dominates the protein tension** at browser-affordable speeds. Pulling geometries with different
  spans cannot be ranked by peak (Gate 2b). Ubiquitin's correct ranking (2a) may be partly drag.
- **Nucleic model:**
  - perfect stems only (no mismatches, bulges, pseudoknots);
  - F½ about 5 pN high on the 20-bp class;
  - Mg²⁺ is approximate;
  - the kinetic time scale follows the assumed k₀.
- **Input formats:** PDB format only (no mmCIF upload); ≤ 400 residues per run; kinetics ≤ 200 bp.
- **No in-browser structure prediction.** A protein sequence works only if UniProt has the exact sequence
  and AlphaFold DB has a model.
- **Gate 3 not run**: there is no secondary-structure folding algorithm, which was declared before the gate.

## Open questions for the owner

1. **Protein friction.** Should the browser protocol move to lower friction (e.g. γ = 0.1) to reduce drag?
   That would make it a different protocol from the reference pipeline's. It would need a new, pre-registered
   Gate 2 run, since the current one is locked.
2. **ssDNA elasticity.** Should it be replaced by a measured model (e.g. salt-dependent extensible WLC/FJC
   from the literature)? It would have to be chosen *before* re-running Gate 4 on a fresh sequence class.
3. **Analytics.** Add the site's Google tag to the pull pages (INTEGRATION.md §4)?
4. **Deployment.** Deploy now as beta, or after Gate 1c completes?

## How to ship (not done)

1. Apply INTEGRATION.md §1–3 (nav, "Simulate this" links, sitemap).
2. Run `python hub/deploy_ftp.py` (it uploads `website/`, including `pull/`).
3. Rotate the FTP passwords that were pasted in chat earlier in this session.

## Files

- `pull-engine/`: crate.
  - `src/api.rs`, `wasm.rs`, `fast.rs`, `nakin.rs`, `prep.rs`, `dmath.rs`: new this phase.
  - `examples/`: `api_call`, `bench`, `forcebench`, `nabench`, `gate4`, `mathbench`.
- `website/pull/`: `index.html`, `about.html`, `benchmarks.html`, `css/pull.css`, `js/*.js`,
  `wasm/pull_engine.wasm`, `data/{benchmarks,validation,calibration}.json`.
- `tests/pull/`:
  - harnesses: `gate1c.py`, `gate2.mjs`, `gate5.mjs`, `gate6.mjs`, `benchmarks.mjs`, `build_validation.mjs`;
  - drivers and checks: `cdp.mjs` (Chrome driver), `smoke.mjs`, `shots.mjs`, `run_jobs.mjs`, `wasm_call.mjs`;
  - `results/*.json`.
- `docs/pull/`: `ARCHITECTURE.md`, `PROTOCOL.md`, `VALIDATION.md`, `INTEGRATION.md`, this report.
