use std::io::{self, BufRead, Write};

const CLEAR: &str = "\x1b[2J\x1b[H";
const DIM: &str = "\x1b[2m";
const CYAN: &str = "\x1b[36m";
const YELLOW: &str = "\x1b[33m";
const GREEN: &str = "\x1b[32m";
const BOLD: &str = "\x1b[1m";
const RESET: &str = "\x1b[0m";

fn main() {
    let stdin = io::stdin();
    let mut stdout = io::stdout().lock();
    let mut keys: Vec<String> = Vec::new();
    let mut vals: Vec<String> = Vec::new();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        let line = line.trim().to_string();
        if line.is_empty() {
            continue;
        }

        for pair in line.split('|') {
            let Some((key, val)) = pair.split_once('=') else {
                continue;
            };
            let key = key.trim();
            let val = val.trim();
            if let Some(pos) = keys.iter().position(|k| k == key) {
                vals[pos] = val.to_string();
            } else {
                keys.push(key.to_string());
                vals.push(val.to_string());
            }
        }

        let _ = write!(stdout, "{CLEAR}{BOLD}{CYAN}PICO-8 DEBUG{RESET}\n{DIM}────────────────────────────────────{RESET}\n");
        for (key, val) in keys.iter().zip(vals.iter()) {
            let _ = write!(stdout, "  {GREEN}{key:<20}{RESET} {YELLOW}{val}{RESET}\n");
        }
        let _ = write!(stdout, "{DIM}────────────────────────────────────{RESET}\n");
        let _ = stdout.flush();
    }
}
