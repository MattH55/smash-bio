// Compare pathway fingerprints: all contacts vs contact blocks. Prints pairwise ρ spread.
import { runJobs, readPdb, loadAnalysis } from './run_jobs.mjs';
const A = loadAnalysis();
const cases = [['1TIT', null, null], ['1UBQ', 1, 76], ['1UBQ', 48, 76], ['2GB1', null, null], ['1HZ6', null, null]];
const speed = Number(process.env.SPEED || 0.1);
for (const [id, a, p] of cases) {
  const pdb = readPdb(id);
  const jobs = Array.from({ length: 10 }, (_, s) => ({ op: 'protein_run', pdb, chain: 'A', speed, dt: 0.01, seed: s + 1, max_samples: 300, ...(a ? { anchor_residue: a, pull_residue: p } : {}) }));
  const runs = await runJobs(jobs, { threads: 10, reduce: r => ({ contact_breaks: r.contact_breaks, n_steps: r.n_steps }) });
  const n = Math.max(...runs[0].contact_breaks.flatMap(c => [c[0], c[1]])) + 1;
  const B = Math.max(4, Math.round(n / 12));
  const groups = {};
  runs[0].contact_breaks.forEach((c, k) => { const g = Math.floor(c[0] / B) + ':' + Math.floor(c[1] / B); (groups[g] ||= []).push(k); });
  const gk = Object.keys(groups).filter(g => groups[g].length >= 3);
  const med = a => { const b = [...a].sort((x, y) => x - y); return b[Math.floor(b.length / 2)]; };
  const fpAll = runs.map(A.fingerprint);
  const fpGrp = fpAll.map(f => gk.map(g => med(groups[g].map(k => f[k]))));
  const spread = fp => { const rk = fp.map(v => { const s = v.map((x, i) => [x, i]).sort((p, q) => p[0] - q[0]); const r = []; s.forEach(([, i], k) => r[i] = k); return r; });
    const pr = (x, y) => { const m = x.length, mx = x.reduce((s, v) => s + v, 0) / m, my = y.reduce((s, v) => s + v, 0) / m; let a = 0, b = 0, c = 0; for (let i = 0; i < m; i++) { a += (x[i] - mx) * (y[i] - my); b += (x[i] - mx) ** 2; c += (y[i] - my) ** 2; } return a / Math.sqrt(b * c); };
    const v = []; for (let i = 0; i < rk.length; i++) for (let j = i + 1; j < rk.length; j++) v.push(pr(rk[i], rk[j])); v.sort((x, y) => x - y);
    return `min ${v[0].toFixed(2)} median ${v[Math.floor(v.length / 2)].toFixed(2)}`; };
  // which block breaks first in each run
  const firsts = fpGrp.map(f => gk[f.indexOf(Math.min(...f))]);
  console.log(`${id}${a ? ` ${a}-${p}` : ''}: ${runs[0].contact_breaks.length} contacts, ${gk.length} blocks (B=${B}) | all-contact ρ ${spread(fpAll)} | block ρ ${spread(fpGrp)} | first block per run: ${firsts.join(' ')}`);
}
