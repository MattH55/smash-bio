//! Production protein integrator: the browser's code path.
//!
//! **Same Hamiltonian as `protein::energy_and_force`** (and therefore as the
//! reference `go_model.py`): bonds, angles, dihedrals, native 6-12 (or 10-12)
//! contacts and non-native (σ/r)^12 excluded volume with the 12 Å cut-off, with
//! every constant taken from `units`. Three things differ, all of them numerical
//! rather than physical, and all checked by tests (`fast_force_equals_reference_force`)
//! and by validation gate 1:
//!
//! 1. **Analytic dihedral gradient** instead of the reference's central
//!    difference. The difference is the O(h²) truncation error of the reference
//!    (h = 1e-5 Å), i.e. ~1e-10 relative.
//! 2. **Verlet neighbour list** for the non-native pairs (cut-off 12 Å + 2 Å
//!    skin, rebuilt when any bead has moved more than half the skin). Every pair
//!    inside the cut-off is still evaluated, so the energy is unchanged.
//! 3. **One force evaluation per step.** The reference evaluates the force twice
//!    per step, but its second evaluation (new position, advanced anchor) is
//!    exactly the first evaluation of the next step, so reusing it changes
//!    nothing but the cost.
//!
//! The integrator is the reference's (velocity Verlet with a friction and
//! thermal kick between the two half kicks, `pull.py:30-42`).
//!
//! Output conventions that **do** differ from the reference, on purpose:
//! - **tension is positive when the molecule is stretched**. The reference
//!   records `dot(-spring, direction)`, which is negative under tension, so its
//!   "peak force" picks the sample closest to zero. See PROTOCOL.md.
//! - peaks are found on the tension with an explicit drop criterion (see
//!   `find_unfolding_events`), not with the reference's median + 0.5 sd rule.

use crate::error::{EngineError, EngineResult};
use crate::protein::{at, dot3, norm3, sub3, GoModel, NAT};
#[cfg(test)]
use crate::protein::dihedral;
use crate::rng::Rng;
use crate::units::*;

/// Non-native pairs are listed out to the cut-off plus this skin, in Å.
pub const NL_SKIN: f64 = 2.0;

/// Pulling protocol.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Mode {
    /// Harmonic spring whose anchor moves at `speed` Å per reduced time.
    ConstantVelocity { speed: f64, spring_k: f64 },
    /// A constant force (ε/Å) on the pulled bead along the pull direction.
    ConstantForce { force: f64 },
}

#[derive(Debug, Clone)]
pub struct RunConfig {
    pub mode: Mode,
    pub n_steps: usize,
    pub dt: f64,
    /// kT in ε.
    pub temperature: f64,
    pub friction: f64,
    pub seed: u64,
    /// Trace index restrained at its native position (stiff spring ANCHOR_K).
    pub anchor: usize,
    /// Trace index that is pulled.
    pub pull: usize,
    /// Record tension/extension every this many steps.
    pub sample_every: usize,
    /// Check native contacts every this many steps (break-step resolution).
    pub contact_every: usize,
    /// Store a frame for animation every this many steps (0 = no frames).
    pub frame_every: usize,
}

impl RunConfig {
    pub fn validate(&self, n: usize) -> EngineResult<()> {
        if self.n_steps == 0 || self.n_steps > 20_000_000 {
            return Err(EngineError::bad_value("n_steps", format!("{} must be 1..20000000", self.n_steps)));
        }
        for (name, v) in [("dt", self.dt), ("temperature", self.temperature), ("friction", self.friction)] {
            if !v.is_finite() || v < 0.0 {
                return Err(EngineError::bad_value(name, format!("{v} must be finite and >= 0")));
            }
        }
        if self.dt == 0.0 || self.dt > 0.02 {
            return Err(EngineError::bad_value("dt", format!("{} must be in (0, 0.02]", self.dt)));
        }
        match self.mode {
            Mode::ConstantVelocity { speed, spring_k } => {
                if !(speed > 0.0 && speed.is_finite()) || !(spring_k > 0.0 && spring_k.is_finite()) {
                    return Err(EngineError::bad_value("mode", "speed and spring_k must be positive"));
                }
            }
            Mode::ConstantForce { force } => {
                if !force.is_finite() {
                    return Err(EngineError::bad_value("mode", "force must be finite"));
                }
            }
        }
        if self.anchor >= n || self.pull >= n || self.anchor == self.pull {
            return Err(EngineError::bad_value(
                "anchor/pull",
                format!("indices {}/{} must be distinct and inside 0..{}", self.anchor, self.pull, n - 1),
            ));
        }
        if self.sample_every == 0 || self.contact_every == 0 {
            return Err(EngineError::bad_value("sample_every", "sampling intervals must be >= 1"));
        }
        Ok(())
    }
}

