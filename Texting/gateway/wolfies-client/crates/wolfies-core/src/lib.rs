//! Shared core library for Wolfies daemon clients.
//!
//! This crate provides the NDJSON protocol types and Unix socket client
//! that are shared across all Wolfies service clients (iMessage, Gmail,
//! Calendar, Reminders, etc.).

pub mod client;
pub mod protocol;

// Re-export commonly used types
pub use client::{emit_response, ClientError, DaemonClient};
pub use protocol::{ErrorPayload, Meta, OutputControls, Profile, Request, Response};
