// Worker pool for the pull engine: one wasm instance per worker, jobs handed out
// as workers free up, cancel = terminate every worker (a wasm call cannot be
// interrupted from outside) and start fresh ones.
'use strict';
window.PullPool = (function () {
  const WORKER_URL = 'js/engine-worker.js';
  const cores = Math.max(1, Math.min(16, navigator.hardwareConcurrency || 4));
  let workers = [];
  let nextId = 1;
  const make = () => new Worker(WORKER_URL);
  function size() { return workers.length; }
  function ensure(n) { while (workers.length < n) workers.push(make()); }
  function reset() { workers.forEach(w => w.terminate()); workers = []; }

  // Single call on a dedicated worker (structure parsing etc.).
  function one(req) {
    ensure(1);
    const w = workers[0];
    return new Promise((resolve, reject) => {
      const id = nextId++;
      const h = ev => {
        if (ev.data.id !== id) return;
        w.removeEventListener('message', h);
        if (!ev.data.ok) return reject(new Error(ev.data.error));
        const r = JSON.parse(ev.data.result);
        if (r.error) { const e = new Error(r.error.message + (r.error.detail ? ': ' + r.error.detail : '')); e.code = r.error.code; return reject(e); }
        resolve(r);
      };
      w.addEventListener('message', h);
      w.postMessage({ id, req });
    });
  }

  // Run many jobs. onDone(index, result|error, ms) per job; resolves when all finish.
  function runAll(jobs, { onDone, parallel } = {}) {
    const n = Math.max(1, Math.min(parallel || cores, jobs.length));
    ensure(n);
    let next = 0, active = 0, finished = 0, cancelled = false;
    const results = new Array(jobs.length);
    let resolveAll;
    const done = new Promise(r => (resolveAll = r));
    const pump = (w) => {
      if (cancelled) return;
      if (next >= jobs.length) { if (active === 0) resolveAll(results); return; }
      const idx = next++;
      const id = nextId++;
      active++;
      const h = ev => {
        if (ev.data.id !== id) return;
        w.removeEventListener('message', h);
        active--; finished++;
        let r;
        if (!ev.data.ok) r = { error: { code: 'worker', message: ev.data.error } };
        else { try { r = JSON.parse(ev.data.result); } catch (e) { r = { error: { code: 'parse', message: String(e) } }; } }
        results[idx] = r;
        if (onDone) onDone(idx, r, ev.data.ms, finished);
        if (finished === jobs.length) resolveAll(results); else pump(w);
      };
      w.addEventListener('message', h);
      w.postMessage({ id, req: jobs[idx] });
    };
    for (let i = 0; i < n; i++) pump(workers[i]);
    return {
      done,
      cancel() { cancelled = true; reset(); resolveAll(null); }
    };
  }
  return { cores, size, one, runAll, reset };
})();