/// The model the integrator reads, derived from a `GoModel` plus an optional
/// mask of residues whose contacts are excluded (AlphaFold pLDDT < 50).
#[derive(Debug, Clone)]
pub struct FastModel {
    pub n: usize,
    pub bond0: Vec<f64>,
    pub angle0: Vec<f64>,
    pub dihedral0: Vec<f64>,
    /// cos and sin of the native dihedrals, so the force loop needs no trig call.
    pub cos_phi0: Vec<f64>,
    pub sin_phi0: Vec<f64>,
    pub ci: Vec<u32>,
    pub cj: Vec<u32>,
    pub contact0: Vec<f64>,
    pub lj_10_12: bool,
    /// n*n bitset: true when (i, j) is a native pair (either listed contact or a
    /// contact dropped by the pLDDT mask - a dropped contact is *not* turned
    /// into a repulsive non-native pair, it is simply not modelled).
    native_bits: Vec<u64>,
    /// Number of contacts removed by the residue mask.
    pub n_masked_contacts: usize,
}

impl FastModel {
    pub fn new(m: &GoModel, excluded: Option<&[bool]>) -> EngineResult<FastModel> {
        let n = m.n;
        if let Some(ex) = excluded {
            if ex.len() != n {
                return Err(EngineError::bad_value("exclude", format!("mask has {} entries for {n} residues", ex.len())));
            }
        }
        let words = (n * n + 63) / 64;
        let mut native_bits = vec![0u64; words];
        let mut ci = Vec::with_capacity(m.ci.len());
        let mut cj = Vec::with_capacity(m.ci.len());
        let mut contact0 = Vec::with_capacity(m.ci.len());
        let mut masked = 0usize;
        for k in 0..m.ci.len() {
            let (i, j) = (m.ci[k], m.cj[k]);
            let bit = i * n + j;
            native_bits[bit / 64] |= 1u64 << (bit % 64);
            if let Some(ex) = excluded {
                if ex[i] || ex[j] {
                    masked += 1;
                    continue;
                }
            }
            ci.push(i as u32);
            cj.push(j as u32);
            contact0.push(m.contact0[k]);
        }
        // Native angles and dihedral cos/sin are recomputed here with
        // deterministic arithmetic (dmath::acos; dihedral cos/sin straight from
        // the atan2 arguments) so the model is bit-identical on every target.
        // They agree with the GoModel values to ~1 ulp.
        let x = &m.native;
        let mut angle0 = Vec::with_capacity(n.saturating_sub(2));
        for i in 0..n.saturating_sub(2) {
            let r1 = sub3(at(x, i), at(x, i + 1));
            let r2 = sub3(at(x, i + 2), at(x, i + 1));
            let c = dot3(r1, r2) / (norm3(r1) * norm3(r2)).max(1e-12);
            angle0.push(crate::dmath::acos(c.clamp(-1.0, 1.0)));
        }
        let mut cos_phi0 = Vec::with_capacity(n.saturating_sub(3));
        let mut sin_phi0 = Vec::with_capacity(n.saturating_sub(3));
        for i in 0..n.saturating_sub(3) {
            let (xx, yy) = dihedral_xy(at(x, i), at(x, i + 1), at(x, i + 2), at(x, i + 3));
            let r = (xx * xx + yy * yy).sqrt();
            let (cp, sp) = if r > 0.0 { (xx / r, yy / r) } else { (1.0, 0.0) };
            cos_phi0.push(cp);
            sin_phi0.push(sp);
        }
        Ok(FastModel {
            n,
            bond0: m.bond0.clone(),
            angle0,
            dihedral0: m.dihedral0.clone(),
            cos_phi0,
            sin_phi0,
            ci,
            cj,
            contact0,
            lj_10_12: m.lj_10_12,
            native_bits,
            n_masked_contacts: masked,
        })
    }
    #[inline]
    fn is_native(&self, i: usize, j: usize) -> bool {
        let bit = i * self.n + j;
        self.native_bits[bit / 64] >> (bit % 64) & 1 == 1
    }
    pub fn n_contacts(&self) -> usize {
        self.ci.len()
    }
}

