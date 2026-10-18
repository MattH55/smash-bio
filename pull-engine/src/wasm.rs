//! Raw C ABI for the browser (no wasm-bindgen, see ARCHITECTURE.md).
//!
//! JavaScript protocol (website/pull/js/engine-worker.js):
//! 1. `ptr = pe_alloc(len)`; copy UTF-8 request bytes into memory at `ptr`.
//! 2. `out = pe_call(ptr, len)` - consumes the request buffer, returns a pointer
//!    to the UTF-8 result; `pe_result_len()` gives its byte length.
//! 3. Read the result, then `pe_free(out, pe_result_len())`.

use std::cell::Cell;

thread_local! {
    static RESULT_LEN: Cell<usize> = const { Cell::new(0) };
}

#[no_mangle]
pub extern "C" fn pe_alloc(len: usize) -> *mut u8 {
    let mut v: Vec<u8> = Vec::with_capacity(len.max(1));
    let p = v.as_mut_ptr();
    std::mem::forget(v);
    p
}

/// # Safety
/// `ptr` must come from `pe_alloc(len)` or be a result pointer with its length.
#[no_mangle]
pub unsafe extern "C" fn pe_free(ptr: *mut u8, len: usize) {
    if !ptr.is_null() {
        drop(Vec::from_raw_parts(ptr, 0, len.max(1)));
    }
}

/// # Safety
/// `ptr`/`len` must describe a buffer from `pe_alloc` holding the request.
#[no_mangle]
pub unsafe extern "C" fn pe_call(ptr: *mut u8, len: usize) -> *mut u8 {
    let req = Vec::from_raw_parts(ptr, len, len.max(1));
    let out = match std::str::from_utf8(&req) {
        Ok(s) => crate::api::call(s),
        Err(_) => crate::api::error_json(&crate::EngineError::invalid_json("request is not UTF-8")),
    };
    drop(req);
    let mut bytes = out.into_bytes();
    bytes.shrink_to_fit();
    let n = bytes.len();
    let p = bytes.as_mut_ptr();
    std::mem::forget(bytes);
    RESULT_LEN.with(|c| c.set(n));
    p
}

#[no_mangle]
pub extern "C" fn pe_result_len() -> usize {
    RESULT_LEN.with(|c| c.get())
}
