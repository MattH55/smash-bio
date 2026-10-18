//! Cα structure-based (Gō) Hamiltonian for proteins, in **reduced units**.
//!
//! Parity target: `smash-sim/src/smashsim/go_model.py`. Every term, every
//! constant and every guard threshold below is a line-by-line port of that file,
//! because brief Phase 2 requires "the same Cα structure-based (Gō) Hamiltonian
//! as SMASH-SIM's reference backend ... with identical parameters", and Phase 7
//! gate 1 requires the two engines to agree rather than merely to look alike.
//!
//! Units (PROTOCOL.md:14): ε = 1, mass = 1 per Cα, distances in Å. Energies are
//! in ε, forces in ε/Å. **These are not piconewtons.** `pull` refuses to label
//! them as such unless the caller supplies a calibration.
//!
//! Sign convention, copied from `go_model.py:3-5`: `energy_and_force` returns
//! the true force F = -∇V, so a minimiser steps along +F and the Langevin kick
//! in `pull` adds `dt * force` to the velocity.

use crate::error::{EngineError, EngineResult};
use crate::json;
use crate::rng::Rng;
use crate::units::*;

pub(crate) const NAT: usize = 3;

/// A Gō model needs a sequence-separated non-bonded pair to be more than a
/// chain; `SEQ_SEP + 2` is the shortest trace with a possible contact.
pub const MIN_CA: usize = SEQ_SEP + 2;

#[inline]
pub(crate) fn sub3(a: [f64; 3], b: [f64; 3]) -> [f64; 3] {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
}
#[inline]
pub(crate) fn dot3(a: [f64; 3], b: [f64; 3]) -> f64 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}
#[inline]
pub(crate) fn norm3(a: [f64; 3]) -> f64 {
    dot3(a, a).sqrt()
}
#[inline]
pub(crate) fn cross3(a: [f64; 3], b: [f64; 3]) -> [f64; 3] {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}
/// Read atom `i` out of a flat xyz buffer.
#[inline]
pub(crate) fn at(x: &[f64], i: usize) -> [f64; 3] {
    [x[i * NAT], x[i * NAT + 1], x[i * NAT + 2]]
}

/// Dihedral of four points, exactly as `go_model.py:18-27`.
///
/// The `arctan2(dot(cross(b1u, v), w), dot(v, w))` form is not the textbook one
/// but it is the reference's, and it is what the parity test compares against;
/// rewriting it as `atan2` of a normalized frame would change the sign
/// convention of every dihedral force.
#[inline]
pub(crate) fn dihedral(p0: [f64; 3], p1: [f64; 3], p2: [f64; 3], p3: [f64; 3]) -> f64 {
    let b0 = sub3(p0, p1);
    let b1 = sub3(p2, p1);
    let b2 = sub3(p3, p2);
    let n = norm3(b1).max(1e-12);
    let b1u = [b1[0] / n, b1[1] / n, b1[2] / n];
    let d0 = dot3(b0, b1u);
    let v = [b0[0] - d0 * b1u[0], b0[1] - d0 * b1u[1], b0[2] - d0 * b1u[2]];
    let d2 = dot3(b2, b1u);
    let w = [b2[0] - d2 * b1u[0], b2[1] - d2 * b1u[1], b2[2] - d2 * b1u[2]];
    let x = dot3(v, w);
    let y = dot3(cross3(b1u, v), w);
    y.atan2(x)
}

/// Wrap an angle difference into (-pi, pi], matching numpy's
/// `arctan2(sin(d), cos(d))`. A dihedral is only defined modulo 2pi, so a raw
/// difference would let a trans peptide pay a full 2pi penalty.
#[inline]
pub(crate) fn wrap(a: f64) -> f64 {
    const TAU: f64 = std::f64::consts::TAU;
    a - TAU * ((a + std::f64::consts::PI) / TAU).floor()
}

/// Three-letter to one-letter code, only for what we display. The Hamiltonian
/// never reads the code; unknown residues become `X` rather than an error,
/// because MSE/SEP etc. still carry valid Cα coordinates.
fn one_letter(name: &str) -> u8 {
    match name.trim().to_ascii_uppercase().as_str() {
        "ALA" => b'A', "ARG" => b'R', "ASN" => b'N', "ASP" => b'D',
        "CYS" => b'C', "GLN" => b'Q', "GLU" => b'E', "GLY" => b'G',
        "HIS" => b'H', "ILE" => b'I', "LEU" => b'L', "LYS" => b'K',
        "MET" => b'M', "PHE" => b'F', "PRO" => b'P', "SER" => b'S',
        "THR" => b'T', "TRP" => b'W', "TYR" => b'Y', "VAL" => b'V',
        "MSE" => b'M', "SEP" => b'S', "TPO" => b'T',
        _ => b'X',
    }
}

/// The native Cα trace plus the residue identity needed to pick pull points.
#[derive(Debug, Clone)]
pub struct Structure {
    /// Free-form label echoed into results, e.g. `"1UBQ:A 1-76"`.
    pub label: String,
    pub chain: char,
    /// PDB residue numbers in trace order; what the user clicks in the viewer.
    pub residues: Vec<i64>,
    /// One-letter codes, `X` when unmapped.
    pub codes: Vec<u8>,
    /// Flat xyz in Å, length 3n.
    pub coords: Vec<f64>,
    /// Provenance notes from parsing (auto chain pick, domain slice, dropped
    /// HETATM). Carried into the result's warnings so the report can state what
    /// the structure the model saw actually was.
    pub notes: Vec<String>,
}

impl Structure {
    #[inline]
    pub fn n(&self) -> usize {
        self.coords.len() / NAT
    }

    pub fn sequence(&self) -> String {
        self.codes.iter().map(|c| *c as char).collect()
    }

    /// PDB residue number -> trace index. Users type the numbering they see in
    /// the 3D view, which is not trace order for a domain sliced out of a chain.
    pub fn index_of_residue(&self, residue: i64) -> EngineResult<usize> {
        self.residues.iter().position(|r| *r == residue).ok_or_else(|| {
            EngineError::bad_value(
                "residue",
                format!(
                    "residue {residue} is not in {label} ({lo}..{hi})",
                    label = self.label,
                    lo = self.residues.first().copied().unwrap_or(0),
                    hi = self.residues.last().copied().unwrap_or(0),
                ),
            )
        })
    }

    /// Reject anything the integrator cannot survive before the run starts.
    fn validate(coords: &[f64], what: &str) -> EngineResult<()> {
        if coords.len() % NAT != 0 {
            return Err(EngineError::bad_value(
                "coords",
                format!("{what}: length {} is not a multiple of 3", coords.len()),
            ));
        }
        let n = coords.len() / NAT;
        if n < MIN_CA {
            return Err(EngineError::unsupported(format!(
                "{what}: {n} Cα is shorter than the {MIN_CA}-residue minimum for a Gō model"
            )));
        }
        if n > MAX_PROTEIN_RESIDUES {
            return Err(EngineError::too_large(format!(
                "{what}: {n} residues exceeds the {MAX_PROTEIN_RESIDUES}-residue browser limit; pick a domain"
            )));
        }
        if coords.iter().any(|v| !v.is_finite()) {
            return Err(EngineError::bad_value("coords", format!("{what}: non-finite coordinate")));
        }
        Ok(())
    }

    /// Build a structure from a flat coordinate buffer.
    pub fn from_coords(label: &str, coords: Vec<f64>) -> EngineResult<Structure> {
        Structure::validate(&coords, label)?;
        let n = coords.len() / NAT;
        Ok(Structure {
            label: label.to_string(),
            chain: 'A',
            residues: (1..=n as i64).collect(),
            codes: vec![b'X'; n],
            coords,
            notes: Vec::new(),
        })
    }
}

/// Column offsets of the fields we need in a PDB ATOM record. The format is
/// columnar by specification, so these are sliced, not whitespace-split: a
/// coordinate can abut its neighbour with no space when the width is full.
///   name 12..16   chain 21   resname 17..20   resi 22..26   x 30..38 y 38..46 z 46..54
///
/// Atom names are right-justified when they are one or two characters (" CA "),
/// so both ends are stripped rather than only the trailing blanks.
fn col(field: &[u8]) -> &[u8] {
    let mut a = 0usize;
    let mut b = field.len();
    while a < b && matches!(field[a], b' ' | b'\t') {
        a += 1;
    }
    while b > a && matches!(field[b - 1], b' ' | b'\t') {
        b -= 1;
    }
    &field[a..b]
}

fn pdb_ca(line: &[u8]) -> Option<(char, i64, u8, [f64; 3])> {
    if line.len() < 54 || &line[0..4] != b"ATOM" {
        return None;
    }
    if col(&line[12..16]) != b"CA" {
        return None;
    }
    let chain = line[21] as char;
    let resi = std::str::from_utf8(col(&line[22..26])).ok()?.parse::<i64>().ok()?;
    let name = std::str::from_utf8(col(&line[17..20])).ok()?;
    let f = |a: usize, b: usize| std::str::from_utf8(col(&line[a..b])).ok()?.parse::<f64>().ok();
    let (Some(px), Some(py), Some(pz)) = (f(30, 38), f(38, 46), f(46, 54)) else {
        return None;
    };
    if !(px.is_finite() && py.is_finite() && pz.is_finite()) {
        return None;
    }
    Some((chain, resi, one_letter(name), [px, py, pz]))
}