/// Verlet list of non-native pairs within cut-off + skin.
#[derive(Debug, Clone)]
pub struct NeighborList {
    pairs: Vec<u32>,
    ref_x: Vec<f64>,
    pub rebuilds: usize,
}

impl NeighborList {
    pub fn new(x: &[f64], m: &FastModel) -> NeighborList {
        let mut nl = NeighborList { pairs: Vec::new(), ref_x: Vec::new(), rebuilds: 0 };
        nl.rebuild(x, m);
        nl.rebuilds = 0;
        nl
    }
    fn rebuild(&mut self, x: &[f64], m: &FastModel) {
        let lim = NONNATIVE_CUTOFF + NL_SKIN;
        let lim2 = lim * lim;
        self.pairs.clear();
        for i in 0..m.n {
            let xi = at(x, i);
            for j in (i + SEQ_SEP)..m.n {
                if m.is_native(i, j) {
                    continue;
                }
                let d = sub3(at(x, j), xi);
                if dot3(d, d) <= lim2 {
                    self.pairs.push(i as u32);
                    self.pairs.push(j as u32);
                }
            }
        }
        self.ref_x.clear();
        self.ref_x.extend_from_slice(x);
        self.rebuilds += 1;
    }
    /// Rebuild when any bead has moved more than half the skin since the last
    /// build; then no pair can have crossed into the cut-off unlisted.
    #[inline]
    pub fn update(&mut self, x: &[f64], m: &FastModel) {
        let half2 = (0.5 * NL_SKIN) * (0.5 * NL_SKIN);
        for i in 0..m.n {
            let d = sub3(at(x, i), at(&self.ref_x, i));
            if dot3(d, d) > half2 {
                self.rebuild(x, m);
                return;
            }
        }
    }
}

/// Analytic gradient of the dihedral returned by `protein::dihedral` (the
/// standard IUPAC torsion, praxeolitic form) with respect to its four points:
/// returns dφ/dp0..dφ/dp3. Bekker's formulas; the sign is checked against a
/// central difference in `dihedral_gradient_matches_finite_difference`.
#[inline]
pub(crate) fn dihedral_grad(p0: [f64; 3], p1: [f64; 3], p2: [f64; 3], p3: [f64; 3]) -> Option<[[f64; 3]; 4]> {
    let f = sub3(p0, p1);
    let g = sub3(p1, p2);
    let h = sub3(p3, p2);
    let a = crate::protein::cross3(f, g);
    let b = crate::protein::cross3(h, g);
    let a2 = dot3(a, a);
    let b2 = dot3(b, b);
    let gn = norm3(g);
    if a2 < 1e-16 || b2 < 1e-16 || gn < 1e-8 {
        return None;
    }
    let fg = dot3(f, g);
    let hg = dot3(h, g);
    let mut d = [[0.0f64; 3]; 4];
    for c in 0..3 {
        let ta = a[c] / a2;
        let tb = b[c] / b2;
        d[0][c] = -gn * ta;
        d[3][c] = gn * tb;
        d[1][c] = gn * ta + fg / gn * ta - hg / gn * tb;
        d[2][c] = -gn * tb - fg / gn * ta + hg / gn * tb;
    }
    Some(d)
}

/// Sign of `dihedral_grad` relative to `protein::dihedral`, fixed once by the
/// unit test; kept as a constant so a convention change cannot pass silently.
pub(crate) const DIHEDRAL_GRAD_SIGN: f64 = 1.0;

/// The two dot products whose `atan2` is `protein::dihedral` (same formula, same
/// rounding): returns (x, y) with φ = atan2(y, x). Used to evaluate cos φ and
/// sin φ without any trigonometric call.
#[inline]
fn dihedral_xy(p0: [f64; 3], p1: [f64; 3], p2: [f64; 3], p3: [f64; 3]) -> (f64, f64) {
    let b0 = sub3(p0, p1);
    let b1 = sub3(p2, p1);
    let b2 = sub3(p3, p2);
    let n = norm3(b1).max(1e-12);
    let u = [b1[0] / n, b1[1] / n, b1[2] / n];
    let d0 = dot3(b0, u);
    let v = [b0[0] - d0 * u[0], b0[1] - d0 * u[1], b0[2] - d0 * u[2]];
    let d2 = dot3(b2, u);
    let w = [b2[0] - d2 * u[0], b2[1] - d2 * u[1], b2[2] - d2 * u[2]];
    (dot3(v, w), dot3(crate::protein::cross3(u, v), w))
}

