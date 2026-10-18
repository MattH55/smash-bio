use pull_engine::dmath;
use std::hint::black_box;
use std::time::Instant;

fn main() {
    for (label, lo, hi) in [("mid", -0.4, 0.4), ("near -1", -0.999999, -0.99), ("near +1", 0.99, 0.999999)] {
        let xs: Vec<f64> = (0..1000).map(|i| lo + (hi - lo) * i as f64 / 999.0).collect();
        let reps = 20000;
        let t = Instant::now();
        let mut acc = 0.0;
        for _ in 0..reps {
            for x in &xs {
                acc += dmath::acos(black_box(*x));
            }
        }
        let d = t.elapsed().as_secs_f64() * 1e9 / (reps * xs.len()) as f64;
        let t = Instant::now();
        for _ in 0..reps {
            for x in &xs {
                acc += black_box(*x).acos();
            }
        }
        let s = t.elapsed().as_secs_f64() * 1e9 / (reps * xs.len()) as f64;
        println!("acos {label}: dmath {d:.1} ns, std {s:.1} ns ({acc:.0})");
    }
    let xs: Vec<f64> = (1..1001).map(|i| i as f64 / 1001.0).collect();
    let t = Instant::now();
    let mut acc = 0.0;
    for _ in 0..20000 {
        for x in &xs {
            acc += dmath::ln(black_box(*x));
        }
    }
    println!("ln dmath {:.1} ns ({acc:.0})", t.elapsed().as_secs_f64() * 1e9 / 2e7);
}