/// The PDB entry id from the HEADER record, when the file carries one.
///
/// The id is at **columns 63-66** (1-based), i.e. bytes `62..66`, per the PDB
/// format specification - not at the end of the record, which a plausible-looking
/// `66..72` slice reads and which comes back blank on every real deposition file
/// (1UBQ's HEADER is 80 columns and its 67th-72nd are the padding after `1UBQ`).
/// A `1XYZ`-style id is always four characters, so the slice is widened slightly
/// and trimmed rather than trusted to land exactly.
fn pdb_id(text: &str) -> Option<String> {
    for line in text.lines() {
        if line.starts_with("HEADER") {
            if let Some(rest) = line.get(62..) {
                let id: String = rest.chars().take(6).collect::<String>().trim().to_string();
                if !id.is_empty() {
                    return Some(id.to_ascii_uppercase());
                }
            }
        }
        // HEADER is the first record of an entry; anything else ends the search.
        if !line.starts_with("HEADER") && !line.starts_with("OBSLT")
            && !line.starts_with("TITLE") && !line.starts_with("COMPND")
            && !line.starts_with("SOURCE") && !line.starts_with("REMARK")
        {
            break;
        }
    }
    None
}

/// Read a Cα trace out of PDB-format text.
///
/// * `chain` - `None` picks the chain with the most Cα atoms. Multi-chain
///   biological assemblies must not be concatenated: pulling "chain A+B" of a
///   dimer is not pulling either monomer, so the largest single chain is the
///   only defensible automatic default, and the chosen chain is reported.
/// * `range` - inclusive PDB residue-number window. This is how the brief's
///   domain picker ("proteins up to 400 residues, offer a domain picker for
///   larger ones") reaches the engine: the page slices, the engine enforces.
///
/// HETATM records are ignored - metals, waters and disulfide atoms have no place
/// in a Cα model, the same treatment PROTOCOL.md:8 gives SOD1 ("disulfides and
/// metals removed"). The consequence, that a staple the crystal actually holds
/// together is modelled as absent, is reported as a warning rather than hidden.
pub fn parse_pdb(
    text: &str,
    chain: Option<char>,
    range: Option<(i64, i64)>,
) -> EngineResult<Structure> {
    let mut rows: Vec<(char, i64, u8, [f64; 3])> = Vec::new();
    let mut het_cys_sg = 0usize;
    let mut het_other = 0usize;
    for line in text.lines() {
        let b = line.as_bytes();
        if b.len() >= 6 && &b[0..6] == b"HETATM" {
            // SG is the disulfide sulfur. Everything else an SOD1-style prep
            // strips (Zn, CU, HOH, ...) is counted together.
            if b.len() >= 54 && col(&b[12..16]) == b"SG" && col(&b[17..20]) == b"CYS" {
                het_cys_sg += 1;
            } else {
                het_other += 1;
            }
            continue;
        }
        let Some(row) = pdb_ca(line.as_bytes()) else { continue };
        // First occurrence of a residue wins: an altloc gives two rows with the
        // same chain and residue number, and both cannot be modelled.
        if rows.iter().any(|r| r.0 == row.0 && r.1 == row.1) {
            continue;
        }
        rows.push(row);
    }
    if rows.is_empty() {
        return Err(EngineError::bad_value(
            "pdb",
            "no ATOM records with a CA atom; a Cα Gō model needs coordinates",
        ));
    }
    let mut notes: Vec<String> = Vec::new();
    if het_cys_sg > 0 {
        notes.push(format!(
            "{het_cys_sg} disulfide sulfur(s) (SG) ignored: a Cα model has no bond to represent, \
             so a staple the crystal holds together is free in the model"
        ));
    }
    if het_other > 0 {
        notes.push(format!("{het_other} HETATM record(s) (metal, ligand or water) ignored"));
    }
    let pick = match chain {
        Some(c) => c,
        None => {
            let mut counts: Vec<(char, usize)> = Vec::new();
            for r in &rows {
                match counts.iter_mut().find(|(c, _)| *c == r.0) {
                    Some(e) => e.1 += 1,
                    None => counts.push((r.0, 1)),
                }
            }
            counts.sort_by_key(|(c, n)| (std::cmp::Reverse(*n), *c));
            if counts.len() > 1 {
                notes.push(format!(
                    "{} chains present; modelled the largest, '{}', alone - concatenating chains \
                     would pull an object that is not any single subunit",
                    counts.len(),
                    counts[0].0
                ));
            }
            counts[0].0
        }
    };
    let mut st = Structure {
        label: String::new(),
        chain: pick,
        residues: Vec::new(),
        codes: Vec::new(),
        coords: Vec::new(),
        notes,
    };
    let mut skipped = 0usize;
    for r in rows.iter().filter(|r| r.0 == pick) {
        if let Some((lo, hi)) = range {
            if r.1 < lo || r.1 > hi {
                skipped += 1;
                continue;
            }
        }
        st.residues.push(r.1);
        st.codes.push(r.2);
        st.coords.extend_from_slice(&r.3);
    }
    if skipped > 0 {
        let (lo, hi) = range.unwrap_or((0, 0));
        st.notes.push(format!(
            "domain slice {lo}..{hi}: {skipped} residue(s) of chain {pick} outside the window \
             were dropped, so the ends of the slice are termini with no native context"
        ));
    }
    if st.coords.is_empty() {
        return Err(EngineError::bad_value(
            "chain",
            format!(
                "chain {pick}{} has no Cα in this selection",
                match range {
                    Some((lo, hi)) => format!(" in residues {lo}..{hi}"),
                    None => String::new(),
                }
            ),
        ));
    }
    // A gap in the numbering means missing residues in the deposited chain. The
    // model will still bond across it, giving one artificially long "bond" that
    // the harmonic term then pulls on; the user must be told, not protected.
    let mut gaps = 0usize;
    for w in st.residues.windows(2) {
        if w[1] - w[0] != 1 {
            gaps += 1;
        }
    }
    if gaps > 0 {
        st.notes.push(format!(
            "{gaps} chain break(s) in the numbering: unmodelled residues are bonded across, so \
             the contour length of this trace is shorter than the real sequence's"
        ));
    }
    Structure::validate(&st.coords, "pdb trace")?;
    let (lo, hi) = (st.residues[0], st.residues[st.residues.len() - 1]);
    st.label = format!("{}:{pick} {lo}-{hi}", pdb_id(text).unwrap_or_else(|| "upload".into()));
    Ok(st)
}

/// The bond, angle, dihedral and contact geometry the Hamiltonian reads.
///
/// Built once from the native structure and reused at every step - this is the
/// brief's "precomputed contact list": an O(n²) scan per step would not fit in a
/// browser tab. Flat `Vec`s rather than fixed arrays so one model can be shared
/// by every replica in a Web Worker pool.
#[derive(Debug, Clone)]
pub struct GoModel {
    pub n: usize,
    /// Flat native coordinates in Å (`native` in the reference dict).
    pub native: Vec<f64>,
    pub bond0: Vec<f64>,
    pub angle0: Vec<f64>,
    pub dihedral0: Vec<f64>,
    /// Native-contact partner indices, always `ci[k] < cj[k]`.
    pub ci: Vec<usize>,
    pub cj: Vec<usize>,
    /// Native contact distance in Å.
    pub contact0: Vec<f64>,
    /// `true` selects the 10-12 Habibi variant, `false` the corpus 6-12 form.
    pub lj_10_12: bool,
    /// Packed (i << 32 | j) native pairs, sorted. This is the reference's
    /// `native = set(zip(ci, cj))` (go_model.py:125); a sorted Vec keeps the
    /// membership test O(log n) without pulling in a hash map whose iteration
    /// order could leak into the non-native sum.
    pub native_pairs: Vec<u64>,
    /// Sequence separations spanned by the contact map, for the report.
    pub min_seq_sep: usize,
    pub max_seq_sep: usize,
}

impl GoModel {
    pub fn n_contacts(&self) -> usize {
        self.ci.len()
    }

    /// Is (i, j) a native contact? `i` and `j` are the unordered pair as the
    /// non-native scan generates it, i.e. always i < j there too.
    #[inline]
    pub fn is_native(&self, i: usize, j: usize) -> bool {
        let key = ((i as u64) << 32) | (j as u64);
        self.native_pairs.binary_search(&key).is_ok()
    }
}