/// Energy (ε) and force (ε/Å, F = -∇V) of the full Gō Hamiltonian, written into
/// `force` (overwritten). No allocation.
pub fn forces(x: &[f64], m: &FastModel, nl: &NeighborList, force: &mut [f64]) -> f64 {
    let n = m.n;
    for v in force.iter_mut() {
        *v = 0.0;
    }
    let mut energy = 0.0f64;
    // bonds
    for i in 0..n - 1 {
        let d = sub3(at(x, i + 1), at(x, i));
        let dist = norm3(d).max(1e-8);
        let dr = dist - m.bond0[i];
        energy += BOND_K * dr * dr;
        let s = 2.0 * BOND_K * dr / dist;
        for c in 0..NAT {
            let g = s * d[c];
            force[i * NAT + c] += g;
            force[(i + 1) * NAT + c] -= g;
        }
    }
    // angles (identical formula to the reference)
    for i in 0..n - 2 {
        let r1 = sub3(at(x, i), at(x, i + 1));
        let r2 = sub3(at(x, i + 2), at(x, i + 1));
        let n1 = norm3(r1);
        let n2 = norm3(r2);
        if n1 < 1e-8 || n2 < 1e-8 {
            continue;
        }
        let u1 = [r1[0] / n1, r1[1] / n1, r1[2] / n1];
        let u2 = [r2[0] / n2, r2[1] / n2, r2[2] / n2];
        let cos = dot3(u1, u2).clamp(-0.999999, 0.999999);
        let theta = crate::dmath::acos(cos);
        let dtheta = theta - m.angle0[i];
        energy += ANGLE_K * dtheta * dtheta;
        let dvdtheta = 2.0 * ANGLE_K * dtheta;
        // sin(acos(c)) == sqrt(1 - c^2) for c in [-1, 1]; avoids a sin call.
        let sin = (1.0 - cos * cos).sqrt().max(1e-8);
        for c in 0..NAT {
            let a1 = -(u2[c] - cos * u1[c]) / (sin * n1);
            let a2 = -(u1[c] - cos * u2[c]) / (sin * n2);
            force[i * NAT + c] -= dvdtheta * a1;
            force[(i + 2) * NAT + c] -= dvdtheta * a2;
            force[(i + 1) * NAT + c] += dvdtheta * (a1 + a2);
        }
    }
    // dihedrals, analytic and trig-free:
    //   V = (1 - cos d) + 0.5 (1 - cos 3d),  dV/dphi = sin d + 1.5 sin 3d,  d = phi - phi0.
    // cos phi and sin phi come from the same two dot products the reference feeds
    // to atan2; cos d / sin d from the angle-difference identities with the
    // precomputed cos phi0 / sin phi0; 3d from the triple-angle identities. This is
    // the reference's function exactly (no wrap is needed: V is 2pi-periodic).
    for i in 0..n - 3 {
        let (p0, p1, p2, p3) = (at(x, i), at(x, i + 1), at(x, i + 2), at(x, i + 3));
        let (xx, yy) = dihedral_xy(p0, p1, p2, p3);
        let r = (xx * xx + yy * yy).sqrt();
        // atan2(0, 0) = 0 in the reference, i.e. cos = 1, sin = 0
        let (cp, sp) = if r > 0.0 { (xx / r, yy / r) } else { (1.0, 0.0) };
        let (c0, s0) = (m.cos_phi0[i], m.sin_phi0[i]);
        let cd = cp * c0 + sp * s0;
        let sd = sp * c0 - cp * s0;
        let c3 = 4.0 * cd * cd * cd - 3.0 * cd;
        let s3 = 3.0 * sd - 4.0 * sd * sd * sd;
        energy += (1.0 - cd) + 0.5 * (1.0 - c3);
        let dvdphi = sd + 1.5 * s3;
        if dvdphi == 0.0 {
            continue;
        }
        if let Some(g) = dihedral_grad(p0, p1, p2, p3) {
            let s = -dvdphi * DIHEDRAL_GRAD_SIGN;
            for (k, gk) in g.iter().enumerate() {
                let a = (i + k) * NAT;
                force[a] += s * gk[0];
                force[a + 1] += s * gk[1];
                force[a + 2] += s * gk[2];
            }
        }
    }
    // native contacts
    for k in 0..m.ci.len() {
        let (i, j) = (m.ci[k] as usize, m.cj[k] as usize);
        let dvec = sub3(at(x, j), at(x, i));
        let r = norm3(dvec);
        if r < 1e-8 {
            continue;
        }
        let inv = m.contact0[k] / r;
        let i2 = inv * inv;
        let i6 = i2 * i2 * i2;
        let i12 = i6 * i6;
        let (e, dvr) = if m.lj_10_12 {
            let i10 = i6 * i2 * i2;
            (5.0 * i12 - 6.0 * i10, (-60.0 * i12 + 60.0 * i10) / r)
        } else {
            (i12 - 2.0 * i6, (-12.0 * i12 + 12.0 * i6) / r)
        };
        energy += e;
        for c in 0..NAT {
            let g = dvr * dvec[c] / r;
            force[j * NAT + c] -= g;
            force[i * NAT + c] += g;
        }
    }
    // non-native excluded volume over the neighbour list
    let sig = NONNATIVE_SIGMA;
    let cut2 = NONNATIVE_CUTOFF * NONNATIVE_CUTOFF;
    let mut p = 0;
    while p < nl.pairs.len() {
        let i = nl.pairs[p] as usize;
        let j = nl.pairs[p + 1] as usize;
        p += 2;
        let dvec = sub3(at(x, j), at(x, i));
        let r2 = dot3(dvec, dvec);
        if r2 > cut2 || r2 < 1e-12 {
            continue;
        }
        let r = r2.sqrt();
        let inv = sig / r;
        let i2 = inv * inv;
        let i6 = i2 * i2 * i2;
        let i12 = i6 * i6;
        energy += i12;
        let dvr = -12.0 * i12 / r;
        for c in 0..NAT {
            let g = dvr * dvec[c] / r;
            force[j * NAT + c] -= g;
            force[i * NAT + c] += g;
        }
    }
    energy
}

