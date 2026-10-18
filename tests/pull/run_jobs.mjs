// Run engine requests on a pool of Node worker threads, each with its own copy
// of the WebAssembly module the browser uses (website/pull/wasm/pull_engine.wasm).
import { Worker, isMainThread, parentPort } from 'node:worker_threads';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import os from 'node:os';
import vm from 'node:vm';

const here = path.dirname(fileURLToPath(import.meta.url));
export const REPO = path.resolve(here, '..', '..');
const WASM = path.join(REPO, 'website', 'pull', 'wasm', 'pull_engine.wasm');

if (!isMainThread) {
  const { instance } = await WebAssembly.instantiate(readFileSync(WASM), {});
  const ex = instance.exports;
  parentPort.on('message', ({ id, req }) => {
    const enc = new TextEncoder().encode(req);
    const p = ex.pe_alloc(enc.length);
    new Uint8Array(ex.memory.buffer, p, enc.length).set(enc);
    const t = performance.now();
    const out = ex.pe_call(p, enc.length);
    const n = ex.pe_result_len();
    const s = new TextDecoder().decode(new Uint8Array(ex.memory.buffer, out, n));
    ex.pe_free(out, n);
    parentPort.postMessage({ id, result: s, ms: performance.now() - t });
  });
}

// jobs: array of request objects. reduce(result, job) keeps what is needed (memory).
export async function runJobs(jobs, { threads = Math.max(1, os.cpus().length - 1), reduce = r => r, onProgress } = {}) {
  const n = Math.min(threads, jobs.length);
  const workers = Array.from({ length: n }, () => new Worker(fileURLToPath(import.meta.url)));
  const results = new Array(jobs.length);
  let next = 0, done = 0;
  await new Promise((resolve, reject) => {
    const pump = w => {
      if (next >= jobs.length) return;
      const i = next++;
      w.once('message', ({ result, ms }) => {
        const r = JSON.parse(result);
        results[i] = r.error ? r : reduce(r, jobs[i]);
        if (results[i] && typeof results[i] === 'object') results[i]._ms = ms;
        done++;
        if (onProgress) onProgress(done, jobs.length, ms);
        if (done === jobs.length) resolve(); else pump(w);
      });
      w.postMessage({ id: i, req: JSON.stringify(jobs[i]) });
    };
    workers.forEach(w => { w.on('error', reject); pump(w); });
  });
  await Promise.all(workers.map(w => w.terminate()));
  return results;
}

// The page's analysis code, loaded as-is (window.PullAnalysis).
export function loadAnalysis() {
  const ctx = { window: {}, console };
  vm.createContext(ctx);
  vm.runInContext(readFileSync(path.join(REPO, 'website', 'pull', 'js', 'analysis.js'), 'utf8'), ctx);
  return ctx.window.PullAnalysis;
}

export function readPdb(name) {
  for (const d of [path.join(REPO, 'pull-engine', 'fixtures'), path.join(REPO, 'tests', 'pull', 'fixtures')]) {
    try { return readFileSync(path.join(d, name + '.pdb'), 'latin1'); } catch { }
  }
  throw new Error('missing fixture ' + name);
}

// Statistics used by the gates.
export function ranks(a) {
  const idx = a.map((v, i) => [v, i]).sort((x, y) => x[0] - y[0]);
  const r = new Array(a.length);
  for (let i = 0; i < idx.length;) {
    let j = i; while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j++;
    for (let k = i; k <= j; k++) r[idx[k][1]] = (i + j) / 2 + 1;
    i = j + 1;
  }
  return r;
}
export function spearman(x, y) {
  const rx = ranks(x), ry = ranks(y), n = x.length;
  const mx = rx.reduce((s, v) => s + v, 0) / n, my = ry.reduce((s, v) => s + v, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) { sxy += (rx[i] - mx) * (ry[i] - my); sxx += (rx[i] - mx) ** 2; syy += (ry[i] - my) ** 2; }
  return sxy / Math.sqrt(sxx * syy);
}
const erfc = x => { // Numerical Recipes erfc, |error| < 1.2e-7
  const z = Math.abs(x), t = 1 / (1 + 0.5 * z);
  const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
  return x >= 0 ? r : 2 - r;
};
// One-sided Mann–Whitney U, H1: x > y. Normal approximation with tie and continuity correction.
export function mannWhitneyGreater(x, y) {
  const all = [...x, ...y], r = ranks(all), n1 = x.length, n2 = y.length;
  const R1 = r.slice(0, n1).reduce((s, v) => s + v, 0);
  const U = R1 - n1 * (n1 + 1) / 2;
  const N = n1 + n2;
  const counts = {}; all.forEach(v => counts[v] = (counts[v] || 0) + 1);
  const tie = Object.values(counts).reduce((s, t) => s + (t ** 3 - t), 0);
  const sigma = Math.sqrt(n1 * n2 / 12 * ((N + 1) - tie / (N * (N - 1))));
  const z = (U - n1 * n2 / 2 - 0.5) / sigma;
  return { U, z, p: 0.5 * erfc(z / Math.SQRT2) };
}
