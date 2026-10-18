// Web Worker hosting one instance of the pull-engine WebAssembly module.
// Message in:  {id, req}   (req: a JSON-serialisable request object or string)
// Message out: {id, ok, result (string), ms}  or  {id, ok:false, error}
'use strict';
let ex = null;
const ready = (async () => {
  const url = new URL('../wasm/pull_engine.wasm', self.location.href);
  const resp = await fetch(url);
  const bytes = await resp.arrayBuffer();
  const { instance } = await WebAssembly.instantiate(bytes, {});
  ex = instance.exports;
})();

function call(text) {
  const enc = new TextEncoder().encode(text);
  const p = ex.pe_alloc(enc.length);
  new Uint8Array(ex.memory.buffer, p, enc.length).set(enc);
  const out = ex.pe_call(p, enc.length);
  const n = ex.pe_result_len();
  const s = new TextDecoder().decode(new Uint8Array(ex.memory.buffer, out, n));
  ex.pe_free(out, n);
  return s;
}

self.onmessage = async (ev) => {
  const { id, req } = ev.data;
  try {
    await ready;
    const t = performance.now();
    const result = call(typeof req === 'string' ? req : JSON.stringify(req));
    self.postMessage({ id, ok: true, result, ms: performance.now() - t });
  } catch (e) {
    self.postMessage({ id, ok: false, error: String(e && e.message || e) });
  }
};
