//! Native twin of tests/pull/wasm_call.mjs: run one API request from a file and
//! write the raw result bytes, for the Gate 5 byte comparison.
//! Usage: cargo run --release --example api_call -- <request.json> <out.json>
use std::time::Instant;

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let req = std::fs::read_to_string(&a[1]).expect("request");
    let t = Instant::now();
    let out = pull_engine::api::call(&req);
    eprintln!("native call {:.0} ms, {} bytes", t.elapsed().as_secs_f64() * 1e3, out.len());
    std::fs::write(&a[2], out.as_bytes()).expect("write");
}
