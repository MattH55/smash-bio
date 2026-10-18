//! Structure preparation flags for the browser (brief, Phase 2 "Structure
//! preparation"): per-residue B-factor (pLDDT for AlphaFold models), disulfides,
//! metal sites, bound ligands and chain breaks.
//!
//! This is a second, read-only pass over the PDB text. `protein::parse_pdb`
//! (which the parity test pins against the reference) is not changed; this
//! module only *adds* information the reference never had, so it can be
//! extended without touching parity.

use crate::json;
use crate::protein::{at, norm3, sub3, Structure};

/// Metal and common ion residue names (HETATM resName), reported as metal sites.
const METALS: &[&str] = &[
    "ZN", "CU", "CU1", "FE", "FE2", "MG", "CA", "MN", "NI", "CO", "CD", "HG", "NA", "K", "MO", "W", "PT",
];
/// HETATM names that are solvent or crystallisation additives, not ligands worth flagging.
const IGNORE_HET: &[&str] = &["HOH", "WAT", "DOD", "SO4", "PO4", "GOL", "EDO", "PEG", "ACT", "CL", "BR", "IOD", "FMT", "DMS", "MPD", "TRS"];

#[derive(Debug, Clone, Default)]
pub struct Prep {
    /// B-factor of each Cα in trace order (pLDDT for AlphaFold models).
    pub bfactor: Vec<f64>,
    /// True when the file is an AlphaFold model (B-factor column = pLDDT).
    pub is_alphafold: bool,
    /// Disulfides as pairs of PDB residue numbers in the modelled chain.
    pub disulfides: Vec<(i64, i64)>,
    /// Metal sites: (residue name, PDB residue number of the HETATM, chain).
    pub metals: Vec<(String, i64, char)>,
    /// Distinct ligand residue names bound to the structure (excluding solvent/additives).
    pub ligands: Vec<String>,
    /// Chain breaks: (residue number before, residue number after, Cα gap in Å).
    pub breaks: Vec<(i64, i64, f64)>,
}

fn field(b: &[u8], lo: usize, hi: usize) -> &str {
    if b.len() < lo {
        return "";
    }
    let hi = hi.min(b.len());
    std::str::from_utf8(&b[lo..hi]).unwrap_or("").trim()
}

/// Annotate a parsed structure from the same PDB text it came from.
pub fn annotate(text: &str, s: &Structure) -> Prep {
    let mut p = Prep::default();
    let upper_head: String = text.lines().take(40).collect::<Vec<_>>().join("\n").to_ascii_uppercase();
    p.is_alphafold = upper_head.contains("ALPHAFOLD") || upper_head.contains("AF-") && upper_head.contains("MODEL");
    let mut bmap: Vec<(i64, f64)> = Vec::new();
    let mut sg: Vec<(i64, [f64; 3])> = Vec::new();
    let mut ss_records: Vec<(i64, i64)> = Vec::new();
    let mut ligands: Vec<String> = Vec::new();
    for line in text.lines() {
        let b = line.as_bytes();
        if b.len() < 6 {
            continue;
        }
        let rec = &b[0..6];
        if rec == b"SSBOND" && b.len() >= 36 {
            let c1 = field(b, 15, 16).chars().next().unwrap_or(' ');
            let c2 = field(b, 29, 30).chars().next().unwrap_or(' ');
            let r1 = field(b, 17, 21).parse::<i64>().ok();
            let r2 = field(b, 31, 35).parse::<i64>().ok();
            if let (Some(r1), Some(r2)) = (r1, r2) {
                if c1 == s.chain && c2 == s.chain {
                    ss_records.push((r1.min(r2), r1.max(r2)));
                }
            }
        } else if (rec == b"ATOM  " || rec == b"HETATM") && b.len() >= 54 {
            let chain = field(b, 21, 22).chars().next().unwrap_or(' ');
            let resname = field(b, 17, 20).to_string();
            let atom = field(b, 12, 16);
            let resseq = field(b, 22, 26).parse::<i64>().ok();
            if rec == b"HETATM" {
                let rn = resname.to_ascii_uppercase();
                if METALS.contains(&rn.as_str()) {
                    if let Some(r) = resseq {
                        if !p.metals.iter().any(|m| m.0 == rn && m.1 == r && m.2 == chain) {
                            p.metals.push((rn, r, chain));
                        }
                    }
                } else if !IGNORE_HET.contains(&rn.as_str()) && !["MSE", "SEP", "TPO"].contains(&rn.as_str()) {
                    if !ligands.contains(&rn) {
                        ligands.push(rn);
                    }
                }
                continue;
            }
            if chain != s.chain {
                continue;
            }
            let Some(r) = resseq else { continue };
            if atom == "CA" && !bmap.iter().any(|(rr, _)| *rr == r) {
                let bf = field(b, 60, 66).parse::<f64>().unwrap_or(f64::NAN);
                bmap.push((r, bf));
            }
            if atom == "SG" && resname == "CYS" {
                let xs = field(b, 30, 38).parse::<f64>();
                let ys = field(b, 38, 46).parse::<f64>();
                let zs = field(b, 46, 54).parse::<f64>();
                if let (Ok(x), Ok(y), Ok(z)) = (xs, ys, zs) {
                    sg.push((r, [x, y, z]));
                }
            }
        }
    }
    p.bfactor = s
        .residues
        .iter()
        .map(|r| bmap.iter().find(|(rr, _)| rr == r).map(|x| x.1).unwrap_or(f64::NAN))
        .collect();
    // disulfides: SSBOND records plus any CYS SG pair within 2.5 Å
    let mut ss = ss_records;
    for a in 0..sg.len() {
        for b2 in (a + 1)..sg.len() {
            let d = norm3(sub3(sg[a].1, sg[b2].1));
            if d < 2.5 {
                let pair = (sg[a].0.min(sg[b2].0), sg[a].0.max(sg[b2].0));
                if !ss.contains(&pair) {
                    ss.push(pair);
                }
            }
        }
    }
    ss.sort();
    ss.dedup();
    // keep only disulfides whose residues are inside the modelled trace
    p.disulfides = ss.into_iter().filter(|(a, b)| s.residues.contains(a) && s.residues.contains(b)).collect();
    p.ligands = ligands;
    // chain breaks: numbering gaps or a Cα-Cα distance above 4.2 Å
    for k in 0..s.residues.len().saturating_sub(1) {
        let d = norm3(sub3(at(&s.coords, k + 1), at(&s.coords, k)));
        if s.residues[k + 1] - s.residues[k] != 1 || d > 4.2 {
            p.breaks.push((s.residues[k], s.residues[k + 1], d));
        }
    }
    p
}

