//! Reference-parity acceptance test for the protein (Ca Gō) path.
//!
//! `tests/pull/parity/expected_protein.json` is exported by
//! `export_protein_reference.py`, which runs the Python reference backend
//! (`smash-sim/src/smashsim/go_model.py` + `pull.py`) over the same cases this
//! file recomputes in Rust. It is the protein counterpart of `parity.rs`, which
//! covers the nucleic path only.
//!
//! Two tiers, deliberately separated:
//!
//! * **static** - parsing, the contact map, and native-state energy/force. These
//!   have no integrator in them, so they must agree to the last bit a comparison
//!   can express. A failure here is a wrong term in the Hamiltonian.
//! * **trajectory** - the pull itself. Every trajectory in the fixture is either
//!   zero-temperature (so `noise_scale == 0` and both engines integrate the
//!   identical deterministic step) or driven by a noise array the reference drew
//!   and wrote into the fixture, consumed via `simulate_with_injected_noise`.
//!   Nothing here compares random streams: NumPy's generator is not reproduced
//!   and a noisy walk from each engine would differ for reasons that are not the
//!   physics.
//!
//! The golden file is optional, exactly as in `parity.rs`: without it this test
//! skips with a message rather than failing, because the reference tree lives
//! outside the isolated engine directory.

use pull_engine::json::{parse, Json};
use pull_engine::protein::{
    build_model, contacts_remaining, energy_and_force, parse_pdb, peak_force, peak_summary,
    peaks, simulate_with_injected_noise, smooth5, GoModel, PullConfig, PullResult, Structure,
};
use pull_engine::units::*;

fn golden_path() -> String {
    concat!(env!("CARGO_MANIFEST_DIR"), "/../tests/pull/parity/expected_protein.json").to_string()
}

fn golden() -> Option<Json> {
    let path = golden_path();
    let text = match std::fs::read_to_string(&path) {
        Ok(t) => t,
        Err(_) => {
            eprintln!(
                "SKIP protein parity: no golden file at {path}\n  \
                 run: python tests/pull/parity/export_protein_reference.py"
            );
            return None;
        }
    };
    match parse(&text) {
        Ok(j) => Some(j),
        Err(e) => {
            eprintln!("SKIP protein parity: golden file is not readable JSON: {e}");
            None
        }
    }
}

/// Absolute-or-relative closeness. Distances and energies in this model are O(1)
/// to O(100), so a bare relative test would treat a 1e-13 force as a failure when
/// both engines effectively printed zero.
fn close(a: f64, b: f64, rel: f64, what: &str) {
    if a.is_nan() || b.is_nan() {
        assert!(
            a.is_nan() && b.is_nan(),
            "{what}: engine {a} vs reference {b} - NaN must match NaN"
        );
        return;
    }
    let scale = a.abs().max(b.abs()).max(1e-12);
    assert!(
        (a - b).abs() / scale < rel,
        "{what}: engine {a} vs reference {b} (rel {:.2e})",
        (a - b).abs() / scale
    );
}

fn close_slice(a: &[f64], b: &[f64], rel: f64, what: &str) {
    assert_eq!(a.len(), b.len(), "{what}: engine has {} values, reference {}", a.len(), b.len());
    for (i, (x, y)) in a.iter().zip(b.iter()).enumerate() {
        close(*x, *y, rel, &format!("{what}[{i}]"));
    }
}

fn fvec(j: &Json, key: &str) -> Vec<f64> {
    let arr = j
        .get(key)
        .unwrap_or_else(|| panic!("fixture has no {key}"))
        .as_arr()
        .unwrap_or_else(|| panic!("fixture {key} is not an array"))
        .to_vec();
    arr.iter()
        .map(|v| match v {
            Json::Num(n) => *n,
            // The exporter writes null for the one undefined value in the model -
            // contacts-remaining on a contact-free trace. A real number there
            // would be the engine inventing a measurement.
            Json::Null => f64::NAN,
            other => panic!("fixture {key} element is not a number: {other:?}"),
        })
        .collect()
}

