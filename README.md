# PICO-8 Game Template

Template for starting new PICO-8 games. Copy this directory and start building.

## Quick Start

```bash
cp -r template/ my-new-game
cd my-new-game
git init
make run
```

## Structure

```
game.p8              -- cart file with #include directives, empty sprite/map/sfx data
Makefile             -- run, debug, lint, test, export (web/png/bin), clean
run.sh               -- quick-launch script
.gitignore           -- exports, caches, editor files
.claude/
  teacher.md         -- PICO-8 teaching prompt for Claude
src/
  main.lua           -- game loop skeleton (_init, _update60, _draw)
  utils.lua          -- tile(), has_solid(), overlaps(), dbg()/dbg_flush()
docs/
  pico8-syntax-reference.md
  pico8-p8scii-reference.md
  pico-8_manual.txt
  token-optimization.md
tools/
  p8lint.py          -- Lua linter for PICO-8
  debugview.py       -- live debug output viewer
tests/
  test_p8lint.py     -- linter unit tests
```

## Make Targets

| Target  | Description                                      |
|---------|--------------------------------------------------|
| `run`   | Launch the game in PICO-8                        |
| `debug` | Launch with live debug viewer (printh output)    |
| `lint`  | Lint all Lua code referenced by the cart         |
| `test`  | Run linter unit tests                            |
| `web`   | Export as HTML (game.html + game.js)             |
| `png`   | Export as cartridge PNG (needs a label via F7)    |
| `bin`   | Export as native executables (Mac/Win/Linux)     |
| `clean` | Remove exported files                            |

## Configuration

Set `PICO8` to override the PICO-8 binary path:

```bash
export PICO8=/path/to/pico8
make run
```

Default: `~/Downloads/pico-8 2/PICO-8.app/Contents/MacOS/pico8`
