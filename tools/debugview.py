#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# ///
"""
Live debug viewer for PICO-8.

Reads pipe-delimited key=value debug output from stdin and displays it
as a continuously-updating terminal dashboard. Uses two threads to
decouple reading from rendering — the reader ingests lines as fast as
they arrive, while the renderer redraws at a fixed interval. This means
high-frequency input won't block on screen redraws, and only the latest
state is ever displayed.

Input format (one line per flush from PICO-8):
  key1=value1|key2=value2|key3=value3

Usage:
  make debug                                     # via Makefile
  tail -f debug.p8l | uv run tools/debugview.py  # standalone

PICO-8 side — use dbg() and dbg_flush() from utils.lua:
  dbg("player", player)
  dbg_flush()
"""

import sys
import threading
import time

# ANSI codes
CLEAR = "\033[2J\033[H"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
BOLD = "\033[1m"
RESET = "\033[0m"

RENDER_INTERVAL = 0.05  # 50ms

lock = threading.Lock()
keys: list[str] = []
vals: dict[str, str] = {}
dirty = False
done = False


def reader():
    """Read stdin line by line, parse key=value pairs, and update shared state.

    Runs in a daemon thread. Sets the dirty flag after each line so the
    renderer knows new data is available. Sets done=True on EOF.
    """
    global dirty, done
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        with lock:
            for pair in line.split("|"):
                if "=" not in pair:
                    continue
                key, val = pair.split("=", 1)
                key = key.strip()
                val = val.strip()
                if key not in vals:
                    keys.append(key)
                vals[key] = val
            dirty = True
    done = True


def render_once():
    """Snapshot the current state and redraw the screen if data has changed.

    Acquires the lock just long enough to copy keys/vals and clear the
    dirty flag, then renders outside the lock so the reader is never
    blocked by terminal I/O.
    """
    global dirty
    with lock:
        if dirty:
            snap_keys = list(keys)
            snap_vals = dict(vals)
            dirty = False
        else:
            return

    parts = [f"{CLEAR}{BOLD}{CYAN}PICO-8 DEBUG{RESET}", f"{DIM}{'─' * 36}{RESET}"]
    for key in snap_keys:
        parts.append(f"  {GREEN}{key:<20}{RESET} {YELLOW}{snap_vals[key]}{RESET}")
    parts.append(f"{DIM}{'─' * 36}{RESET}")
    sys.stdout.write("\n".join(parts) + "\n")
    sys.stdout.flush()


def renderer():
    """Render loop — redraws at RENDER_INTERVAL, plus one final pass after EOF."""
    while not done:
        render_once()
        time.sleep(RENDER_INTERVAL)
    render_once()  # final flush after reader is done


def main():
    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()
    try:
        renderer()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