/// Native geometry and the contact list, from a Cα trace (`go_model.py:30-60`).
///
/// The contact rule is **ASSUMED** (PROTOCOL.md:26): |i-j| >= SEQ_SEP and a
/// native Cα-Cα distance below CONTACT_CUTOFF. SMOG's real shadow map needs all
/// heavy atoms and an occlusion test this engine does not ship, so this map is
/// denser than SMOG's on tightly packed β-sandwiches like I27 - one reason every
/// protein force produced here is labelled unvalidated.
pub fn build_model(coords: &[f64], lj_10_12: bool) -> EngineResult<GoModel> {
    Structure::validate(coords, "coords")?;
    let n = coords.len() / NAT;
    let mut m = GoModel {
        n,
        native: coords.to_vec(),
        bond0: Vec::with_capacity(n - 1),
        angle0: Vec::with_capacity(n - 2),
        dihedral0: Vec::with_capacity(n - 3),
        ci: Vec::new(),
        cj: Vec::new(),
        contact0: Vec::new(),
        lj_10_12,
        native_pairs: Vec::new(),
        min_seq_sep: n,
        max_seq_sep: 0,
    };
    for i in 0..n - 1 {
        m.bond0.push(norm3(sub3(at(coords, i + 1), at(coords, i))));
    }
    for i in 0..n - 2 {
        let v1 = sub3(at(coords, i), at(coords, i + 1));
        let v2 = sub3(at(coords, i + 2), at(coords, i + 1));
        let d = dot3(v1, v2) / (norm3(v1) * norm3(v2)).max(1e-12);
        m.angle0.push(d.clamp(-1.0, 1.0).acos());
    }
    for i in 0..n - 3 {
        let phi = dihedral(at(coords, i), at(coords, i + 1), at(coords, i + 2), at(coords, i + 3));
        m.dihedral0.push(phi);
    }
    for i in 0..n {
        for j in (i + SEQ_SEP)..n {
            let r = norm3(sub3(at(coords, j), at(coords, i)));
            if r < CONTACT_CUTOFF {
                m.ci.push(i);
                m.cj.push(j);
                m.contact0.push(r);
                let sep = j - i;
                if sep < m.min_seq_sep {
                    m.min_seq_sep = sep;
                }
                if sep > m.max_seq_sep {
                    m.max_seq_sep = sep;
                }
            }
        }
    }
    if m.ci.is_empty() {
        m.min_seq_sep = 0;
    }
    m.native_pairs = m
        .ci
        .iter()
        .zip(m.cj.iter())
        .map(|(i, j)| ((*i as u64) << 32) | (*j as u64))
        .collect();
    m.native_pairs.sort_unstable();
    Ok(m)
}

/// Potential energy and force of the Cα Gō model, `go_model.py:63-158`.
///
/// Returns `(energy in ε, force in ε/Å)` with F = -∇V. `x` is the flat xyz
/// buffer; it is taken mutably because the dihedral gradient is computed by a
/// central difference that perturbs the four atoms in place, exactly as the
/// reference does, and perturbing in the same order reproduces the reference's
/// rounding bit for bit. The buffer is restored to its input values except for
/// sub-ulp drift from the (+eps, -eps) pairs - drift the reference also has, so
/// it is deliberately not "cleaned up".
///
/// The terms, in the order the reference evaluates them:
/// 1. bonds      `BOND_K (r-r0)^2`, curvature 2*BOND_K
/// 2. angles     `ANGLE_K (θ-θ0)^2`
/// 3. dihedrals  `ε(1-cos Δφ) + 0.5ε(1-cos 3Δφ)`, ASSUMED ε_bb = ε for all
/// 4. native     `(r0/r)^12 - 2(r0/r)^6` minimum at r0 with depth ε, or the
///               10-12 Habibi variant `5 inv^12 - 6 inv^10`
/// 5. non-native `(σ/r)^12` excluded volume, cut off beyond NONNATIVE_CUTOFF
pub fn energy_and_force(x: &mut [f64], m: &GoModel) -> (f64, Vec<f64>) {
    let n = m.n;
    let mut force = vec![0.0f64; n * NAT];
    let mut energy = 0.0f64;

    // ---- bonds (go_model.py:69-77) ----
    // dist is floored at 1e-8 so a collapsed pair cannot divide by zero; the
    // same floor is kept here because dropping it changes the result for
    // structures the integrator reaches transiently.
    for i in 0..n - 1 {
        let d = sub3(at(x, i + 1), at(x, i));
        let dist = norm3(d).max(1e-8);
        let dr = dist - m.bond0[i];
        energy += BOND_K * dr * dr;
        let s = 2.0 * BOND_K * dr / dist;
        let g = [s * d[0], s * d[1], s * d[2]];
        // F_i = -dV/dx_i = +g, F_{i+1} = -g  (go_model.py:76-77)
        for c in 0..NAT {
            force[i * NAT + c] += g[c];
            force[(i + 1) * NAT + c] -= g[c];
        }
    }

    // ---- angles (go_model.py:79-99) ----
    for i in 0..n - 2 {
        let r1 = sub3(at(x, i), at(x, i + 1));
        let r2 = sub3(at(x, i + 2), at(x, i + 1));
        let n1 = norm3(r1);
        let n2 = norm3(r2);
        if n1 < 1e-8 || n2 < 1e-8 {
            continue;
        }
        let u1 = [r1[0] / n1, r1[1] / n1, r1[2] / n1];
        let u2 = [r2[0] / n2, r2[1] / n2, r2[2] / n2];
        let cos = dot3(u1, u2).clamp(-0.999999, 0.999999);
        let theta = cos.acos();
        let dtheta = theta - m.angle0[i];
        energy += ANGLE_K * dtheta * dtheta;
        let dvdtheta = 2.0 * ANGLE_K * dtheta;
        let sin = theta.sin().max(1e-8);
        // theta = arccos(u1.u2) with r1 = x[i]-x[i+1], r2 = x[i+2]-x[i+1].
        let a1 = [
            -(u2[0] - cos * u1[0]) / (sin * n1),
            -(u2[1] - cos * u1[1]) / (sin * n1),
            -(u2[2] - cos * u1[2]) / (sin * n1),
        ];
        let a2 = [
            -(u1[0] - cos * u2[0]) / (sin * n2),
            -(u1[1] - cos * u2[1]) / (sin * n2),
            -(u1[2] - cos * u2[2]) / (sin * n2),
        ];
        for c in 0..NAT {
            force[i * NAT + c] -= dvdtheta * a1[c];
            force[(i + 2) * NAT + c] -= dvdtheta * a2[c];
            force[(i + 1) * NAT + c] += dvdtheta * (a1[c] + a2[c]);
        }
    }

    // ---- dihedrals, central difference (go_model.py:104-122) ----
    let eps = 1e-5;
    for i in 0..n - 3 {
        let phi0 = m.dihedral0[i];
        let e0 = dih_energy(dihedral(at(x, i), at(x, i + 1), at(x, i + 2), at(x, i + 3)), phi0);
        energy += e0;
        for a in [i, i + 1, i + 2, i + 3] {
            for c in 0..NAT {
                let k = a * NAT + c;
                x[k] += eps;
                let pp = dih_energy(
                    dihedral(at(x, i), at(x, i + 1), at(x, i + 2), at(x, i + 3)),
                    phi0,
                );
                x[k] -= eps;
                x[k] -= eps;
                let pm = dih_energy(
                    dihedral(at(x, i), at(x, i + 1), at(x, i + 2), at(x, i + 3)),
                    phi0,
                );
                x[k] += eps;
                force[k] -= (pp - pm) / (2.0 * eps);
            }
        }
    }

    // ---- native contacts (go_model.py:124-142) ----
    for k in 0..m.ci.len() {
        let (i, j) = (m.ci[k], m.cj[k]);
        let dvec = sub3(at(x, j), at(x, i));
        let r = norm3(dvec);
        if r < 1e-8 {
            continue;
        }
        let inv = m.contact0[k] / r;
        let (e, dvr) = if m.lj_10_12 {
            (
                5.0 * inv.powi(12) - 6.0 * inv.powi(10),
                (-60.0 * inv.powi(12) + 60.0 * inv.powi(10)) / r,
            )
        } else {
            (
                inv.powi(12) - 2.0 * inv.powi(6),
                (-12.0 * inv.powi(12) + 12.0 * inv.powi(6)) / r,
            )
        };
        energy += e;
        let g = [dvr * dvec[0] / r, dvr * dvec[1] / r, dvr * dvec[2] / r];
        for c in 0..NAT {
            force[j * NAT + c] -= g[c];
            force[i * NAT + c] += g[c];
        }
    }
    non_native(x, m, &mut force, &mut energy);
    (energy, force)
}

/// V(Δφ) = ε(1 - cos Δφ) + 0.5ε(1 - cos 3Δφ), with Δφ wrapped. go_model.py:108.
#[inline]
pub(crate) fn dih_energy(phi: f64, phi0: f64) -> f64 {
    let d = wrap(phi - phi0);
    1.0 - d.cos() + 0.5 * (1.0 - (3.0 * d).cos())
}
/// Non-native excluded volume, `go_model.py:143-157`.
///
/// V = (sigma/r)^12 with no attractive tail, evaluated only for pairs the native
/// map does not already describe, and skipped beyond NONNATIVE_CUTOFF. The pair
/// scan runs i ascending, j ascending, exactly like the reference's nested
/// `range` loops, because the floating-point sum of `energy` is order-dependent
/// and parity means bit-comparable accumulation, not just the same formula.
fn non_native(x: &[f64], m: &GoModel, force: &mut [f64], energy: &mut f64) {
    let sig = NONNATIVE_SIGMA;
    for i in 0..m.n {
        for j in (i + SEQ_SEP)..m.n {
            if m.is_native(i, j) {
                continue;
            }
            let dvec = sub3(at(x, j), at(x, i));
            let r = norm3(dvec);
            if r < 1e-6 || r > NONNATIVE_CUTOFF {
                continue;
            }
            let inv = sig / r;
            let i12 = inv.powi(12);
            *energy += i12;
            let dvr = -12.0 * i12 / r;
            let g = [dvr * dvec[0] / r, dvr * dvec[1] / r, dvr * dvec[2] / r];
            force[j * NAT + 0] -= g[0];
            force[j * NAT + 1] -= g[1];
            force[j * NAT + 2] -= g[2];
            force[i * NAT + 0] += g[0];
            force[i * NAT + 1] += g[1];
            force[i * NAT + 2] += g[2];
        }
    }
}

