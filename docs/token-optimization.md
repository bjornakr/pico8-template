# Token Optimization

PICO-8 has an 8192 token limit and a 65535 character limit. You'll almost always hit the token limit first.

## What counts as a token

Each of these is 1 token:
- Variable name (`player_x`)
- Operator (`+`, `-`, `=`)
- Keyword (`if`, `end`, `function`)
- Number (`42`)
- String literal (`"hello world"`)

Comments, whitespace, and semicolons are free.

`x = x + 1` = 4 tokens, regardless of variable name length.

## Checking token count

- `pico8-ls` VS Code extension shows it live
- `info` command inside PICO-8

## Shrinko8 (minifier)

The go-to tool for reducing token/char/compressed size.

- Repo: https://github.com/thisismypassport/shrinko8
- Requires Python 3.8+

```bash
pip install shrinko8

shrinko8 game.p8 game_min.p8 --focus-tokens       # reduce token count
shrinko8 game.p8 game_min.p8 --focus-chars         # reduce character count
shrinko8 game.p8 game_min.p8 --focus-compressed    # reduce compressed size
```

Flags can be combined. Also lints your code as a side effect.

## Manual optimization tricks

Community guide: https://github.com/seleb/PICO-8-Token-Optimizations

Key techniques:
- Store data in strings and parse at runtime instead of using tables
- Inline functions in hot paths (function call overhead is real)
- Use built-in API calls over custom implementations (they run natively)