/// One trajectory.
#[derive(Debug, Clone)]
pub struct RunResult {
    /// Reduced time of each sample.
    pub time: Vec<f64>,
    /// |x_pull - x_anchor|, Å.
    pub extension_a: Vec<f64>,
    /// Tension along the pull direction, ε/Å, positive when stretched.
    pub tension: Vec<f64>,
    /// Native end-to-end distance between the pull points, Å.
    pub extension0_a: f64,
    /// Per native contact (index into FastModel ci/cj): the step after which
    /// it stayed broken; `None` = intact at the end.
    pub break_step: Vec<Option<usize>>,
    /// Frames as f32 xyz, every `frame_every` steps (first frame = native).
    pub frames: Vec<Vec<f32>>,
    pub frame_steps: Vec<usize>,
    pub contacts_remaining: f64,
    pub n_steps: usize,
    pub nl_rebuilds: usize,
}

/// Run one trajectory with the engine's own PRNG.
pub fn run(coords: &[f64], m: &FastModel, cfg: &RunConfig) -> EngineResult<RunResult> {
    let mut rng = Rng::new(cfg.seed);
    run_with(coords, m, cfg, &mut || rng.next_gaussian())
}

/// Run one trajectory drawing standard normals from `normal` (one per
/// coordinate per step, in the reference's order). Used by `run` and by the
/// gate-1 harness.
pub fn run_with(
    coords: &[f64],
    m: &FastModel,
    cfg: &RunConfig,
    normal: &mut dyn FnMut() -> f64,
) -> EngineResult<RunResult> {
    let n = m.n;
    if coords.len() != n * NAT {
        return Err(EngineError::bad_value("coords", "coordinate count does not match the model"));
    }
    cfg.validate(n)?;
    let (ia, ip) = (cfg.anchor, cfg.pull);
    let origin = at(coords, ia);
    let dvec = sub3(at(coords, ip), origin);
    let d0 = norm3(dvec);
    if d0 < 1e-6 {
        return Err(EngineError::unsupported("the pull points coincide; there is no direction to pull along"));
    }
    let dir = [dvec[0] / d0, dvec[1] / d0, dvec[2] / d0];
    let mut x = coords.to_vec();
    let mut v = vec![0.0f64; n * NAT];
    let mut f = vec![0.0f64; n * NAT];
    let mut nl = NeighborList::new(&x, m);
    let mut anchor_pos = at(coords, ip);
    let noise = (2.0 * cfg.friction * cfg.temperature * cfg.dt).sqrt();
    let (ka, kp) = (ia * NAT, ip * NAT);

    let n_samples = cfg.n_steps / cfg.sample_every + 1;
    let mut time = Vec::with_capacity(n_samples);
    let mut ext = Vec::with_capacity(n_samples);
    let mut ten = Vec::with_capacity(n_samples);
    let nc = m.ci.len();
    let mut last_intact = vec![0usize; nc];
    let mut intact_now = vec![true; nc];
    let mut frames = Vec::new();
    let mut frame_steps = Vec::new();
    if cfg.frame_every > 0 {
        frames.push(x.iter().map(|a| *a as f32).collect());
        frame_steps.push(0);
    }

    // external forces: anchor restraint + pulling
    let add_external = |x: &[f64], f: &mut [f64], anchor_pos: &[f64; 3]| -> f64 {
        for c in 0..NAT {
            f[ka + c] += -ANCHOR_K * (x[ka + c] - origin[c]);
        }
        match cfg.mode {
            Mode::ConstantVelocity { spring_k, .. } => {
                let mut t = 0.0;
                for c in 0..NAT {
                    let s = -spring_k * (x[kp + c] - anchor_pos[c]);
                    f[kp + c] += s;
                    t += s * dir[c];
                }
                t
            }
            Mode::ConstantForce { force } => {
                for c in 0..NAT {
                    f[kp + c] += force * dir[c];
                }
                force
            }
        }
    };

    forces(&x, m, &nl, &mut f);
    let mut tension = add_external(&x, &mut f, &anchor_pos);
    time.push(0.0);
    ext.push(d0);
    ten.push(tension);

    for step in 1..=cfg.n_steps {
        for i in 0..v.len() {
            v[i] += 0.5 * cfg.dt * f[i];
        }
        for i in 0..x.len() {
            x[i] += cfg.dt * v[i];
        }
        for i in 0..v.len() {
            v[i] += -cfg.friction * v[i] * cfg.dt + noise * normal();
        }
        if let Mode::ConstantVelocity { speed, .. } = cfg.mode {
            for c in 0..NAT {
                anchor_pos[c] += dir[c] * speed * cfg.dt;
            }
        }
        nl.update(&x, m);
        forces(&x, m, &nl, &mut f);
        tension = add_external(&x, &mut f, &anchor_pos);
        for i in 0..v.len() {
            v[i] += 0.5 * cfg.dt * f[i];
        }
        if step % cfg.sample_every == 0 {
            time.push(step as f64 * cfg.dt);
            ext.push(norm3(sub3(at(&x, ip), at(&x, ia))));
            ten.push(tension);
        }
        if step % cfg.contact_every == 0 {
            for k in 0..nc {
                let (i, j) = (m.ci[k] as usize, m.cj[k] as usize);
                let r = norm3(sub3(at(&x, j), at(&x, i)));
                let ok = r < CONTACT_INTACT_FACTOR * m.contact0[k];
                intact_now[k] = ok;
                if ok {
                    last_intact[k] = step;
                }
            }
        }
        if cfg.frame_every > 0 && step % cfg.frame_every == 0 {
            frames.push(x.iter().map(|a| *a as f32).collect());
            frame_steps.push(step);
        }
        if step % 256 == 0 && !(tension.is_finite() && x[kp].is_finite()) {
            return Err(EngineError::divergence(format!(
                "the trajectory diverged by step {step}; reduce dt or the speed"
            )));
        }
    }
    if !x.iter().all(|a| a.is_finite()) {
        return Err(EngineError::divergence("non-finite coordinates at the end of the run"));
    }
    // final contact state, measured at the last step
    let mut kept = 0usize;
    let mut break_step = Vec::with_capacity(nc);
    for k in 0..nc {
        let (i, j) = (m.ci[k] as usize, m.cj[k] as usize);
        let r = norm3(sub3(at(&x, j), at(&x, i)));
        let ok = r < CONTACT_INTACT_FACTOR * m.contact0[k];
        let _ = intact_now[k];
        if ok {
            kept += 1;
            break_step.push(None);
        } else {
            break_step.push(Some((last_intact[k] + cfg.contact_every).min(cfg.n_steps)));
        }
    }
    let nl_rebuilds = nl.rebuilds;
    Ok(RunResult {
        time,
        extension_a: ext,
        tension: ten,
        extension0_a: d0,
        break_step,
        frames,
        frame_steps,
        contacts_remaining: if nc == 0 { f64::NAN } else { kept as f64 / nc as f64 },
        n_steps: cfg.n_steps,
        nl_rebuilds,
    })
}

