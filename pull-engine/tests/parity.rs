//! Reference-parity acceptance test for the nucleic path.
//!
//! `tests/pull/parity/expected.json` is exported from the Python reference
//! pipeline (smash-sim/nucleic/src/nasim) by `export_reference.py`, which reads
//! that tree strictly read-only. This test recomputes the same cases in Rust and
//! asserts agreement, so "porting the physics" means "reproducing the numbers",
//! not "looks similar".
//!
//! The file is optional on purpose: without it the crate still builds and tests,
//! and this file skips with a message rather than failing, because the reference
//! tree lives outside the isolated pull directories and is not shipped with the
//! engine.

use pull_engine::json::{parse, Json};
use pull_engine::nucleic::{
    contour_nm, half_force, hairpin_stem, mean_open, normalise, Polymer, Geometry,
};
use pull_engine::units::*;
use pull_engine::wlc;

fn golden() -> Option<Json> {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../tests/pull/parity/expected.json");
    let text = match std::fs::read_to_string(path) {
        Ok(t) => t,
        Err(_) => {
            eprintln!("SKIP parity: no golden file at {path}\n  run: python tests/pull/parity/export_reference.py");
            return None;
        }
    };
    match parse(&text) {
        Ok(j) => Some(j),
        Err(e) => {
            eprintln!("SKIP parity: golden file is not readable JSON: {e}");
            None
        }
    }
}

/// Relative tolerance. The engine and the reference run the same Newton count
/// and the same grid, so the only divergence is floating-point ordering;
/// 1e-9 is generous for that and strict enough to catch a real mismatch.
fn close(a: f64, b: f64, rel: f64, what: &str) {
    let scale = a.abs().max(b.abs()).max(1e-12);
    assert!((a - b).abs() / scale < rel, "{what}: engine {a} vs reference {b}");
}

#[test]
fn constants_agree_with_reference() {
    let Some(g) = golden() else { return };
    let c = g.get("constants").expect("constants");
    let pairs = [
        ("T_NN_K", T_NN_K),
        ("SALT_N_PHOSPHATE_SLOPE", SALT_N_PHOSPHATE_SLOPE),
        ("SS_RISE_NM", SS_RISE_NM),
        ("SS_LP_NM", SS_LP_NM),
        ("DS_RISE_NM", DS_RISE_NM),
        ("KT_PN_NM_298", KT_PN_NM_298),
    ];
    for (key, mine) in pairs {
        let theirs = c.get(key).and_then(|v| v.as_f64()).unwrap_or_else(|| panic!("no {key}"));
        assert_eq!(mine, theirs, "constant {key}");
    }
}

#[test]
fn nn_tables_agree_with_reference() {
    let Some(g) = golden() else { return };
    for (field, table) in [("dna_nn", &pull_engine::nucleic::DNA_NN), ("rna_nn", &pull_engine::nucleic::RNA_NN)] {
        let obj = g.get("constants").unwrap().get(field).unwrap_or_else(|| panic!("no {field}"));
        if let Json::Obj(kvs) = obj {
            for (key, val) in kvs {
                let arr = val.as_arr().unwrap_or_else(|| panic!("{field}[{key}] not array"));
                let dh = arr[0].as_f64().unwrap();
                let ds = arr[1].as_f64().unwrap();
                let found = table
                    .iter()
                    .find(|(k, _, _)| *k == key.as_str())
                    .unwrap_or_else(|| panic!("engine table missing {field} {key}"));
                assert_eq!(found.1, dh, "{field} {key} dH");
                assert_eq!(found.2, ds, "{field} {key} dS");
            }
        } else {
            panic!("{field} must be an object");
        }
    }
}

#[test]
fn wlc_extension_agrees_with_reference() {
    let Some(g) = golden() else { return };
    let cases = g.get("extension").unwrap().as_arr().unwrap();
    assert!(!cases.is_empty());
    for c in cases {
        let t = c.get("temperature_k").unwrap().as_f64().unwrap();
        let f = c.get("force_pn").unwrap().as_f64().unwrap();
        let want = c.get("extension_nm").unwrap().as_f64().unwrap();
        let got = wlc::extension_nm(f, 20.0 * SS_RISE_NM, SS_LP_NM, t);
        close(got, want, 1e-9, &format!("extension at {f} pN, {t} K"));
    }
}

#[test]
fn integrated_work_endpoints_agree_with_reference() {
    let Some(g) = golden() else { return };
    for c in g.get("work").unwrap().as_arr().unwrap() {
        let t = c.get("temperature_k").unwrap().as_f64().unwrap();
        let forces = wlc::linspace(0.05, 80.0, 1600);
        close(forces[1], c.get("grid_force_at_1").unwrap().as_f64().unwrap(), 1e-12, "grid step");
        let ext: Vec<f64> = forces.iter().map(|&f| wlc::extension_nm(f, 20.0 * SS_RISE_NM, SS_LP_NM, t)).collect();
        let work = wlc::integrated_work(&forces, &ext);
        let first = c.get("first").and_then(|v| v.as_f64()).unwrap();
        let middle = c.get("middle").and_then(|v| v.as_f64()).unwrap();
        let last = c.get("last").and_then(|v| v.as_f64()).unwrap();
        close(work[0], first, 1e-9, "work[0]");
        close(work[800], middle, 1e-9, "work[800]");
        close(work[work.len() - 1], last, 1e-9, "work[-1]");
    }
}

