//! The engine's one entry point: a JSON request in, a JSON result out.
//!
//! The browser (through `wasm.rs`) and the native gate harnesses call the same
//! `call` function, so "native and WebAssembly give byte-identical output"
//! (Gate 5) compares exactly the code the page runs.
//!
//! Ops (`"op"` field):
//! * `version`          - engine identity.
//! * `structure`        - parse a PDB, return the Cα trace, contact map and prep flags.
//! * `protein_run`      - one Gō-model pulling trajectory (production `fast` path).
//! * `nucleic_landscape`- NN thermodynamics + instrument: F½, Δx, landscape, equilibrium FEC.
//! * `nucleic_kinetic`  - kinetic Monte Carlo trajectory (moving trap or force clamp).
//!
//! Every error is returned as `{"error":{"code","message","detail"}}`.

use crate::error::{EngineError, EngineResult};
use crate::fast::{self, FastModel, Mode, RunConfig};
use crate::json::{self, Json};
use crate::nakin::{self, Construct, KinConfig, Landscape, NaSystem, Thermo};
use crate::nucleic::{normalise, Polymer};
use crate::prep;
use crate::protein::{build_model, parse_pdb, resolve_pull_points, Structure};
use crate::units::*;
use crate::{ENGINE_NAME, ENGINE_VERSION, MODEL_GO_CA, MODEL_NN_WLC};

/// Handle one request. Never panics on bad input.
pub fn call(input: &str) -> String {
    match dispatch(input) {
        Ok(s) => s,
        Err(e) => error_json(&e),
    }
}

pub fn error_json(e: &EngineError) -> String {
    format!(
        "{{\"error\":{{\"code\":{},\"message\":{},\"detail\":{}}}}}",
        json::quote(&e.code),
        json::quote(&e.message),
        e.detail.as_deref().map(json::quote).unwrap_or_else(|| "null".into())
    )
}

fn dispatch(input: &str) -> EngineResult<String> {
    let req = json::parse(input)?;
    let op = req.str_at("op", "");
    match op.as_str() {
        "version" => Ok(version()),
        "structure" => structure(&req),
        "protein_run" => protein_run(&req),
        "nucleic_landscape" => nucleic_landscape(&req),
        "nucleic_kinetic" => nucleic_kinetic(&req),
        "" => Err(EngineError::missing_field("op")),
        other => Err(EngineError::bad_value("op", format!("unknown op {other:?}"))),
    }
}

fn version() -> String {
    format!(
        "{{\"engine\":{},\"version\":{},\"models\":[{},{}]}}",
        json::quote(ENGINE_NAME),
        json::quote(ENGINE_VERSION),
        json::quote(MODEL_GO_CA),
        json::quote(MODEL_NN_WLC)
    )
}

fn arr_f64(v: &[f64]) -> String {
    let mut s = String::with_capacity(v.len() * 10 + 2);
    s.push('[');
    for (i, x) in v.iter().enumerate() {
        if i > 0 {
            s.push(',');
        }
        s.push_str(&json::num(*x));
    }
    s.push(']');
    s
}

/// Coordinates to 3 decimals (mÅ) - display only, keeps frames small.
fn arr_coords(v: &[f32]) -> String {
    let mut s = String::with_capacity(v.len() * 8 + 2);
    s.push('[');
    for (i, x) in v.iter().enumerate() {
        if i > 0 {
            s.push(',');
        }
        let r = (*x as f64 * 1000.0).round() / 1000.0;
        s.push_str(&json::num(r));
    }
    s.push(']');
    s
}

fn opt_i64(req: &Json, key: &str) -> Option<i64> {
    req.get(key).and_then(|v| v.as_f64()).map(|v| v.round() as i64)
}

fn parse_structure(req: &Json) -> EngineResult<(String, Structure)> {
    let pdb = req.get("pdb").and_then(|v| v.as_str()).ok_or_else(|| EngineError::missing_field("pdb"))?;
    let chain = req.get("chain").and_then(|v| v.as_str()).and_then(|s| s.trim().chars().next());
    let range = match (opt_i64(req, "range_start"), opt_i64(req, "range_end")) {
        (Some(a), Some(b)) => Some((a.min(b), a.max(b))),
        _ => None,
    };
    let s = parse_pdb(pdb, chain, range)?;
    Ok((pdb.to_string(), s))
}

/// Residues whose native contacts are excluded: AlphaFold models below the pLDDT cutoff.
fn exclusion_mask(p: &prep::Prep, cutoff: f64) -> Option<Vec<bool>> {
    if !p.is_alphafold || !(cutoff > 0.0) {
        return None;
    }
    let m: Vec<bool> = p.bfactor.iter().map(|b| b.is_finite() && *b < cutoff).collect();
    if m.iter().any(|x| *x) { Some(m) } else { None }
}