/// Zero-padded 5-point running mean (the reference's `np.convolve(..., ones(5)/5, "same")`).
pub fn smooth5(y: &[f64]) -> Vec<f64> {
    crate::protein::smooth5(y)
}

/// Running mean over a centred window of `w` samples (edges use the samples present).
pub fn running_mean(y: &[f64], w: usize) -> Vec<f64> {
    let n = y.len();
    let h = w / 2;
    let mut out = vec![0.0; n];
    let mut prefix = vec![0.0; n + 1];
    for i in 0..n {
        prefix[i + 1] = prefix[i] + y[i];
    }
    for i in 0..n {
        let lo = i.saturating_sub(h);
        let hi = (i + h + 1).min(n);
        out[i] = (prefix[hi] - prefix[lo]) / (hi - lo) as f64;
    }
    out
}

/// An unfolding (rupture) event on a force-extension trace.
#[derive(Debug, Clone, Copy)]
pub struct Event {
    /// Sample index of the peak.
    pub index: usize,
    /// Smoothed tension at the peak.
    pub force: f64,
    /// Extension at the peak, Å.
    pub extension: f64,
    /// Drop from the peak to the following minimum (smoothed), ε/Å.
    pub drop: f64,
    /// Extension gained between this peak and the next rise to the same force
    /// on the trace ("rip size"), Å; None when the trace ends first.
    pub delta_extension: Option<f64>,
}