/// Fraction of native contacts still under 1.2 x their native distance
/// (`pull.py:75-82`). NaN when the model has no contacts at all - an extended
/// chain has no Gō map, and "0% intact" would claim a measurement we cannot make.
pub fn contacts_remaining(x: &[f64], m: &GoModel) -> f64 {
    if m.ci.is_empty() {
        return f64::NAN;
    }
    let mut kept = 0usize;
    for k in 0..m.ci.len() {
        let (i, j) = (m.ci[k], m.cj[k]);
        if norm3(sub3(at(x, j), at(x, i))) < CONTACT_INTACT_FACTOR * m.contact0[k] {
            kept += 1;
        }
    }
    kept as f64 / m.ci.len() as f64
}

/// The smoothed force trace, `pull.py:65-66`.
///
/// `np.convolve(force, ones(5)/5, mode="same")` is a *zero-padded* moving average:
/// at the ends the window runs off the trace and the missing samples contribute
/// nothing, but the divisor stays 5.0. Dividing by the number of samples actually
/// present would be the "nice" thing to do and would disagree with the reference
/// at the first and last two points, which is precisely where unfolding events
/// land, so the naive form is kept.
pub fn smooth5(force: &[f64]) -> Vec<f64> {
    let n = force.len();
    let mut out = vec![0.0f64; n];
    for i in 0..n {
        let mut acc = 0.0f64;
        for k in (i as i64 - 2)..=(i as i64 + 2) {
            if k >= 0 && (k as usize) < n {
                acc += force[k as usize];
            }
        }
        out[i] = acc / 5.0;
    }
    out
}

fn median(v: &[f64]) -> f64 {
    let mut s = v.to_vec();
    s.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let n = s.len();
    if n == 0 {
        return f64::NAN;
    }
    if n % 2 == 1 {
        s[n / 2]
    } else {
        0.5 * (s[n / 2 - 1] + s[n / 2])
    }
}

/// Population standard deviation, the `np.std` default (ddof = 0), computed in
/// the same two-pass form numpy uses.
fn std_pop(v: &[f64]) -> f64 {
    let n = v.len();
    if n == 0 {
        return f64::NAN;
    }
    let mean = v.iter().sum::<f64>() / n as f64;
    let ss = v.iter().map(|a| (a - mean) * (a - mean)).sum::<f64>() / n as f64;
    ss.sqrt()
}

/// Peak indices of the force trace, `pull.py:62-72`: local maxima of the
/// smoothed trace that beat median + 0.5 x std of that trace. A trace shorter
/// than the 5-point window has no peaks, matching the reference's early return.
pub fn peaks(force: &[f64]) -> Vec<usize> {
    if force.len() < 5 {
        return Vec::new();
    }
    let smooth = smooth5(force);
    let level = median(&smooth) + 0.5 * std_pop(&smooth);
    let mut hits = Vec::new();
    for i in 1..smooth.len() - 1 {
        if smooth[i] >= smooth[i - 1] && smooth[i] > smooth[i + 1] && smooth[i] > level {
            hits.push(i);
        }
    }
    hits
}

/// The peak force reported by the reference: the largest *raw* trace value at a
/// peak index, falling back to the global maximum when no peak passes the level
/// (`pull.py:50`). Note it is the raw trace, not the smoothed one.
pub fn peak_force(force: &[f64]) -> f64 {
    let hits = peaks(force);
    if hits.is_empty() {
        return force.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    }
    hits.iter().map(|&i| force[i]).fold(f64::NEG_INFINITY, f64::max)
}

/// First index attaining the maximum, the `numpy.argmax` convention: strict `>`
/// while scanning left to right, so ties keep the earliest index. `finish` needs
/// this because the reference's peak force and its step must refer to the same
/// sample; two passes that disagree on which of several equal maxima wins would
/// report a force and a position from different steps.
fn argmax_first(force: &[f64]) -> usize {
    let mut best = f64::NEG_INFINITY;
    let mut at = 0usize;
    for (i, a) in force.iter().enumerate() {
        if *a > best {
            best = *a;
            at = i;
        }
    }
    at
}

/// `(peak_force, n_peaks, peak_step)` for a force trace, in one place so the
/// reported force and the reported step cannot come from different passes over
/// the trace. `pull.py:46-50` returns the first two; the step is what a viewer
/// needs to put a marker on the curve, and the reference's own statistic (max
/// raw value at a peak index) determines which index that marker is.
pub fn peak_summary(force: &[f64]) -> (f64, usize, usize) {
    let hits = peaks(force);
    if hits.is_empty() {
        let best = force.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        return (best, 0, argmax_first(force));
    }
    let mut best = f64::NEG_INFINITY;
    let mut at = hits[0];
    for &i in &hits {
        if force[i] > best {
            best = force[i];
            at = i;
        }
    }
    (best, hits.len(), at)
}
/// An explicit epsilon/mass calibration, the thing PROTOCOL.md:39 says does not
/// exist yet: "the speed grid is a configuration value, not 1 m/s, until epsilon
/// and the time unit are calibrated".
///
/// Reduced units fix the *ratios*, not the scale. With energy unit ε, length
/// unit 1 Å and bead mass m0, the derived units are
///
///   force  ε/Å        ->  epsilon_J * 1e22  pN
///   time   Å sqrt(m/ε) ->  1e-10 * sqrt(m0_kg / epsilon_J)  s
///   speed  Å/tau      ->  sqrt(epsilon_J / m0_kg)           m/s
///
/// Supplying this is a *claim about the model*, so it is opt-in: with no
/// calibration the result carries reduced numbers only and the JSON says so.
#[derive(Debug, Clone, Copy)]
pub struct Calibration {
    /// Well depth ε, in kJ/mol.
    pub epsilon_kj_per_mol: f64,
    /// Mass of one Cα bead, in atomic mass units. A residue is ~110 Da.
    pub bead_mass_amu: f64,
}

const AVOGADRO: f64 = 6.02214076e23;
const AMU_KG: f64 = 1.66053906660e-27;

impl Calibration {
    /// ε expressed in joules per molecule.
    #[inline]
    fn epsilon_j(&self) -> f64 {
        self.epsilon_kj_per_mol * 1000.0 / AVOGADRO
    }
    /// Multiply a reduced force (ε/Å) by this for pN.
    #[inline]
    pub fn pn_per_reduced_force(&self) -> f64 {
        // 1 Å = 1e-10 m, and 1 N = 1e12 pN.
        self.epsilon_j() / 1e-10 * 1e12
    }
    /// Multiply a reduced time by this for picoseconds.
    #[inline]
    pub fn ps_per_reduced_time(&self) -> f64 {
        let m0 = self.bead_mass_amu * AMU_KG;
        1e-10 * (m0 / self.epsilon_j()).sqrt() * 1e12
    }
    /// Multiply a reduced speed (Å per reduced time) by this for m/s.
    #[inline]
    pub fn m_s_per_reduced_speed(&self) -> f64 {
        let m0 = self.bead_mass_amu * AMU_KG;
        (self.epsilon_j() / m0).sqrt()
    }
}

/// The pulling run's parameters; every default is the reference's own default
/// (`pull.py:11-13`, PROTOCOL.md:34-41), so an omitted field is a field the
/// reference also leaves at its default.
#[derive(Debug, Clone)]
pub struct PullConfig {
    /// Anchor speed, Å per reduced time. `pull.py:12` default 0.2.
    pub speed: f64,
    /// Pulling-spring stiffness, ε/Å². `pull.py:12` default 0.1.
    pub spring_k: f64,
    /// Trajectory length in steps. `pull.py:12` default 800.
    pub n_steps: usize,
    /// Time step, reduced. `pull.py:12` default 0.002.
    pub dt: f64,
    /// Thermal energy kT, reduced (ε). `pull.py:12` default 0.5.
    pub temperature: f64,
    /// Langevin friction γ, reduced. `pull.py:13` default 1.0.
    pub friction: f64,
    /// PRNG seed. `pull.py:13` default 1.
    pub seed: u64,
    /// Contact shape: 10-12 (Habibi variant) instead of the corpus 6-12 form.
    pub lj_10_12: bool,
    /// Trace index held by the stiff anchor. `None` = the first residue, which
    /// is what the reference does (`x[0]`, pull.py:21,32).
    pub anchor: Option<usize>,
    /// Trace index the pulling spring acts on. `None` = the last residue
    /// (`x[-1]`, pull.py:24,33).
    pub pull: Option<usize>,
    /// Reference end-to-end distance, Å, subtracted from the raw distance to give
    /// `extension_nm`. The reference never subtracts anything - its "extension"
    /// is the end-to-end distance itself (`pull.py:44`) - so a fixture leaves
    /// this `None` and compares `extension_a` directly. Physically a folded
    /// domain does start at zero extension, so a real run sets it.
    pub extension0_a: Option<f64>,
    /// Absent until someone measures ε. See `Calibration`.
    pub calibration: Option<Calibration>,
}

