//! Nucleic-acid pulling with an instrument: equilibrium force-extension,
//! constant-force hopping and base-pair-level kinetic Monte Carlo of a moving
//! optical trap (brief, Phase 3).
//!
//! # Model
//! * **States**: n = number of base pairs open from the base of the stem
//!   (the end attached to the handles), n = 0..N. For a hairpin, opening the last
//!   (closing) base pair dissolves the loop. One-dimensional unzipping
//!   coordinate, as in `nucleic::mean_open` and the reference `hairpin.py`.
//! * **Chemistry** (`Thermo::Browser`, the default): Watson-Crick stacks from the
//!   published ΔH/ΔS (`nucleic::DNA_NN` / `RNA_NN`) evaluated **at the measurement
//!   temperature**; monovalent salt as SantaLucia's per-phosphate term scaled
//!   with temperature; an approximate Mg²⁺ equivalence (flagged); and the
//!   **hairpin-loop initiation** ΔG°37/ΔH from the Nearest Neighbor Database
//!   (DNA: `dna_loop_dg/dh.txt`, RNA: Turner 2004 `turner_2004_loop_dg/dh.txt`).
//!   `Thermo::Reference` reproduces the reference pipeline's choices (37 °C tables,
//!   no loop term) for comparison.
//! * **Mechanics**: dsDNA handles as an extensible WLC, the trap as a harmonic
//!   spring, released single strand as a WLC with the reference's assumed
//!   0.59 nm/nt and 0.75 nm persistence length, and a 2 nm projection for the
//!   folded hairpin. Free energy at fixed trap position X is the Legendre form
//!   G(n, X) = G_chem(n) + F X - ∫₀^F X_n(F') dF'.
//! * **Kinetics**: nearest-neighbour hops n → n ± 1 with rate
//!   k0 · exp(-ΔG / 2kT) (detailed balance, symmetric split), Gillespie
//!   dynamics with the trap moving at constant speed (null events cap the trap
//!   displacement between rate updates). k0 is a single attempt frequency, an
//!   input: no fitted value exists in the reference (`kinetics.py`: "The attempt
//!   frequency is an argument. It is not fit"). Default 1e6 s⁻¹ (order of
//!   magnitude used for base-pair kinetics; editable, stated on the page).

use crate::dmath;
use crate::error::{EngineError, EngineResult};
use crate::json;
use crate::nucleic::{normalise, stem_delta_g, Polymer, StemThermo};
use crate::rng::Rng;
use crate::units::*;
use crate::wlc;

/// NNDB hairpin-loop initiation, loop sizes 3..=30: (size, ΔG°37 kcal/mol, ΔH kcal/mol).
/// DNA: rna.urmc.rochester.edu/NNDB/parameter_tables/dna/dna_loop_{dg,dh}.txt, HAIRPIN column.
pub const DNA_HAIRPIN_LOOP: [(usize, f64, f64); 28] = [
    (3, 3.4, -0.6), (4, 3.4, -2.3), (5, 3.5, -12.1), (6, 4.2, -16.7), (7, 4.2, -13.6), (8, 4.2, -14.1),
    (9, 4.3, -14.1), (10, 4.4, -14.1), (11, 4.5, -14.1), (12, 4.6, -14.1), (13, 4.7, -14.1), (14, 4.8, -14.1),
    (15, 5.0, -14.1), (16, 5.1, -14.1), (17, 5.2, -14.1), (18, 5.3, -14.1), (19, 5.4, -14.1), (20, 5.5, -14.1),
    (21, 5.6, -14.1), (22, 5.7, -14.1), (23, 5.8, -14.1), (24, 5.9, -14.1), (25, 6.0, -14.1), (26, 6.1, -14.1),
    (27, 6.2, -14.1), (28, 6.3, -14.1), (29, 6.4, -14.1), (30, 6.5, -14.1),
];
/// RNA: NNDB Turner 2004 (RNAstructure tables) `turner_2004_loop_{dg,dh}.txt`, HAIRPIN column.
pub const RNA_HAIRPIN_LOOP: [(usize, f64, f64); 28] = [
    (3, 5.4, 1.3), (4, 5.6, 4.8), (5, 5.7, 3.6), (6, 5.4, -2.9), (7, 6.0, 1.3), (8, 5.5, -2.9),
    (9, 6.4, 5.0), (10, 6.5, 5.0), (11, 6.6, 5.0), (12, 6.7, 5.0), (13, 6.8, 5.0), (14, 6.9, 5.0),
    (15, 6.9, 5.0), (16, 7.0, 5.0), (17, 7.1, 5.0), (18, 7.1, 5.0), (19, 7.2, 5.0), (20, 7.2, 5.0),
    (21, 7.3, 5.0), (22, 7.3, 5.0), (23, 7.4, 5.0), (24, 7.4, 5.0), (25, 7.5, 5.0), (26, 7.5, 5.0),
    (27, 7.5, 5.0), (28, 7.6, 5.0), (29, 7.6, 5.0), (30, 7.7, 5.0),
];
const R_KCAL: f64 = 1.98720425864083e-3;
/// Projection of a folded hairpin along the pull axis (helix diameter), nm.
pub const D_FOLD_NM: f64 = 2.0;

