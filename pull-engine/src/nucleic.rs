//! Nucleic-acid hairpins: published nearest-neighbour stacks plus a worm-like
//! chain, giving equilibrium half-unzipping forces in physical units.
//!
//! Parity target: smash-sim/nucleic/src/nasim/{params,thermo,hairpin,wlc}.py.
//!
//! Provenance of the numbers (transcribed, not fitted):
//!   DNA - Allawi & SantaLucia, Biochemistry 36:10581 (1997), the unified table
//!         as reproduced in SantaLucia, PNAS 95:1460 (1998).
//!   RNA - Xia, Mathews & Turner, Biochemistry 37:14719 (1998), the Watson-Crick
//!         stacks carried in the Turner 2004 set. U is matched as T.
//! Both are published measurements. Facts and measured values are not
//! copyrightable; this transcription is independent and the module carries no
//! third-party code, so the engine keeps its zero-dependency licence.
//! Values are (dH kcal/mol, dS cal/mol/K); dG = dH - T*dS/1000 at T_NN_K.

use crate::error::{EngineError, EngineResult};
use crate::units::*;
use crate::wlc;

type NnTable = &'static [(&'static str, f64, f64); 10];

/// Keyed 5'-XY-3' / 3'-ZW-5'. Only the 10 symmetry-unique stacks are published;
/// the other 6 spellings reuse the reverse-complement key (see `lookup`).
/// Public so the browser and the parity harness can display exactly what was used.
pub const DNA_NN: [(&str, f64, f64); 10] = [
    ("AA/TT", -7.9, -22.2),
    ("AT/TA", -7.2, -20.4),
    ("TA/AT", -7.2, -21.3),
    ("CA/GT", -8.5, -22.7),
    ("GT/CA", -8.4, -22.4),
    ("CT/GA", -7.8, -21.0),
    ("GA/CT", -8.2, -22.2),
    ("CG/GC", -10.6, -27.2),
    ("GC/CG", -9.8, -24.4),
    ("GG/CC", -8.0, -19.9),
];

/// RNA Watson-Crick stacks, Xia et al. 1998.
pub const RNA_NN: [(&str, f64, f64); 10] = [
    ("AA/TT", -6.82, -19.0),
    ("AT/TA", -9.38, -26.7),
    ("TA/AT", -7.69, -20.5),
    ("CA/GT", -10.44, -26.9),
    ("GT/CA", -11.40, -29.5),
    ("CT/GA", -10.48, -27.1),
    ("GA/CT", -12.44, -32.5),
    ("CG/GC", -10.64, -26.7),
    ("GC/CG", -14.88, -36.9),
    ("GG/CC", -13.39, -32.7),
];

#[inline]
fn comp(b: u8) -> Option<u8> {
    match b {
        b'A' => Some(b'T'),
        b'T' => Some(b'A'),
        b'C' => Some(b'G'),
        b'G' => Some(b'C'),
        _ => None,
    }
}

/// Normalise a sequence: uppercase, drop whitespace, U read as T (the notation
/// of the Xia table, as thermo.py:6 and :39 do).
pub fn normalise(seq: &str) -> Vec<u8> {
    seq
        .bytes()
        .filter(|b| !b.is_ascii_whitespace())
        .map(|b| b.to_ascii_uppercase())
        .map(|b| if b == b'U' { b'T' } else { b })
        .collect()
}

/// dG of one stack at a given temperature, kcal/mol.
fn dg_of(dh: f64, ds: f64, temperature_k: f64) -> f64 {
    dh - temperature_k * ds / 1000.0
}

/// Reverse the dinucleotide and swap strands: 5'-XY-3'/3'-ZW-5' becomes
/// 5'-WV-3'/3'-YX-5'. Turns the 6 unpublished spellings into the 10 published
/// ones (thermo.py:26-29).
fn flip_key(key: &str) -> String {
    match key.split_once('/') {
        Some((l, r)) => {
            let rl: String = r.chars().rev().collect();
            let ll: String = l.chars().rev().collect();
            format!("{rl}/{ll}")
        }
        None => key.to_string(),
    }
}

