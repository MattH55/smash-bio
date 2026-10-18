//! Deterministic PRNG. sfc64 seeded through SplitMix64.
//!
//! The whole engine is reproducible from `(seed, config)`: the reference
//! protocol in smash-sim/docs/PROTOCOL.md states results must carry a seed, and
//! the brief requires determinism on re-run. `rand` is not used, so the stream
//! is also stable across recompiles and identical on native and wasm targets
//! (no target-dependent float fast-math in the hot loop).

pub struct Rng {
    a: u64,
    b: u64,
    c: u64,
    d: u64,
    spare: Option<f64>,
}

fn splitmix64(x: &mut u64) -> u64 {
    *x = x.wrapping_add(0x9e3779b97f4a7c15);
    let mut z = *x;
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
    z ^ (z >> 31)
}

impl Rng {
    /// Seed any u64 (including 0) through SplitMix64, then discard 12 values.
    pub fn new(seed: u64) -> Rng {
        let mut s = seed;
        let mut r = Rng {
            a: splitmix64(&mut s),
            b: splitmix64(&mut s),
            c: splitmix64(&mut s),
            d: splitmix64(&mut s),
            spare: None,
        };
        for _ in 0..12 {
            r.next_u64();
        }
        r
    }

    #[inline]
    pub fn next_u64(&mut self) -> u64 {
        let t = self.a.wrapping_add(self.b);
        self.a = self.b ^ (self.b >> 26);
        self.b = self.c.wrapping_add(self.c << 2); // c << 2 kept in u64
        self.c = self.c.rotate_left(21).wrapping_add(t);
        self.d = self.d.wrapping_add(1);
        t.wrapping_add(self.d)
    }

    /// Uniform in [0,1) with 53 bits of randomness.
    #[inline]
    pub fn next_f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 * (1.0 / 9007199254740992.0)
    }

    /// Standard normal by polar Box-Muller. The log is `dmath::ln`, not the
    /// platform libm (MSVC and wasm libm differ in the last bit), so the stream
    /// is bit-identical on native and wasm.
    /// Both deviates of each accepted pair are used (the second is returned on
    /// the next call), halving the log calls.
    pub fn next_gaussian(&mut self) -> f64 {
        if let Some(g) = self.spare.take() {
            return g;
        }
        loop {
            let u = self.next_f64() * 2.0 - 1.0;
            let v = self.next_f64() * 2.0 - 1.0;
            let s = u * u + v * v;
            if s > 0.0 && s < 1.0 {
                let k = (-2.0 * crate::dmath::ln(s) / s).sqrt();
                self.spare = Some(v * k);
                return u * k;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn same_seed_same_stream() {
        let mut a = Rng::new(20261011);
        let mut b = Rng::new(20261011);
        for _ in 0..1000 {
            assert_eq!(a.next_u64(), b.next_u64());
        }
    }

    #[test]
    fn different_seeds_differ() {
        let mut a = Rng::new(1);
        let mut b = Rng::new(2);
        assert_ne!(a.next_u64(), b.next_u64());
    }

    #[test]
    fn gaussian_moments() {
        let mut r = Rng::new(7);
        let n = 200_000usize;
        let mut sum = 0.0f64;
        let mut sum2 = 0.0f64;
        for _ in 0..n {
            let x = r.next_gaussian();
            sum += x;
            sum2 += x * x;
        }
        let mean = sum / n as f64;
        let var = sum2 / n as f64 - mean * mean;
        assert!(mean.abs() < 0.02, "mean {}", mean);
        assert!((var - 1.0).abs() < 0.03, "var {}", var);
    }

    #[test]
    fn uniform_in_range() {
        let mut r = Rng::new(99);
        for _ in 0..100_000 {
            let x = r.next_f64();
            assert!(x >= 0.0 && x < 1.0);
        }
    }
}
