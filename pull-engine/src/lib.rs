//! # pull-engine
//!
//! Isolated in-browser force-pull engine for SMASH-BIO. Rust compiled to
//! `wasm32-unknown-unknown`; the same source builds a native test binary, so
//! every physics path the browser runs is covered by `cargo test`.
//!
//! Design constraints, recorded in full in `docs/pull/ARCHITECTURE.md`:
//!
//! * **Zero dependencies.** No serde, no rand, no wasm-bindgen, no ViennaRNA,
//!   no SMOG. The JSON reader/writer (`json`), the PRNG (`rng`), the Ca Gō
//!   Hamiltonian (`protein`) and the
//!   nearest-neighbour tables (`nucleic`) are hand-written from published
//!   primary literature, which keeps the bundle licence-clean and makes the
//!   build reproducible without a registry fetch.
//! * **Determinism.** Every stochastic run is a pure function of
//!   `(seed, config)`. Repeated runs byte-match, which is what makes the
//!   comparison against the Python reference pipeline meaningful.
//! * **Two unit systems, never mixed.** `reduced` for protein SMD, `physical`
//!   for nucleic nearest-neighbour results. The output schema makes
//!   `unit_system` mandatory for exactly this reason; see `units`.
//! * **Null, not zero.** A construct the model cannot represent, a stem that is
//!   not stable, and a diverged trajectory all emit `null` with a reason. The
//!   reference pipeline states the rule directly in `nucleic/docs/OUTPUT_FORMAT.md`
//!   line 7: "A null simulation is not a force of zero."

pub mod api;
pub mod dmath;
pub mod error;
pub mod fast;
pub mod json;
pub mod nakin;
pub mod nucleic;
pub mod prep;
pub mod protein;
pub mod rng;
pub mod units;
pub mod wasm;
pub mod wlc;

pub use error::{EngineError, EngineResult};

/// Engine build identity, written into every result so a stored JSON can be
/// traced back to the code that produced it.
pub const ENGINE_NAME: &str = "pull-engine";
pub const ENGINE_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Short identifier for the physical model families the engine can run.
/// Mirrors the `model_family` field of the results schema.
pub const MODEL_NN_WLC: &str = "nearest-neighbour+WLC";
pub const MODEL_GO_CA: &str = "Go-Ca-Langevin";

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_is_available() {
        assert_eq!(ENGINE_VERSION, "0.1.0");
        assert!(!ENGINE_NAME.is_empty());
    }
}