/// Hairpin-loop initiation ΔG(T) in kcal/mol: ΔH - T (ΔH - ΔG37)/310.15, i.e. the
/// tabulated ΔS held constant. Loops > 30 use NNDB's logarithmic extrapolation.
pub fn loop_initiation_kcal(polymer: Polymer, size: usize, temperature_k: f64) -> EngineResult<f64> {
    if size < 3 {
        return Err(EngineError::unsupported(format!("a hairpin loop of {size} nt is sterically impossible (minimum 3)")));
    }
    let t = match polymer {
        Polymer::Dna => &DNA_HAIRPIN_LOOP,
        Polymer::Rna => &RNA_HAIRPIN_LOOP,
    };
    let (dg37, dh, extra) = if size <= 30 {
        let (_, g, h) = t[size - 3];
        (g, h, 0.0)
    } else {
        let (_, g, h) = t[27];
        (g, h, 1.75 * R_KCAL * temperature_k * dmath::ln(size as f64 / 30.0))
    };
    let ds = (dh - dg37) / T_NN_K; // kcal/mol/K
    Ok(dh - temperature_k * ds + extra)
}

/// `stem_delta_g` for stems longer than its 512-nt guard: chunks overlapping by
/// one nucleotide, so every stack is counted once and the salt term still uses
/// N - 1 phosphates in total.
fn long_stem_delta_g(seq: &[u8], polymer: Polymer, na_molar: f64, temperature_k: f64) -> EngineResult<StemThermo> {
    let s: String = seq.iter().map(|b| *b as char).collect();
    if seq.len() <= 512 {
        return stem_delta_g(&s, polymer, na_molar, temperature_k);
    }
    let mut start = 0usize;
    let mut out: Option<StemThermo> = None;
    while start + 1 < seq.len() {
        let end = (start + 512).min(seq.len());
        let part = stem_delta_g(&s[start..end], polymer, na_molar, temperature_k)?;
        out = Some(match out {
            None => part,
            Some(mut acc) => {
                acc.dg_1m_kcal += part.dg_1m_kcal;
                acc.salt_correction_kcal += part.salt_correction_kcal;
                acc.dg_fold_kcal += part.dg_fold_kcal;
                acc.steps.extend(part.steps);
                acc
            }
        });
        start = end - 1;
    }
    let mut th = out.unwrap();
    th.sequence = s;
    th.n_bp = seq.len();
    Ok(th)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Construct {
    /// Single hairpin: stem of `n_bp` pairs closing a loop of `loop_nt`.
    Hairpin,
    /// Long duplex unzipped from one end: opening n bp releases 2n nt.
    Unzip,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Thermo {
    /// Stacks at the measurement temperature + loop initiation (browser default).
    Browser,
    /// Reference pipeline: stacks at 37 °C, no loop term (comparison only).
    Reference,
}

#[derive(Debug, Clone)]
pub struct NaSystem {
    pub polymer: Polymer,
    pub construct: Construct,
    /// 5'->3' stem strand from the base (the handle side) towards the loop.
    pub stem: String,
    pub loop_nt: usize,
    pub temperature_k: f64,
    pub na_mm: f64,
    pub mg_mm: f64,
    pub thermo: Thermo,
    // instrument
    pub trap_k_pn_nm: f64,
    pub handle_bp: f64,
    pub handle_lp_nm: f64,
    pub handle_s_pn: f64,
    pub ss_rise_nm: f64,
    pub ss_lp_nm: f64,
}

/// Precomputed energies and force tables.
#[derive(Debug, Clone)]
pub struct Landscape {
    pub n_bp: usize,
    /// G_chem(n), pN nm, n = 0..=N; G_chem(0) = 0.
    pub g_chem: Vec<f64>,
    /// Released single-stranded nucleotides per state.
    pub m_nt: Vec<f64>,
    /// Folded-hairpin projection per state, nm.
    pub d_nm: Vec<f64>,
    pub kt: f64,
    pub dg_fold_kcal: f64,
    pub dg_stacks_kcal: f64,
    pub salt_kcal: f64,
    pub loop_kcal: f64,
    pub na_eq_mm: f64,
    pub trap_k: f64,
    pub notes: Vec<String>,
    // force tables
    df: f64,
    a: Vec<f64>,
    ia: Vec<f64>,
    s1: Vec<f64>,
    is1: Vec<f64>,
}

const F_MAX: f64 = 100.0;
const DF: f64 = 0.01;

impl Landscape {
    pub fn build(sys: &NaSystem) -> EngineResult<Landscape> {
        let seq = normalise(&sys.stem);
        let n_bp = seq.len();
        if n_bp < 2 {
            return Err(EngineError::bad_value("stem", "a stem needs at least 2 base pairs"));
        }
        if n_bp > 2000 {
            return Err(EngineError::too_large(format!("{n_bp} bp; the equilibrium model is limited to 2,000")));
        }
        if !(sys.temperature_k > 250.0 && sys.temperature_k < 373.0) {
            return Err(EngineError::bad_value("temperature", "must be between 250 and 373 K"));
        }
        if !(sys.trap_k_pn_nm > 0.0) {
            return Err(EngineError::bad_value("trap_k", "trap stiffness must be positive"));
        }
        let mut notes = Vec::new();
        let na_eq = sys.na_mm + if sys.mg_mm > 0.0 {
            notes.push(format!(
                "Mg2+ ({} mM) is treated by an approximate monovalent equivalence ([Na+]eq = [Na+] + 120 sqrt([Mg2+]) in mM); results with Mg2+ are approximate",
                sys.mg_mm
            ));
            120.0 * sys.mg_mm.sqrt()
        } else {
            0.0
        };
        if na_eq <= 0.0 {
            return Err(EngineError::bad_value("salt", "monovalent salt must be positive"));
        }
        let t_chem = match sys.thermo {
            Thermo::Browser => sys.temperature_k,
            Thermo::Reference => T_NN_K,
        };
        let th = long_stem_delta_g(&seq, sys.polymer, na_eq / 1000.0, t_chem)?;
        // salt: reference uses the 37 C slope; the browser scales the (entropic) term with T
        let salt = match sys.thermo {
            Thermo::Browser => th.salt_correction_kcal * sys.temperature_k / T_NN_K,
            Thermo::Reference => th.salt_correction_kcal,
        };
        let loop_kcal = match (sys.construct, sys.thermo) {
            (Construct::Hairpin, Thermo::Browser) => loop_initiation_kcal(sys.polymer, sys.loop_nt, sys.temperature_k)?,
            (Construct::Hairpin, Thermo::Reference) => {
                notes.push("reference thermodynamics: stacks at 37 C and no loop-initiation term (comparison mode)".into());
                0.0
            }
            (Construct::Unzip, _) => 0.0,
        };
        let n_steps = th.steps.len().max(1);
        let salt_each = salt / n_steps as f64;
        let mut g_chem = vec![0.0f64; n_bp + 1];
        let mut acc = 0.0;
        for k in 1..=n_bp {
            if k <= th.steps.len() {
                acc += -(th.steps[k - 1].dg_kcal + salt_each) * KCAL_TO_PN_NM;
            }
            g_chem[k] = acc;
        }
        if sys.construct == Construct::Hairpin {
            // opening the closing pair releases the loop: the unfolded state no longer pays it
            g_chem[n_bp] -= loop_kcal * KCAL_TO_PN_NM;
        }
        let mut m_nt = vec![0.0f64; n_bp + 1];
        let mut d_nm = vec![0.0f64; n_bp + 1];
        for n in 0..=n_bp {
            m_nt[n] = 2.0 * n as f64;
            if sys.construct == Construct::Hairpin {
                if n == n_bp {
                    m_nt[n] += sys.loop_nt as f64;
                } else {
                    d_nm[n] = D_FOLD_NM;
                }
            }
        }
        let kt = wlc::kT_pn_nm(sys.temperature_k);
        // force tables
        let nf = (F_MAX / DF).round() as usize + 1;
        let lh = DS_RISE_NM * sys.handle_bp.max(0.0);
        let mut a = vec![0.0f64; nf];
        let mut s1 = vec![0.0f64; nf];
        for i in 0..nf {
            let f = i as f64 * DF;
            let xh = if lh > 0.0 {
                lh * (wlc::extension_fraction(f, sys.handle_lp_nm, sys.temperature_k) + f / sys.handle_s_pn)
            } else {
                0.0
            };
            a[i] = xh + f / sys.trap_k_pn_nm;
            s1[i] = sys.ss_rise_nm * wlc::extension_fraction(f, sys.ss_lp_nm, sys.temperature_k);
        }
        let cum = |y: &Vec<f64>| -> Vec<f64> {
            let mut out = vec![0.0f64; y.len()];
            for i in 1..y.len() {
                out[i] = out[i - 1] + 0.5 * (y[i] + y[i - 1]) * DF;
            }
            out
        };
        let ia = cum(&a);
        let is1 = cum(&s1);
        Ok(Landscape {
            n_bp,
            g_chem,
            m_nt,
            d_nm,
            kt,
            dg_fold_kcal: th.dg_1m_kcal + salt + loop_kcal,
            dg_stacks_kcal: th.dg_1m_kcal,
            salt_kcal: salt,
            loop_kcal,
            na_eq_mm: na_eq,
            trap_k: sys.trap_k_pn_nm,
            notes,
            df: DF,
            a,
            ia,
            s1,
            is1,
        })
    }

    #[inline]
    fn interp(&self, y: &[f64], f: f64) -> f64 {
        let u = (f / self.df).clamp(0.0, (y.len() - 1) as f64);
        let i = (u.floor() as usize).min(y.len() - 2);
        let w = u - i as f64;
        y[i] * (1.0 - w) + y[i + 1] * w
    }

    /// Total extension (trap displacement) of state n at force f, nm.
    #[inline]
    pub fn x_total(&self, n: usize, f: f64) -> f64 {
        self.interp(&self.a, f) + self.m_nt[n] * self.interp(&self.s1, f) + self.d_nm[n]
    }
    /// Molecular extension of the released strand + folded projection at force f, nm.
    #[inline]
    pub fn x_molecule(&self, n: usize, f: f64) -> f64 {
        self.m_nt[n] * self.interp(&self.s1, f) + self.d_nm[n]
    }

    /// Force at trap position `x` in state n (bisection on the monotone x_total).
    pub fn force_at(&self, n: usize, x: f64) -> f64 {
        if x <= self.x_total(n, 0.0) {
            return 0.0;
        }
        let (mut lo, mut hi) = (0.0f64, F_MAX);
        if self.x_total(n, hi) <= x {
            return F_MAX;
        }
        for _ in 0..40 {
            let mid = 0.5 * (lo + hi);
            if self.x_total(n, mid) < x {
                lo = mid;
            } else {
                hi = mid;
            }
            if hi - lo < 1e-6 {
                break;
            }
        }
        0.5 * (lo + hi)
    }

    /// G(n, X) at fixed trap position, pN nm, and the force in that state.
    pub fn g_at(&self, n: usize, x: f64) -> (f64, f64) {
        let f = self.force_at(n, x);
        let mech = f * x - (self.interp(&self.ia, f) + self.m_nt[n] * self.interp(&self.is1, f) + self.d_nm[n] * f);
        (self.g_chem[n] + mech, f)
    }

    /// Constant-force ensemble: G_F(n) = G_chem(n) - ∫ x_molecule dF (handles cancel), pN nm.
    pub fn g_force(&self, n: usize, f: f64) -> f64 {
        self.g_chem[n] - (self.m_nt[n] * self.interp(&self.is1, f) + self.d_nm[n] * f)
    }

    /// Probability of each state at constant force.
    pub fn populations(&self, f: f64) -> Vec<f64> {
        let g: Vec<f64> = (0..=self.n_bp).map(|n| self.g_force(n, f)).collect();
        let gmin = g.iter().cloned().fold(f64::INFINITY, f64::min);
        let w: Vec<f64> = g.iter().map(|e| dmath::exp(-(e - gmin) / self.kt)).collect();
        let z: f64 = w.iter().sum();
        w.into_iter().map(|v| v / z).collect()
    }

    /// F½: force at which the fully open state holds half the population
    /// (bisection on 0.05..F_MAX). None if the stem is not stable at zero force
    /// or never opens in the window.
    pub fn f_half(&self) -> Option<f64> {
        let p_open = |f: f64| *self.populations(f).last().unwrap();
        if p_open(0.05) >= 0.5 {
            return None;
        }
        if p_open(F_MAX - 1.0) < 0.5 {
            return None;
        }
        let (mut lo, mut hi) = (0.05f64, F_MAX - 1.0);
        for _ in 0..60 {
            let mid = 0.5 * (lo + hi);
            if p_open(mid) < 0.5 {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        Some(0.5 * (lo + hi))
    }

    /// Local minima of G_F(n) other than the folded and fully open states, deeper
    /// than 1 kT relative to their lower neighbouring barrier: (n, ΔG in kT vs n=0).
    pub fn intermediates(&self, f: f64) -> Vec<(usize, f64)> {
        let g: Vec<f64> = (0..=self.n_bp).map(|n| self.g_force(n, f)).collect();
        let mut out = Vec::new();
        for n in 1..self.n_bp {
            if g[n] < g[n - 1] && g[n] <= g[n + 1] {
                // barrier depth: max to the left until a lower point, and to the right
                let left = g[..n].iter().cloned().fold(f64::MIN, f64::max);
                let right = g[n + 1..].iter().cloned().fold(f64::MIN, f64::max);
                if left.min(right) - g[n] > self.kt {
                    out.push((n, (g[n] - g[0]) / self.kt));
                }
            }
        }
        out
    }
}

/// Equilibrium force-extension at fixed trap positions (trap ensemble).
#[derive(Debug, Clone)]
pub struct EqCurve {
    pub trap_nm: Vec<f64>,
    pub force_pn: Vec<f64>,
    pub ext_nm: Vec<f64>,
    pub mean_open: Vec<f64>,
}

pub fn equilibrium_curve(l: &Landscape, f_end: f64, points: usize) -> EqCurve {
    let x0 = l.x_total(0, 0.5);
    let x1 = l.x_total(l.n_bp, f_end.min(F_MAX - 1.0));
    let mut out = EqCurve { trap_nm: vec![], force_pn: vec![], ext_nm: vec![], mean_open: vec![] };
    let pts = points.max(10);
    let mut gs = vec![0.0f64; l.n_bp + 1];
    let mut fs = vec![0.0f64; l.n_bp + 1];
    for k in 0..pts {
        let x = x0 + (x1 - x0) * k as f64 / (pts - 1) as f64;
        let mut gmin = f64::INFINITY;
        for n in 0..=l.n_bp {
            let (g, f) = l.g_at(n, x);
            gs[n] = g;
            fs[n] = f;
            gmin = gmin.min(g);
        }
        let mut z = 0.0;
        let mut fm = 0.0;
        let mut nm = 0.0;
        for n in 0..=l.n_bp {
            let w = dmath::exp(-(gs[n] - gmin) / l.kt);
            z += w;
            fm += w * fs[n];
            nm += w * n as f64;
        }
        let f = fm / z;
        out.trap_nm.push(x - x0);
        out.force_pn.push(f);
        // handles + molecule extension = trap displacement minus bead displacement F/k
        out.ext_nm.push((x - f / l.trap_k) - (x0 - 0.5 / l.trap_k));
        out.mean_open.push(nm / z);
    }
    out
}

/// One kinetic trajectory sample.
#[derive(Debug, Clone, Copy)]
pub struct Sample {
    pub t_s: f64,
    pub trap_nm: f64,
    pub force_pn: f64,
    pub n_open: usize,
}

/// A transition between the folded basin (n < N/2) and the fully open state.
#[derive(Debug, Clone, Copy)]
pub struct Transition {
    pub t_s: f64,
    /// true = unfolding (reached n = N), false = refolding (reached n = 0).
    pub unfold: bool,
    pub force_pn: f64,
    /// Molecular extension change at the transition force, nm.
    pub dx_nm: f64,
}

#[derive(Debug, Clone)]
pub struct KinConfig {
    /// Trap speed nm/s (ramp mode). Ignored in clamp mode.
    pub speed_nm_s: f64,
    /// Ramp until the force in the open state reaches this, pN; then reverse (if refold).
    pub f_end_pn: f64,
    pub refold: bool,
    /// Constant force (clamp mode) in pN; Some(...) selects clamp mode.
    pub clamp_pn: Option<f64>,
    /// Clamp duration, s.
    pub duration_s: f64,
    pub k0_per_s: f64,
    pub seed: u64,
    pub max_samples: usize,
    /// Safety cap on Monte Carlo events.
    pub max_events: u64,
}

#[derive(Debug, Clone)]
pub struct KinResult {
    pub samples: Vec<Sample>,
    pub transitions: Vec<Transition>,
    pub events: u64,
    pub truncated: bool,
    /// Index of the first refolding-phase sample (ramp mode), samples.len() if none.
    pub refold_start: usize,
}

/// Gillespie kinetic Monte Carlo of the unzipping coordinate with a moving trap
/// (ramp) or at constant force (clamp).
pub fn kinetic(l: &Landscape, cfg: &KinConfig) -> EngineResult<KinResult> {
    if !(cfg.k0_per_s > 0.0) {
        return Err(EngineError::bad_value("k0", "attempt frequency must be positive"));
    }
    let n_bp = l.n_bp;
    let mut rng = Rng::new(cfg.seed);
    let half = n_bp / 2;
    let mut res = KinResult { samples: vec![], transitions: vec![], events: 0, truncated: false, refold_start: 0 };
    let mut n = 0usize;
    let mut t = 0.0f64;
    let mut basin_open = false;

    if let Some(fc) = cfg.clamp_pn {
        // ---- constant force ----
        let g: Vec<f64> = (0..=n_bp).map(|k| l.g_force(k, fc)).collect();
        // start in the more populated basin, as a clamp experiment would after settling
        let pop = l.populations(fc);
        let p_open: f64 = pop[half.max(1)..].iter().sum();
        if p_open > 0.5 {
            n = n_bp;
            basin_open = true;
        }
        let dt_s = cfg.duration_s / cfg.max_samples.max(2) as f64;
        let mut next_sample = 0.0;
        let rate = |a: usize, b: usize| cfg.k0_per_s * dmath::exp(-(g[b] - g[a]) / (2.0 * l.kt));
        while t < cfg.duration_s {
            while next_sample <= t && res.samples.len() < cfg.max_samples {
                res.samples.push(Sample { t_s: next_sample, trap_nm: l.x_molecule(n, fc), force_pn: fc, n_open: n });
                next_sample += dt_s;
            }
            let kp = if n < n_bp { rate(n, n + 1) } else { 0.0 };
            let km = if n > 0 { rate(n, n - 1) } else { 0.0 };
            let r = kp + km;
            if r <= 0.0 {
                break;
            }
            t += -dmath::ln(1.0 - rng.next_f64()) / r;
            n = if rng.next_f64() * r < kp { n + 1 } else { n - 1 };
            res.events += 1;
            if !basin_open && n == n_bp {
                basin_open = true;
                res.transitions.push(Transition { t_s: t, unfold: true, force_pn: fc, dx_nm: l.x_molecule(n_bp, fc) - l.x_molecule(0, fc) });
            } else if basin_open && n == 0 {
                basin_open = false;
                res.transitions.push(Transition { t_s: t, unfold: false, force_pn: fc, dx_nm: l.x_molecule(n_bp, fc) - l.x_molecule(0, fc) });
            }
            if res.events >= cfg.max_events {
                res.truncated = true;
                break;
            }
        }
        res.refold_start = res.samples.len();
        return Ok(res);
    }

    // ---- moving trap ----
    if !(cfg.speed_nm_s > 0.0) {
        return Err(EngineError::bad_value("speed", "trap speed must be positive"));
    }
    let x_start = l.x_total(0, 0.5);
    let x_turn = l.x_total(n_bp, cfg.f_end_pn.clamp(1.0, F_MAX - 1.0));
    let span = x_turn - x_start;
    let total_t = if cfg.refold { 2.0 * span / cfg.speed_nm_s } else { span / cfg.speed_nm_s };
    let dt_s = total_t / cfg.max_samples.max(2) as f64;
    // The trap advances in ticks of DX_TICK nm (1/10 of the extension of one
    // released nucleotide at 10 pN) and is held fixed within a tick, so G(n, X)
    // is evaluated at most once per state per tick (cached by tick stamp).
    // Waiting times are exponential, so cutting a wait at a tick boundary and
    // redrawing is exact for piecewise-constant rates.
    const DX_TICK: f64 = 0.05;
    let t_tick = DX_TICK / cfg.speed_nm_s;
    let t_half = span / cfg.speed_nm_s;
    let mut next_sample = 0.0;
    res.refold_start = usize::MAX;
    let pos = |t: f64| -> (f64, bool) {
        if t <= t_half {
            (x_start + cfg.speed_nm_s * t, true)
        } else {
            (x_turn - cfg.speed_nm_s * (t - t_half), false)
        }
    };
    let mut gcache = vec![0.0f64; n_bp + 1];
    let mut fcache = vec![0.0f64; n_bp + 1];
    let mut stamp = vec![u64::MAX; n_bp + 1];
    let mut tick: u64 = 0;
    let mut x = pos(0.5 * t_tick).0;
    let mut g_of = |k: usize, tick: u64, x: f64, gcache: &mut Vec<f64>, fcache: &mut Vec<f64>| -> (f64, f64) {
        if stamp[k] != tick {
            let (g, f) = l.g_at(k, x);
            gcache[k] = g;
            fcache[k] = f;
            stamp[k] = tick;
        }
        (gcache[k], fcache[k])
    };
    while t < total_t {
        let t_next = (tick + 1) as f64 * t_tick;
        while next_sample <= t && res.samples.len() < cfg.max_samples {
            let (xs, fws) = pos(next_sample);
            if !fws && res.refold_start == usize::MAX {
                res.refold_start = res.samples.len();
            }
            let (_, f) = l.g_at(n, xs);
            res.samples.push(Sample { t_s: next_sample, trap_nm: xs - x_start, force_pn: f, n_open: n });
            next_sample += dt_s;
        }
        let (g0, f0) = g_of(n, tick, x, &mut gcache, &mut fcache);
        let kp = if n < n_bp { cfg.k0_per_s * dmath::exp(-(g_of(n + 1, tick, x, &mut gcache, &mut fcache).0 - g0) / (2.0 * l.kt)) } else { 0.0 };
        let km = if n > 0 { cfg.k0_per_s * dmath::exp(-(g_of(n - 1, tick, x, &mut gcache, &mut fcache).0 - g0) / (2.0 * l.kt)) } else { 0.0 };
        let r = kp + km;
        let tau = if r > 0.0 { -dmath::ln(1.0 - rng.next_f64()) / r } else { f64::INFINITY };
        if t + tau >= t_next {
            // no hop in this tick: move the trap
            t = t_next;
            tick += 1;
            x = pos((tick as f64 + 0.5) * t_tick).0;
            continue;
        }
        t += tau;
        n = if rng.next_f64() * r < kp { n + 1 } else { n - 1 };
        res.events += 1;
        // Report forces as an experiment reads them: the last force on the folded
        // branch before a rip, the last force on the open branch before a zip.
        let _ = f0;
        if !basin_open && n == n_bp {
            basin_open = true;
            let f = l.force_at(0, x);
            res.transitions.push(Transition { t_s: t, unfold: true, force_pn: f, dx_nm: l.x_molecule(n_bp, f) - l.x_molecule(0, f) });
        } else if basin_open && n == 0 {
            basin_open = false;
            let f = l.force_at(n_bp, x);
            res.transitions.push(Transition { t_s: t, unfold: false, force_pn: f, dx_nm: l.x_molecule(n_bp, f) - l.x_molecule(0, f) });
        }
        if res.events >= cfg.max_events {
            res.truncated = true;
            break;
        }
    }
    if res.refold_start == usize::MAX {
        res.refold_start = res.samples.len();
    }
    Ok(res)
}

/// Auto-detect a single perfect hairpin: the longest run of Watson-Crick pairs
/// between the 5' and 3' ends that leaves a loop of at least 3 nt. Returns
/// (stem 5'->3' from the base, loop length) or None.
pub fn detect_hairpin(sequence: &str) -> Option<(String, usize)> {
    let s = normalise(sequence);
    let comp = |b: u8| match b {
        b'A' => b'T',
        b'T' => b'A',
        b'C' => b'G',
        b'G' => b'C',
        _ => 0,
    };
    let len = s.len();
    let mut nbp = 0;
    while nbp < len / 2 && comp(s[nbp]) == s[len - 1 - nbp] && comp(s[nbp]) != 0 {
        nbp += 1;
    }
    while nbp > 0 && len - 2 * nbp < 3 {
        nbp -= 1;
    }
    if nbp < 3 {
        return None;
    }
    Some((s[..nbp].iter().map(|b| *b as char).collect(), len - 2 * nbp))
}

impl Landscape {
    pub fn summary_json(&self, sys: &NaSystem) -> String {
        let fh = self.f_half();
        let (dx, pops, inter) = match fh {
            Some(f) => (
                Some(self.x_molecule(self.n_bp, f) - self.x_molecule(0, f)),
                self.g_force_profile(f),
                self.intermediates(f),
            ),
            None => (None, self.g_force_profile(0.0), vec![]),
        };
        let inter_j: Vec<String> = inter.iter().map(|(n, g)| format!("{{\"n_open\":{n},\"dG_kT\":{}}}", json::num(*g))).collect();
        let notes: Vec<String> = self.notes.iter().map(|s| json::quote(s)).collect();
        format!(
            "{{\"n_bp\":{},\"loop_nt\":{},\"construct\":{},\"thermo\":{},\"dG_fold_kcal\":{},\"dG_stacks_kcal\":{},\"salt_kcal\":{},\"loop_kcal\":{},\"dG_unfold_kT\":{},\"na_eq_mM\":{},\"kT_pN_nm\":{},\"F_half_pN\":{},\"delta_x_at_F_half_nm\":{},\"delta_Lc_nm\":{},\"landscape_at_F_half_kT\":[{}],\"intermediates\":[{}],\"notes\":[{}]}}",
            self.n_bp,
            sys.loop_nt,
            json::quote(match sys.construct { Construct::Hairpin => "hairpin", Construct::Unzip => "unzip" }),
            json::quote(match sys.thermo { Thermo::Browser => "browser", Thermo::Reference => "reference" }),
            json::num(self.dg_fold_kcal),
            json::num(self.dg_stacks_kcal),
            json::num(self.salt_kcal),
            json::num(self.loop_kcal),
            json::num(self.g_chem[self.n_bp] / self.kt),
            json::num(self.na_eq_mm),
            json::num(self.kt),
            fh.map(json::num).unwrap_or_else(|| "null".into()),
            dx.map(json::num).unwrap_or_else(|| "null".into()),
            json::num(self.m_nt[self.n_bp] * sys.ss_rise_nm),
            pops.iter().map(|v| json::num(*v)).collect::<Vec<_>>().join(","),
            inter_j.join(","),
            notes.join(",")
        )
    }
    fn g_force_profile(&self, f: f64) -> Vec<f64> {
        let g0 = self.g_force(0, f);
        (0..=self.n_bp).map(|n| (self.g_force(n, f) - g0) / self.kt).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sys(stem: &str, loop_nt: usize, thermo: Thermo) -> NaSystem {
        NaSystem {
            polymer: Polymer::Dna,
            construct: Construct::Hairpin,
            stem: stem.into(),
            loop_nt,
            temperature_k: 296.15,
            na_mm: 200.0,
            mg_mm: 0.0,
            thermo,
            trap_k_pn_nm: 0.3,
            handle_bp: 1600.0,
            handle_lp_nm: 50.0,
            handle_s_pn: 1000.0,
            ss_rise_nm: SS_RISE_NM,
            ss_lp_nm: SS_LP_NM,
        }
    }

    #[test]
    fn loop_table_matches_nndb_at_37c() {
        assert!((loop_initiation_kcal(Polymer::Dna, 4, T_NN_K).unwrap() - 3.4).abs() < 1e-9);
        assert!((loop_initiation_kcal(Polymer::Rna, 6, T_NN_K).unwrap() - 5.4).abs() < 1e-9);
        assert!(loop_initiation_kcal(Polymer::Dna, 2, T_NN_K).is_err());
        // > 30 extrapolates upward
        assert!(loop_initiation_kcal(Polymer::Dna, 40, T_NN_K).unwrap() > 6.5);
    }

    #[test]
    fn loop_term_lowers_f_half() {
        let stem = "GAGTCCTGGATCCTGTCCGC";
        let with_loop = Landscape::build(&sys(stem, 4, Thermo::Browser)).unwrap().f_half().unwrap();
        let reference = Landscape::build(&sys(stem, 4, Thermo::Reference)).unwrap().f_half().unwrap();
        assert!(with_loop < reference, "loop {with_loop} vs reference {reference}");
        assert!(with_loop > 5.0 && with_loop < 30.0, "F1/2 {with_loop}");
    }

    #[test]
    fn force_at_inverts_x_total() {
        let l = Landscape::build(&sys("GCGCATATGCGC", 4, Thermo::Browser)).unwrap();
        for f in [1.0, 5.0, 12.5, 30.0] {
            let x = l.x_total(3, f);
            assert!((l.force_at(3, x) - f).abs() < 1e-4);
        }
    }

    #[test]
    fn kinetic_ramp_unfolds_and_refolds() {
        let l = Landscape::build(&sys("GAGTCCTGGATCCTGTCCGC", 4, Thermo::Browser)).unwrap();
        let fh = l.f_half().unwrap();
        let cfg = KinConfig {
            speed_nm_s: 100.0, f_end_pn: fh + 8.0, refold: true, clamp_pn: None, duration_s: 0.0,
            k0_per_s: 1e6, seed: 5, max_samples: 2000, max_events: 50_000_000,
        };
        let r = kinetic(&l, &cfg).unwrap();
        assert!(r.transitions.iter().any(|t| t.unfold), "no unfolding seen");
        assert!(r.transitions.iter().any(|t| !t.unfold), "no refolding seen");
        let rip = r.transitions.iter().find(|t| t.unfold).unwrap();
        assert!(rip.force_pn > fh - 6.0 && rip.force_pn < fh + 8.0, "rip {} vs F1/2 {fh}", rip.force_pn);
        let r2 = kinetic(&l, &cfg).unwrap();
        assert_eq!(r.events, r2.events, "same seed must give the same trajectory");
    }

    #[test]
    fn clamp_at_f_half_hops() {
        let l = Landscape::build(&sys("GCGCATATGCGC", 4, Thermo::Browser)).unwrap();
        let fh = l.f_half().unwrap();
        let cfg = KinConfig {
            speed_nm_s: 0.0, f_end_pn: 0.0, refold: false, clamp_pn: Some(fh), duration_s: 0.05,
            k0_per_s: 1e6, seed: 9, max_samples: 1000, max_events: 50_000_000,
        };
        let r = kinetic(&l, &cfg).unwrap();
        assert!(r.transitions.len() >= 2, "expected hopping at F1/2, got {} transitions", r.transitions.len());
    }

    #[test]
    fn detect_hairpin_finds_stem_and_loop() {
        let (stem, lp) = detect_hairpin("GCGCATATGCGCTTTTGCGCATATGCGC").unwrap();
        assert_eq!(stem, "GCGCATATGCGC");
        assert_eq!(lp, 4);
        assert!(detect_hairpin("AAAAAAAAAAAA").is_none());
    }

    #[test]
    fn unzip_equilibrium_is_monotone_in_open_pairs() {
        let mut s = sys("GCGTATTAGCCGATAATCGGCTAATACGC", 0, Thermo::Browser);
        s.construct = Construct::Unzip;
        let l = Landscape::build(&s).unwrap();
        let c = equilibrium_curve(&l, 25.0, 120);
        let first = c.mean_open[0];
        let last = *c.mean_open.last().unwrap();
        assert!(last > first + 10.0, "unzipping should open the duplex: {first} -> {last}");
    }
}
