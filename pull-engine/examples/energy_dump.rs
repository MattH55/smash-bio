//! Gate X1 reference: engine energy and forces of the Cα Gō Hamiltonian at the
//! native structure and at 5 frames of a pulling trajectory.
//! Usage: cargo run --release --example energy_dump -- <pdb> <chain> > out.json
use pull_engine::fast::{forces, run, FastModel, Mode, NeighborList, RunConfig};
use pull_engine::json;
use pull_engine::protein::{build_model, parse_pdb};

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let pdb = std::fs::read_to_string(&a[1]).expect("pdb");
    let s = parse_pdb(&pdb, a.get(2).and_then(|c| c.chars().next()), None).expect("parse");
    let gm = build_model(&s.coords, false).unwrap();
    let fm = FastModel::new(&gm, None).unwrap();
    let n = s.n();
    let cfg = RunConfig {
        mode: Mode::ConstantVelocity { speed: 0.2, spring_k: 0.1 },
        n_steps: 100_000, dt: 0.01, temperature: 0.5, friction: 1.0, seed: 3,
        anchor: 0, pull: n - 1, sample_every: 1000, contact_every: 25, frame_every: 20_000,
    };
    let r = run(&s.coords, &fm, &cfg).unwrap();
    let mut confs: Vec<Vec<f64>> = vec![s.coords.clone()];
    for f in r.frames.iter().skip(1) {
        confs.push(f.iter().map(|v| *v as f64).collect());
    }
    let mut out = Vec::new();
    for c in &confs {
        let nl = NeighborList::new(c, &fm);
        let mut f = vec![0.0; c.len()];
        let e = forces(c, &fm, &nl, &mut f);
        let arr = |v: &[f64]| format!("[{}]", v.iter().map(|x| json::num(*x)).collect::<Vec<_>>().join(","));
        out.push(format!("{{\"coords\":{},\"energy\":{},\"force\":{}}}", arr(c), json::num(e), arr(&f)));
    }
    println!("{{\"label\":{},\"native\":{},\"confs\":[{}]}}", json::quote(&s.label), {
        let v: Vec<String> = s.coords.iter().map(|x| json::num(*x)).collect();
        format!("[{}]", v.join(","))
    }, out.join(","));
}
