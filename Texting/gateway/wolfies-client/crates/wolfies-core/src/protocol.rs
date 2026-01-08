//! Protocol types for the Wolfies daemon NDJSON protocol.
//!
//! The daemon uses newline-delimited JSON (NDJSON) over a Unix domain socket.
//! Each request and response is a single JSON object followed by a newline.

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// A request to the daemon.
///
/// Request format:
/// ```json
/// {"id": "uuid", "v": 1, "method": "...", "params": {...}}
/// ```
#[derive(Debug, Serialize)]
pub struct Request {
    /// Unique request identifier (echoed in response)
    pub id: String,
    /// Protocol version (always 1)
    pub v: u8,
    /// Method name (e.g., "health", "unread_count", "bundle")
    pub method: String,
    /// Method parameters (empty object `{}` if none)
    pub params: Value,
}

impl Request {
    /// Create a new request with the given method and parameters.
    pub fn new(method: impl Into<String>, params: Value) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            v: 1,
            method: method.into(),
            params,
        }
    }

    /// Create a request with no parameters.
    pub fn no_params(method: impl Into<String>) -> Self {
        Self::new(method, Value::Object(serde_json::Map::new()))
    }
}

/// A response from the daemon.
///
/// Response format:
/// ```json
/// {"id": "uuid", "ok": true/false, "result": {...}, "error": null, "meta": {...}}
/// ```
#[derive(Debug, Deserialize)]
pub struct Response {
    /// Echo of the request id
    pub id: String,
    /// Success flag
    pub ok: bool,
    /// Result payload (present when ok=true)
    pub result: Option<Value>,
    /// Error payload (present when ok=false)
    pub error: Option<ErrorPayload>,
    /// Metadata (timing, protocol version)
    pub meta: Option<Meta>,
}

/// Error payload returned by the daemon.
#[derive(Debug, Deserialize, Serialize)]
pub struct ErrorPayload {
    /// Error code (e.g., "INVALID_JSON", "UNKNOWN_METHOD", "ERROR")
    pub code: String,
    /// Human-readable error message
    pub message: String,
    /// Optional additional details
    pub details: Option<Value>,
}

/// Response metadata.
#[derive(Debug, Deserialize)]
pub struct Meta {
    /// Time spent processing in daemon (milliseconds)
    pub server_ms: Option<f64>,
    /// Protocol version
    pub protocol_v: Option<u8>,
    /// Serialization time (milliseconds, only when profiling enabled)
    pub serialize_ms: Option<f64>,
    /// Profiling data (only when WOLFIES_PROFILE=1)
    pub profile: Option<Profile>,
}

/// Profiling data from daemon (optional).
#[derive(Debug, Deserialize)]
pub struct Profile {
    /// SQLite query time (milliseconds)
    pub sqlite_ms: Option<f64>,
    /// Result building time (milliseconds)
    pub build_ms: Option<f64>,
    /// Contact resolution time (milliseconds)
    pub resolve_ms: Option<f64>,
}

/// Output control parameters for daemon requests.
///
/// These are passed in `params` to control output format and size.
#[derive(Debug, Default, Clone)]
pub struct OutputControls {
    /// Use minimal JSON preset (lowest token cost)
    pub minimal: bool,
    /// Use compact JSON output
    pub compact: bool,
    /// Comma-separated field allowlist (overrides presets)
    pub fields: Option<String>,
    /// Truncate text fields to this length
    pub max_text_chars: Option<u32>,
    /// Search text column only (faster, for text_search and bundle)
    pub text_only: bool,
}

impl OutputControls {
    /// Add output control fields to a JSON object.
    pub fn apply_to(&self, obj: &mut serde_json::Map<String, Value>) {
        if self.minimal {
            obj.insert("minimal".to_string(), Value::Bool(true));
        }
        if self.compact {
            obj.insert("compact".to_string(), Value::Bool(true));
        }
        if let Some(ref fields) = self.fields {
            obj.insert("fields".to_string(), Value::String(fields.clone()));
        }
        if let Some(chars) = self.max_text_chars {
            obj.insert("max_text_chars".to_string(), Value::Number(chars.into()));
        }
        if self.text_only {
            obj.insert("text_only".to_string(), Value::Bool(true));
        }
    }
}