fn structure(req: &Json) -> EngineResult<String> {
    let (pdb, s) = parse_structure(req)?;
    let p = prep::annotate(&pdb, &s);
    let gm = build_model(&s.coords, false)?;
    let n = s.n();
    let contacts: Vec<String> = (0..gm.ci.len()).map(|k| format!("[{},{}]", gm.ci[k], gm.cj[k])).collect();
    let coords: Vec<f32> = s.coords.iter().map(|v| *v as f32).collect();
    let d0 = {
        let (a, b) = (&s.coords[0..3], &s.coords[(n - 1) * 3..n * 3]);
        ((a[0] - b[0]).powi(2) + (a[1] - b[1]).powi(2) + (a[2] - b[2]).powi(2)).sqrt()
    };
    let notes: Vec<String> = s.notes.iter().map(|x| json::quote(x)).collect();
    let res: Vec<String> = s.residues.iter().map(|r| r.to_string()).collect();
    Ok(format!(
        "{{\"label\":{},\"chain\":{},\"n\":{n},\"residues\":[{}],\"sequence\":{},\"coords\":{},\"contacts\":[{}],\"n_contacts\":{},\"end_to_end_a\":{},\"contour_a\":{},\"notes\":[{}],\"prep\":{}}}",
        json::quote(&s.label),
        json::quote(&s.chain.to_string()),
        res.join(","),
        json::quote(&s.sequence()),
        arr_coords(&coords),
        contacts.join(","),
        gm.ci.len(),
        json::num(d0),
        json::num(3.8 * (n as f64 - 1.0)),
        notes.join(","),
        p.to_json()
    ))
}

