// Gate 5 (docs/pull/VALIDATION.md): determinism.
// (a) native build vs WebAssembly in Chrome, byte-identical result JSON, for one
//     protein run (1UBQ, quick) and one nucleic kinetic run;
// (b) two runs in Chrome byte-identical.
// Needs the static server on http://127.0.0.1:8791 serving website/ and the
// native example built (cargo build --release --examples).
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { writeFileSync, readFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { launch } from './cdp.mjs';
import { REPO, readPdb } from './run_jobs.mjs';

const BASE = process.env.BASE || 'http://127.0.0.1:8791/pull/';
const reqs = {
  protein_1UBQ_quick: { op: 'protein_run', pdb: readPdb('1UBQ'), chain: 'A', speed: 0.2, dt: 0.01, spring_k: 0.1, temperature: 0.5, friction: 1, seed: 1, max_samples: 1500, frames: 20 },
  nucleic_kinetic_hp20: { op: 'nucleic_kinetic', sequence: 'GAGTCCTGGATCCTGTCCGCTTTTGCGGACAGGATCCAGGACTC', temperature_k: 296.15, na_mm: 200, speed_nm_s: 100, refold: true, seed: 1, max_samples: 1500 },
};
const sha = s => createHash('sha256').update(s).digest('hex');
const exe = path.join(REPO, 'pull-engine', 'target', 'release', 'examples', process.platform === 'win32' ? 'api_call.exe' : 'api_call');
const td = mkdtempSync(path.join(tmpdir(), 'gate5-'));
const native = {};
for (const [k, r] of Object.entries(reqs)) {
  const rp = path.join(td, k + '.req.json'), op = path.join(td, k + '.out.json');
  writeFileSync(rp, JSON.stringify(r));
  execFileSync(exe, [rp, op], { stdio: 'ignore' });
  native[k] = sha(readFileSync(op));
}
const b = await launch({ port: 9335 });
const chrome = { run1: {}, run2: {} };
try {
  await b.goto(BASE + 'index.html');
  for (const run of ['run1', 'run2']) {
    for (const [k, r] of Object.entries(reqs)) {
      chrome[run][k] = await b.eval(`(async () => {
        const w = new Worker('js/engine-worker.js');
        const s = await new Promise((res, rej) => { w.onmessage = e => e.data.ok ? res(e.data.result) : rej(e.data.error); w.postMessage({ id: 1, req: ${JSON.stringify(JSON.stringify(r))} }); });
        w.terminate();
        const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
        return [...new Uint8Array(h)].map(x => x.toString(16).padStart(2, '0')).join('');
      })()`);
    }
  }
} finally { await b.close(); }
const a = Object.keys(reqs).every(k => native[k] === chrome.run1[k]);
const bb = Object.keys(reqs).every(k => chrome.run1[k] === chrome.run2[k]);
const out = {
  gate: '5', chrome: b.version, native, chrome_hashes: chrome, a, b: bb,
  detail_a: `${Object.keys(reqs).join(', ')}: SHA-256 native ${a ? '=' : '≠'} Chrome (${b.version}).`,
  detail_b: `Two fresh workers in Chrome: ${bb ? 'identical' : 'different'} hashes.`,
};
writeFileSync(path.join(REPO, 'tests', 'pull', 'results', 'gate5.json'), JSON.stringify(out, null, 1));
console.log(JSON.stringify({ a, b: bb, native, chrome }, null, 1));
