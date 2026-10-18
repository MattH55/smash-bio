//! Physical constants and the reference protocol numbers.
//!
//! Two unit systems live in this engine and they must never be confused, which
//! is exactly why `smash-sim-results.schema.json` makes `unit_system` required:
//!
//!   * protein SMD runs are **reduced** (epsilon = 1, mass = 1 per Ca, lengths
//!     in Angstrom). The reference implementation itself labels its output
//!     "reduced (epsilon, Angstrom). Not piconewtons." (smash-sim pull.py:58)
//!     and PROTOCOL.md:39 says the speed grid "is a configuration value, not
//!     1 m/s, until epsilon and the time unit are calibrated". This engine takes
//!     that seriously: forces come out in epsilon/Angstrom, and a pN value is
//!     emitted only when the caller supplies an explicit epsilon_in_pN_nm scale.
//!   * nucleic nearest-neighbour + WLC results are **physical** (pN, nm,
//!     kcal/mol), because those parameters are published in physical units.

/// 1 kcal/mol expressed in pN nm. Used to compare a chemical free energy with
/// mechanical stretching work. Same constant as the reference (thermo.py:8).
pub const KCAL_TO_PN_NM: f64 = 6.9477;

/// Thermal energy at 298.15 K in pN nm (k_B T = 4.11 pN nm). Scaled linearly in
/// temperature elsewhere: kT(T) = KT_PN_NM_298 * T / 298.15. Reference: params.py:18.
pub const KT_PN_NM_298: f64 = 4.114;

/// Nearest-neighbour tables are parametrised at 37 C. Reference: params.py:10.
pub const T_NN_K: f64 = 310.15;

/// Default measurement temperature when a record does not state one. Reference:
/// NUCLEIC_PLAN.md line 3, which also requires this default to be flagged.
pub const T_DEFAULT_K: f64 = 298.15;

/// SantaLucia (1998) monovalent-salt slope, kcal/mol per phosphate per ln(M).
/// Reference: params.py:11.
pub const SALT_N_PHOSPHATE_SLOPE: f64 = 0.114;

/// Single-strand rise per nucleotide, nm. **ASSUMED** high-salt value after
/// Smith, Cui & Bustamante (Science 1996); flagged as an assumption in
/// NUCLEIC_PLAN.md line 29 and in params.py:13-14.
pub const SS_RISE_NM: f64 = 0.59;

/// Single-strand persistence length, nm. Same ASSUMED source as SS_RISE_NM.
pub const SS_LP_NM: f64 = 0.75;

/// Double-helix rise per base pair, nm (B-DNA). Used for handles and for linear
/// duplex unzipping only.
pub const DS_RISE_NM: f64 = 0.34;

/// dsDNA persistence length, nm. Same usage caveat as DS_RISE_NM.
pub const DS_LP_NM: f64 = 50.0;

// ---- Protein reference protocol (smash-sim/docs/PROTOCOL.md) ----
/// Bond stiffness in the form V = BOND_K (r - r0)^2. ASSUMED leading factor of
/// 1/2 omitted, so the curvature is 200. PROTOCOL.md:20, go_model.py:11.
pub const BOND_K: f64 = 100.0;
/// Angle stiffness, V = ANGLE_K (theta - theta0)^2. go_model.py:12.
pub const ANGLE_K: f64 = 20.0;
/// Non-native excluded-volume sigma, Angstrom. **ASSUMED** (PROTOCOL.md:24).
pub const NONNATIVE_SIGMA: f64 = 4.0;
/// Minimum sequence separation for a native contact. go_model.py:15.
pub const SEQ_SEP: usize = 4;
/// Native-contact cutoff, Angstrom. **ASSUMED** (PROTOCOL.md:26).
pub const CONTACT_CUTOFF: f64 = 8.0;
/// Non-native pairs are ignored beyond this distance, Angstrom. go_model.py:150.
pub const NONNATIVE_CUTOFF: f64 = 12.0;
/// A contact counts as intact below this multiple of its native distance.
/// PROTOCOL.md:45, pull.py:80.
pub const CONTACT_INTACT_FACTOR: f64 = 1.2;
/// Stiff anchor holding the first Ca, epsilon/Angstrom^2. PROTOCOL.md:41.
pub const ANCHOR_K: f64 = 50.0;
/// Langevin friction, reduced. **ASSUMED** (PROTOCOL.md:36).
pub const FRICTION: f64 = 1.0;
/// Langevin thermal energy, reduced. **ASSUMED** (PROTOCOL.md:37).
pub const KBT_REDUCED: f64 = 0.5;
/// Time step, reduced. **ASSUMED** (PROTOCOL.md:38).
pub const DT: f64 = 0.002;
/// Default reduced spring constant, epsilon/Angstrom^2. PROTOCOL.md:39.
pub const SPRING_K_DEFAULT: f64 = 0.1;
/// Default reduced pull speed, Angstrom per reduced time. pull.py:12.
pub const SPEED_DEFAULT: f64 = 0.2;
/// Default trajectory length in steps. pull.py:12 (`n_steps: int = 800`).
pub const N_STEPS_DEFAULT: usize = 800;

/// Longest Ca trace the engine will build in one browser tab. Brief Phase 1:
/// "proteins up to 400 residues (offer a domain picker for larger ones)".
/// Refusing is better than an out-of-memory tab crash, which is also why
/// `EngineError::too_large` exists.
pub const MAX_PROTEIN_RESIDUES: usize = 400;

// ---- Protein contour-length analysis convention (PROTOCOL.md:47) ----
// These are the only protein numbers in this file that are physical, because
// PROTOCOL.md:47 states them as an *analysis* convention, not as model
// parameters: "DeltaLc uses the extensible worm-like chain from the SOD1
// paper's analysis convention: protein persistence length 0.85 nm, elastic
// modulus 2000 pN, 0.36 nm per amino acid. That conversion needs forces in pN."
// A reduced-unit trace therefore reports extension in Angstrom and no pN DeltaLc
// until a calibration supplies the pN scale (see `protein::Calibration`).

/// Protein persistence length, nm. PROTOCOL.md:47.
pub const PROTEIN_LP_NM: f64 = 0.85;
/// Stretch (elastic) modulus of a pulled polypeptide, pN. PROTOCOL.md:47.
pub const PROTEIN_STRETCH_MODULUS_PN: f64 = 2000.0;
/// Contour length per amino acid in the fully extended chain, nm. PROTOCOL.md:47.
pub const AA_RISE_NM: f64 = 0.36;