fn protein_run(req: &Json) -> EngineResult<String> {
    let (pdb, s) = parse_structure(req)?;
    let p = prep::annotate(&pdb, &s);
    let n = s.n();
    let (a, b) = resolve_pull_points(&s, opt_i64(req, "anchor_residue"), opt_i64(req, "pull_residue"))?;
    let anchor = a.unwrap_or(0);
    let pull = b.unwrap_or(n - 1);
    let lj = req.bool_at("lj_10_12", false);
    let gm = build_model(&s.coords, lj)?;
    let cutoff = req.f64_at("plddt_cutoff", 50.0);
    let mask = exclusion_mask(&p, cutoff);
    let fm = FastModel::new(&gm, mask.as_deref())?;

    let dt = req.f64_at("dt", 0.01);
    let mode_s = req.str_at("mode", "velocity");
    let d0 = {
        let (u, v) = (&s.coords[anchor * 3..anchor * 3 + 3], &s.coords[pull * 3..pull * 3 + 3]);
        ((u[0] - v[0]).powi(2) + (u[1] - v[1]).powi(2) + (u[2] - v[2]).powi(2)).sqrt()
    };
    let sep = (pull as f64 - anchor as f64).abs();
    let contour = 3.8 * sep;
    let (mode, n_steps) = match mode_s.as_str() {
        "velocity" => {
            let speed = req.f64_at("speed", 0.05);
            let spring_k = req.f64_at("spring_k", 0.1);
            if !(speed > 0.0) {
                return Err(EngineError::bad_value("speed", "must be positive"));
            }
            let steps = match req.get("n_steps").and_then(|v| v.as_f64()) {
                Some(s) => s.round() as usize,
                None => {
                    let frac = req.f64_at("travel_fraction", 0.9);
                    let travel = (frac * (contour - d0)).max(10.0);
                    (travel / (speed * dt)).ceil() as usize
                }
            };
            (Mode::ConstantVelocity { speed, spring_k }, steps)
        }
        "force" => {
            let force = req.f64_at("force", 1.0);
            let steps = req.f64_at("n_steps", 200_000.0).round() as usize;
            (Mode::ConstantForce { force }, steps)
        }
        other => return Err(EngineError::bad_value("mode", format!("{other:?} is velocity or force"))),
    };
    let max_samples = req.f64_at("max_samples", 1500.0).max(10.0) as usize;
    let frames_wanted = req.f64_at("frames", 0.0).max(0.0) as usize;
    let cfg = RunConfig {
        mode,
        n_steps,
        dt,
        temperature: req.f64_at("temperature", 0.5),
        friction: req.f64_at("friction", FRICTION),
        seed: req.f64_at("seed", 1.0).max(0.0) as u64,
        anchor,
        pull,
        sample_every: (n_steps / max_samples).max(1),
        contact_every: req.f64_at("contact_every", 25.0).max(1.0) as usize,
        frame_every: if frames_wanted > 0 { (n_steps / frames_wanted).max(1) } else { 0 },
    };
    let r = fast::run(&s.coords, &fm, &cfg)?;
    let events = fast::find_unfolding_events(&r.extension_a, &r.tension);
    let ev: Vec<String> = events
        .iter()
        .map(|e| {
            format!(
                "{{\"index\":{},\"force\":{},\"extension_a\":{},\"drop\":{},\"delta_extension_a\":{}}}",
                e.index,
                json::num(e.force),
                json::num(e.extension),
                json::num(e.drop),
                e.delta_extension.map(json::num).unwrap_or_else(|| "null".into())
            )
        })
        .collect();
    let breaks: Vec<String> = (0..fm.ci.len())
        .map(|k| {
            format!(
                "[{},{},{}]",
                fm.ci[k],
                fm.cj[k],
                r.break_step[k].map(|v| v.to_string()).unwrap_or_else(|| "null".into())
            )
        })
        .collect();
    let frames: Vec<String> = r.frames.iter().map(|f| arr_coords(f)).collect();
    let fsteps: Vec<String> = r.frame_steps.iter().map(|v| v.to_string()).collect();
    let peak = fast::smooth5(&r.tension).iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let mut warnings: Vec<String> = s.notes.clone();
    if let Some(m) = &mask {
        warnings.push(format!(
            "AlphaFold model: {} residue(s) with pLDDT < {cutoff} have their native contacts removed ({} contacts)",
            m.iter().filter(|x| **x).count(),
            fm.n_masked_contacts
        ));
    }
    if !p.disulfides.is_empty() {
        warnings.push(format!(
            "{} disulfide bond(s) are not modelled as covalent: they can break in the simulation but not in the experiment",
            p.disulfides.len()
        ));
    }
    if !p.metals.is_empty() {
        warnings.push(format!("{} metal site(s) not modelled", p.metals.len()));
    }
    if !p.breaks.is_empty() {
        warnings.push(format!("{} chain break(s): the trace is bonded across missing residues", p.breaks.len()));
    }
    let w: Vec<String> = warnings.iter().map(|x| json::quote(x)).collect();
    let (mode_name, speed, spring_k, force) = match cfg.mode {
        Mode::ConstantVelocity { speed, spring_k } => ("velocity", speed, spring_k, f64::NAN),
        Mode::ConstantForce { force } => ("force", f64::NAN, f64::NAN, force),
    };
    Ok(format!(
        "{{\"model_family\":{},\"unit_system\":\"reduced\",\"force_unit\":\"epsilon_per_angstrom\",\"label\":{},\"n\":{n},\"anchor_index\":{anchor},\"pull_index\":{pull},\"anchor_residue\":{},\"pull_residue\":{},\"mode\":\"{mode_name}\",\"speed\":{},\"spring_k\":{},\"force\":{},\"dt\":{},\"temperature\":{},\"friction\":{},\"seed\":{},\"n_steps\":{},\"sample_every\":{},\"n_contacts\":{},\"n_masked_contacts\":{},\"extension0_a\":{},\"contour_a\":{},\"time\":{},\"extension_a\":{},\"tension\":{},\"peak_tension\":{},\"events\":[{}],\"contact_breaks\":[{}],\"contacts_remaining\":{},\"frames\":[{}],\"frame_steps\":[{}],\"nl_rebuilds\":{},\"warnings\":[{}]}}",
        json::quote(MODEL_GO_CA),
        json::quote(&s.label),
        s.residues[anchor],
        s.residues[pull],
        json::num(speed),
        json::num(spring_k),
        json::num(force),
        json::num(cfg.dt),
        json::num(cfg.temperature),
        json::num(cfg.friction),
        cfg.seed,
        cfg.n_steps,
        cfg.sample_every,
        fm.ci.len(),
        fm.n_masked_contacts,
        json::num(r.extension0_a),
        json::num(contour),
        arr_f64(&r.time),
        arr_f64(&r.extension_a),
        arr_f64(&r.tension),
        json::num(peak),
        ev.join(","),
        breaks.join(","),
        json::num(r.contacts_remaining),
        frames.join(","),
        fsteps.join(","),
        r.nl_rebuilds,
        w.join(",")
    ))
}