fn ivec(j: &Json, key: &str) -> Vec<i64> {
    j.get(key)
        .unwrap_or_else(|| panic!("fixture has no {key}"))
        .as_arr()
        .unwrap_or_else(|| panic!("fixture {key} is not an array"))
        .to_vec()
        .iter()
        .map(|v| v.as_f64().unwrap_or_else(|| panic!("fixture {key} element {v:?} is not a number")) as i64)
        .collect()
}

fn fnum(j: &Json, key: &str) -> f64 {
    match j.get(key) {
        Some(Json::Num(n)) => *n,
        Some(Json::Null) => f64::NAN,
        Some(other) => panic!("fixture {key} is not a number: {other:?}"),
        None => panic!("fixture has no {key}"),
    }
}

/// A trajectory is a list of step samples; the fixture stores them as JSON arrays.
fn run_config(run: &Json) -> PullConfig {
    let c = run.get("config").expect("run config");
    PullConfig {
        speed: fnum(c, "speed"),
        spring_k: fnum(c, "spring_k"),
        n_steps: fnum(c, "n_steps") as usize,
        dt: fnum(c, "dt"),
        temperature: fnum(c, "temperature"),
        friction: fnum(c, "friction"),
        seed: 1,
        lj_10_12: false,
        anchor: None,
        pull: None,
        // The reference's "extension" is the raw end-to-end distance, so nothing
        // is subtracted and the fixture compares extension_A directly.
        extension0_a: None,
        calibration: None,
    }
}

// ---CONSTANTS AND MODEL GEOMETRY---

#[test]
fn constants_agree_with_reference() {
    let Some(g) = golden() else { return };
    let c = g.get("constants").expect("constants");
    let pairs = [
        ("BOND_K", BOND_K),
        ("ANGLE_K", ANGLE_K),
        ("CONTACT_CUTOFF", CONTACT_CUTOFF),
        ("NONNATIVE_SIGMA", NONNATIVE_SIGMA),
        ("ANCHOR_K", ANCHOR_K),
    ];
    for (key, mine) in pairs {
        assert_eq!(mine, fnum(c, key), "constant {key}");
    }
    assert_eq!(fnum(c, "SEQ_SEP") as usize, SEQ_SEP, "constant SEQ_SEP");
}

/// The contact map and the native geometry the Hamiltonian reads, for one case.
///
/// `ci`/`cj` are indices and `native_pairs` is a packed key, so both are compared
/// exactly: a contact list is not a floating-point quantity, and an off-by-one in
/// the sequence-separation rule shows up here rather than as a mysterious energy.
fn check_model(m: &GoModel, want: &Json, what: &str) {
    assert_eq!(m.n, fnum(want, "n") as usize, "{what}: n");
    close_slice(&m.bond0, &fvec(want, "bond0"), 1e-12, &format!("{what}: bond0"));
    close_slice(&m.angle0, &fvec(want, "angle0"), 1e-12, &format!("{what}: angle0"));
    close_slice(&m.dihedral0, &fvec(want, "dihedral0"), 1e-12, &format!("{what}: dihedral0"));
    let ci = ivec(want, "ci");
    let cj = ivec(want, "cj");
    assert_eq!(m.ci.len(), ci.len(), "{what}: contact count");
    for k in 0..ci.len() {
        assert_eq!(m.ci[k] as i64, ci[k], "{what}: ci[{k}]");
        assert_eq!(m.cj[k] as i64, cj[k], "{what}: cj[{k}]");
    }
    close_slice(&m.contact0, &fvec(want, "contact0"), 1e-12, &format!("{what}: contact0"));
    let packed: Vec<i64> = m.native_pairs.iter().map(|&p| p as i64).collect();
    let want_packed: Vec<i64> = fvec(want, "native_pairs").iter().map(|v| *v as i64).collect();
    assert_eq!(
        packed, want_packed,
        "{what}: the packed (i<<32|j) list is the non-native scan's membership test"
    );
    assert_eq!(m.min_seq_sep as i64, fnum(want, "min_seq_sep") as i64, "{what}: min_seq_sep");
    assert_eq!(m.max_seq_sep as i64, fnum(want, "max_seq_sep") as i64, "{what}: max_seq_sep");
    // The packed form must agree with the index form, or `is_native` lies.
    for k in 0..m.ci.len() {
        assert!(m.is_native(m.ci[k], m.cj[k]), "{what}: (ci,cj) must be native");
        assert!(!m.is_native(m.cj[k], m.ci[k]), "{what}: reversed pairs are not stored");
    }
}

