//! Deterministic transcendental functions.
//!
//! `f64::ln`, `exp`, `acos` call the platform maths library: MSVC's CRT on a
//! Windows native build, Rust's bundled libm on wasm32. Their last-bit results
//! differ, which breaks Gate 5 (native and browser byte-identical). These
//! versions use only +, -, *, / and sqrt, which IEEE 754 rounds identically on
//! every target, so the result is a pure function of the input bits everywhere.
//! Accuracy is about 1 ulp, far below anything the models resolve. Written
//! from the textbook reductions (Cody & Waite argument reduction, atanh series
//! for log, Taylor series for exp; fdlibm's rational approximation for acos).

const LN2_HI: f64 = 6.931_471_803_691_238_164_90e-1;
const LN2_LO: f64 = 1.908_214_929_270_587_700_02e-10;
const LN2: f64 = std::f64::consts::LN_2;
const SQRT_HALF: f64 = std::f64::consts::FRAC_1_SQRT_2;
const PI: f64 = std::f64::consts::PI;
const FRAC_PI_2: f64 = std::f64::consts::FRAC_PI_2;

/// 1/(2k+1), k = 0..12: the atanh series of `ln`.
const LN_C: [f64; 13] = {
    let mut c = [0.0; 13];
    let mut k = 0;
    while k < 13 {
        c[k] = 1.0 / (2 * k + 1) as f64;
        k += 1;
    }
    c
};
/// 1/k!, k = 0..14: the Taylor series of `exp`.
const EXP_C: [f64; 15] = {
    let mut c = [0.0; 15];
    let mut f = 1.0;
    let mut k = 0;
    while k < 15 {
        if k > 0 {
            f *= k as f64;
        }
        c[k] = 1.0 / f;
        k += 1;
    }
    c
};

/// Natural logarithm.
pub fn ln(x: f64) -> f64 {
    if x.is_nan() || x < 0.0 {
        return f64::NAN;
    }
    if x == 0.0 {
        return f64::NEG_INFINITY;
    }
    if x.is_infinite() {
        return f64::INFINITY;
    }
    let mut bits = x.to_bits();
    let mut k: i64 = 0;
    if bits >> 52 == 0 {
        // subnormal: scale into the normal range
        bits = (x * 18014398509481984.0).to_bits(); // 2^54
        k -= 54;
    }
    k += ((bits >> 52) & 0x7ff) as i64 - 1023;
    let mut m = f64::from_bits((bits & 0x000f_ffff_ffff_ffff) | 0x3ff0_0000_0000_0000); // [1, 2)
    if m > 2.0 * SQRT_HALF {
        m *= 0.5;
        k += 1;
    }
    // m in [sqrt(1/2), sqrt(2)); ln m = 2 atanh(s), s = (m-1)/(m+1), |s| < 0.1716
    let f = m - 1.0;
    let s = f / (2.0 + f);
    let z = s * s;
    // 2(s + s^3/3 + ... + s^25/25); z^12 < 1.5e-18
    let mut p = 0.0;
    for c in LN_C.iter().rev() {
        p = p * z + c;
    }
    let kf = k as f64;
    kf * LN2_HI + (2.0 * s * p + kf * LN2_LO)
}

/// Exponential.
pub fn exp(x: f64) -> f64 {
    if x.is_nan() {
        return x;
    }
    if x > 709.782_712_893_384 {
        return f64::INFINITY;
    }
    if x < -745.133_219_101_941_1 {
        return 0.0;
    }
    // x = k ln2 + r, |r| <= ln2/2
    let kf = (x / LN2).round();
    let r = (x - kf * LN2_HI) - kf * LN2_LO;
    // Taylor to r^14: |r|^15/15! < 1e-19
    let mut p = 0.0;
    for c in EXP_C.iter().rev() {
        p = p * r + c;
    }
    scale2(p, kf as i64)
}

/// v * 2^k for k in the range exp needs, without libm's ldexp.
fn scale2(v: f64, k: i64) -> f64 {
    let pow2 = |e: i64| f64::from_bits(((e + 1023) as u64) << 52);
    if k > 1023 {
        v * pow2(1023) * pow2(k - 1023)
    } else if k < -1022 {
        v * pow2(-1022) * pow2(k + 1022).max(f64::MIN_POSITIVE) * if k + 1022 < -1022 { 0.0 } else { 1.0 }
    } else {
        v * pow2(k)
    }
}

