//! Native timing of the production protein pull (`fast`), to size the browser run plan.
//! Usage: cargo run --release --example bench -- <pdb> <chain> <speed> <dt> [travel_fraction]
use pull_engine::fast::{find_unfolding_events, run, FastModel, Mode, RunConfig};
use pull_engine::protein::{build_model, parse_pdb};
use std::time::Instant;

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let pdb = std::fs::read_to_string(&a[1]).expect("pdb");
    let chain = a.get(2).and_then(|s| s.chars().next());
    let speed: f64 = a.get(3).map(|s| s.parse().unwrap()).unwrap_or(0.5);
    let dt: f64 = a.get(4).map(|s| s.parse().unwrap()).unwrap_or(0.005);
    let frac: f64 = a.get(5).map(|s| s.parse().unwrap()).unwrap_or(0.9);
    let s = parse_pdb(&pdb, chain, None).expect("parse");
    let n = s.n();
    let gm = build_model(&s.coords, false).unwrap();
    let fm = FastModel::new(&gm, None).unwrap();
    let d0 = {
        let (p, q) = (&s.coords[0..3], &s.coords[(n - 1) * 3..n * 3]);
        ((p[0] - q[0]).powi(2) + (p[1] - q[1]).powi(2) + (p[2] - q[2]).powi(2)).sqrt()
    };
    let travel = frac * (3.8 * (n as f64 - 1.0) - d0);
    let steps = (travel / (speed * dt)).ceil() as usize;
    let cfg = RunConfig {
        mode: Mode::ConstantVelocity { speed, spring_k: 0.1 },
        n_steps: steps, dt, temperature: 0.5, friction: 1.0, seed: 1,
        anchor: 0, pull: n - 1, sample_every: (steps / 2000).max(1), contact_every: 25, frame_every: 0,
    };
    let t = Instant::now();
    let r = run(&s.coords, &fm, &cfg).expect("run");
    let secs = t.elapsed().as_secs_f64();
    let ev = find_unfolding_events(&r.extension_a, &r.tension);
    let peak = r.tension.iter().cloned().fold(f64::MIN, f64::max);
    println!(
        "{} n={n} contacts={} speed={speed} dt={dt} steps={steps} -> {secs:.2}s ({:.2} us/step, {} NL rebuilds) ext {:.0}->{:.0} A (contour {:.0}) max tension {:.2} events {} contacts_left {:.2}",
        s.label, fm.n_contacts(), secs * 1e6 / steps as f64, r.nl_rebuilds,
        r.extension0_a, r.extension_a.last().unwrap(), 3.8 * (n as f64 - 1.0), peak, ev.len(), r.contacts_remaining
    );
    for e in ev.iter().take(8) {
        println!("   event at ext {:.0} A: tension {:.2}, drop {:.2}, rip {:?}", e.extension, e.force, e.drop, e.delta_extension.map(|d| (d * 10.0).round() / 10.0));
    }
}