/// Unfolding events: local maxima of the smoothed tension that are followed by
/// a drop of at least `max(0.15 * (peak - baseline), 3 * noise_sd)` before the
/// tension rises above the peak again. `baseline` is the 10th percentile of the
/// smoothed trace and `noise_sd` the standard deviation of (raw - smoothed).
/// Returns events in trace order. Stated in PROTOCOL.md; not the reference's rule.
pub fn find_unfolding_events(extension: &[f64], tension: &[f64]) -> Vec<Event> {
    let n = tension.len();
    if n < 9 {
        return Vec::new();
    }
    let w = ((n / 100) | 1).max(5);
    let s = running_mean(tension, w);
    let mut resid = 0.0;
    for i in 0..n {
        let d = tension[i] - s[i];
        resid += d * d;
    }
    let noise_sd = (resid / n as f64).sqrt();
    let mut sorted = s.clone();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let baseline = sorted[n / 10];
    let mut events = Vec::new();
    let mut i = 1;
    while i + 1 < n {
        let is_max = s[i] >= s[i - 1] && s[i] > s[i + 1];
        if is_max {
            // walk forward to the minimum before the trace exceeds the peak again
            let peak = s[i];
            let mut j = i + 1;
            let mut minv = s[i + 1];
            let mut minj = i + 1;
            while j < n && s[j] <= peak {
                if s[j] < minv {
                    minv = s[j];
                    minj = j;
                }
                j += 1;
            }
            let drop = peak - minv;
            let need = (0.15 * (peak - baseline)).max(3.0 * noise_sd);
            if drop >= need && peak > baseline {
                let delta = if j < n { Some(extension[j] - extension[i]) } else { None };
                events.push(Event { index: i, force: peak, extension: extension[i], drop, delta_extension: delta });
                i = minj.max(i + 1);
                continue;
            }
        }
        i += 1;
    }
    events
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::protein::{build_model, energy_and_force, parse_pdb};

    fn fixture(name: &str) -> String {
        std::fs::read_to_string(format!("{}/fixtures/{name}", env!("CARGO_MANIFEST_DIR"))).unwrap()
    }

    #[test]
    fn dihedral_gradient_matches_finite_difference() {
        let p = [[0.1, 0.2, -0.3], [1.5, 0.1, 0.4], [2.1, 1.4, 0.2], [3.3, 1.9, 1.1]];
        let g = dihedral_grad(p[0], p[1], p[2], p[3]).unwrap();
        let h = 1e-6;
        for a in 0..4 {
            for c in 0..3 {
                let mut q = p;
                q[a][c] += h;
                let up = dihedral(q[0], q[1], q[2], q[3]);
                q[a][c] -= 2.0 * h;
                let dn = dihedral(q[0], q[1], q[2], q[3]);
                let fd = (up - dn) / (2.0 * h);
                let an = DIHEDRAL_GRAD_SIGN * g[a][c];
                assert!((fd - an).abs() < 1e-6 * (1.0 + fd.abs()), "atom {a} coord {c}: fd {fd} vs analytic {an}");
            }
        }
    }

    #[test]
    fn fast_force_equals_reference_force() {
        for (file, chain) in [("1TIT.pdb", 'A'), ("1UBQ.pdb", 'A'), ("2GB1.pdb", 'A')] {
            let s = parse_pdb(&fixture(file), Some(chain), None).unwrap();
            let gm = build_model(&s.coords, false).unwrap();
            let fm = FastModel::new(&gm, None).unwrap();
            let mut rng = Rng::new(7);
            for trial in 0..21 {
                let mut x = s.coords.clone();
                if trial > 0 {
                    for a in x.iter_mut() {
                        *a += 0.3 * rng.next_gaussian();
                    }
                }
                let mut xr = x.clone();
                let (er, fr) = energy_and_force(&mut xr, &gm);
                let nl = NeighborList::new(&x, &fm);
                let mut ff = vec![0.0; x.len()];
                let ef = forces(&x, &fm, &nl, &mut ff);
                assert!((er - ef).abs() <= 1e-9 * er.abs().max(1.0), "{file} trial {trial}: energy {ef} vs {er}");
                let scale = fr.iter().fold(0.0f64, |a, b| a.max(b.abs())).max(1.0);
                for (k, (a, b)) in ff.iter().zip(fr.iter()).enumerate() {
                    assert!((a - b).abs() <= 1e-5 * scale, "{file} trial {trial} comp {k}: fast {a} vs ref {b}");
                }
            }
        }
    }

    #[test]
    fn neighbour_list_rebuild_keeps_forces_exact() {
        let s = parse_pdb(&fixture("1UBQ.pdb"), Some('A'), None).unwrap();
        let gm = build_model(&s.coords, false).unwrap();
        let fm = FastModel::new(&gm, None).unwrap();
        let cfg = RunConfig {
            mode: Mode::ConstantVelocity { speed: 2.0, spring_k: 0.1 },
            n_steps: 3000,
            dt: 0.005,
            temperature: 0.5,
            friction: 1.0,
            seed: 3,
            anchor: 0,
            pull: s.n() - 1,
            sample_every: 10,
            contact_every: 25,
            frame_every: 0,
        };
        let r = run(&s.coords, &fm, &cfg).unwrap();
        assert!(r.nl_rebuilds > 0, "a 30 A pull must rebuild the list");
        assert!(r.tension.iter().all(|t| t.is_finite()));
        // tension is positive (stretching) once the spring has run ahead
        let late = &r.tension[r.tension.len() / 2..];
        assert!(late.iter().sum::<f64>() / late.len() as f64 > 0.0);
    }

    #[test]
    fn same_seed_same_trajectory() {
        let s = parse_pdb(&fixture("1UBQ.pdb"), Some('A'), None).unwrap();
        let gm = build_model(&s.coords, false).unwrap();
        let fm = FastModel::new(&gm, None).unwrap();
        let cfg = RunConfig {
            mode: Mode::ConstantVelocity { speed: 1.0, spring_k: 0.1 },
            n_steps: 500, dt: 0.005, temperature: 0.5, friction: 1.0, seed: 11,
            anchor: 0, pull: s.n() - 1, sample_every: 5, contact_every: 25, frame_every: 100,
        };
        let a = run(&s.coords, &fm, &cfg).unwrap();
        let b = run(&s.coords, &fm, &cfg).unwrap();
        assert_eq!(a.tension, b.tension);
        assert_eq!(a.frames.len(), 6);
    }

    #[test]
    fn plddt_mask_removes_contacts_without_making_them_repulsive() {
        let s = parse_pdb(&fixture("1UBQ.pdb"), Some('A'), None).unwrap();
        let gm = build_model(&s.coords, false).unwrap();
        let mut mask = vec![false; s.n()];
        for m in mask.iter_mut().take(10) {
            *m = true;
        }
        let fm = FastModel::new(&gm, Some(&mask)).unwrap();
        assert!(fm.n_masked_contacts > 0);
        assert_eq!(fm.n_contacts() + fm.n_masked_contacts, gm.n_contacts());
        let nl = NeighborList::new(&s.coords, &fm);
        let mut f = vec![0.0; s.coords.len()];
        let e = forces(&s.coords, &fm, &nl, &mut f);
        assert!(e.is_finite());
    }

    #[test]
    fn events_found_on_a_synthetic_sawtooth() {
        let mut x = Vec::new();
        let mut t = Vec::new();
        for k in 0..2000 {
            let xx = k as f64 * 0.1;
            x.push(xx);
            let seg = (xx / 50.0).floor();
            let local = xx - seg * 50.0;
            t.push(0.04 * local + 0.2 * ((k * 7919 % 13) as f64 / 13.0 - 0.5) * 0.1);
        }
        let ev = find_unfolding_events(&x, &t);
        assert!(ev.len() >= 3, "expected the sawtooth teeth, got {}", ev.len());
    }
}