fn lookup(table: NnTable, key: &str) -> EngineResult<(f64, f64)> {
    for (k, dh, ds) in table.iter() {
        if *k == key {
            return Ok((*dh, *ds));
        }
    }
    let f = flip_key(key);
    for (k, dh, ds) in table.iter() {
        if *k == f {
            return Ok((*dh, *ds));
        }
    }
    Err(EngineError::unsupported(format!("no published stack {key}")).with(format!("tried {f}")))
}


#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Polymer {
    Dna,
    Rna,
}

impl Polymer {
    pub fn parse(s: &str) -> EngineResult<Polymer> {
        match s.trim().to_ascii_uppercase().as_str() {
            "" | "DNA" => Ok(Polymer::Dna),
            "RNA" => Ok(Polymer::Rna),
            other => Err(EngineError::bad_value("polymer", format!("{other:?} is DNA or RNA"))),
        }
    }
    pub fn as_str(self) -> &'static str {
        match self {
            Polymer::Dna => "DNA",
            Polymer::Rna => "RNA",
        }
    }
    fn table(self) -> NnTable {
        match self {
            Polymer::Dna => &DNA_NN,
            Polymer::Rna => &RNA_NN,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Geometry {
    /// Hairpin: opening n base pairs releases two single strands.
    Hairpin,
    /// Linear duplex unzipping: two singles minus the duplex rise.
    DuplexUnzip,
}

impl Geometry {
    pub fn parse(s: &str) -> EngineResult<Geometry> {
        match s.trim().to_ascii_lowercase().as_str() {
            "" | "hairpin" => Ok(Geometry::Hairpin),
            "duplex_unzip" | "duplex-unzip" | "unzip" | "zipping" => Ok(Geometry::DuplexUnzip),
            other => Err(EngineError::bad_value("geometry", format!("{other:?}"))),
        }
    }
    pub fn as_str(self) -> &'static str {
        match self {
            Geometry::Hairpin => "hairpin",
            Geometry::DuplexUnzip => "duplex_unzip",
        }
    }
}

/// One stem step: the published key and its free energy.
#[derive(Debug, Clone)]
pub struct Stack {
    pub key: String,
    pub dg_kcal: f64,
}

#[derive(Debug, Clone)]
pub struct StemThermo {
    pub sequence: String,
    pub polymer: Polymer,
    pub n_bp: usize,
    pub dg_1m_kcal: f64,
    pub salt_correction_kcal: f64,
    pub dg_fold_kcal: f64,
    pub na_molar: f64,
    pub temperature_k: f64,
    pub steps: Vec<Stack>,
}

/// Folding free energy of a Watson-Crick stem.
///
/// Bimolecular initiation is deliberately omitted: a hairpin is unimolecular
/// (NUCLEIC_PLAN.md line 19). The loop penalty is omitted unless the caller
/// states a loop length, which is the reference's `loop_unspecified` behaviour.
/// Salt is SantaLucia 1998: dG([Na]) = dG(1M) - 0.114 * (n_bp - 1) * ln[Na].
///
/// `temperature_k` here is the temperature the *thermodynamic tables* are read
/// at, not the temperature of the pull. The reference never overrides its
/// default of `T_NN_K` (thermo.py:12, hairpin.py:49), so `half_force` and
/// `mean_open` call this at `T_NN_K` and use `temperature_k` only for the WLC
/// elasticity and kT. Callers that want a temperature-dependent stem (a melt
/// curve) should pass the melt temperature explicitly and keep the two apart.
pub fn stem_delta_g(
    sequence: &str,
    polymer: Polymer,
    na_molar: f64,
    temperature_k: f64,
) -> EngineResult<StemThermo> {
    let seq = normalise(sequence);
    if seq.len() < 2 {
        return Err(EngineError::bad_value("sequence", "stem needs at least two nucleotides"));
    }
    if seq.len() > 512 {
        return Err(EngineError::too_large(format!("{} nucleotides in a stem", seq.len())));
    }
    for b in &seq {
        if comp(*b).is_none() {
            return Err(EngineError::bad_value(
                "sequence",
                format!("base {:?} is not A, C, G, T or U", *b as char),
            ));
        }
    }
    if !(na_molar > 0.0) {
        return Err(EngineError::bad_value("na_molar", "sodium concentration must be positive"));
    }

    let table = polymer.table();
    let mut steps = Vec::with_capacity(seq.len() - 1);
    let mut total = 0.0f64;
    for pair in seq.windows(2) {
        let key = format!(
            "{}{}/{}{}",
            pair[0] as char,
            pair[1] as char,
            comp(pair[0]).unwrap() as char,
            comp(pair[1]).unwrap() as char
        );
        let (dh, ds) = lookup(table, &key)?;
        let dg = dg_of(dh, ds, temperature_k);
        total += dg;
        steps.push(Stack { key, dg_kcal: dg });
    }
    let n_bp = seq.len();
    let phosphates = (n_bp - 1) as f64;
    // dmath::ln: platform-independent bits (Gate 5); equal to f64::ln within 1 ulp
    let correction = -SALT_N_PHOSPHATE_SLOPE * phosphates * crate::dmath::ln(na_molar);

    Ok(StemThermo {
        sequence: seq.iter().map(|b| *b as char).collect(),
        polymer,
        n_bp,
        dg_1m_kcal: total,
        salt_correction_kcal: correction,
        dg_fold_kcal: total + correction,
        na_molar,
        temperature_k,
        steps,
    })
}

/// Contour released by opening `n_open` base pairs, nm (hairpin.py:15-20).
pub fn contour_nm(n_open: usize, geometry: Geometry) -> f64 {
    let n = n_open as f64;
    match geometry {
        Geometry::Hairpin => 2.0 * n * SS_RISE_NM,
        Geometry::DuplexUnzip => n * (2.0 * SS_RISE_NM - DS_RISE_NM),
    }
}

#[derive(Debug, Clone)]
pub struct HalfForce {
    pub thermo: StemThermo,
    /// The temperature the pull is measured at. The reference publishes this as
    /// `temperature_K` (hairpin.py:67); `thermo.temperature_k` is a different
    /// number (always `T_NN_K` on this path) and must not be substituted for it.
    pub measurement_k: f64,
    pub geometry: Geometry,
    pub delta_lc_nm: f64,
    pub unfold_cost_pn_nm: f64,
    pub f_half_pn: f64,
    pub grid_used: String,
}

/// Half-unfolding force: the force at which the accumulated stretching work
/// equals the unfolding free energy (NUCLEIC_PLAN.md line 33).
///
/// This is an equilibrium quantity: no loading rate and no friction enter. The
/// grid and the crossing rule are the reference's (hairpin.py:52-60): 1600
/// points over 0.05-80 pN, and because work[i] integrates through forces[i+1]
/// the reported force is that sample, not the one at the crossing index.
pub fn half_force(
    sequence: &str,
    polymer: Polymer,
    na_molar: f64,
    geometry: Geometry,
    temperature_k: f64,
) -> EngineResult<HalfForce> {
    // Chemistry is tabulated at 37 C, so stem_delta_g is evaluated at T_NN_K
    // (thermo.py:12 defaults to it and hairpin.py:49 never overrides it) even
    // when the pull is measured at another temperature. temperature_k enters
    // only the WLC elasticity below. Mixing the two would move every reported
    // force by several pN, so this split is deliberate, not incidental.
    let thermo = stem_delta_g(sequence, polymer, na_molar, T_NN_K)?;
    let cost = -thermo.dg_fold_kcal * KCAL_TO_PN_NM;
    let length = contour_nm(thermo.n_bp, geometry);

    let mut out = HalfForce {
        thermo,
        measurement_k: temperature_k,
        geometry,
        delta_lc_nm: length,
        unfold_cost_pn_nm: cost,
        f_half_pn: f64::NAN,
        grid_used: String::new(),
    };

    if !(cost > 0.0) {
        // Stem is not stable under these parameters. Emit null, not zero:
        // OUTPUT_FORMAT.md line 7, "A null simulation is not a force of zero."
        out.grid_used = "none_stem_unstable".into();
        return Ok(out);
    }

    let forces = wlc::linspace(0.05, 80.0, 1600);
    let mut acc = 0.0f64;
    let mut crossed: Option<f64> = None;
    for i in 0..forces.len() - 1 {
        let e0 = wlc::extension_nm(forces[i], length, SS_LP_NM, temperature_k);
        let e1 = wlc::extension_nm(forces[i + 1], length, SS_LP_NM, temperature_k);
        acc += (e1 + e0) * 0.5 * (forces[i + 1] - forces[i]);
        if acc >= cost {
            crossed = Some(forces[i + 1]);
            break;
        }
    }
    match crossed {
        Some(f) => {
            out.f_half_pn = f;
            out.grid_used = "0.05-80pN/1600".into();
        }
        None => out.grid_used = "0.05-80pN/1600_below_window".into(),
    }
    Ok(out)
}

/// Expected number of open base pairs at one force, from Boltzmann weights of
/// the one-dimensional unzipping coordinate (hairpin.py:71-103). The salt term
/// is distributed evenly across stacks, exactly as the reference does.
pub fn mean_open(
    sequence: &str,
    force_pn: f64,
    polymer: Polymer,
    na_molar: f64,
    geometry: Geometry,
    temperature_k: f64,
) -> EngineResult<f64> {
    // Chemistry at T_NN_K (see half_force for why); temperature_k drives the
    // elasticity and the Boltzmann weights below.
    let thermo = stem_delta_g(sequence, polymer, na_molar, T_NN_K)?;
    let n_steps = thermo.steps.len().max(1);
    let salt_each = thermo.salt_correction_kcal / n_steps as f64;

    // Prefix sums of the favourable stack free energies, in pN nm, along the
    // unfolded direction.
    let mut running = 0.0f64;
    let mut step_cost = Vec::with_capacity(n_steps);
    for st in &thermo.steps {
        running += -(st.dg_kcal + salt_each) * KCAL_TO_PN_NM;
        step_cost.push(running);
    }

    let grid = wlc::linspace(0.05, force_pn.max(0.05), 400);
    let kt = KT_PN_NM_298 * (temperature_k / 298.15);
    let mut energies = vec![0.0f64; thermo.n_bp + 1];
    for n_open in 1..=thermo.n_bp {
        // Opening n_open bp breaks n_open - 1 stacks; the reference caps this at
        // the number of published steps and is explicit that a step is a stack.
        let broken = n_open.min(step_cost.len());
        let chemical = if broken > 0 { step_cost[broken - 1] } else { 0.0 };
        let length = contour_nm(n_open, geometry);
        let mut acc = 0.0f64;
        for i in 0..grid.len() - 1 {
            let e0 = wlc::extension_nm(grid[i], length, SS_LP_NM, temperature_k);
            let e1 = wlc::extension_nm(grid[i + 1], length, SS_LP_NM, temperature_k);
            acc += (e1 + e0) * 0.5 * (grid[i + 1] - grid[i]);
            if grid[i + 1] >= force_pn {
                break;
            }
        }
        energies[n_open] = chemical - acc;
    }

    let emin = energies.iter().cloned().fold(f64::INFINITY, f64::min);
    let mut w = Vec::with_capacity(energies.len());
    let mut z = 0.0f64;
    for e in &energies {
        let x = (-(e - emin) / kt).exp();
        if x.is_finite() {
            w.push(x);
            z += x;
        } else {
            w.push(0.0);
        }
    }
    if !(z > 0.0) {
        return Err(EngineError::divergence("partition function collapsed"));
    }
    let mut mean = 0.0f64;
    for (n, p) in w.iter().enumerate() {
        mean += n as f64 * p / z;
    }
    Ok(mean)
}

/// Pairing check used before a stem is trusted: the ends of a single
/// `(((...)))` hairpin must be Watson-Crick complementary. Branched structures
/// and pseudoknots return None, matching hairpin.py:23-43 - they are
/// `model_gap`, never silently simulated as a hairpin (NUCLEIC_PLAN.md line 9).
pub fn hairpin_stem(sequence: &str, dot_bracket: &str) -> Option<String> {
    let seq = normalise(sequence);
    let dot: Vec<u8> = dot_bracket.bytes().filter(|b| !b.is_ascii_whitespace()).collect();
    if seq.len() < 4 || dot.len() != seq.len() {
        return None;
    }
    let open = dot.iter().take_while(|b| **b == b'(').count();
    if open < 2 {
        return None;
    }
    let mid = open + dot[open..].iter().take_while(|b| **b == b'.').count();
    if mid == open || mid >= dot.len() {
        return None;
    }
    let close = dot[mid..].iter().take_while(|b| **b == b')').count();
    if mid + close != dot.len() || close != open {
        return None;
    }
    let stem = &seq[..open];
    let right = &seq[seq.len() - open..];
    for (l, r) in stem.iter().zip(right.iter().rev()) {
        match comp(*l) {
            Some(c) if c == *r => {}
            _ => return None,
        }
    }
    Some(stem.iter().map(|b| *b as char).collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_stack_dg_matches_published_37c_values() {
        // SantaLucia 1998 reports dG37 of AA/TT = -1.00, CG/GC = -2.17,
        // GC/CG = -2.24, TA/AT = -0.58 kcal/mol. The engine derives dG from the
        // published (dH, dS) pair, and those tabulated dG values are rounded
        // independently, so agreement is to ~0.02 kcal/mol, not exactly.
        let checks = [("AA/TT", -1.00), ("CG/GC", -2.17), ("GC/CG", -2.24), ("TA/AT", -0.58)];
        for (key, expected) in checks {
            let (dh, ds) = lookup(&DNA_NN, key).unwrap();
            let dg = dg_of(dh, ds, T_NN_K);
            assert!((dg - expected).abs() < 0.02, "{key}: {dg} vs {expected}");
        }
    }

    #[test]
    fn symmetry_flip_finds_unpublished_spellings() {
        // Keys are 5'-XY-3' over the partners written 3'-to-5' in pairing order,
        // so 5'-AG-3' is "AG/TC". That spelling is not published; flipping must
        // recover the published CT/GA (-7.8, -21.0).
        let direct = lookup(&DNA_NN, "CT/GA").unwrap();
        let flipped = lookup(&DNA_NN, "AG/TC").unwrap();
        assert_eq!(direct, flipped);
        assert!((flipped.0 + 7.8).abs() < 1e-12);
        // A key that is not a Watson-Crick stack in either spelling is refused.
        assert!(lookup(&DNA_NN, "AA/CA").is_err());
        assert!(lookup(&DNA_NN, "ZZ/AA").is_err());
    }

    #[test]
    fn rna_stacks_are_the_xia_1998_set() {
        let (dh, ds) = lookup(&RNA_NN, "GC/CG").unwrap();
        assert!((dh + 14.88).abs() < 1e-9 && (ds + 36.9).abs() < 1e-9);
    }

    #[test]
    fn salt_is_neutral_at_one_molar_and_destabilises_dilute_salt() {
        let s = "GCGCGCGCGC";
        let one = stem_delta_g(s, Polymer::Dna, 1.0, T_NN_K).unwrap();
        assert!(one.salt_correction_kcal.abs() < 1e-12);
        let low = stem_delta_g(s, Polymer::Dna, 0.01, T_NN_K).unwrap();
        assert!(low.salt_correction_kcal > 0.0, "dilute salt must destabilise");
        assert!(low.dg_fold_kcal > one.dg_fold_kcal);
    }

    #[test]
    fn gc_stem_is_stronger_than_at_stem() {
        let at = stem_delta_g("ATATATATAT", Polymer::Dna, 1.0, T_NN_K).unwrap();
        let gc = stem_delta_g("GCGCGCGCGC", Polymer::Dna, 1.0, T_NN_K).unwrap();
        assert!(gc.dg_fold_kcal < at.dg_fold_kcal);
    }

    #[test]
    fn hairpin_delta_lc_is_two_singles_per_bp() {
        let h = half_force("GCGCGCGCGC", Polymer::Dna, 1.0, Geometry::Hairpin, 298.15).unwrap();
        assert!((h.delta_lc_nm - 2.0 * 10.0 * SS_RISE_NM).abs() < 1e-12);
        let z = half_force("GCGCGCGCGC", Polymer::Dna, 1.0, Geometry::DuplexUnzip, 298.15).unwrap();
        assert!((z.delta_lc_nm - 10.0 * (2.0 * SS_RISE_NM - DS_RISE_NM)).abs() < 1e-12);
    }

    #[test]
    fn unstable_stem_is_nan_not_zero() {
        // Very dilute salt on a weak stem: if the cost is not positive the force
        // must be null and the grid must say why.
        let h = half_force("AT", Polymer::Rna, 1e-6, Geometry::Hairpin, 298.15).unwrap();
        if !(h.unfold_cost_pn_nm > 0.0) {
            assert!(h.f_half_pn.is_nan());
            assert_eq!(h.grid_used, "none_stem_unstable");
        }
    }

    #[test]
    fn hairpin_stem_requires_a_single_wc_helix() {
        // A 4-bp stem plus a 3-nt loop is 11 nucleotides, so the structure must
        // be 11 characters too: "((((...))))". hairpin.py matches that pattern
        // with re.fullmatch, so anything else is not a single hairpin.
        assert_eq!(hairpin_stem("GGCCTTTGGCC", "((((...))))").as_deref(), Some("GGCC"));
        // Not Watson-Crick: A opposite G at the innermost pair.
        assert_eq!(hairpin_stem("GGCATTTGGCC", "((((...))))"), None);
        // Extra unpaired tail, and a bulge inside the helix.
        assert_eq!(hairpin_stem("GGCCTTTGGCCGG", "((((...)))).."), None);
        assert_eq!(hairpin_stem("GGCCTTGTGGCC", "((((..))))"), None);
        // Leading unpaired nucleotides are not the 5' stem of one hairpin.
        assert_eq!(hairpin_stem("AGGCTTTGGCT", ".(((...)))"), None);
        // Unbalanced brackets, and a one-pair stem, which hairpin.py:36-37 rejects.
        assert_eq!(hairpin_stem("GGCTTTGCC", "(((...))"), None);
        assert_eq!(hairpin_stem("AGCT", "(..)"), None);
    }

    #[test]
    fn bad_input_is_rejected_not_silently_zeroed() {
        assert!(stem_delta_g("GGXCC", Polymer::Dna, 1.0, T_NN_K).is_err());
        assert!(stem_delta_g("G", Polymer::Dna, 1.0, T_NN_K).is_err());
        assert!(stem_delta_g("GCGC", Polymer::Dna, 0.0, T_NN_K).is_err());
        assert!(Polymer::parse("PROTEIN").is_err());
        assert!(Geometry::parse("pseudoknot").is_err());
    }

    #[test]
    fn rna_u_input_is_read_as_t() {
        // The Xia table is written with T for U (thermo.py:6,39). Input spelled
        // with U must reach the same numbers as the same stem spelled with T.
        let with_u = stem_delta_g("GUGC", Polymer::Rna, 1.0, T_NN_K).unwrap();
        let with_t = stem_delta_g("GTGC", Polymer::Rna, 1.0, T_NN_K).unwrap();
        assert_eq!(with_u.sequence, with_t.sequence);
        assert!((with_u.dg_fold_kcal - with_t.dg_fold_kcal).abs() < 1e-12);
        // Lower case and embedded whitespace are tolerated too.
        let loose = stem_delta_g(" g U g C ", Polymer::Rna, 1.0, T_NN_K).unwrap();
        assert_eq!(loose.sequence, "GTGC");
    }

    #[test]
    fn steps_are_reported_per_stack_for_the_audit_trail() {
        let t = stem_delta_g("GCGC", Polymer::Dna, 1.0, T_NN_K).unwrap();
        assert_eq!(t.steps.len(), 3);
        assert_eq!(t.steps[0].key, "GC/CG");
        assert_eq!(t.n_bp, 4);
    }

    #[test]
    fn declared_stem_ranking_is_nucleic_validation_gate_one() {
        // VALIDATION.md gate 1: F1/2 increases across the three declared stems
        // and deltaLc increases with stem length.
        let mut f = Vec::new();
        for stem in ["ATATATATATATATATATAT", "ATGCATGCATGCATGCATGC", "GCGCGCGCGCGCGCGCGCGC"] {
            let h = half_force(stem, Polymer::Dna, 1.0, Geometry::Hairpin, 298.15).unwrap();
            f.push(h.f_half_pn);
        }
        for i in 1..f.len() {
            assert!(f[i] > f[i - 1], "F1/2 not increasing: {f:?}");
        }
        let short = half_force("GCGCGC", Polymer::Dna, 1.0, Geometry::Hairpin, 298.15).unwrap();
        let long = half_force("GCGCGCGCGCGCGCGCGCGC", Polymer::Dna, 1.0, Geometry::Hairpin, 298.15)
            .unwrap();
        assert!(long.delta_lc_nm > short.delta_lc_nm);
        assert!(short.f_half_pn.is_finite() && long.f_half_pn.is_finite());
    }

    #[test]
    fn half_force_lands_inside_the_reported_window() {
        let h = half_force("GCGCGCGCGCGCGCGCGCGC", Polymer::Dna, 1.0, Geometry::Hairpin, 298.15)
            .unwrap();
        assert!(h.f_half_pn > 0.0 && h.f_half_pn <= 80.0, "landed at {}", h.f_half_pn);
        assert!(h.grid_used.starts_with("0.05-80pN/1600"), "{}", h.grid_used);
    }

    #[test]
    fn mean_open_increases_with_force() {
        let s = "GCGCGCGCGC";
        let lo = mean_open(s, 1.0, Polymer::Dna, 1.0, Geometry::Hairpin, 298.15).unwrap();
        let hi = mean_open(s, 40.0, Polymer::Dna, 1.0, Geometry::Hairpin, 298.15).unwrap();
        assert!(hi > lo, "{lo} then {hi}");
        assert!(hi <= 10.0001 && lo >= 0.0);
    }

    #[test]
    fn chemistry_is_temperature_independent_but_elasticity_is_not() {
        // The regression the parity grid cannot catch: every golden case is
        // pulled at 298.15 K, where the measurement temperature and a mistaken
        // chemistry temperature coincide. hairpin.py:49 calls stem_delta_g with
        // no temperature argument, so the stack energies are always the 37 C
        // values and only the WLC sees temperature_k. Evaluating the chemistry
        // at 298.15 K instead inflates this stem's cost by 14% (331.16 vs the
        // correct 290.40 pN nm) and shifts F1/2 by several grid samples, which
        // is exactly how this path first failed parity.
        let stem = "GCGCGCGCGCGCGCGCGCGC";
        let cold = half_force(stem, Polymer::Dna, 1.0, Geometry::Hairpin, 298.15).unwrap();
        let hot = half_force(stem, Polymer::Dna, 1.0, Geometry::Hairpin, 310.15).unwrap();

        // Unfolding free energy is read off the tables at T_NN_K in both runs.
        assert_eq!(cold.unfold_cost_pn_nm, hot.unfold_cost_pn_nm);
        assert_eq!(cold.thermo.dg_fold_kcal, hot.thermo.dg_fold_kcal);
        assert_eq!(cold.thermo.temperature_k, T_NN_K);
        assert_eq!(hot.thermo.temperature_k, T_NN_K);

        // The measurement temperature is still what gets published.
        assert_eq!(cold.measurement_k, 298.15);
        assert_eq!(hot.measurement_k, 310.15);

        // But the elasticity carries it. At these forces the chain is far from
        // saturation, where x/L ~ F*L/(5*kT*lc), so the accumulated work scales
        // as F^2/kT and a fixed cost is reached at F ~ sqrt(cost*kT). A warmer
        // entropic spring is stiffer, so it needs MORE force: cold 22.6 pN, hot
        // 22.8 pN. If this ever fails the two temperatures have been merged.
        assert!(
            hot.f_half_pn > cold.f_half_pn,
            "warmer pull must need more force: cold {} hot {}",
            cold.f_half_pn,
            hot.f_half_pn
        );
    }
}