fn name_of(c: &Json) -> String {
    c.get("name").unwrap().as_str().unwrap().to_string()
}

#[test]
fn model_geometry_agrees_for_every_synthetic_trace() {
    let Some(g) = golden() else { return };
    for c in g.get("synthetic").unwrap().as_arr().unwrap() {
        let name = name_of(c);
        let coords = fvec(c, "coords");
        check_model(&build_model(&coords, false).unwrap(), c.get("model").unwrap(), &name);
    }
}

#[test]
fn model_geometry_agrees_for_every_real_structure() {
    let Some(g) = golden() else { return };
    for c in g.get("pdb").unwrap().as_arr().unwrap() {
        let name = name_of(c);
        let coords = fvec(c.get("structure").unwrap(), "coords");
        check_model(&build_model(&coords, false).unwrap(), c.get("model").unwrap(), &name);
    }
}
// ---STATIC ENERGY AND FORCE---

/// Native-state energy and force for both contact forms.
///
/// The dihedral gradient is a central difference that perturbs the buffer it is
/// given (`energy_and_force` takes `&mut`), so each call here gets a private copy
/// exactly as the exporter does, and contacts-remaining is read from the pristine
/// geometry.
fn check_static(coords: &[f64], want: &Json, what: &str) {
    let m = build_model(coords, false).unwrap();
    let ml = build_model(coords, true).unwrap();

    let mut x = coords.to_vec();
    let (e, f) = energy_and_force(&mut x, &m);
    close(e, fnum(want, "energy"), 1e-9, &format!("{what}: native energy (lj12-6)"));
    close_slice(&f, &fvec(want, "force"), 1e-9, &format!("{what}: native force (lj12-6)"));

    let mut x = coords.to_vec();
    let (e10, f10) = energy_and_force(&mut x, &ml);
    close(e10, fnum(want, "energy_lj10_12"), 1e-9, &format!("{what}: native energy (lj10-12)"));
    close_slice(&f10, &fvec(want, "force_lj10_12"), 1e-9, &format!("{what}: native force (lj10-12)"));

    // The native state is intact by definition - unless the trace has no contacts
    // at all, which the reference reports as NaN and the fixture writes as null.
    close(
        contacts_remaining(coords, &m),
        fnum(want, "contacts_remaining"),
        1e-12,
        &format!("{what}: contacts at the native state"),
    );

    // Fixture-independent sanity bound on the native residual force.
    //
    // Bonds, angles, dihedrals and native contacts are each at their minimum in the
    // native geometry, but the native state is *not* an exact stationary point of the
    // full Hamiltonian: the non-native excluded-volume term eps*(sigma/r)^12
    // (sigma = 4 A, PROTOCOL.md) still pushes on every non-contact pair inside the
    // 12 A cutoff. Its force is 12*sigma^12/r^13, i.e. 3.7e-4 eps/A at 8 A and
    // ~1.5e-2 at 6 A - the scale actually observed (1e-4 to 1e-3 on real structures).
    // The reference has the identical residual, which is why the parity checks above
    // pass to 1e-9. The bound below therefore guards against a *broken* term (an
    // order-of-magnitude-larger force), not against this physical residual.
    let worst = f.iter().fold(0.0f64, |acc, a| acc.max(a.abs()));
    assert!(
        worst < 2e-2,
        "{what}: native residual force {worst:.3e} eps/A exceeds what the non-native \
         excluded-volume term can produce - a bonded or contact term is likely wrong"
    );
    // The buffer's sub-ulp drift must stay sub-ulp: it is the reason the exporter
    // reads contacts after the energy, and it must never reach a real coordinate.
    let drift = x
        .iter()
        .zip(coords.iter())
        .fold(0.0f64, |acc, (a, b)| acc.max((a - b).abs()));
    assert!(drift < 1e-9, "{what}: the central difference disturbed coordinates by {drift:.3e}");
}

