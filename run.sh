#!/usr/bin/env bash
# Launch PICO-8 with this cart
PICO8="${PICO8:-$HOME/Downloads/pico-8 2/PICO-8.app/Contents/MacOS/pico8}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
CART="$ROOT/game.p8"

exec "$PICO8" -root_path "$ROOT" -run "$CART"
