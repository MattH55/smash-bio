//! Engine errors. Every error becomes a structured JSON `{"error":...}` rather
//! than a panic, because the browser is the caller and a trap in WASM loses the
//! message. `panic = "abort"` is set in the release profile, so errors must not
//! rely on unwinding.

use std::fmt;

#[derive(Debug, Clone)]
pub struct EngineError {
    /// Stable machine-readable tag the UI keys on.
    pub code: String,
    pub message: String,
    /// Optional detail, e.g. the offending JSON path or a residue count.
    pub detail: Option<String>,
}

impl EngineError {
    pub fn new(code: &str, message: impl Into<String>) -> EngineError {
        EngineError { code: code.to_string(), message: message.into(), detail: None }
    }
    pub fn with(self, detail: impl Into<String>) -> EngineError {
        EngineError { detail: Some(detail.into()), ..self }
    }

    // Fixed vocabulary used across the browser layer and documented in
    // docs/pull/ARCHITECTURE.md.
    pub fn invalid_json(detail: impl Into<String>) -> EngineError {
        EngineError::new("invalid_json", "input is not valid JSON").with(detail)
    }
    pub fn missing_field(field: &str) -> EngineError {
        EngineError::new("missing_field", format!("required field absent: {field}"))
    }
    pub fn bad_value(field: &str, detail: impl Into<String>) -> EngineError {
        EngineError::new("bad_value", format!("invalid value for {field}")).with(detail)
    }
    pub fn unsupported(detail: impl Into<String>) -> EngineError {
        EngineError::new("unsupported_record", "this construct is outside the model's scope")
            .with(detail)
    }
    pub fn too_large(detail: impl Into<String>) -> EngineError {
        // A browser tab has a hard memory ceiling; refusing early is better than
        // an out-of-memory tab crash.
        EngineError::new("structure_too_large", "structure exceeds the configured limit")
            .with(detail)
    }
    pub fn divergence(detail: impl Into<String>) -> EngineError {
        EngineError::new("numerical_divergence", "the integrator diverged").with(detail)
    }
    pub fn not_run(reason: impl Into<String>) -> EngineError {
        // Mirrors the reference pipeline's rule: a null simulation is not a zero.
        EngineError::new("not_run", "simulation not run").with(reason)
    }
}

impl fmt::Display for EngineError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match &self.detail {
            Some(d) => write!(f, "{}: {} ({})", self.code, self.message, d),
            None => write!(f, "{}: {}", self.code, self.message),
        }
    }
}

impl From<crate::json::JsonErr> for EngineError {
    fn from(e: crate::json::JsonErr) -> EngineError {
        EngineError::invalid_json(e.0)
    }
}

pub type EngineResult<T> = Result<T, EngineError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn display_includes_code_and_detail() {
        let e = EngineError::bad_value("n_steps", "0 not allowed");
        let s = e.to_string();
        assert!(s.contains("bad_value"), "{s}");
        assert!(s.contains("n_steps"), "{s}");
        assert_eq!(e.code, "bad_value");
        assert_eq!(e.detail.as_deref(), Some("0 not allowed"));
    }

    #[test]
    fn json_error_converts() {
        let e: EngineError = crate::json::JsonErr("boom".into()).into();
        assert_eq!(e.code, "invalid_json");
        assert_eq!(e.detail.as_deref(), Some("boom"));
    }
}