#[test]
fn static_energy_and_force_agree_for_synthetic_traces() {
    let Some(g) = golden() else { return };
    let cases = g.get("synthetic").unwrap().as_arr().unwrap();
    assert_eq!(cases.len(), 4, "four synthetic traces expected");
    for c in cases {
        let name = name_of(c);
        let coords = fvec(c, "coords");
        check_static(&coords, c.get("static").unwrap(), &name);
        let n = coords.len() / 3;
        let mut acc = 0.0;
        for k in 0..3 {
            let d = coords[(n - 1) * 3 + k] - coords[k];
            acc += d * d;
        }
        close(acc.sqrt(), fnum(c, "end_to_end_A"), 1e-12, &format!("{name}: end-to-end"));
    }
}

#[test]
fn static_energy_and_force_agree_for_real_structures() {
    let Some(g) = golden() else { return };
    for c in g.get("pdb").unwrap().as_arr().unwrap() {
        let name = name_of(c);
        let coords = fvec(c.get("structure").unwrap(), "coords");
        check_static(&coords, c.get("static").unwrap(), &name);
    }
}

#[test]
fn a_contact_free_trace_reports_undefined_contacts_not_zero() {
    let Some(g) = golden() else { return };
    // `sheet10` and `straight6` have no native contacts. `pull.py:76` returns NaN,
    // never 0.0, and the difference is the whole point: 0.0 reads as "the structure
    // unfolded completely", NaN reads as "this model has no contacts to unfold".
    let found = g
        .get("synthetic")
        .unwrap()
        .as_arr()
        .unwrap()
        .into_iter()
        .filter(|c| c.get("model").unwrap().get("ci").unwrap().as_arr().unwrap().is_empty())
        .collect::<Vec<_>>();
    assert!(!found.is_empty(), "the fixture must include a contact-free trace");
    for c in found {
        let name = name_of(c);
        let coords = fvec(c, "coords");
        let m = build_model(&coords, false).unwrap();
        assert!(contacts_remaining(&coords, &m).is_nan(), "{name}: must be NaN");
        // The fixture's null and the engine's NaN are the same statement.
        assert!(fnum(c.get("static").unwrap(), "contacts_remaining").is_nan(), "{name}: fixture null");
    }
}

// ---PEAK STATISTICS, ON THEIR OWN---

