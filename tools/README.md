# Tools

Development tools for the PICO-8 project. All tools are standalone Python scripts run via [uv](https://docs.astral.sh/uv/).

## debugview.py

Live debug dashboard that displays PICO-8 variable state in the terminal.

PICO-8 sends pipe-delimited `key=value` pairs via `printh()` (see `dbg()` / `dbg_flush()` in `src/utils.lua`). The viewer parses these and displays them as a continuously-updating table.

**Architecture:** Two threads — a reader that ingests stdin as fast as possible, and a renderer that redraws at a fixed 50ms interval. Only the latest state is ever displayed, so high-frequency input doesn't cause rendering bottlenecks.

```
make debug
# or standalone:
tail -f debug.p8l | uv run tools/debugview.py
```

## p8lint.py

Linter for PICO-8 Lua code. Reads a `.p8` cart, resolves `#include` directives, and checks for common issues:

- `missing-local` — variable assigned without `local` inside a function
- `global-outside-init` — global first assigned outside `_init()`
- `duplicate-function` — non-local function defined more than once
- `unused-variable` — local declared but never read
- `unreachable-code` — code after exhaustive if/else returns
- `missing-callback` — `_init`, `_update`/`_update60`, or `_draw` not defined
- `undefined-variable` — variable used but never assigned

Suppress a warning on a specific line with `--lint:ignore=rule-name`.

```
make lint
# or standalone:
uv run tools/p8lint.py game.p8
```