/// Build the nucleic system from a request. Accepts either `stem` (+ `loop`) or
/// a full hairpin `sequence` (stem auto-detected) for hairpins, and `sequence`
/// for unzipping.
fn na_system(req: &Json) -> EngineResult<(NaSystem, Vec<String>)> {
    let polymer = Polymer::parse(&req.str_at("polymer", "DNA"))?;
    let construct = match req.str_at("construct", "hairpin").as_str() {
        "hairpin" => Construct::Hairpin,
        "unzip" | "duplex_unzip" => Construct::Unzip,
        other => return Err(EngineError::bad_value("construct", format!("{other:?} is hairpin or unzip"))),
    };
    let thermo = match req.str_at("thermo", "browser").as_str() {
        "browser" => Thermo::Browser,
        "reference" => Thermo::Reference,
        other => return Err(EngineError::bad_value("thermo", format!("{other:?} is browser or reference"))),
    };
    let mut notes = vec![];
    let (stem, loop_nt) = match construct {
        Construct::Hairpin => {
            if let Some(st) = req.get("stem").and_then(|v| v.as_str()) {
                (st.to_string(), req.f64_at("loop", 4.0).max(0.0) as usize)
            } else {
                let seq = req.get("sequence").and_then(|v| v.as_str()).ok_or_else(|| EngineError::missing_field("sequence"))?;
                match nakin::detect_hairpin(seq) {
                    Some((st, l)) => {
                        notes.push(format!("hairpin detected: {}-bp stem {} closing a {}-nt loop", st.len(), st, l));
                        (st, l)
                    }
                    None => {
                        return Err(EngineError::unsupported(
                            "no perfect Watson-Crick hairpin (stem >= 3 bp from the two ends, loop >= 3 nt) was found; \
                             give the stem and loop explicitly, or use unzip mode",
                        ))
                    }
                }
            }
        }
        Construct::Unzip => {
            let seq = req.get("sequence").and_then(|v| v.as_str()).ok_or_else(|| EngineError::missing_field("sequence"))?;
            (seq.to_string(), 0)
        }
    };
    let bad: Vec<char> = normalise(&stem).iter().filter(|b| !matches!(b, b'A' | b'C' | b'G' | b'T')).map(|b| *b as char).collect();
    if !bad.is_empty() {
        return Err(EngineError::bad_value("sequence", format!("only A, C, G, T/U are allowed (found {:?})", bad[0])));
    }
    Ok((
        NaSystem {
            polymer,
            construct,
            stem,
            loop_nt,
            temperature_k: req.f64_at("temperature_k", 298.15),
            na_mm: req.f64_at("na_mm", 150.0),
            mg_mm: req.f64_at("mg_mm", 0.0),
            thermo,
            trap_k_pn_nm: req.f64_at("trap_k", 0.3),
            handle_bp: req.f64_at("handle_bp", 2000.0),
            handle_lp_nm: req.f64_at("handle_lp_nm", DS_LP_NM),
            handle_s_pn: req.f64_at("handle_s_pn", 1000.0),
            ss_rise_nm: req.f64_at("ss_rise_nm", SS_RISE_NM),
            ss_lp_nm: req.f64_at("ss_lp_nm", SS_LP_NM),
        },
        notes,
    ))
}

fn nucleic_landscape(req: &Json) -> EngineResult<String> {
    let (sys, notes) = na_system(req)?;
    let l = Landscape::build(&sys)?;
    let f_end = req.f64_at("f_end", l.f_half().map(|f| f + 10.0).unwrap_or(30.0));
    let c = nakin::equilibrium_curve(&l, f_end, req.f64_at("points", 400.0) as usize);
    let summary = l.summary_json(&sys);
    let n: Vec<String> = notes.iter().map(|x| json::quote(x)).collect();
    Ok(format!(
        "{{\"model_family\":{},\"unit_system\":\"physical\",\"stem\":{},\"summary\":{},\"equilibrium\":{{\"trap_nm\":{},\"force_pn\":{},\"extension_nm\":{},\"mean_open\":{}}},\"input_notes\":[{}]}}",
        json::quote(MODEL_NN_WLC),
        json::quote(&sys.stem),
        summary,
        arr_f64(&c.trap_nm),
        arr_f64(&c.force_pn),
        arr_f64(&c.ext_nm),
        arr_f64(&c.mean_open),
        n.join(",")
    ))
}

