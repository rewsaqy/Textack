//! textack-sim: sim worker in Rust (protocol v1, stdio).
//!
//! Reads newline-delimited JSON from stdin, writes replies to stdout.
//! Blank lines are skipped; unparseable lines carry no envelope and
//! produce no reply. EOF ends the loop (exit 0).

mod game;
mod mt;
mod protocol;

use std::io::{BufRead, Write};
use std::time::{SystemTime, UNIX_EPOCH};

use serde_json::Value;

use crate::mt::Mt;

fn nanos_seed() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos() as u64)
        .unwrap_or(0x243F_6A88_85A3_08D3)
}

fn main() {
    let stdin = std::io::stdin();
    let mut out = std::io::stdout();
    let mut live = Mt::from_seed(nanos_seed());
    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        if line.trim().is_empty() {
            continue;
        }
        let reply = match serde_json::from_str::<Value>(&line) {
            Ok(v) => protocol::handle(&v, &mut live),
            Err(_) => continue,
        };
        let mut s = serde_json::to_string(&reply).unwrap_or_else(|_| {
            "{\"v\":1,\"t\":\"error\",\"code\":\"bad-message\"}".to_string()
        });
        s.push('\n');
        if out.write_all(s.as_bytes()).is_err() {
            break;
        }
        if out.flush().is_err() {
            break;
        }
        if reply.get("t").and_then(|t| t.as_str()) == Some("bye") {
            break;
        }
    }
}
