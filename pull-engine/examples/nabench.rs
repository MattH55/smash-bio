//! Native timing and sanity print of the nucleic engine (`nakin`).
use pull_engine::nakin::*;
use pull_engine::nucleic::Polymer;
use std::time::Instant;

fn main() {
    let sys = NaSystem {
        polymer: Polymer::Dna,
        construct: Construct::Hairpin,
        stem: "GAGTCCTGGATCCTGTCCGC".into(),
        loop_nt: 4,
        temperature_k: 296.15,
        na_mm: 200.0,
        mg_mm: 0.0,
        thermo: Thermo::Browser,
        trap_k_pn_nm: 0.3,
        handle_bp: 1600.0,
        handle_lp_nm: 50.0,
        handle_s_pn: 1000.0,
        ss_rise_nm: 0.59,
        ss_lp_nm: 0.75,
    };
    let l = Landscape::build(&sys).unwrap();
    println!("{}", l.summary_json(&sys));
    let fh = l.f_half().unwrap();
    for speed in [20.0, 100.0, 500.0] {
        let cfg = KinConfig {
            speed_nm_s: speed, f_end_pn: fh + 8.0, refold: true, clamp_pn: None, duration_s: 0.0,
            k0_per_s: 1e6, seed: 1, max_samples: 2000, max_events: 200_000_000,
        };
        let t = Instant::now();
        let r = kinetic(&l, &cfg).unwrap();
        let tr: Vec<String> = r.transitions.iter().take(6).map(|t| format!("{}{:.1}", if t.unfold { "U" } else { "R" }, t.force_pn)).collect();
        println!("speed {speed} nm/s: {:.2}s, {} events, transitions {:?}", t.elapsed().as_secs_f64(), r.events, tr);
    }
    let mut u = sys.clone();
    u.construct = Construct::Unzip;
    u.stem = "GCGTATTAGCCGATAATCGGCTAATACGCAT".repeat(60);
    let t = Instant::now();
    let lu = Landscape::build(&u).unwrap();
    let c = equilibrium_curve(&lu, 25.0, 400);
    println!("unzip {} bp: equilibrium curve {:.2}s, force range {:.1}-{:.1}", lu.n_bp, t.elapsed().as_secs_f64(),
        c.force_pn.iter().cloned().fold(f64::MAX, f64::min), c.force_pn.iter().cloned().fold(0.0, f64::max));
}