fn nucleic_kinetic(req: &Json) -> EngineResult<String> {
    let (sys, _) = na_system(req)?;
    let l = Landscape::build(&sys)?;
    let fh = l.f_half();
    let clamp = req.get("clamp_pn").and_then(|v| v.as_f64());
    let cfg = KinConfig {
        speed_nm_s: req.f64_at("speed_nm_s", 100.0),
        f_end_pn: req.f64_at("f_end", fh.map(|f| f + 8.0).unwrap_or(30.0)),
        refold: req.bool_at("refold", true),
        clamp_pn: clamp,
        duration_s: req.f64_at("duration_s", 1.0),
        k0_per_s: req.f64_at("k0", 1e6),
        seed: req.f64_at("seed", 1.0).max(0.0) as u64,
        max_samples: req.f64_at("max_samples", 2000.0).max(10.0) as usize,
        max_events: req.f64_at("max_events", 3e8) as u64,
    };
    let r = nakin::kinetic(&l, &cfg)?;
    let t: Vec<f64> = r.samples.iter().map(|s| s.t_s).collect();
    let x: Vec<f64> = r.samples.iter().map(|s| s.trap_nm).collect();
    let f: Vec<f64> = r.samples.iter().map(|s| s.force_pn).collect();
    let no: Vec<f64> = r.samples.iter().map(|s| s.n_open as f64).collect();
    let tr: Vec<String> = r
        .transitions
        .iter()
        .map(|t| format!("{{\"t_s\":{},\"unfold\":{},\"force_pn\":{},\"dx_nm\":{}}}", json::num(t.t_s), t.unfold, json::num(t.force_pn), json::num(t.dx_nm)))
        .collect();
    Ok(format!(
        "{{\"model_family\":{},\"unit_system\":\"physical\",\"mode\":{},\"seed\":{},\"k0_per_s\":{},\"F_half_pN\":{},\"n_bp\":{},\"time_s\":{},\"trap_nm\":{},\"force_pn\":{},\"n_open\":{},\"refold_start\":{},\"transitions\":[{}],\"events\":{},\"truncated\":{}}}",
        json::quote(MODEL_NN_WLC),
        json::quote(if clamp.is_some() { "clamp" } else { "ramp" }),
        cfg.seed,
        json::num(cfg.k0_per_s),
        fh.map(json::num).unwrap_or_else(|| "null".into()),
        l.n_bp,
        arr_f64(&t),
        arr_f64(&x),
        arr_f64(&f),
        arr_f64(&no),
        r.refold_start,
        tr.join(","),
        r.events,
        r.truncated
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_and_errors() {
        assert!(call("{\"op\":\"version\"}").contains(ENGINE_VERSION));
        assert!(call("not json").contains("invalid_json"));
        assert!(call("{\"op\":\"nope\"}").contains("bad_value"));
        assert!(call("{\"op\":\"protein_run\"}").contains("missing_field"));
    }

    #[test]
    fn protein_run_roundtrips_as_json() {
        let pdb = std::fs::read_to_string(format!("{}/fixtures/1UBQ.pdb", env!("CARGO_MANIFEST_DIR"))).unwrap();
        let req = format!("{{\"op\":\"protein_run\",\"pdb\":{},\"chain\":\"A\",\"speed\":0.5,\"n_steps\":2000,\"frames\":4}}", json::quote(&pdb));
        let out = call(&req);
        let j = json::parse(&out).unwrap_or_else(|e| panic!("{e}: {}", &out[..out.len().min(300)]));
        assert!(j.get("error").is_none(), "{out}");
        assert_eq!(j.str_at("unit_system", ""), "reduced");
        assert_eq!(j.get("frames").unwrap().as_arr().unwrap().len(), 5);
        assert_eq!(call(&req), out, "deterministic");
        let s = call(&format!("{{\"op\":\"structure\",\"pdb\":{}}}", json::quote(&pdb)));
        assert!(json::parse(&s).unwrap().f64_at("n", 0.0) == 76.0);
    }

    #[test]
    fn nucleic_ops_roundtrip() {
        let req = "{\"op\":\"nucleic_landscape\",\"sequence\":\"GAGTCCTGGATCCTGTCCGCTTTTGCGGACAGGATCCAGGACTC\",\"temperature_k\":296.15,\"na_mm\":200}";
        let out = call(req);
        let j = json::parse(&out).unwrap();
        assert!(j.get("error").is_none(), "{out}");
        assert!(j.get("summary").unwrap().f64_at("F_half_pN", 0.0) > 5.0);
        let k = call("{\"op\":\"nucleic_kinetic\",\"stem\":\"GCGCATATGCGC\",\"loop\":4,\"speed_nm_s\":200,\"seed\":3}");
        let kj = json::parse(&k).unwrap();
        assert!(kj.get("error").is_none(), "{k}");
        assert!(!kj.get("transitions").unwrap().as_arr().unwrap().is_empty());
    }
}
