# SMASH-Pull architecture

SMASH-Pull is a browser-only pulling simulator. One Rust crate (`pull-engine/`) is compiled to a
WebAssembly module, which a static page (`website/pull/`) runs in Web Workers. No server code runs.

```
website/pull/index.html ── js/pull-app.js ──► js/pool.js ──► N × js/engine-worker.js ──► wasm/pull_engine.wasm
        │                     │                                   (one wasm instance per worker)
        │                     ├─ js/sources.js   RCSB / AlphaFold DB / UniProt fetches (CORS, read-only)
        │                     ├─ js/analysis.js  events → ΔLc, Bell–Evans, unfolding order, dwell times
        │                     ├─ js/charts.js    SVG charts (export SVG/PNG)
        │                     └─ js/viewer.js    canvas Cα viewer
        └─ js/chrome.js  nav/footer/theme (mirror of ../js/app.js for a sub-folder; see INTEGRATION.md)
```

## Engine (`pull-engine/src`)

| Module | Role |
|---|---|
| `api.rs` | The single entry point: `call(json) -> json`. Ops `version`, `structure`, `protein_run`, `nucleic_landscape`, `nucleic_kinetic`. Errors are `{"error":{code,message,detail}}`, never panics. |
| `wasm.rs` | Raw C ABI: `pe_alloc`, `pe_free`, `pe_call`, `pe_result_len`. |
| `protein.rs` | **Parity path**: PDB parser, Gō model builder, the reference Hamiltonian (central-difference dihedrals) and integrator, kept line-for-line with smash-sim so Gate 1a can pin it. |
| `fast.rs` | **Production path**: same Hamiltonian, analytic dihedral gradient, Verlet neighbour list, one force call per step, positive tension, contact break steps, trajectory frames, event detection. |
| `prep.rs` | Structure flags the reference never had: B-factor/pLDDT, disulfides, metals, ligands, chain breaks. |
| `nucleic.rs` | Parity path for nucleic thermodynamics (reference `nasim`). |
| `nakin.rs` | Production nucleic model: thermodynamics at T + loop initiation, instrument (handles + trap), equilibrium curve, F½, kinetic Monte Carlo (ramp and clamp), hairpin detection. |
| `wlc.rs`, `units.rs`, `rng.rs`, `json.rs`, `error.rs`, `dmath.rs` | Support. |

## Decisions

**D1. Rust with zero dependencies.** No serde, rand, wasm-bindgen, ViennaRNA or SMOG. This keeps the
licence surface to our own code plus published parameter values, and lets the build run offline.
Cost: hand-written JSON reader/writer (`json.rs`) and a 55-line C-ABI shim (`wasm.rs`).

**D2. One JSON API for native and wasm.** `api::call` is used by the page (through `wasm.rs`) and by the
native harnesses (`examples/api_call.rs`), so Gate 5 compares exactly the code the page runs.

**D3. Bit-for-bit determinism across targets.** Every stochastic result is a pure function of
(seed, request). `f64::ln/exp/acos` call the platform maths library (MSVC CRT natively, Rust's libm on
wasm32), and those differ in the last bit. Once a trajectory differs by one bit, it drifts. `dmath.rs`
therefore implements `ln`, `exp` and `acos` with `+ - * /` and `sqrt` only, which IEEE 754 rounds
identically everywhere. Native dihedral cos/sin are taken from the atan2 arguments, with no trig call. The
result is byte-identical output native vs Chrome (Gate 5a). `acos` uses fdlibm's rational approximation
(Sun notice preserved); the earlier pure arcsine series was 4× slower.

**D4. A canvas Cα viewer instead of Mol\*.** Mol\* would add a large bundle, a CDN or self-hosted copy to
maintain, and a WebGL dependency, all to draw what is a single line of beads. The canvas viewer (about 150
lines, no dependencies) rotates, zooms (pinch on touch), picks residues, colours by index, pLDDT or
unfolding order, and animates trajectory frames. Mol\* remains an option if all-atom display is wanted.

**D5. No third-party requests from the pull pages.** The brief allows only smash-bio.org assets and
structure/sequence servers. The pages therefore use system fonts and inline SVG icons (no Google Fonts,
no Font Awesome CDN) and carry **no Google tag**. See INTEGRATION.md if analytics are wanted.

**D6. Own page chrome.** `../js/app.js` rewrites links only for `/sim/`; from `/pull/` its links would be
broken, and the brief forbids editing it. `js/chrome.js` renders the same nav/footer markup with `../`
links and shares the `smash:theme` localStorage key. INTEGRATION.md gives the two-line app.js change
after which chrome.js can be dropped.

**D7. Worker pool, not threads in wasm.** A wasm call cannot be interrupted, so each replica is one
call and Cancel terminates the workers. `navigator.hardwareConcurrency` workers. Phones (<4 cores, or
coarse pointer with a short screen side under 600 px) get the Quick protocol only.

**D8. Effective-contour ΔLc.** A WLC fit to a simulated force curve is biased by solvent drag at the
speeds a browser can afford (PROTOCOL.md §P4). The model gives the exact quantity instead. That is the
shortest bonded-plus-intact-contact path between the attachment points, computed from the engine's
per-contact break steps. I27 releases 28 nm in total, matching experiment.

**D9. Nucleic kinetics on a ticked trap.** The trap moves in 0.05 nm ticks and is held fixed within a
tick. That makes the rates piecewise constant, so Gillespie with exponential waits cut at tick
boundaries is exact for that trajectory, and G(n, X) is cached per tick. The result is 10⁶–10⁷ events/s natively.

## Memory and size

- `pull_engine.wasm`: ≈ 245 KB, no imports.
- Protein runs keep at most `max_samples` (1,500) trace points and ≤ 80 frames (f32, 3 decimals in JSON).
- Proteins are capped at 400 residues (domain picker above that); nucleic equilibrium at 2,000 bp;
  kinetics at 200 bp in the UI.

## Build

```
cd pull-engine
cargo test --release                                  # 80 tests: unit, parity (1a), fast=reference (1b)
cargo build --release --lib --target wasm32-unknown-unknown
copy target/wasm32-unknown-unknown/release/pull_engine.wasm ../website/pull/wasm/
```

Toolchain used: cargo 1.99 (stable), target `wasm32-unknown-unknown`. Release profile: opt-level 3, LTO,
`panic = "abort"`, stripped.
