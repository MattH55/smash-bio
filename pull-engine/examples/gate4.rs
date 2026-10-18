//! Gate 4 (docs/pull/VALIDATION.md): sequence-class benchmark against Woodside et al. 2006, 20R55/4T.
//! Prints one JSON object; the gate runner stores it in tests/pull/results/gate4.json.
use pull_engine::json;
use pull_engine::nakin::*;
use pull_engine::nucleic::Polymer;
use pull_engine::rng::Rng;

const SEED: u64 = 20261014;

/// Random 20-bp stem with exactly `gc` G/C positions.
fn stem(rng: &mut Rng, gc: usize) -> String {
    let mut is_gc: Vec<bool> = (0..20).map(|i| i < gc).collect();
    for i in (1..20).rev() {
        let j = (rng.next_u64() % (i as u64 + 1)) as usize;
        is_gc.swap(i, j);
    }
    is_gc
        .iter()
        .map(|g| {
            let coin = rng.next_f64() < 0.5;
            match (g, coin) {
                (true, true) => 'G',
                (true, false) => 'C',
                (false, true) => 'A',
                (false, false) => 'T',
            }
        })
        .collect()
}

fn system(stem: &str, thermo: Thermo) -> NaSystem {
    NaSystem {
        polymer: Polymer::Dna,
        construct: Construct::Hairpin,
        stem: stem.into(),
        loop_nt: 4,
        temperature_k: 296.15,
        na_mm: 200.0,
        mg_mm: 0.0,
        thermo,
        trap_k_pn_nm: 0.3,
        handle_bp: 1600.0,
        handle_lp_nm: 50.0,
        handle_s_pn: 1000.0,
        ss_rise_nm: 0.59,
        ss_lp_nm: 0.75,
    }
}

fn median(mut v: Vec<f64>) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n % 2 == 1 { v[n / 2] } else { 0.5 * (v[n / 2 - 1] + v[n / 2]) }
}

fn class(gc: usize, seed: u64, thermo: Thermo) -> (Vec<String>, Vec<f64>, Vec<f64>) {
    let mut rng = Rng::new(seed);
    let mut stems = vec![];
    let mut fh = vec![];
    let mut dx = vec![];
    for _ in 0..30 {
        let s = stem(&mut rng, gc);
        let l = Landscape::build(&system(&s, thermo)).unwrap();
        let f = l.f_half().unwrap_or(f64::NAN);
        fh.push(f);
        dx.push(l.x_molecule(l.n_bp, f) - l.x_molecule(0, f));
        stems.push(s);
    }
    (stems, fh, dx)
}

fn arr(v: &[f64]) -> String {
    format!("[{}]", v.iter().map(|x| json::num(*x)).collect::<Vec<_>>().join(","))
}

fn main() {
    let (stems, fh, dx) = class(11, SEED, Thermo::Browser);
    let (_, fh_ref, dx_ref) = class(11, SEED, Thermo::Reference);
    let mf = median(fh.clone());
    let mdx = median(dx.clone());
    let pass_f = (mf - 13.2).abs() <= 3.0;
    let pass_dx = (mdx - 18.0).abs() <= 0.2 * 18.0;
    let mut gc_medians = vec![];
    for (k, gc) in [0usize, 5, 11, 15, 20].iter().enumerate() {
        let (_, f, _) = class(*gc, SEED + 1 + k as u64, Thermo::Browser);
        gc_medians.push((*gc, median(f.into_iter().filter(|x| x.is_finite()).collect())));
    }
    let mono = gc_medians.windows(2).all(|w| w[1].1 > w[0].1);
    let st: Vec<String> = stems.iter().map(|s| json::quote(s)).collect();
    let gcj: Vec<String> = gc_medians.iter().map(|(g, f)| format!("{{\"gc_percent\":{},\"median_F_half_pN\":{}}}", g * 5, json::num(*f))).collect();
    println!(
        "{{\"gate\":\"4\",\"target\":{{\"F_half_pN\":13.2,\"delta_x_nm\":18}},\"stems\":[{}],\"F_half_pN\":{},\"delta_x_nm\":{},\"median_F_half_pN\":{},\"median_delta_x_nm\":{},\"pass_F_half\":{},\"pass_delta_x\":{},\"reference_thermo\":{{\"median_F_half_pN\":{},\"median_delta_x_nm\":{}}},\"gc_series\":[{}],\"gc_monotonic\":{},\"pass\":{}}}",
        st.join(","), arr(&fh), arr(&dx), json::num(mf), json::num(mdx), pass_f, pass_dx,
        json::num(median(fh_ref)), json::num(median(dx_ref)), gcj.join(","), mono, pass_f && pass_dx && mono
    );
}
