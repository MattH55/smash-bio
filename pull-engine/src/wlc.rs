//! Inextensible Marko-Siggia worm-like chain, in physical units (pN, nm).
//!
//! Parity target: smash-sim/nucleic/src/nasim/wlc.py. The Marko-Siggia
//! interpolation
//!     F*Lp/kT = 1/(2(1 - x/Lc)^2) - 1/4 + x/Lc        (x/Lc = extension/contour)
//! is inverted for the extension at a given force by a fixed-count Newton solve
//! rather than a root bracket, so the result is identical on native and WASM
//! (no target-dependent solver tolerance).

/// kT in pN nm at an arbitrary temperature, anchored to KT_PN_NM_298.
#[inline]
#[allow(non_snake_case)] // kT is the physics symbol, not a camel-case identifier
pub fn kT_pn_nm(temperature_k: f64) -> f64 {
    crate::units::KT_PN_NM_298 * (temperature_k / 298.15)
}

/// Fraction of contour extended, x = extension / contour, for one force.
///
/// Newton on g(x) = 1/(4(1-x)^2) - 1/4 + x - y with y = F*Lp/kT, started near
/// the high-force asymptote x ~ 1 - 1/(2 sqrt(y)). 16 iterations, same as the
/// reference; x is clamped to (0, 0.999) so the singularity at x = 1 is never
/// evaluated.
pub fn extension_fraction(force_pn: f64, lp_nm: f64, temperature_k: f64) -> f64 {
    let y = lp_nm * force_pn.max(0.0) / kT_pn_nm(temperature_k);
    let mut x = (1.0 - 0.5 / y.max(1e-12).sqrt()).clamp(0.0, 0.98);
    for _ in 0..16 {
        let d = (1.0 - x).max(1e-8);
        let residual = 0.25 / (d * d) - 0.25 + x - y;
        let slope = 0.5 / (d * d * d) + 1.0;
        x = (x - residual / slope).clamp(0.0, 0.999);
    }
    x
}

/// End-to-end extension in nm at one force.
pub fn extension_nm(force_pn: f64, contour_nm: f64, lp_nm: f64, temperature_k: f64) -> f64 {
    extension_fraction(force_pn, lp_nm, temperature_k) * contour_nm
}

/// Cumulative stretching work W(F) = integral of x dF, sampled on `force`,
/// starting at the first sample.
///
/// Output length is `force.len() - 1`, and entry i is the integral through
/// force[i + 1]. That offset convention is copied from the reference
/// (wlc.py:30-41) because half_force reads its crossing index against it; a
/// "tidier" same-length array would shift every reported force by one sample.
pub fn integrated_work(force: &[f64], ext: &[f64]) -> Vec<f64> {
    let n = force.len().min(ext.len());
    let mut out = Vec::with_capacity(n.saturating_sub(1));
    let mut acc = 0.0f64;
    for i in 0..n.saturating_sub(1) {
        acc += (ext[i + 1] + ext[i]) * 0.5 * (force[i + 1] - force[i]);
        out.push(acc);
    }
    out
}

/// Evenly spaced inclusive range, matching numpy.linspace(a, b, n).
pub fn linspace(a: f64, b: f64, n: usize) -> Vec<f64> {
    if n == 0 {
        return Vec::new();
    }
    if n == 1 {
        return vec![a];
    }
    let mut v = Vec::with_capacity(n);
    let last = (n - 1) as f64;
    for i in 0..n {
        v.push(a + (b - a) * (i as f64 / last));
    }
    v
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::units::{SS_LP_NM, SS_RISE_NM};

    #[test]
    fn low_force_extension_is_small_and_monotonic() {
        let contour = 20.0 * SS_RISE_NM;
        let mut prev = -1.0;
        for i in 0..40 {
            let f = 0.1 * i as f64;
            let x = extension_nm(f, contour, SS_LP_NM, 298.15);
            assert!(x > prev, "{f} pN gave {x} after {prev}");
            assert!(x < contour);
            prev = x;
        }
    }

    #[test]
    fn high_force_approaches_but_never_reaches_contour() {
        let contour = 20.0 * SS_RISE_NM;
        // An inextensible chain cannot reach Lc. At 80 pN with Lp = 0.75 nm,
        // F*Lp/kT ~ 14.6, and the Marko-Siggia interpolation gives ~0.87 of
        // contour: a number to record, not a failure. The hard requirements are
        // monotonicity and the asymptote x ~ 1 - 1/(2 sqrt(y)).
        let mut prev = 0.0f64;
        for f in [10.0, 20.0, 40.0, 80.0, 160.0, 320.0] {
            let r = extension_fraction(f, SS_LP_NM, 298.15);
            assert!(r > prev && r < 1.0, "{f} pN gave ratio {r} after {prev}");
            prev = r;
        }
        let at80 = extension_nm(80.0, contour, SS_LP_NM, 298.15);
        assert!(at80 / contour > 0.85 && at80 / contour < 0.90, "ratio {}", at80 / contour);
        let y = SS_LP_NM * 80.0 / kT_pn_nm(298.15);
        let asymptote = 1.0 - 0.5 / y.sqrt();
        assert!((at80 / contour - asymptote).abs() < 0.02, "asymptote {asymptote}");
    }

    #[test]
    fn negative_force_clamps_to_zero_extension() {
        assert_eq!(extension_nm(-5.0, 10.0, SS_LP_NM, 298.15), 0.0);
    }

    #[test]
    fn inversion_round_trips_through_the_marko_siggia_force() {
        let lp = 0.75;
        let t = 298.15;
        for &f in &[1.0, 5.0, 20.0, 65.0] {
            let x = extension_fraction(f, lp, t);
            let back = (0.25 / (1.0 - x).powi(2) - 0.25 + x) * kT_pn_nm(t) / lp;
            assert!((back - f).abs() < 1e-6 * f.max(1.0), "{f} -> {back}");
        }
    }

    #[test]
    fn work_is_cumulative_and_offsets_by_one_sample() {
        let f = linspace(0.0, 10.0, 11);
        let e = vec![1.0; 11];
        let w = integrated_work(&f, &e);
        assert_eq!(w.len(), 10);
        assert!((w[0] - 1.0).abs() < 1e-12);
        assert!((w[9] - 10.0).abs() < 1e-12);
    }

    #[test]
    #[allow(non_snake_case)] // kT is the physics symbol
    fn kT_scales_linearly_with_temperature() {
        assert!((kT_pn_nm(596.30) - 2.0 * crate::units::KT_PN_NM_298).abs() < 1e-12);
    }
}