impl Default for PullConfig {
    fn default() -> PullConfig {
        PullConfig {
            speed: SPEED_DEFAULT,
            spring_k: SPRING_K_DEFAULT,
            n_steps: N_STEPS_DEFAULT,
            dt: DT,
            temperature: KBT_REDUCED,
            friction: FRICTION,
            seed: 1,
            lj_10_12: false,
            anchor: None,
            pull: None,
            extension0_a: None,
            calibration: None,
        }
    }
}

impl PullConfig {
    /// Reject nonsense before 800 steps of dynamics waste a worker's time slice.
    /// The reference checks nothing; a browser must.
    pub fn validate(&self) -> EngineResult<()> {
        if self.n_steps == 0 || self.n_steps > 2_000_000 {
            return Err(EngineError::bad_value(
                "n_steps",
                format!("{} must be 1..2000000", self.n_steps),
            ));
        }
        for (name, v) in [
            ("speed", self.speed),
            ("spring_k", self.spring_k),
            ("dt", self.dt),
            ("temperature", self.temperature),
            ("friction", self.friction),
        ] {
            if !v.is_finite() || v < 0.0 {
                return Err(EngineError::bad_value(name, format!("{v} must be finite and >= 0")));
            }
        }
        if self.dt == 0.0 {
            return Err(EngineError::bad_value("dt", "a zero time step simulates nothing"));
        }
        Ok(())
    }

    /// Noise amplitude, `pull.py:28`. Written as the reference writes it.
    #[inline]
    fn noise_scale(&self) -> f64 {
        (2.0 * self.friction * self.temperature * self.dt).sqrt()
    }
}

/// One trajectory's worth of output. Field names follow `pull.py:47-59`, which
/// is the shape the Python reference returns and what the fixtures record.
#[derive(Debug, Clone)]
pub struct PullResult {
    /// What was pulled, e.g. `1TIT:A 1-89`.
    pub label: String,
    pub n_residues: usize,
    pub n_contacts: usize,
    /// End-to-end distance per step, Å.
    pub extension_a: Vec<f64>,
    /// Spring force along the pull direction per step, ε/Å.
    pub force_reduced: Vec<f64>,
    /// Largest sampled pulling force, ε/Å.
    pub peak_force_reduced: f64,
    pub n_force_peaks: usize,
    /// Index of the peak carrying `peak_force_reduced`.
    pub peak_step: usize,
    /// Fraction of native contacts still within 1.2 x their native distance.
    pub native_contacts_remaining: f64,
    /// Final coordinates, flat xyz Å.
    pub final_coords: Vec<f64>,
    pub energy_final: f64,
    /// End-to-end distance of the *native* structure, Å: extension zero.
    pub extension0_a: f64,
    pub config: PullConfig,
    /// Provenance and caveat notes, reduced units first.
    pub warnings: Vec<String>,
}
/// One Langevin thermal draw per coordinate per step.
///
/// `simulate_with_noise` takes this as an argument because the engine's own PRNG
/// (sfc64, `rng`) cannot reproduce NumPy's MT19937, and a parity test that lets
/// the two streams differ tests nothing but the integrator. Injecting the
/// reference's own `rng.normal(size = x.shape)` values makes a full noisy
/// trajectory bit-comparable: whatever remains at the end is pure floating-point
/// ordering, which is the thing the parity gate is meant to bound.
///
/// Production runs never use it: `simulate` draws from `Rng`, and the hook is
/// `pub(crate)` so it is not part of the browser-facing API.
pub(crate) trait NoiseSource {
    /// The next standard-normal draw. The caller multiplies by `noise_scale`,
    /// exactly as `pull.py:37` broadcasts `noise_scale * rng.normal(...)`.
    fn next_standard(&mut self) -> f64;
}

/// The production source: sfc64 Box-Muller, `rng::Rng::next_gaussian`.
struct EngineNoise(Rng);

impl NoiseSource for EngineNoise {
    #[inline]
    fn next_standard(&mut self) -> f64 {
        self.0.next_gaussian()
    }
}

/// Constant-velocity Langevin pull, `pull.py:11-59`.
///
/// The loop is transcribed rather than "improved", in the reference's own order:
/// half kick at the old position, full drift, friction plus noise, then the half
/// kick at the new position with the anchor already advanced. Three properties
/// are easy to break and are pinned by the parity fixture:
///
/// * the anchor advances *before* the second spring evaluation, so the sampled
///   force is the force of the spring stretched to where the handle now is;
/// * the reported force is `dot(-spring, direction)` - the model-side reaction
///   projected on the pull axis - not `dot(force_on_atom, direction)`, which
///   would differ only in sign but the reference's sign is the one a peak is read
///   against;
/// * the noise is drawn in atom-major, component-minor order (`rng.normal(size =
///   x.shape)`), so a different draw order desynchronises the whole trajectory.
///
/// `cfg.anchor` / `cfg.pull` default to the termini, which is all the reference
/// can do; any other pair is a different pull geometry the corpus numbers do not
/// describe, and the run says so in `warnings`.
pub fn simulate(coords: &[f64], m: &GoModel, cfg: &PullConfig) -> EngineResult<PullResult> {
    simulate_with_noise(coords, m, cfg, &mut EngineNoise(Rng::new(cfg.seed)))
}

/// A noise array consumed in atom-major, component-minor order.
struct ArrayNoise<'a>(&'a [f64], usize);

impl NoiseSource for ArrayNoise<'_> {
    #[inline]
    fn next_standard(&mut self) -> f64 {
        let v = self.0[self.1];
        self.1 += 1;
        v
    }
}

/// The pull with the thermal draws supplied by the caller, for the parity test.
///
/// `pull.py` draws from NumPy's PCG64/MT19937, which no zero-dependency Rust port
/// reproduces, so an end-to-end noisy run between the two engines would compare
/// two different random walks and prove nothing about the integrator. Feeding the
/// reference's own `rng.normal(size = x.shape)` stream in makes every arithmetic
/// step shared: any remaining difference is floating-point ordering and nothing
/// else, which is exactly what the parity gate is supposed to measure.
///
/// `noise` must hold `cfg.n_steps * 3 * m.n` values in the reference's C order.
/// A short array is an error rather than a silent zero-fill, because padding the
/// tail with zeros would quietly change the trajectory.
pub fn simulate_with_injected_noise(
    coords: &[f64],
    m: &GoModel,
    cfg: &PullConfig,
    noise: &[f64],
) -> EngineResult<PullResult> {
    let want = cfg.n_steps * m.n * NAT;
    if noise.len() < want {
        return Err(EngineError::bad_value(
            "noise",
            format!("injected noise has {} draws, the run needs {want}", noise.len()),
        ));
    }
    simulate_with_noise(coords, m, cfg, &mut ArrayNoise(noise, 0))
}

