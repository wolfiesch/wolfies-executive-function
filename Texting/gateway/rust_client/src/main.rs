//! Fast Rust client for the Wolfies iMessage daemon.
//!
//! This client speaks the NDJSON protocol over a Unix domain socket,
//! providing a significant speedup over the Python client by eliminating
//! the Python interpreter startup overhead.

mod client;
mod protocol;

use clap::{Parser, Subcommand};
use protocol::{OutputControls, Request};
use serde_json::{json, Map, Value};
use std::process::ExitCode;

/// Fast Rust client for the Wolfies iMessage daemon.
#[derive(Parser, Debug)]
#[command(name = "wolfies-daemon-client")]
#[command(version, about, long_about = None)]
struct Cli {
    /// Unix socket path
    #[arg(long, default_value_t = default_socket_path())]
    socket: String,

    /// Socket timeout in seconds
    #[arg(long, default_value_t = 2.0)]
    timeout: f64,

    /// Print full response wrapper (for debugging)
    #[arg(long)]
    raw_response: bool,

    /// Pretty-print JSON output
    #[arg(long)]
    pretty: bool,

    /// Use minimal JSON preset (lowest token cost)
    #[arg(long)]
    minimal: bool,

    /// Use compact JSON output
    #[arg(long)]
    compact: bool,

    /// Comma-separated field allowlist (overrides presets)
    #[arg(long)]
    fields: Option<String>,

    /// Truncate text fields to this length
    #[arg(long)]
    max_text_chars: Option<u32>,

    /// Search text column only (faster, for text_search and bundle)
    #[arg(long)]
    text_only_search: bool,

    #[command(subcommand)]
    command: Command,
}

fn default_socket_path() -> String {
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    format!("{}/.wolfies-imessage/daemon.sock", home)
}

#[derive(Subcommand, Debug)]
enum Command {
    /// Check daemon health
    Health,

    /// Get unread message count
    UnreadCount,

    /// Get unread messages
    Unread {
        /// Maximum messages to return
        #[arg(long, default_value_t = 20)]
        limit: u32,
    },

    /// Get recent messages from each conversation
    Recent {
        /// Maximum messages to return
        #[arg(long, default_value_t = 10)]
        limit: u32,
    },

    /// Search messages by text
    TextSearch {
        /// Search query (required)
        query: String,

        /// Maximum results to return
        #[arg(long, default_value_t = 20)]
        limit: u32,

        /// Only return messages since this ISO datetime
        #[arg(long)]
        since: Option<String>,
    },

    /// Get messages from a specific phone number
    MessagesByPhone {
        /// Phone number (e.g., +14155551234)
        phone: String,

        /// Maximum messages to return
        #[arg(long, default_value_t = 20)]
        limit: u32,
    },

    /// Bundled multi-operation request
    Bundle {
        /// Comma-separated sections to include (meta,unread_count,unread_messages,recent,search,contact_messages)
        #[arg(long)]
        include: Option<String>,

        /// Unread messages limit
        #[arg(long, default_value_t = 20)]
        unread_limit: u32,

        /// Recent messages limit
        #[arg(long, default_value_t = 10)]
        recent_limit: u32,

        /// Search query (required for search section)
        #[arg(long)]
        query: Option<String>,

        /// Search results limit
        #[arg(long, default_value_t = 20)]
        search_limit: u32,

        /// Phone number (required for contact_messages section)
        #[arg(long)]
        phone: Option<String>,

        /// Contact messages limit
        #[arg(long, default_value_t = 20)]
        messages_limit: u32,

        /// Only return messages since this ISO datetime
        #[arg(long)]
        since: Option<String>,
    },
}

fn main() -> ExitCode {
    let cli = Cli::parse();

    // Build output controls from global flags
    let controls = OutputControls {
        minimal: cli.minimal,
        compact: cli.compact,
        fields: cli.fields.clone(),
        max_text_chars: cli.max_text_chars,
        text_only: cli.text_only_search,
    };

    // Build the request based on subcommand
    let request = match &cli.command {
        Command::Health => Request::no_params("health"),

        Command::UnreadCount => Request::no_params("unread_count"),

        Command::Unread { limit } => {
            let mut params = Map::new();
            params.insert("limit".to_string(), json!(limit));
            controls.apply_to(&mut params);
            Request::new("unread_messages", Value::Object(params))
        }

        Command::Recent { limit } => {
            let mut params = Map::new();
            params.insert("limit".to_string(), json!(limit));
            controls.apply_to(&mut params);
            Request::new("recent", Value::Object(params))
        }

        Command::TextSearch { query, limit, since } => {
            let mut params = Map::new();
            params.insert("query".to_string(), json!(query));
            params.insert("limit".to_string(), json!(limit));
            if let Some(ref s) = since {
                params.insert("since".to_string(), json!(s));
            }
            controls.apply_to(&mut params);
            Request::new("text_search", Value::Object(params))
        }

        Command::MessagesByPhone { phone, limit } => {
            let mut params = Map::new();
            params.insert("phone".to_string(), json!(phone));
            params.insert("limit".to_string(), json!(limit));
            controls.apply_to(&mut params);
            Request::new("messages_by_phone", Value::Object(params))
        }

        Command::Bundle {
            include,
            unread_limit,
            recent_limit,
            query,
            search_limit,
            phone,
            messages_limit,
            since,
        } => {
            let mut params = Map::new();

            if let Some(ref inc) = include {
                params.insert("include".to_string(), json!(inc));
            }

            params.insert("unread_limit".to_string(), json!(unread_limit));
            params.insert("recent_limit".to_string(), json!(recent_limit));
            params.insert("search_limit".to_string(), json!(search_limit));
            params.insert("messages_limit".to_string(), json!(messages_limit));

            if let Some(ref q) = query {
                params.insert("query".to_string(), json!(q));
            }
            if let Some(ref p) = phone {
                params.insert("phone".to_string(), json!(p));
            }
            if let Some(ref s) = since {
                params.insert("since".to_string(), json!(s));
            }

            controls.apply_to(&mut params);
            Request::new("bundle", Value::Object(params))
        }
    };

    // Create client and send request
    let daemon_client = client::DaemonClient::new(&cli.socket, cli.timeout);

    match daemon_client.call(&request) {
        Ok(response) => {
            let output = client::emit_response(&response, cli.raw_response, cli.pretty);
            println!("{}", output);

            if response.ok {
                ExitCode::from(0)
            } else {
                ExitCode::from(1)
            }
        }
        Err(e) => {
            // Format client-side error as daemon-style response
            let error_json = client::DaemonClient::format_client_error(&e);
            let output = if cli.pretty {
                serde_json::to_string_pretty(&error_json).unwrap_or_else(|_| "{}".to_string())
            } else {
                serde_json::to_string(&error_json).unwrap_or_else(|_| "{}".to_string())
            };
            eprintln!("{}", output);
            ExitCode::from(2)
        }
    }
}