/// `pull.py:62-72` in isolation: `smooth5`, median, std and the argmax tie-break
/// folded together. Mixing that into a simulation mismatch hides which of the four
/// broke, so these cases carry no physics at all.
#[test]
fn peak_rule_agrees_on_synthetic_force_traces() {
    let Some(g) = golden() else { return };
    let cases = g.get("peaks").unwrap().as_arr().unwrap();
    assert_eq!(cases.len(), 6, "six peak fixtures expected");
    for c in cases {
        let name = name_of(c);
        let f = fvec(c, "force");
        // `np.convolve(force, ones(5)/5, mode="same")` returns max(5, len) samples,
        // so for a trace shorter than the kernel numpy hands back a *longer* array
        // than `smooth5` computes. The engine cannot reach that: `simulate` refuses
        // n_steps < 5, so `peaks` only ever sees a trace at least as long as the
        // window, and the short case is about the early return, not the shape.
        if f.len() >= 5 {
            close_slice(&smooth5(&f), &fvec(c, "smooth5"), 1e-12, &format!("{name}: smooth5"));
        }
        let hits = peaks(&f);
        let want: Vec<i64> = hits.iter().map(|i| *i as i64).collect();
        assert_eq!(want, ivec(c, "peaks"), "{name}: peak indices");
        assert_eq!(hits.len(), fnum(c, "n_peaks") as usize, "{name}: n_peaks");
        close(peak_force(&f), fnum(c, "peak_force"), 1e-12, &format!("{name}: peak_force"));
        let (pf, np, step) = peak_summary(&f);
        close(pf, fnum(c, "peak_force"), 1e-12, &format!("{name}: peak_summary force"));
        assert_eq!(np, fnum(c, "n_peaks") as usize, "{name}: peak_summary count");
        assert_eq!(
            step,
            fnum(c, "peak_step") as usize,
            "{name}: a tie between equal peaks must resolve to the earliest index, \
             the numpy.argmax convention the exporter pins"
        );
    }
    // The too-short case is the reference's own early return; the flat case is the
    // one where the zero-padded edges turn a constant trace into a peak. Both are
    // properties of the rule that must be reproduced, not "fixed".
    let short = name_index(&cases, "too_short");
    assert_eq!(ivec(&cases[short], "peaks"), Vec::<i64>::new(), "a 3-sample trace has no peaks");
    assert_eq!(fnum(&cases[short], "n_peaks"), 0.0);
    let flat = name_index(&cases, "flat5");
    assert_eq!(
        ivec(&cases[flat], "peaks"),
        vec![2],
        "np.convolve's zero padding makes the middle of a flat trace its own local \
         maximum, so the reference reports a peak at 2. An engine that normalises \
         the window by the samples present would report none, and would disagree."
    );
    assert_eq!(fnum(&cases[flat], "peak_force"), 2.0, "the peak value is the raw trace value");
    // Equal-height peaks resolve to the earliest, which argmax_first guarantees.
    let twin = name_index(&cases, "twin_equal_peaks");
    assert_eq!(ivec(&cases[twin], "peaks"), vec![10, 25], "both bumps are peaks");
    assert_eq!(fnum(&cases[twin], "peak_step"), 10.0, "a tie takes the earlier index");
    // ...and when the later bump is larger, the marker follows the larger one.
    let uneq = name_index(&cases, "two_unequal_peaks");
    assert_eq!(ivec(&cases[uneq], "peaks"), vec![8, 20]);
    assert_eq!(fnum(&cases[uneq], "peak_step"), 20.0, "the marker sits on the larger peak");
}

fn name_index(cases: &[Json], want: &str) -> usize {
    cases
        .iter()
        .position(|c| c.get("name").and_then(|n| n.as_str()) == Some(want))
        .unwrap_or_else(|| panic!("no peak fixture named {want}"))
}


// ---TRAJECTORIES---

