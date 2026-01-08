//! Unix socket client for the Wolfies daemon.

use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::UnixStream;
use std::path::Path;
use std::time::Duration;

use crate::protocol::{ErrorPayload, Request, Response};
use thiserror::Error;

/// Errors that can occur when communicating with the daemon.
#[derive(Error, Debug)]
pub enum ClientError {
    #[error("Socket not found: {0}")]
    SocketNotFound(String),

    #[error("Connection failed: {0}")]
    ConnectionFailed(#[from] std::io::Error),

    #[error("JSON serialization error: {0}")]
    SerializeError(#[source] serde_json::Error),

    #[error("JSON parse error: {0}")]
    ParseError(#[source] serde_json::Error),

    #[error("Empty response from daemon")]
    EmptyResponse,

    #[error("Timeout waiting for response")]
    Timeout,
}

/// A client for the Wolfies daemon.
pub struct DaemonClient {
    socket_path: String,
    timeout: Duration,
}

impl DaemonClient {
    /// Create a new client with the given socket path and timeout.
    pub fn new(socket_path: impl Into<String>, timeout_secs: f64) -> Self {
        Self {
            socket_path: socket_path.into(),
            timeout: Duration::from_secs_f64(timeout_secs),
        }
    }

    /// Create a client with the default socket path.
    pub fn default_socket(timeout_secs: f64) -> Self {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let socket_path = format!("{}/.wolfies-imessage/daemon.sock", home);
        Self::new(socket_path, timeout_secs)
    }

    /// Send a request to the daemon and receive a response.
    pub fn call(&self, request: &Request) -> Result<Response, ClientError> {
        let path = Path::new(&self.socket_path);

        // Check if socket exists
        if !path.exists() {
            return Err(ClientError::SocketNotFound(self.socket_path.clone()));
        }

        // Connect to socket
        let stream = UnixStream::connect(path)?;
        stream.set_read_timeout(Some(self.timeout))?;
        stream.set_write_timeout(Some(self.timeout))?;

        // Send request as NDJSON (compact JSON + newline)
        let mut writer = &stream;
        let json = serde_json::to_string(request).map_err(ClientError::SerializeError)?;
        writer.write_all(json.as_bytes())?;
        writer.write_all(b"\n")?;
        writer.flush()?;

        // Read one NDJSON line
        let mut reader = BufReader::new(&stream);
        let mut line = String::new();
        let bytes_read = reader.read_line(&mut line)?;

        if bytes_read == 0 {
            return Err(ClientError::EmptyResponse);
        }

        // Parse response
        let response: Response = serde_json::from_str(&line).map_err(ClientError::ParseError)?;

        Ok(response)
    }

    /// Format a client-side error as a daemon-style error response.
    pub fn format_client_error(err: &ClientError) -> serde_json::Value {
        let (code, message, details) = match err {
            ClientError::SocketNotFound(path) => (
                "DAEMON_NOT_RUNNING",
                format!("Socket not found: {}", path),
                Some(serde_json::json!({ "socket": path })),
            ),
            ClientError::ConnectionFailed(e) => (
                "CONNECT_FAILED",
                e.to_string(),
                Some(serde_json::json!({
                    "exception_type": format!("{:?}", e.kind())
                })),
            ),
            ClientError::Timeout => ("TIMEOUT", "Timeout waiting for response".to_string(), None),
            ClientError::EmptyResponse => {
                ("EMPTY_RESPONSE", "Empty response from daemon".to_string(), None)
            }
            ClientError::SerializeError(e) => {
                ("SERIALIZE_ERROR", format!("JSON serialization error: {}", e), None)
            }
            ClientError::ParseError(e) => {
                ("PARSE_ERROR", format!("JSON parse error: {}", e), None)
            }
        };

        serde_json::json!({
            "ok": false,
            "error": {
                "code": code,
                "message": message,
                "details": details
            }
        })
    }
}

/// Emit the response to stdout according to output mode.
///
/// - Default: print `result` only (or error wrapper if failed)
/// - `--raw-response`: print full response wrapper
/// - `--pretty`: pretty-print JSON
pub fn emit_response(response: &Response, raw: bool, pretty: bool) -> String {
    if raw {
        // Print full response wrapper
        if pretty {
            serde_json::to_string_pretty(response).unwrap_or_else(|_| "{}".to_string())
        } else {
            serde_json::to_string(response).unwrap_or_else(|_| "{}".to_string())
        }
    } else if !response.ok {
        // Error: print stable error shape
        let err = response.error.as_ref().map(|e| {
            serde_json::json!({
                "code": e.code,
                "message": e.message,
                "details": e.details
            })
        }).unwrap_or_else(|| {
            serde_json::json!({
                "code": "ERROR",
                "message": "unknown error",
                "details": null
            })
        });
        let out = serde_json::json!({ "ok": false, "error": err });
        if pretty {
            serde_json::to_string_pretty(&out).unwrap_or_else(|_| "{}".to_string())
        } else {
            serde_json::to_string(&out).unwrap_or_else(|_| "{}".to_string())
        }
    } else {
        // Success: print result only
        let result = response.result.as_ref().unwrap_or(&serde_json::Value::Null);
        if pretty {
            serde_json::to_string_pretty(result).unwrap_or_else(|_| "null".to_string())
        } else {
            serde_json::to_string(result).unwrap_or_else(|_| "null".to_string())
        }
    }
}

// Custom serialization for Response (needed for raw output)
impl serde::Serialize for Response {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        use serde::ser::SerializeStruct;
        let mut state = serializer.serialize_struct("Response", 5)?;
        state.serialize_field("id", &self.id)?;
        state.serialize_field("ok", &self.ok)?;
        state.serialize_field("result", &self.result)?;
        state.serialize_field("error", &self.error)?;
        state.serialize_field("meta", &self.meta)?;
        state.end()
    }
}

impl serde::Serialize for crate::protocol::Meta {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        use serde::ser::SerializeStruct;
        let mut state = serializer.serialize_struct("Meta", 4)?;
        state.serialize_field("server_ms", &self.server_ms)?;
        state.serialize_field("protocol_v", &self.protocol_v)?;
        if self.serialize_ms.is_some() {
            state.serialize_field("serialize_ms", &self.serialize_ms)?;
        }
        if self.profile.is_some() {
            state.serialize_field("profile", &self.profile)?;
        }
        state.end()
    }
}

impl serde::Serialize for crate::protocol::Profile {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        use serde::ser::SerializeStruct;
        let mut state = serializer.serialize_struct("Profile", 3)?;
        state.serialize_field("sqlite_ms", &self.sqlite_ms)?;
        state.serialize_field("build_ms", &self.build_ms)?;
        state.serialize_field("resolve_ms", &self.resolve_ms)?;
        state.end()
    }
}
