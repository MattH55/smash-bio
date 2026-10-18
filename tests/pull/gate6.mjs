// Gate 6 (docs/pull/VALIDATION.md): performance in Chrome through the real page.
// Titin I27 "standard" run (3 speeds x 10 replicas) must finish in < 60 s with
// navigator.hardwareConcurrency workers. Also times a larger structure.
// Run on an otherwise idle machine. Needs the static server on :8791.
import { writeFileSync } from 'node:fs';
import path from 'node:path';
import { launch } from './cdp.mjs';
import { REPO } from './run_jobs.mjs';

const BASE = process.env.BASE || 'http://127.0.0.1:8791/pull/';
const b = await launch({ port: 9336 });
const timings = [];
try {
  for (const [id, proto] of [['1TIT', 'standard'], ['2L7A', 'standard'], ['1TIT', 'quick']]) {
    await b.goto(BASE + `index.html#m=protein&src=pdb:${id}&inst=afm&proto=${proto}`);
    await b.waitFor(`document.getElementById('load-status').classList.contains('ok')`, 60000);
    const info = await b.eval(`document.getElementById('load-status').textContent`);
    const cores = await b.eval('navigator.hardwareConcurrency');
    await b.eval(`document.getElementById('run-btn').click()`);
    const t0 = Date.now();
    await b.waitFor(`!document.getElementById('results').hidden || document.getElementById('run-status').classList.contains('err')`, 900000, 200);
    const s = (Date.now() - t0) / 1000;
    const st = await b.eval(`document.getElementById('run-status').textContent`);
    timings.push({ structure: id, protocol: proto, seconds: s, workers: cores, status: st, loaded: info });
    console.log(id, proto, s.toFixed(1), 's |', st);
  }
} finally { await b.close(); }
const i27 = timings.find(t => t.structure === '1TIT' && t.protocol === 'standard');
const out = { gate: '6', chrome: b.version, timings, pass: i27.seconds < 60, detail: `I27 standard (30 trajectories): ${i27.seconds.toFixed(1)} s with ${i27.workers} workers in Chrome ${b.version.replace('Chrome/', '')}; talin R3 (2L7A, 125 residues) standard: ${timings[1].seconds.toFixed(1)} s; I27 quick: ${timings[2].seconds.toFixed(1)} s.` };
writeFileSync(path.join(REPO, 'tests', 'pull', 'results', 'gate6.json'), JSON.stringify(out, null, 1));
console.log(out.detail, out.pass ? 'PASS' : 'FAIL');