/// Every recorded quantity of one run, in one place, so the zero-temperature tier
/// and the injected-noise tier cannot quietly test different subsets.
///
/// Tolerances: these are 100-240 velocity-Verlet Langevin steps on a stiff Gō
/// potential. With the noise supplied by the fixture (or T = 0, where the draw is
/// multiplied by exactly zero) the two engines share every arithmetic step, so any
/// divergence is pure floating-point ordering and grows with the step count rather
/// than with the force magnitudes: 1e-9 on the traces, 1e-7 on the final
/// coordinates. Peak indices are integers and are compared exactly, because a
/// marker one sample off is a difference a reader can see on the plot.
fn check_run(run: &Json, coords: &[f64], noise: Option<&[f64]>, what: &str) -> PullResult {
    let cfg = run_config(run);
    let m = build_model(coords, cfg.lj_10_12).unwrap();
    let res = match noise {
        Some(n) => simulate_with_injected_noise(coords, &m, &cfg, n),
        None => pull_engine::protein::simulate(coords, &m, &cfg),
    }
    .unwrap_or_else(|e| panic!("{what}: the engine refused the fixture run: {e}"));

    assert_eq!(res.n_residues, m.n, "{what}: residue count");
    close_slice(&res.extension_a, &fvec(run, "extension_A"), 1e-9, &format!("{what}: extension"));
    close_slice(&res.force_reduced, &fvec(run, "force_reduced"), 1e-9, &format!("{what}: force"));
    close(res.peak_force_reduced, fnum(run, "peak_force_reduced"), 1e-9, &format!("{what}: peak force"));
    assert_eq!(res.n_force_peaks, fnum(run, "n_force_peaks") as usize, "{what}: peak count");
    assert_eq!(
        res.peak_step, fnum(run, "peak_step") as usize,
        "{what}: the peak marker must sit on the same sample in both engines"
    );
    let mine: Vec<i64> = peaks(&res.force_reduced).iter().map(|i| *i as i64).collect();
    assert_eq!(mine, ivec(run, "peaks"), "{what}: every peak index");
    close(
        res.native_contacts_remaining,
        fnum(run, "native_contacts_remaining"),
        1e-12,
        &format!("{what}: contacts remaining"),
    );
    close(res.energy_final, fnum(run, "energy_final"), 1e-9, &format!("{what}: final energy"));
    close_slice(&res.final_coords, &fvec(run, "final_coords"), 1e-7, &format!("{what}: final coords"));

    // `finish` reports its peak statistics through `peak_summary`; re-deriving them
    // from the engine's own trace proves the result fields and the summary function
    // cannot drift apart, which is the reason they were folded into one pass.
    let (pf, np, ps) = peak_summary(&res.force_reduced);
    assert_eq!((np, ps), (res.n_force_peaks, res.peak_step), "{what}: peak_summary vs result fields");
    close(pf, res.peak_force_reduced, 1e-12, &format!("{what}: peak_summary vs result force"));
    res
}

#[test]
fn zero_temperature_trajectories_agree_for_synthetic_traces() {
    let Some(g) = golden() else { return };
    let cases = g.get("synthetic").unwrap().as_arr().unwrap();
    assert_eq!(cases.len(), 4, "four synthetic traces expected");
    for c in cases {
        let name = name_of(c);
        let coords = fvec(c, "coords");
        let runs = c.get("runs").unwrap().as_arr().unwrap();
        let run = &runs[0];
        assert_eq!(run.get("label").unwrap().as_str(), Some("zero_temperature"));
        check_run(run, &coords, None, &format!("{name}/zero_temperature"));
    }
}

#[test]
fn injected_noise_trajectories_agree_for_synthetic_traces() {
    let Some(g) = golden() else { return };
    let cases = g.get("synthetic").unwrap().as_arr().unwrap();
    for c in cases {
        let name = name_of(c);
        let coords = fvec(c, "coords");
        let runs = c.get("runs").unwrap().as_arr().unwrap();
        assert_eq!(runs.len(), 2, "{name}: a zero-temperature and an injected-noise run");
        let run = &runs[1];
        assert_eq!(run.get("label").unwrap().as_str(), Some("injected_noise"));
        let noise = fvec(c, "noise");
        let n = fnum(c.get("model").unwrap(), "n") as usize;
        let steps = fnum(run.get("config").unwrap(), "n_steps") as usize;
        assert_eq!(
            noise.len(),
            steps * n * 3,
            "{name}: the fixture noise must be exactly the draws the reference consumed"
        );
        check_run(run, &coords, Some(&noise), &format!("{name}/injected_noise"));
    }
}

// ---TIER 2: PDB PARSING---