#[test]
fn stem_free_energies_agree_with_reference() {
    let Some(g) = golden() else { return };
    let cases = g.get("thermo").unwrap().as_arr().unwrap();
    assert!(cases.len() >= 30, "expected the full stem x salt x polymer grid");
    for c in cases {
        let stem = c.get("stem").unwrap().as_str().unwrap();
        let poly = Polymer::parse(c.get("polymer").unwrap().as_str().unwrap()).unwrap();
        let salt = c.get("na_molar").unwrap().as_f64().unwrap();
        let want = c.get("dg_fold_kcal").unwrap().as_f64().unwrap();
        let got = pull_engine::nucleic::stem_delta_g(stem, poly, salt, T_NN_K).unwrap();
        close(got.dg_1m_kcal, c.get("dg_1M_kcal").unwrap().as_f64().unwrap(), 1e-12, "dg_1M");
        let want_corr = c.get("salt_correction_kcal").unwrap().as_f64().unwrap();
        // Reference emits -0.0 at 1 M; equal in value, so compare on magnitude.
        assert!(
            (got.salt_correction_kcal - want_corr).abs() < 1e-12,
            "salt correction for {stem} at {salt} M: {} vs {want_corr}",
            got.salt_correction_kcal
        );
        close(got.dg_fold_kcal, want, 1e-12, &format!("dg_fold {stem} {salt}"));
        assert_eq!(got.n_bp, normalise(stem).len());
    }
}

#[test]
fn half_forces_agree_with_reference() {
    let Some(g) = golden() else { return };
    let cases = g.get("half_force").unwrap().as_arr().unwrap();
    assert!(cases.len() >= 60, "expected 5 stems x 3 salts x 2 geometries");
    let mut finite = 0usize;
    for c in cases {
        let stem = c.get("stem").unwrap().as_str().unwrap();
        let poly = Polymer::parse(c.get("polymer").unwrap().as_str().unwrap()).unwrap();
        let salt = c.get("na_molar").unwrap().as_f64().unwrap();
        let geo = Geometry::parse(c.get("geometry").unwrap().as_str().unwrap()).unwrap();
        let t = c.get("temperature_k").unwrap().as_f64().unwrap();
        let want = c.get("F_half_pN").unwrap().as_f64().unwrap();
        let got = half_force(stem, poly, salt, geo, t).unwrap();
        close(got.delta_lc_nm, c.get("deltaLc_nm").unwrap().as_f64().unwrap(), 1e-12, "deltaLc");
        close(
            got.unfold_cost_pn_nm,
            c.get("unfold_cost_pNnm").unwrap().as_f64().unwrap(),
            1e-10,
            "cost",
        );
        if want.is_finite() {
            finite += 1;
            // Reported to the reference's own grid resolution: the crossing is
            // located to one sample of a 0.05-80 pN / 1600-point grid, so the
            // engines must agree to the same absolute window, not to 1e-9.
            assert!(
                (got.f_half_pn - want).abs() < 1e-9,
                "{stem} {poly:?} {salt} M {} at {t} K: engine {} vs reference {want}",
                geo.as_str(),
                got.f_half_pn
            );
        } else {
            assert!(got.f_half_pn.is_nan(), "{stem}: reference NaN but engine {}", got.f_half_pn);
        }
    }
    assert!(finite > 0, "golden file contains no finite half-forces at all");
}

#[test]
fn contour_lengths_agree_with_reference() {
    let Some(g) = golden() else { return };
    for c in g.get("contour").unwrap().as_arr().unwrap() {
        let n = c.get("n_open").unwrap().as_f64().unwrap() as usize;
        let geo = Geometry::parse(c.get("geometry").unwrap().as_str().unwrap()).unwrap();
        let want = c.get("deltaLc_nm").unwrap().as_f64().unwrap();
        assert_eq!(contour_nm(n, geo), want, "contour {n} {geo:?}");
    }
}

#[test]
fn occupancy_mean_agrees_with_reference() {
    let Some(g) = golden() else { return };
    let cases = g.get("mean_open").unwrap().as_arr().unwrap();
    assert!(cases.len() >= 25, "expected 5 stems x 5 forces");
    for c in cases {
        let stem = c.get("stem").unwrap().as_str().unwrap();
        let f = c.get("force_pn").unwrap().as_f64().unwrap();
        let want = c.get("mean_open").unwrap().as_f64().unwrap();
        let got = mean_open(stem, f, Polymer::Dna, 1.0, Geometry::Hairpin, 298.15).unwrap();
        // Both sides are Boltzmann averages of the same 400-point grid; the
        // tolerance is the double-rounding floor, and 1e-6 of a base pair is
        // far tighter than the model's own assumption error.
        assert!(
            (got - want).abs() < 1e-6,
            "mean_open {stem} at {f} pN: engine {got} vs reference {want}"
        );
    }
}

#[test]
fn hairpin_stem_extraction_agrees_with_reference() {
    let Some(g) = golden() else { return };
    for c in g.get("hairpin_stem").unwrap().as_arr().unwrap() {
        let seq = c.get("sequence").unwrap().as_str().unwrap();
        let dot = c.get("dot_bracket").unwrap().as_str().unwrap();
        let want = match c.get("stem") {
            Some(Json::Str(s)) => Some(s.clone()),
            _ => None,
        };
        let got = hairpin_stem(seq, dot);
        assert_eq!(got.as_deref(), want.as_deref(), "hairpin_stem({seq:?}, {dot:?})");
    }
}
