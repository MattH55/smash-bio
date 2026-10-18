// Precompute the benchmark set shown on website/pull/benchmarks.html and used by
// the simulator's "Compare" panel. Browser standard protocol, wasm engine.
// Writes website/pull/data/benchmarks.json.
import { writeFileSync, mkdirSync, readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { runJobs, readPdb, REPO, loadAnalysis } from './run_jobs.mjs';

const A = loadAnalysis();
const STD = { dt: 0.01, spring_k: 0.1, temperature: 0.5, friction: 1, travel_fraction: 0.9, max_samples: 1500 };
const SPEEDS = [0.05, 0.1, 0.2];
const REPS = Number(process.env.REPS || 10);
// Experimental context: approximate literature values (AFM unless noted), quoted
// for orientation only; the model is not calibrated against them.
const PROTEINS = [
  { name: 'Titin I27', pdb: '1TIT', chain: 'A', dirs: [{ label: 'N–C', a: null, p: null, experiment: '≈204 pN at 0.6 µm/s; ΔLc 28.1 nm', ref: 'Carrion-Vazquez et al., PNAS 96:3694 (1999)' }] },
  { name: 'Ubiquitin', pdb: '1UBQ', chain: 'A', dirs: [
    { label: 'N–C', a: 1, p: 76, experiment: '≈203 pN at 0.4 µm/s', ref: 'Carrion-Vazquez et al., NSMB 10:738 (2003)' },
    { label: 'K48–C', a: 48, p: 76, experiment: '≈85 pN at 0.4 µm/s', ref: 'Carrion-Vazquez et al., NSMB 10:738 (2003)' }] },
  { name: 'Protein G B1 (GB1)', pdb: '2GB1', chain: 'A', dirs: [{ label: 'N–C', a: null, p: null, experiment: '≈180 pN at 0.4 µm/s; ΔLc ≈18 nm', ref: 'Cao & Li, Nature Materials 5:109 (2006)' }] },
  { name: 'Protein L B1', pdb: '1HZ6', chain: 'A', dirs: [{ label: 'N–C', a: null, p: null, experiment: '≈150 pN at 0.7 µm/s', ref: 'Brockwell et al., Biophys. J. 89:506 (2005)' }] },
  { name: 'Talin rod R3', pdb: '2L7A', chain: 'A', dirs: [{ label: 'N–C', a: null, p: null, experiment: '≈5 pN (magnetic tweezers, force clamp)', ref: 'Yao et al., Sci. Rep. 4:4610 (2014)' }] },
];
const jobs = [];
const meta = [];
for (const pr of PROTEINS) {
  const pdb = readPdb(pr.pdb);
  for (const d of pr.dirs) for (const v of SPEEDS) for (let s = 1; s <= REPS; s++) {
    const j = { op: 'protein_run', pdb, chain: pr.chain, speed: v, seed: s, ...STD };
    if (d.a != null) { j.anchor_residue = d.a; j.pull_residue = d.p; }
    jobs.push(j); meta.push({ pr, d, v, s });
  }
}
const structs = {};
for (const pr of PROTEINS) structs[pr.pdb] = (await runJobs([{ op: 'structure', pdb: readPdb(pr.pdb), chain: pr.chain }], { threads: 1 }))[0];
const t0 = Date.now();
const CACHE = path.join(REPO, 'tests', 'pull', 'results', 'benchmarks_raw.json');
const res = existsSync(CACHE) && !process.env.FRESH ? JSON.parse(readFileSync(CACHE, 'utf8')) : await runJobs(jobs, {
  threads: Number(process.env.THREADS || 8),
  reduce: (r, j) => {
    const S = structs[meta[jobs.indexOf(j)].pr.pdb];
    const inc = A.contourIncrements(r, S.coords);
    const keep = { peak: r.peak_tension, events: r.events.length, dlc: inc.map(e => e.dLc), lc_final: A.finalContour(r, S.coords), contour: r.contour_a, d0: r.extension0_a, label: r.label, anchor: r.anchor_residue, pull: r.pull_residue, n_steps: r.n_steps };
    if (j.seed === 1) { const k = Math.max(1, Math.floor(r.extension_a.length / 300)); keep.trace = { x: r.extension_a.filter((_, i) => i % k === 0).map(v => +v.toFixed(2)), y: r.tension.filter((_, i) => i % k === 0).map(v => +v.toFixed(3)) }; }
    return keep;
  },
  onProgress: (d, n) => { if (d % 15 === 0 || d === n) console.error(`${d}/${n} (${((Date.now() - t0) / 1000).toFixed(0)} s)`); }
});
const bad = res.filter(r => r.error); if (bad.length) { console.error(bad.slice(0, 2)); process.exit(1); }
writeFileSync(CACHE, JSON.stringify(res));
const mean = a => a.length ? a.reduce((s, v) => s + v, 0) / a.length : null;
const sd = a => a.length > 1 ? Math.sqrt(a.reduce((s, v) => s + (v - mean(a)) ** 2, 0) / (a.length - 1)) : null;
const r3 = v => v == null ? null : +v.toFixed(3);
const protein = PROTEINS.map(pr => ({
  name: pr.name, pdb: pr.pdb, chain: pr.chain,
  directions: pr.dirs.map(d => {
    const per = SPEEDS.map(v => {
      const rr = res.filter((_, i) => meta[i].pr === pr && meta[i].d === d && meta[i].v === v);
      const dl = rr.flatMap(r => r.dlc);
      return { speed: v, n: rr.length, peak_mean: r3(mean(rr.map(r => r.peak))), peak_sd: r3(sd(rr.map(r => r.peak))), events_mean: r3(mean(rr.map(r => r.events))), dlc_mean_nm: r3(mean(dl) / 10), dlc_total_nm: r3(mean(rr.map(r => r.dlc.reduce((s, x) => s + x, 0))) / 10), trace: rr.find(r => r.trace)?.trace };
    });
    const any = res.find((_, i) => meta[i].pr === pr && meta[i].d === d);
    const mid = per.find(q => q.speed === 0.1);
    const lnr = per.flatMap(q => res.filter((_, i) => meta[i].pr === pr && meta[i].d === d && meta[i].v === q.speed).map(r => ({ lnr: Math.log(STD.spring_k * q.speed), f: r.peak })));
    const bell = A.bellFit(lnr, STD.temperature);
    return { label: d.label, anchor: any.anchor, pull: any.pull, contour_nm: r3((any.contour - any.d0) / 10), peak_mean: mid.peak_mean, peak_sd: mid.peak_sd, xb_A: bell ? r3(bell.xb) : null, xb_se_A: bell ? r3(bell.xbSe) : null, per_speed: per, experiment: d.experiment, ref: d.ref };
  })
}));

// ---- nucleic benchmarks
const nuc = [];
const NA = [
  { name: '20-bp DNA hairpin, 4T loop (example)', req: { sequence: 'GAGTCCTGGATCCTGTCCGCTTTTGCGGACAGGATCCAGGACTC', temperature_k: 296.15, na_mm: 200 } },
  { name: '12-bp GC-rich DNA hairpin', req: { sequence: 'GCGCGGCCGCGCTTTTGCGCGGCCGCGC', temperature_k: 298.15, na_mm: 150 } },
  { name: '12-bp RNA hairpin, GAAA loop', req: { sequence: 'GGCGCAUCCGGCGAAAGCCGGAUGCGCC', polymer: 'RNA', temperature_k: 298.15, na_mm: 150 } },
];
for (const n of NA) {
  const L = (await runJobs([{ op: 'nucleic_landscape', ...n.req }], { threads: 1 }))[0];
  const kin = await runJobs(Array.from({ length: 20 }, (_, i) => ({ op: 'nucleic_kinetic', ...n.req, speed_nm_s: 100, refold: true, seed: i + 1, max_samples: 400 })), { threads: 8, reduce: r => ({ un: r.transitions.filter(t => t.unfold).map(t => t.force_pn)[0], re: r.transitions.filter(t => !t.unfold).map(t => t.force_pn).at(-1) }) });
  const un = kin.map(k => k.un).filter(Number.isFinite), re = kin.map(k => k.re).filter(Number.isFinite);
  nuc.push({ name: n.name, sequence: n.req.sequence, T_K: n.req.temperature_k, na_mM: n.req.na_mm, n_bp: L.summary.n_bp, loop_nt: L.summary.loop_nt, dG_fold_kcal: r3(L.summary.dG_fold_kcal), F_half_pN: r3(L.summary.F_half_pN), dx_nm: r3(L.summary.delta_x_at_F_half_nm), unfold_pN: r3(mean(un)), unfold_sd: r3(sd(un)), refold_pN: r3(mean(re)), refold_sd: r3(sd(re)), speed_nm_s: 100 });
}
// long unzipping: equilibrium only
let s = 20261014 >>> 0; const seq = Array.from({ length: 600 }, () => { s = (s * 1664525 + 1013904223) >>> 0; return 'ACGT'[s >>> 30]; }).join('');
const U = (await runJobs([{ op: 'nucleic_landscape', construct: 'unzip', sequence: seq, temperature_k: 298.15, na_mm: 150, points: 300, f_end: 25 }], { threads: 1 }))[0];
const fz = U.equilibrium.force_pn.filter((f, i) => U.equilibrium.mean_open[i] > 20 && U.equilibrium.mean_open[i] < 580);
const unzip = { name: '600-bp random duplex, unzipping (equilibrium)', n_bp: 600, mean_force_pN: r3(mean(fz)), min_pN: r3(Math.min(...fz)), max_pN: r3(Math.max(...fz)), experiment: 'λ-DNA unzipping fluctuates between ≈10 and ≈15 pN', ref: 'Essevaz-Roulet, Bockelmann & Heslot, PNAS 94:11935 (1997)', curve: { x: U.equilibrium.extension_nm.map(v => +v.toFixed(1)), y: U.equilibrium.force_pn.map(v => +v.toFixed(2)) } };

const gate = n => { const p = path.join(REPO, 'tests', 'pull', 'results', n + '.json'); return existsSync(p) ? JSON.parse(readFileSync(p, 'utf8').replace(/^\uFEFF/, '')) : null; };
const g4 = gate('gate4');
const out = {
  generated: new Date().toISOString().slice(0, 10), engine: 'pull-engine ' + (await runJobs([{ op: 'version' }], { threads: 1 }))[0].version,
  protocol: { ...STD, speeds: SPEEDS, replicas: REPS, units: 'tension in model units ε/Å (not pN); lengths in nm' },
  protein, nucleic: nuc, unzip,
  sequence_class: g4 ? { target: g4.target, median_F_half_pN: g4.median_F_half_pN, median_delta_x_nm: g4.median_delta_x_nm, reference_thermo: g4.reference_thermo, gc_series: g4.gc_series, pass: g4.pass } : null,
};
mkdirSync(path.join(REPO, 'website', 'pull', 'data'), { recursive: true });
writeFileSync(path.join(REPO, 'website', 'pull', 'data', 'benchmarks.json'), JSON.stringify(out));
for (const p of protein) for (const d of p.directions) console.log(`${p.name} ${d.label}: peak@0.1 ${d.peak_mean}±${d.peak_sd}, xb ${d.xb_A} Å, ΔLc total ${d.per_speed.map(q => q.dlc_total_nm).join('/')} nm (contour ${d.contour_nm})`);
for (const n of nuc) console.log(n.name, 'F½', n.F_half_pN, 'unfold', n.unfold_pN, 'refold', n.refold_pN);
console.log('unzip mean', unzip.mean_force_pN, 'wall', ((Date.now() - t0) / 1000).toFixed(0), 's');