/// The Rust parser's choices, written down and checked. There is no Python PDB
/// parser to agree with, so "parity" here means the exporter applied the same
/// column arithmetic independently and recorded what was selected.
fn check_structure(case: &Json, text: &str, what: &str) -> Structure {
    let want = case.get("structure").unwrap();
    // `chain_requested` is null for the automatic pick, which is `None` here; a
    // chain letter means the caller asked for that chain specifically.
    let requested: Option<char> = case
        .get("chain_requested")
        .and_then(|v| v.as_str())
        .and_then(|s| s.chars().next());
    let window: Option<(i64, i64)> = case
        .get("window_requested")
        .and_then(|v| v.as_arr())
        .map(|a| (a[0].as_f64().unwrap() as i64, a[1].as_f64().unwrap() as i64));

    let got = parse_pdb(text, requested, window)
        .unwrap_or_else(|e| panic!("{what}: the engine refused to parse the fixture PDB: {e}"));

    assert_eq!(got.label, want.get("label").unwrap().as_str().unwrap(), "{what}: label");
    assert_eq!(
        got.chain,
        want.get("chain").unwrap().as_str().unwrap().chars().next().unwrap(),
        "{what}: selected chain"
    );
    assert_eq!(got.n() as i64, fnum(want, "n") as i64, "{what}: residue count");
    assert_eq!(
        got.residues.iter().map(|v| *v as i64).collect::<Vec<i64>>(),
        ivec(want, "residues"),
        "{what}: PDB residue numbers, in trace order, including any gap"
    );
    assert_eq!(
        got.sequence(),
        want.get("codes").unwrap().as_str().unwrap(),
        "{what}: one-letter codes, X where unmapped"
    );
    // Coordinates come off the same columns and are parsed from the same decimal
    // strings by both implementations, so exact equality is the right demand here
    // rather than a tolerance.
    let want_coords = fvec(want, "coords");
    assert_eq!(got.coords.len(), want_coords.len(), "{what}: coordinate count");
    for (i, (a, b)) in got.coords.iter().zip(want_coords.iter()).enumerate() {
        assert!(a == b, "{what}: Ca coordinate {i} differs: engine {a} vs fixture {b}");
    }
    let want_notes: Vec<&str> = want
        .get("notes")
        .unwrap()
        .as_arr()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap())
        .collect();
    assert_eq!(
        got.notes.len(),
        want_notes.len(),
        "{what}: provenance notes - engine {:?} vs fixture {:?}",
        got.notes,
        want_notes
    );
    for (mine, theirs) in got.notes.iter().zip(want_notes.iter()) {
        // The two implementations word each note independently; the count, the
        // order and the numbers inside are what carry the information, so that is
        // what is compared rather than the prose.
        assert_eq!(
            mine.chars().filter(|c| c.is_ascii_digit()).collect::<String>(),
            theirs.chars().filter(|c| c.is_ascii_digit()).collect::<String>(),
            "{what}: note counts differ\n  engine: {mine}\n  fixture: {theirs}"
        );
    }
    assert_eq!(
        fnum(want, "n_chains_seen") as usize,
        got.notes
            .iter()
            .filter(|n| n.contains("modelled the largest"))
            .count()
            .max(1)
            .min(usize::MAX),
        "{what}: multi-chain note presence (informational)"
    );
    // A gap in the numbering must be reported, not silently bonded across.
    let gaps = got.residues.windows(2).filter(|w| w[1] - w[0] != 1).count();
    assert_eq!(gaps, fnum(want, "n_gaps") as usize, "{what}: chain breaks");
    got
}

#[test]
fn pdb_parsing_agrees_for_real_structures() {
    let Some(g) = golden() else { return };
    let dir = concat!(env!("CARGO_MANIFEST_DIR"), "/../tests/pull/parity/fixtures");
    let mut ran = 0;
    for case in g.get("pdb").unwrap().as_arr().unwrap() {
        let name = name_of(case);
        // The domain-sliced case reuses its base file.
        let file = case
            .get("file")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .unwrap_or_else(|| format!("{}.pdb", base_name(&name)));
        let path = format!("{dir}/{file}");
        let text = std::fs::read_to_string(&path)
            .unwrap_or_else(|e| panic!("{name}: the fixture PDB is missing from {path}: {e}"));
        check_structure(case, &text, &name);
        ran += 1;
    }
    assert!(ran > 0, "the fixture has no PDB cases");
}

fn base_name(name: &str) -> String {
    match name.split_once('-') {
        Some((a, _)) => a.to_string(),
        None => name.to_string(),
    }
}