impl Prep {
    pub fn to_json(&self) -> String {
        let b: Vec<String> = self.bfactor.iter().map(|v| json::num(*v)).collect();
        let ss: Vec<String> = self.disulfides.iter().map(|(a, b)| format!("[{a},{b}]")).collect();
        let me: Vec<String> = self
            .metals
            .iter()
            .map(|(n, r, c)| format!("{{\"name\":{},\"residue\":{r},\"chain\":{}}}", json::quote(n), json::quote(&c.to_string())))
            .collect();
        let li: Vec<String> = self.ligands.iter().map(|l| json::quote(l)).collect();
        let br: Vec<String> = self.breaks.iter().map(|(a, b, d)| format!("[{a},{b},{}]", json::num(*d))).collect();
        format!(
            "{{\"bfactor\":[{}],\"is_alphafold\":{},\"disulfides\":[{}],\"metals\":[{}],\"ligands\":[{}],\"breaks\":[{}]}}",
            b.join(","),
            self.is_alphafold,
            ss.join(","),
            me.join(","),
            li.join(","),
            br.join(",")
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::protein::parse_pdb;

    #[test]
    fn ubiquitin_has_no_disulfide_and_full_bfactors() {
        let t = std::fs::read_to_string(format!("{}/fixtures/1UBQ.pdb", env!("CARGO_MANIFEST_DIR"))).unwrap();
        let s = parse_pdb(&t, Some('A'), None).unwrap();
        let p = annotate(&t, &s);
        assert_eq!(p.bfactor.len(), s.n());
        assert!(p.bfactor.iter().all(|b| b.is_finite()));
        assert!(p.disulfides.is_empty());
        assert!(!p.is_alphafold);
    }

    #[test]
    fn sg_pair_is_detected_as_disulfide() {
        let pdb = "\
ATOM      1  CA  CYS A   1       0.000   0.000   0.000  1.00 90.00           C\n\
ATOM      2  SG  CYS A   1       1.000   0.000   0.000  1.00 90.00           S\n\
ATOM      3  CA  GLY A   2       3.800   0.000   0.000  1.00 90.00           C\n\
ATOM      4  CA  GLY A   3       7.600   0.000   0.000  1.00 40.00           C\n\
ATOM      5  CA  GLY A   4      11.400   0.000   0.000  1.00 90.00           C\n\
ATOM      6  CA  CYS A   5      11.400   3.800   0.000  1.00 90.00           C\n\
ATOM      7  SG  CYS A   5       2.000   1.000   0.000  1.00 90.00           S\n\
ATOM      8  CA  GLY A   6       7.600   3.800   0.000  1.00 90.00           C\n\
ATOM      9  CA  GLY A   7       3.800   3.800   0.000  1.00 90.00           C\n\
HETATM   10 ZN    ZN A 101       5.000   5.000   5.000  1.00 90.00          ZN\n";
        let s = parse_pdb(pdb, Some('A'), None).unwrap();
        let p = annotate(pdb, &s);
        assert_eq!(p.disulfides, vec![(1, 5)]);
        assert_eq!(p.metals.len(), 1);
        assert!((p.bfactor[2] - 40.0).abs() < 1e-9);
        assert!(p.to_json().contains("\"disulfides\":[[1,5]]"));
    }
}