fn simulate_with_noise(
    coords: &[f64],
    m: &GoModel,
    cfg: &PullConfig,
    rng: &mut dyn NoiseSource,
) -> EngineResult<PullResult> {
    cfg.validate()?;
    Structure::validate(coords, "coords")?;
    let n = m.n;
    if cfg.n_steps < 5 {
        return Err(EngineError::bad_value(
            "n_steps",
            "a trace shorter than the 5-point smoothing window cannot report peaks",
        ));
    }
    let anchor = cfg.anchor.unwrap_or(0);
    let pull = cfg.pull.unwrap_or(n - 1);
    if anchor >= n || pull >= n {
        return Err(EngineError::bad_value(
            "anchor/pull",
            format!("indices {anchor}/{pull} outside 0..{}", n - 1),
        ));
    }
    if anchor == pull {
        return Err(EngineError::bad_value(
            "anchor/pull",
            "the restraint and the pull point cannot be the same residue",
        ));
    }

    let mut x = coords.to_vec();
    let mut v = vec![0.0f64; n * NAT];
    let origin = at(coords, anchor);
    let dvec = sub3(at(coords, pull), at(coords, anchor));
    let dn = norm3(dvec);
    if dn < 1e-8 {
        return Err(EngineError::unsupported(format!(
            "pull points {} and {} are {dn:.3} A apart: there is no end-to-end vector to pull along",
            if anchor == 0 { "the N-terminus" } else { "the anchor" },
            if pull == n - 1 { "the C-terminus" } else { "the pull point" }
        )));
    }
    let direction = [dvec[0] / dn, dvec[1] / dn, dvec[2] / dn];
    let mut anchor_pos = at(coords, pull);
    let ka = anchor * NAT;
    let kp = pull * NAT;

    let mut extension = vec![0.0f64; cfg.n_steps];
    let mut force_trace = vec![0.0f64; cfg.n_steps];
    let noise_scale = cfg.noise_scale();

    for step in 0..cfg.n_steps {
        // ---- half kick at the current position ----
        let mut f = energy_and_force(&mut x, m).1;
        let mut spring = [0.0f64; 3];
        for c in 0..NAT {
            f[ka + c] += -ANCHOR_K * (x[ka + c] - origin[c]);
            spring[c] = -cfg.spring_k * (x[kp + c] - anchor_pos[c]);
            f[kp + c] += spring[c];
        }
        for i in 0..v.len() {
            v[i] += 0.5 * cfg.dt * f[i];
        }
        for i in 0..x.len() {
            x[i] += cfg.dt * v[i];
        }
        // ---- friction and thermal kick (pull.py:37) ----
        for i in 0..n {
            for c in 0..NAT {
                let k = i * NAT + c;
                v[k] += -cfg.friction * v[k] * cfg.dt + noise_scale * rng.next_standard();
            }
        }
        // ---- half kick at the new position, anchor advanced first ----
        let mut f = energy_and_force(&mut x, m).1;
        for c in 0..NAT {
            f[ka + c] += -ANCHOR_K * (x[ka + c] - origin[c]);
            anchor_pos[c] += direction[c] * cfg.speed * cfg.dt;
            spring[c] = -cfg.spring_k * (x[kp + c] - anchor_pos[c]);
            f[kp + c] += spring[c];
        }
        for i in 0..v.len() {
            v[i] += 0.5 * cfg.dt * f[i];
        }
        extension[step] = norm3(sub3(at(&x, pull), at(&x, anchor)));
        // dot(-spring, direction), written out so no temporary vector is
        // allocated per step; 800 steps x a few ns each is the browser's budget.
        force_trace[step] =
            -(spring[0] * direction[0] + spring[1] * direction[1] + spring[2] * direction[2]);
        if step % 64 == 63 && x.iter().any(|a| !a.is_finite()) {
            return Err(EngineError::divergence(format!(
                "coordinates became non-finite by step {}; reduce dt or the pull speed",
                step + 1
            )));
        }
    }
    if force_trace.iter().any(|a| !a.is_finite()) {
        return Err(EngineError::divergence(
            "the force trace left the finite range; these last samples are not a measurement",
        ));
    }
    finish(x, &extension, &force_trace, m, cfg, cfg.extension0_a.unwrap_or(dn), anchor, pull)
}

/// Assemble the result: peak statistics exactly as `pull.py:46-50` computes them,
/// then the provenance notes a report has to carry.
fn finish(
    mut x: Vec<f64>,
    extension: &[f64],
    force_trace: &[f64],
    m: &GoModel,
    cfg: &PullConfig,
    extension0_a: f64,
    anchor: usize,
    pull: usize,
) -> EngineResult<PullResult> {
    let (peak_force_reduced, n_force_peaks, peak_step) = peak_summary(force_trace);
    let energy_final = energy_and_force(&mut x, m).0;
    let mut res = PullResult {
        label: String::new(),
        n_residues: m.n,
        n_contacts: m.n_contacts(),
        extension_a: extension.to_vec(),
        force_reduced: force_trace.to_vec(),
        peak_force_reduced,
        n_force_peaks,
        peak_step,
        native_contacts_remaining: contacts_remaining(&x, m),
        final_coords: x,
        energy_final,
        extension0_a,
        config: cfg.clone(),
        warnings: Vec::new(),
    };
    res.annotate(anchor, pull);
    Ok(res)
}

impl PullResult {
    /// The caveats, in the order a reader needs them: units first, then geometry,
    /// then whatever the PDB parse left out.
    fn annotate(&mut self, anchor: usize, pull: usize) {
        self.warnings.push(
            "forces and energies are reduced model units (epsilon, angstrom), NOT piconewtons"
                .to_string(),
        );
        self.warnings.push(
            "protein parity status: UNVALIDATED - no measured calibration for epsilon exists"
                .to_string(),
        );
        self.warnings.push(format!(
            "contact map is the assumed Cα rule (|i-j| >= {SEQ_SEP}, native distance < {CONTACT_CUTOFF} A); \
             SMOG's heavy-atom shadow map is not implemented, so the map may be denser than SMOG's"
        ));
        if anchor != 0 || pull != self.n_residues - 1 {
            self.warnings.push(format!(
                "pulled between trace indices {anchor} and {pull} instead of the termini; \
                 every corpus number was computed with terminal pulls"
            ));
        }
        if self.n_force_peaks == 0 {
            self.warnings.push(
                "no force peak cleared median + 0.5*std, so peak_force is the global maximum of a \
                 noisy trace rather than an unfolding event"
                    .to_string(),
            );
        }
        if self.native_contacts_remaining.is_nan() {
            self.warnings.push(
                "the structure has no native contacts, so contacts-remaining is undefined"
                    .to_string(),
            );
        }
    }
}
/// Map PDB residue numbers - the numbers a user reads off the 3D view - to trace
/// indices. `None` keeps the reference's termini. This indirection matters
/// because a domain sliced out of a chain has residue numbers that do not run
/// 1..n, so index and number diverge exactly when the picker is used.
pub fn resolve_pull_points(
    s: &Structure,
    anchor: Option<i64>,
    pull: Option<i64>,
) -> EngineResult<(Option<usize>, Option<usize>)> {
    let a = match anchor {
        Some(r) => Some(s.index_of_residue(r)?),
        None => None,
    };
    let p = match pull {
        Some(r) => Some(s.index_of_residue(r)?),
        None => None,
    };
    Ok((a, p))
}

/// Build the model and pull it. This is the entry point a page calls: the model
/// is a derived object nobody wants to manage separately, and building it here
/// keeps "the coordinates that defined the contacts" and "the coordinates the
/// integrator started from" the same buffer, which is the one way to guarantee
/// the native reference state is the state that was parsed.
pub fn simulate_structure(s: &Structure, cfg: &PullConfig) -> EngineResult<PullResult> {
    let m = build_model(&s.coords, cfg.lj_10_12)?;
    let mut res = simulate(&s.coords, &m, cfg)?;
    res.label = s.label.clone();
    // Parse provenance outranks generic caveats: the reader needs to know what
    // structure they are looking at before they care about its units.
    let mut warnings = s.notes.clone();
    warnings.extend(res.warnings);
    res.warnings = warnings;
    Ok(res)
}

/// Parse PDB text and pull it in one call, optionally restricted to one chain
/// and one residue range, with pull points given as PDB residue numbers.
pub fn pull_from_pdb(
    text: &str,
    chain: Option<char>,
    range: Option<(i64, i64)>,
    anchor_residue: Option<i64>,
    pull_residue: Option<i64>,
    mut cfg: PullConfig,
) -> EngineResult<PullResult> {
    let s = parse_pdb(text, chain, range)?;
    let (a, p) = resolve_pull_points(&s, anchor_residue, pull_residue)?;
    cfg.anchor = Some(a.unwrap_or(0));
    cfg.pull = Some(p.unwrap_or(s.n() - 1));
    simulate_structure(&s, &cfg)
}

impl PullResult {
    /// Peak force in pN, or `None` when no calibration was supplied. A missing
    /// calibration is not a zero and must not print as one.
    pub fn peak_force_pn(&self) -> Option<f64> {
        self.config
            .calibration
            .map(|c| self.peak_force_reduced * c.pn_per_reduced_force())
    }

    /// Pull speed in m/s, or `None` uncalibrated. PROTOCOL.md:39's warning that
    /// the speed grid "is a configuration value, not 1 m/s" lives here.
    pub fn speed_m_per_s(&self) -> Option<f64> {
        self.config
            .calibration
            .map(|c| self.config.speed * c.m_s_per_reduced_speed())
    }

    /// Loading rate, force over time, in pN/s - the x-axis of the Bell fit the
    /// brief asks for (peak force against loading rate). Uncalibrated, reduced
    /// units per reduced time is meaningless to fit against, so this returns
    /// `None` rather than a number that looks like a rate.
    pub fn loading_rate_pn_per_s(&self) -> Option<f64> {
        let c = self.config.calibration?;
        let span = self.config.n_steps as f64 * self.config.dt * c.ps_per_reduced_time() * 1e-12;
        if span <= 0.0 {
            return None;
        }
        Some(self.peak_force_pn()? / span)
    }

