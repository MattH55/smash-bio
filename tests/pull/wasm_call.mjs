// Call the WebAssembly engine from Node (same V8 as Chrome).
// Usage: node wasm_call.mjs <request.json | -> [out.json]
// Prints wall time to stderr; writes the raw result bytes to out.json (or stdout).
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const wasmPath = path.join(here, "..", "..", "website", "pull", "wasm", "pull_engine.wasm");
const { instance } = await WebAssembly.instantiate(readFileSync(wasmPath), {});
const ex = instance.exports;

export function call(reqText) {
  const enc = new TextEncoder().encode(reqText);
  const p = ex.pe_alloc(enc.length);
  new Uint8Array(ex.memory.buffer, p, enc.length).set(enc);
  const out = ex.pe_call(p, enc.length);
  const n = ex.pe_result_len();
  const bytes = new Uint8Array(ex.memory.buffer, out, n).slice();
  ex.pe_free(out, n);
  return bytes;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const src = process.argv[2];
  const req = src === "-" ? readFileSync(0, "utf8") : readFileSync(src, "utf8");
  const t = performance.now();
  const bytes = call(req);
  console.error(`wasm call ${(performance.now() - t).toFixed(0)} ms, ${bytes.length} bytes`);
  if (process.argv[3]) writeFileSync(process.argv[3], bytes);
  else process.stdout.write(Buffer.from(bytes));
}
