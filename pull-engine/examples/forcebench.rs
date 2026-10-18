//! Time `fast::forces` and its trig-heavy pieces on a folded and on an unfolded conformation.
use pull_engine::fast::{forces, run, FastModel, Mode, NeighborList, RunConfig};
use pull_engine::protein::{build_model, parse_pdb};
use std::hint::black_box;
use std::time::Instant;

fn dih(p0: [f64; 3], p1: [f64; 3], p2: [f64; 3], p3: [f64; 3]) -> (f64, f64) {
    let s = |a: [f64; 3], b: [f64; 3]| [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
    let d = |a: [f64; 3], b: [f64; 3]| a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    let b0 = s(p0, p1);
    let b1 = s(p2, p1);
    let b2 = s(p3, p2);
    let n = d(b1, b1).sqrt();
    let u = [b1[0] / n, b1[1] / n, b1[2] / n];
    let v = [b0[0] - d(b0, u) * u[0], b0[1] - d(b0, u) * u[1], b0[2] - d(b0, u) * u[2]];
    let w = [b2[0] - d(b2, u) * u[0], b2[1] - d(b2, u) * u[1], b2[2] - d(b2, u) * u[2]];
    let c = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
    (d(v, w), d(c, w))
}

fn profile(label: &str, x: &[f64], fm: &FastModel, phi0: &[f64]) {
    let nl = NeighborList::new(x, fm);
    let mut f = vec![0.0; x.len()];
    let reps = 20000;
    let t = Instant::now();
    for _ in 0..reps {
        black_box(forces(black_box(x), fm, &nl, &mut f));
    }
    let total = t.elapsed().as_secs_f64() * 1e6 / reps as f64;
    let n = x.len() / 3;
    let p = |i: usize| [x[3 * i], x[3 * i + 1], x[3 * i + 2]];
    // the (x, y) arguments atan2 sees, and the wrapped differences sin sees
    let args: Vec<(f64, f64)> = (0..n - 3).map(|i| dih(p(i), p(i + 1), p(i + 2), p(i + 3))).collect();
    let t = Instant::now();
    let mut acc = 0.0;
    for _ in 0..reps {
        for (xx, yy) in &args {
            acc += black_box(*yy).atan2(black_box(*xx));
        }
    }
    let t_atan2 = t.elapsed().as_secs_f64() * 1e6 / reps as f64;
    let phis: Vec<f64> = args.iter().map(|(xx, yy)| yy.atan2(*xx)).collect();
    let t = Instant::now();
    for _ in 0..reps {
        for (k, ph) in phis.iter().enumerate() {
            let d = black_box(ph - phi0[k]);
            acc += d.sin() + (3.0 * d).sin() + d.cos() + (3.0 * d).cos();
        }
    }
    let t_sincos = t.elapsed().as_secs_f64() * 1e6 / reps as f64;
    let coss: Vec<f64> = (0..n - 2)
        .map(|i| {
            let s = |a: [f64; 3], b: [f64; 3]| [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
            let r1 = s(p(i), p(i + 1));
            let r2 = s(p(i + 2), p(i + 1));
            let d = |a: [f64; 3], b: [f64; 3]| a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
            (d(r1, r2) / (d(r1, r1) * d(r2, r2)).sqrt()).clamp(-0.999999, 0.999999)
        })
        .collect();
    let t = Instant::now();
    for _ in 0..reps {
        for c in &coss {
            acc += pull_engine::dmath::acos(black_box(*c));
        }
    }
    let t_dacos = t.elapsed().as_secs_f64() * 1e6 / reps as f64;
    let t = Instant::now();
    for _ in 0..reps {
        for c in &coss {
            acc += black_box(*c).acos();
        }
    }
    let t_sacos = t.elapsed().as_secs_f64() * 1e6 / reps as f64;
    println!("{label}: acos x{} dmath {t_dacos:.2} us, std {t_sacos:.2} us; cos range {:.6}..{:.6}", coss.len(),
        coss.iter().cloned().fold(1.0, f64::min), coss.iter().cloned().fold(-1.0, f64::max));
    let small = args.iter().filter(|(xx, yy)| xx.abs() < 1e-6 && yy.abs() < 1e-6).count();
    let maxphi = phis.iter().map(|p| p.abs()).fold(0.0f64, f64::max);
    println!(
        "{label}: forces {total:.1} us | atan2 x{} {t_atan2:.1} us | sin/cos x{} {t_sincos:.1} us | tiny atan2 args {small} | max |phi| {maxphi:.2} (acc {:.1})",
        n - 3, 4 * (n - 3), acc / 1e9
    );
}

fn main() {
    let pdb = std::fs::read_to_string("fixtures/1TIT.pdb").unwrap();
    let s = parse_pdb(&pdb, Some('A'), None).unwrap();
    let gm = build_model(&s.coords, false).unwrap();
    let fm = FastModel::new(&gm, None).unwrap();
    profile("native   ", &s.coords, &fm, &gm.dihedral0);
    let n = s.n();
    let cfg = RunConfig {
        mode: Mode::ConstantVelocity { speed: 0.1, spring_k: 0.1 },
        n_steps: 175_000, dt: 0.01, temperature: 0.5, friction: 1.0, seed: 1,
        anchor: 0, pull: n - 1, sample_every: 1000, contact_every: 25, frame_every: 175_000,
    };
    let r = run(&s.coords, &fm, &cfg).unwrap();
    let last: Vec<f64> = r.frames.last().unwrap().iter().map(|v| *v as f64).collect();
    profile("unfolded ", &last, &fm, &gm.dihedral0);
}