// acos: the rational approximation of fdlibm e_acos.c (Sun Microsystems,
// 1993: "Permission to use, copy, modify, and distribute this software is
// freely granted, provided that this notice is preserved."). Algorithm and
// coefficients only; recorded in docs/pull/REPORT-pull.md licences.
const PIO2_HI: f64 = 1.570_796_326_794_896_558_00e+00;
const PIO2_LO: f64 = 6.123_233_995_736_766_035_87e-17;
const PS0: f64 = 1.666_666_666_666_666_574_15e-01;
const PS1: f64 = -3.255_658_186_224_009_154_05e-01;
const PS2: f64 = 2.012_125_321_348_629_258_81e-01;
const PS3: f64 = -4.005_553_450_067_941_140_27e-02;
const PS4: f64 = 7.915_349_942_898_145_321_76e-04;
const PS5: f64 = 3.479_331_075_960_211_675_70e-05;
const QS1: f64 = -2.403_394_911_734_414_218_78e+00;
const QS2: f64 = 2.020_945_760_233_505_694_71e+00;
const QS3: f64 = -6.882_839_716_054_532_930_30e-01;
const QS4: f64 = 7.703_815_055_590_193_527_91e-02;

#[inline]
fn acos_r(z: f64) -> f64 {
    let p = z * (PS0 + z * (PS1 + z * (PS2 + z * (PS3 + z * (PS4 + z * PS5)))));
    let q = 1.0 + z * (QS1 + z * (QS2 + z * (QS3 + z * QS4)));
    p / q
}

/// Arccosine, input clamped to [-1, 1].
pub fn acos(x: f64) -> f64 {
    if x.is_nan() {
        return x;
    }
    let x = x.clamp(-1.0, 1.0);
    if x == 1.0 {
        return 0.0;
    }
    if x == -1.0 {
        return 2.0 * PIO2_HI + 2.0 * PIO2_LO;
    }
    if x.abs() < 0.5 {
        return PIO2_HI - (x - (PIO2_LO - x * acos_r(x * x)));
    }
    if x < 0.0 {
        let z = (1.0 + x) * 0.5;
        let s = z.sqrt();
        let w = acos_r(z) * s - PIO2_LO;
        return 2.0 * (PIO2_HI - (s + w));
    }
    let z = (1.0 - x) * 0.5;
    let s = z.sqrt();
    let df = f64::from_bits(s.to_bits() & 0xffff_ffff_0000_0000);
    let c = (z - df * df) / (s + df);
    let w = acos_r(z) * s + c;
    2.0 * (df + w)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ulps(a: f64, b: f64) -> u64 {
        if a == b {
            return 0;
        }
        (a.to_bits() as i64 - b.to_bits() as i64).unsigned_abs()
    }

    #[test]
    fn ln_matches_std() {
        let mut x = 1e-300;
        while x < 1e300 {
            for m in [1.0, 1.37, 2.9, 7.123] {
                let v = x * m;
                assert!(ulps(ln(v), v.ln()) <= 2 || (ln(v) - v.ln()).abs() < 1e-15, "ln({v}) {} vs {}", ln(v), v.ln());
            }
            x *= 13.7;
        }
        assert_eq!(ln(1.0), 0.0);
        assert!(ln(-1.0).is_nan());
        assert!((ln(5e-324) - (5e-324f64).ln()).abs() < 1e-12);
    }

    #[test]
    fn exp_matches_std() {
        let mut x = -740.0;
        while x < 709.0 {
            let (a, b) = (exp(x), x.exp());
            assert!(ulps(a, b) <= 2 || ((a - b) / b).abs() < 1e-15, "exp({x}) {a} vs {b}");
            x += 0.731;
        }
        assert_eq!(exp(0.0), 1.0);
        assert_eq!(exp(-800.0), 0.0);
        assert!(exp(800.0).is_infinite());
    }

    #[test]
    fn acos_matches_std() {
        let mut x = -1.0;
        while x <= 1.0 {
            assert!(ulps(acos(x), x.acos()) <= 2 || (acos(x) - x.acos()).abs() < 1e-16, "acos({x}) {} vs {}", acos(x), x.acos());
            x += 0.0013;
        }
        assert_eq!(acos(1.0), 0.0);
        assert!((acos(-1.0) - PI).abs() < 1e-16);
    }
}
