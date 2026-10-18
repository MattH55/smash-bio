// Gate 2 (docs/pull/VALIDATION.md): protein pulling geometry against experiment,
// protocol P_std, production engine (the browser's wasm module).
// Writes tests/pull/results/gate2.json.
import { writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { runJobs, readPdb, REPO, mannWhitneyGreater, spearman } from './run_jobs.mjs';

const P_STD = { dt: 0.005, speed: 0.5, spring_k: 0.1, temperature: 0.5, friction: 1, travel_fraction: 0.9, max_samples: 1500 };
const SEEDS = Array.from({ length: 20 }, (_, i) => i + 1);
const CASES = [
  { key: 'ubq_NC', pdb: '1UBQ', a: 1, p: 76 },
  { key: 'ubq_K48C', pdb: '1UBQ', a: 48, p: 76 },
  { key: 'gfp_117_182', pdb: '1EMA', a: 117, p: 182, exp: 548 },
  { key: 'gfp_182_212', pdb: '1EMA', a: 182, p: 212, exp: 356 },
  { key: 'gfp_3_132', pdb: '1EMA', a: 3, p: 132, exp: 346 },
  { key: 'gfp_132_212', pdb: '1EMA', a: 132, p: 212, exp: 127 },
  { key: 'gfp_3_212', pdb: '1EMA', a: 3, p: 212, exp: 117 },
];
const jobs = [];
for (const c of CASES) {
  const pdb = readPdb(c.pdb);
  for (const seed of SEEDS) jobs.push({ op: 'protein_run', pdb, chain: 'A', anchor_residue: c.a, pull_residue: c.p, seed, ...P_STD, _key: c.key });
}
const t0 = Date.now();
const res = await runJobs(jobs.map(({ _key, ...j }) => j), {
  threads: Number(process.env.THREADS || 8),
  reduce: r => ({ peak: r.peak_tension, n_steps: r.n_steps, events: r.events.length, contacts_remaining: r.contacts_remaining, label: r.label }),
  onProgress: (d, n) => { if (d % 10 === 0 || d === n) console.error(`${d}/${n} (${((Date.now() - t0) / 1000).toFixed(0)} s)`); }
});
const errs = res.filter(r => r.error);
if (errs.length) { console.error('errors:', errs.slice(0, 3)); process.exit(1); }
const by = {};
jobs.forEach((j, i) => (by[j._key] ||= []).push(res[i].peak));
const mean = a => a.reduce((s, v) => s + v, 0) / a.length;
const sd = a => Math.sqrt(a.reduce((s, v) => s + (v - mean(a)) ** 2, 0) / (a.length - 1));
const summary = Object.fromEntries(CASES.map(c => [c.key, { anchor: c.a, pull: c.p, experiment_pN: c.exp ?? null, peaks: by[c.key], mean: mean(by[c.key]), sd: sd(by[c.key]), n_steps: res[jobs.findIndex(j => j._key === c.key)].n_steps }]));
// 2a
const mw = mannWhitneyGreater(by.ubq_NC, by.ubq_K48C);
const g2a = { mean_NC: mean(by.ubq_NC), mean_K48C: mean(by.ubq_K48C), U: mw.U, z: mw.z, p_one_sided: mw.p, pass: mean(by.ubq_NC) > mean(by.ubq_K48C) && mw.p < 0.05 };
// 2b
const strong = ['gfp_117_182', 'gfp_182_212', 'gfp_3_132'], weak = ['gfp_132_212', 'gfp_3_212'];
const sep = strong.every(s => weak.every(w => summary[s].mean > summary[w].mean));
const gk = [...strong, ...weak];
const rho = spearman(gk.map(k => summary[k].mean), gk.map(k => summary[k].experiment_pN));
const g2b = { strong_above_weak: sep, spearman_rho: rho, pass: sep && rho >= 0.7 };
const out = { gate: '2', protocol: P_STD, seeds: SEEDS, engine: 'pull-engine wasm (Node ' + process.version + ')', wall_s: (Date.now() - t0) / 1000, cases: summary, gate2a: g2a, gate2b: g2b, pass: g2a.pass && g2b.pass };
mkdirSync(path.join(REPO, 'tests', 'pull', 'results'), { recursive: true });
writeFileSync(path.join(REPO, 'tests', 'pull', 'results', 'gate2.json'), JSON.stringify(out, null, 1));
for (const c of CASES) console.log(`${c.key.padEnd(12)} peak ${summary[c.key].mean.toFixed(3)} ± ${summary[c.key].sd.toFixed(3)}${c.exp ? '  exp ' + c.exp + ' pN' : ''}`);
console.log('2a', JSON.stringify(g2a));
console.log('2b', JSON.stringify(g2b));