    /// Downsample the trace to at most `max_points` (first and last always kept)
    /// so a chart can be drawn without shipping 800 samples through a worker
    /// postMessage per replica.
    pub fn downsample(&self, max_points: usize) -> (Vec<f64>, Vec<f64>) {
        let n = self.force_reduced.len();
        if max_points == 0 || n <= max_points {
            return (self.extension_a.clone(), self.force_reduced.clone());
        }
        let mut ext = Vec::with_capacity(max_points);
        let mut frc = Vec::with_capacity(max_points);
        for k in 0..max_points {
            let i = if max_points == 1 {
                0
            } else {
                (k as u64 * (n as u64 - 1) / (max_points as u64 - 1)) as usize
            };
            ext.push(self.extension_a[i]);
            frc.push(self.force_reduced[i]);
        }
        (ext, frc)
    }
}
impl PullResult {
    /// The result as schema-shaped JSON.
    ///
    /// Every number carries its unit and its `unit_system`, which is what
    /// `smash-sim-results.schema.json` requires of a simulated value, for the
    /// stated reason: "a required unit_system to every value so reduced-unit
    /// results can never be mistaken for physical ones". The peak force is
    /// therefore emitted twice when a calibration exists - once reduced, once
    /// physical - and only once when it does not. A reduced-only run has no pN
    /// field at all rather than a pN field of `null`, because a viewer that reads
    /// `results[].value` and finds null renders a blank, which is the honest
    /// answer, whereas a `0` would be the false one.
    pub fn to_json(&self, max_points: usize) -> String {
        let cal = self.config.calibration;
        let unit_system = if cal.is_some() {
            "reduced_with_stated_conversion"
        } else {
            "reduced"
        };
        let mut o = String::new();
        o.push_str("{\n");
        o.push_str("  \"schema_version\": \"1.0.0\",\n");
        o.push_str(&format!(
            "  \"engine\": {{\"name\": {}, \"version\": {}}},\n",
            json::quote(crate::ENGINE_NAME),
            json::quote(crate::ENGINE_VERSION)
        ));
        o.push_str(&format!("  \"model_family\": {},\n", json::quote(crate::MODEL_GO_CA)));
        o.push_str(&format!("  \"unit_system\": {},\n", json::quote(unit_system)));
        o.push_str("  \"units_note\": \"forces and energies are reduced model units (epsilon, angstrom). Not piconewtons unless a calibration is supplied.\",\n");
        o.push_str("  \"parity_status\": \"UNVALIDATED\",\n");

        o.push_str("  \"structure\": {\n");
        o.push_str(&format!("    \"label\": {},\n", json::quote(&self.label)));
        o.push_str(&format!("    \"n_residues\": {},\n", self.n_residues));
        o.push_str(&format!("    \"n_native_contacts\": {},\n", self.n_contacts));
        o.push_str(&format!("    \"extension0_A\": {}\n", json::num(self.extension0_a)));
        o.push_str("  },\n");

        o.push_str("  \"config\": {\n");
        o.push_str(&format!("    \"speed_reduced\": {},\n", json::num(self.config.speed)));
        o.push_str(&format!("    \"spring_k_reduced\": {},\n", json::num(self.config.spring_k)));
        o.push_str(&format!("    \"n_steps\": {},\n", self.config.n_steps));
        o.push_str(&format!("    \"dt_reduced\": {},\n", json::num(self.config.dt)));
        o.push_str(&format!("    \"temperature_reduced\": {},\n", json::num(self.config.temperature)));
        o.push_str(&format!("    \"friction_reduced\": {},\n", json::num(self.config.friction)));
        o.push_str(&format!("    \"seed\": {},\n", self.config.seed));
        o.push_str(&format!("    \"lj_10_12\": {},\n", self.config.lj_10_12));
        let anchor = self.config.anchor.unwrap_or(0);
        let pull = self.config.pull.unwrap_or(self.n_residues.saturating_sub(1));
        o.push_str(&format!("    \"anchor_index\": {anchor},\n"));
        o.push_str(&format!("    \"pull_index\": {pull},\n"));
        match cal {
            Some(c) => {
                o.push_str("    \"calibration\": {\n");
                o.push_str(&format!(
                    "      \"epsilon_kj_per_mol\": {},\n      \"bead_mass_amu\": {},\n      \"pn_per_reduced_force\": {},\n      \"ps_per_reduced_time\": {},\n      \"m_s_per_reduced_speed\": {}\n",
                    json::num(c.epsilon_kj_per_mol),
                    json::num(c.bead_mass_amu),
                    json::num(c.pn_per_reduced_force()),
                    json::num(c.ps_per_reduced_time()),
                    json::num(c.m_s_per_reduced_speed())
                ));
                // No trailing comma: `calibration` is the last field of `config`,
                // and `JSON.parse` rejects a trailing separator. The comma belongs
                // on the fields that *precede* a value, not on the final one.
                o.push_str("    }\n");
            }
            None => o.push_str("    \"calibration\": null\n"),
        }
        o.push_str("  },\n");
        // ---- results[], in the SMFS Result field set the schema mirrors ----
        o.push_str("  \"results\": [\n");
        let mut any = false;
        let mut result = |o: &mut String, quantity: &str, label: &str, value: f64, unit: &str, sys: &str, n_events: usize| {
            // JSON separates entries with a comma *between* them, not before the
            // first: emit one only when an element has already been written.
            if std::mem::replace(&mut any, true) {
                o.push_str(",\n");
            }
            o.push_str(&format!("    {{\"quantity\": {}, \"label\": {}, \"value\": {}, \"unit\": {}, \"unit_system\": {}, \"statistic\": \"single_value\", \"n_events\": {}, \"model_family\": {}}}",
                json::quote(quantity),
                json::quote(label),
                json::num(value),
                json::quote(unit),
                json::quote(sys),
                n_events,
                json::quote(crate::MODEL_GO_CA)));
        };
        // "unfolding_force" is the schema's quantity for a peak; label says which
        // statistic engine-side we took, since peak-of-smoothed-raw differs from
        // the maximum of the trace and a reader must be able to tell them apart.
        result(&mut o, "unfolding_force", "peak force of the trace", self.peak_force_reduced, "epsilon/angstrom", unit_system, 1);
        if let Some(pn) = self.peak_force_pn() {
            result(&mut o, "unfolding_force", "peak force of the trace, calibrated", pn, "pN", "physical", 1);
        }
        if let Some(rate) = self.loading_rate_pn_per_s() {
            result(&mut o, "loading_rate", "loading rate over the trajectory", rate, "pN/s", "physical", 1);
        }
        if let Some(sp) = self.speed_m_per_s() {
            result(&mut o, "velocity", "anchor speed, calibrated", sp, "m/s", "physical", 1);
        }
        // Number of force peaks is a count of steps/intermediates in schema terms,
        // and it is unitless in both systems, so it is always emitted.
        result(&mut o, "number_of_steps_or_intermediates", "force peaks detected", self.n_force_peaks as f64, "1", unit_system, self.n_force_peaks.max(1));
        result(&mut o, "other", "fraction of native contacts remaining", self.native_contacts_remaining, "1", unit_system, 1);
        result(&mut o, "contour_length", "native end-to-end distance", self.extension0_a, "angstrom", unit_system, 1);
        result(&mut o, "other", "final potential energy", self.energy_final, "epsilon", unit_system, 1);
        o.push_str("\n  ],\n");

        // ---- the curve ----
        let (ext, frc) = self.downsample(max_points);
        o.push_str("  \"trajectory\": {\n");
        o.push_str(&format!("    \"n_samples\": {},\n", self.force_reduced.len()));
        o.push_str(&format!("    \"downsampled_to\": {},\n", ext.len()));
        o.push_str("    \"extension_unit\": \"angstrom\",\n");
        o.push_str("    \"force_unit\": \"epsilon/angstrom\",\n");
        o.push_str("    \"extension\": [");
        for (i, v) in ext.iter().enumerate() {
            if i > 0 {
                o.push_str(", ");
            }
            o.push_str(&json::num(*v));
        }
        o.push_str("],\n    \"force\": [");
        for (i, v) in frc.iter().enumerate() {
            if i > 0 {
                o.push_str(", ");
            }
            o.push_str(&json::num(*v));
        }
        o.push_str("],\n");
        o.push_str(&format!("    \"peak_index\": {}\n", self.peak_step));
        o.push_str("  },\n");

        o.push_str("  \"warnings\": [");
        for (i, w) in self.warnings.iter().enumerate() {
            if i > 0 {
                o.push_str(", ");
            }
            o.push_str(&json::quote(w));
        }
        o.push_str("]\n}\n");
        o
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::json::Json;

    /// A short helical Ca trace: long enough to have native contacts (n >= MIN_CA)
    /// and to keep the reference's 5-point peak window meaningful.
    fn helix(n: usize) -> Vec<f64> {
        let mut v = Vec::with_capacity(n * NAT);
        for i in 0..n {
            let t = i as f64;
            let th = 100f64.to_radians() * t;
            v.extend_from_slice(&[2.3 * th.cos(), 2.3 * th.sin(), 1.5 * t]);
        }
        v
    }

    fn cfg(n_steps: usize) -> PullConfig {
        PullConfig {
            speed: 0.2,
            spring_k: 0.1,
            n_steps,
            dt: 0.002,
            temperature: 0.0,
            friction: 1.0,
            seed: 1,
            ..Default::default()
        }
    }

    fn parse_or_fail(text: &str) -> Json {
        match crate::json::parse(text) {
            Ok(j) => j,
            Err(e) => panic!("to_json produced unreadable JSON: {e}\n---\n{text}\n---"),
        }
    }

    /// A hand-built result, so the JSON edge cases do not depend on getting the
    /// engine to diverge on purpose.
    fn result_with(peak: f64, contacts: f64, energy: f64, cal: Option<Calibration>) -> PullResult {
        PullResult {
            label: "TEST:A 1-8".to_string(),
            n_residues: 8,
            n_contacts: 12,
            extension_a: vec![20.0, 20.5, 21.0, 21.5, 22.0],
            force_reduced: vec![0.1, 0.4, 0.9, 0.4, 0.1],
            peak_force_reduced: peak,
            n_force_peaks: 1,
            peak_step: 2,
            native_contacts_remaining: contacts,
            final_coords: vec![0.0; 24],
            energy_final: energy,
            extension0_a: 10.5,
            config: PullConfig {
                calibration: cal,
                ..cfg(5)
            },
            warnings: vec!["note one".to_string(), "note \"two\"".to_string()],
        }
    }

    fn results_of(parsed: &Json) -> Vec<Json> {
        parsed
            .get("results")
            .and_then(|v| v.as_arr())
            .unwrap_or_else(|| panic!("json has no results[] array"))
            .to_vec()
    }

    #[test]
    fn json_is_parseable_when_results_have_multiple_entries() {
        // The comma logic and the per-object brace count: with a calibration the
        // results[] array carries eight entries, which is exactly the shape that
        // used to emit a leading comma and a stray closing brace.
        let cal = Calibration {
            epsilon_kj_per_mol: 1.0,
            bead_mass_amu: 110.0,
        };
        let text = result_with(0.9, 0.75, -3.25, Some(cal)).to_json(16);
        let parsed = parse_or_fail(&text);
        let results = results_of(&parsed);
        assert!(
            results.len() >= 5,
            "a calibrated run must emit the reduced peak, the pN peak, the loading rate, \
             the velocity and the counts, got {}",
            results.len()
        );
        for entry in &results {
            for key in [
                "quantity", "label", "value", "unit", "unit_system", "statistic", "n_events",
                "model_family",
            ] {
                assert!(
                    entry.get(key).is_some(),
                    "a results[] entry is missing {key}: {entry:?}"
                );
            }
        }
        assert_eq!(
            text.matches('{').count(),
            text.matches('}').count(),
            "unbalanced braces in {text}"
        );
        assert_eq!(field_str(&parsed, "unit_system"), "reduced_with_stated_conversion");
    }

    fn field_str(j: &Json, key: &str) -> String {
        j.get(key)
            .and_then(|v| v.as_str())
            .unwrap_or_else(|| panic!("json has no string field {key}"))
            .to_string()
    }

    #[test]
    fn json_without_calibration_carries_no_physical_entries() {
        let parsed = parse_or_fail(&result_with(0.9, 0.75, -3.25, None).to_json(16));
        assert_eq!(field_str(&parsed, "unit_system"), "reduced");
        assert!(
            !results_of(&parsed)
                .iter()
                .any(|e| e.get("unit").and_then(|u| u.as_str()) == Some("pN")),
            "a reduced-only run must not claim a pN value"
        );
        assert!(
            matches!(
                parsed.get("config").and_then(|c| c.get("calibration")),
                Some(Json::Null)
            ),
            "the config must record calibration: null rather than a fabricated conversion"
        );
    }

    #[test]
    fn json_emits_null_not_nan_for_undefined_numbers() {
        // contacts-remaining is NaN when the structure has no native contacts, and
        // a diverged run can hand back an infinite energy. Neither is a JSON token,
        // and a viewer that reads the value must not be handed a `0`.
        let text = result_with(f64::NAN, f64::NAN, f64::INFINITY, None).to_json(16);
        let parsed = parse_or_fail(&text);
        let nulls = results_of(&parsed)
            .iter()
            .filter(|e| matches!(e.get("value"), Some(Json::Null)))
            .count();
        assert!(
            nulls >= 3,
            "peak force, contacts-remaining and final energy should all be null, got {nulls}"
        );
        assert!(
            !text.contains("NaN") && !text.contains("Infinity"),
            "non-finite tokens leaked into strict JSON"
        );
    }

    #[test]
    fn json_honours_max_points_and_escapes_warnings() {
        let text = result_with(1e20, 0.5, -0.0, None).to_json(3);
        let parsed = parse_or_fail(&text);
        let traj = parsed.get("trajectory").expect("trajectory");
        assert_eq!(traj.get("extension").unwrap().as_arr().unwrap().len(), 3);
        assert_eq!(traj.get("force").unwrap().as_arr().unwrap().len(), 3);
        assert_eq!(traj.get("n_samples").unwrap().as_f64(), Some(5.0));
        assert_eq!(traj.get("peak_index").unwrap().as_f64(), Some(2.0));
        // The hand-built warnings contain a quote, which must not break the array.
        let w = parsed.get("warnings").unwrap().as_arr().unwrap();
        assert_eq!(w.len(), 2);
        assert_eq!(w[1].as_str(), Some("note \"two\""));
    }
    #[test]
    fn injected_noise_shorter_than_the_run_is_rejected() {
        let coords = helix(8);
        let m = build_model(&coords, false).unwrap();
        let c = cfg(5);
        let need = c.n_steps * m.n * NAT;
        let err = simulate_with_injected_noise(&coords, &m, &c, &vec![0.0; need - 1])
            .expect_err("a short noise array must be an error, not a silent zero-fill");
        assert!(
            err.to_string().contains(&need.to_string()),
            "the error must state how many draws the run needs: {err}"
        );
        // Exactly enough is enough; one draw to spare is ignored, not demanded.
        assert!(simulate_with_injected_noise(&coords, &m, &c, &vec![0.1; need]).is_ok());
        assert!(simulate_with_injected_noise(&coords, &m, &c, &vec![0.1; need + 7]).is_ok());
    }

    #[test]
    fn injected_noise_is_reproducible_and_order_matters() {
        let coords = helix(8);
        let m = build_model(&coords, false).unwrap();
        let c = PullConfig {
            temperature: 0.5,
            ..cfg(40)
        };
        let need = c.n_steps * m.n * NAT;
        let noise: Vec<f64> = (0..need).map(|k| ((k as f64) * 0.37).sin()).collect();
        let a = simulate_with_injected_noise(&coords, &m, &c, &noise).unwrap();
        let b = simulate_with_injected_noise(&coords, &m, &c, &noise).unwrap();
        assert_eq!(a.final_coords, b.final_coords, "the same noise must give the same run");
        assert_eq!(a.force_reduced, b.force_reduced);
        assert_eq!(a.energy_final, b.energy_final);

        // The draws are consumed atom-major, component-minor, exactly as
        // `rng.normal(size = x.shape)` fills them, so swapping two adjacent
        // component draws is a different physical trajectory. If the engine read
        // the array component-major instead, this assertion would pass silently.
        let mut swapped = noise.clone();
        swapped.swap(0, 1);
        let d = simulate_with_injected_noise(&coords, &m, &c, &swapped).unwrap();
        assert_ne!(a.final_coords, d.final_coords, "draw order must matter");
        // ...and the first divergence is at the atom that owns those components.
        let first_diff = (0..a.final_coords.len())
            .find(|k| a.final_coords[*k] != d.final_coords[*k])
            .expect("a differing trajectory must differ somewhere");
        assert!(
            first_diff < 3 * 3,
            "a swapped draw in step 0 must perturb an early atom, not a late one \
             (first difference at flat index {first_diff})"
        );
    }

    #[test]
    fn zero_temperature_ignores_the_noise_stream_entirely() {
        let coords = helix(8);
        let m = build_model(&coords, false).unwrap();
        let c = cfg(30);
        let need = c.n_steps * m.n * NAT;
        let wild = simulate_with_injected_noise(&coords, &m, &c, &vec![7.5; need]).unwrap();
        let none = simulate_with_injected_noise(&coords, &m, &c, &vec![0.0; need]).unwrap();
        assert!(
            wild.final_coords == none.final_coords,
            "noise_scale is sqrt(2*friction*T*dt) and T is 0, so no draw may survive"
        );
        // The engine's own PRNG must be equally irrelevant at T = 0: that is what
        // makes a zero-temperature fixture a fair comparison between the engines.
        let mut s1 = c.clone();
        s1.seed = 1;
        let mut s2 = c.clone();
        s2.seed = 99;
        let r1 = simulate(&coords, &m, &s1).unwrap();
        let r2 = simulate(&coords, &m, &s2).unwrap();
        assert_eq!(r1.final_coords, r2.final_coords);
        assert_eq!(r1.force_reduced, r2.force_reduced);
        assert_eq!(r1.force_reduced, none.force_reduced, "injected zeros must equal the engine at T=0");
    }

    #[test]
    fn short_traces_are_rejected_before_the_physics() {
        // `peaks` needs a 5-sample window; the reference returns an empty peak list
        // for a shorter trace, so a run that cannot report a peak is refused.
        let coords = helix(8);
        let m = build_model(&coords, false).unwrap();
        let c = cfg(4);
        let err = simulate(&coords, &m, &c).expect_err("4 steps cannot carry a 5-point window");
        assert!(err.to_string().contains("n_steps"), "{err}");
        // A degenerate pull geometry has no axis to pull along.
        let mut same = helix(8);
        let head = [same[0], same[1], same[2]];
        same[21..24].copy_from_slice(&head);
        let e2 = simulate(&same, &build_model(&same, false).unwrap(), &cfg(8))
            .expect_err("anchor and pull on top of each other");
        assert!(e2.to_string().contains("no end-to-end vector"), "{e2}");
    }

}












