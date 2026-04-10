# PICO-8 P8SCII Control Codes Reference

> Extracted from the PICO-8 v0.2.7 Manual

P8SCII control codes are special characters (CHR(0)..CHR(15)) that modify text rendering, cursor position, and can even play audio when used in `PRINT()` strings. They work in all contexts -- interactive console and runtime code.

Parameters use a superset of hex: `0`..`f` = 0..15, `g` = 16, `h` = 17, etc.

Only cursor position and foreground colour persist between `PRINT()` calls. All other attributes reset each call (unless defaults are set via memory, see below).

---

## Control Codes

| Code | Escape | Effect |
|------|--------|--------|
| 0 | `\0` | Terminate printing |
| 1 | `\*` | Repeat next char P0 times. `?"\*3a"` -> `aaa` |
| 2 | `\#` | Draw solid background with colour P0 |
| 3 | `\-` | Shift cursor horizontally by P0-16 pixels |
| 4 | `\|` | Shift cursor vertically by P0-16 pixels |
| 5 | `\+` | Shift cursor by P0-16, P1-16 pixels |
| 6 | `\^` | Special command (see below) |
| 7 | `\a` | Audio (see below) |
| 8 | `\b` | Backspace |
| 9 | `\t` | Tab |
| a | `\n` | Newline |
| b | `\v` | Decorate previous character (see below) |
| c | `\f` | Set foreground colour |
| d | `\r` | Carriage return |
| e | `\014` | Switch to custom font (defined at 0x5600) |
| f | `\015` | Switch to default font |

---

## Special Commands (`\^`)

### Cursor and Layout

| Command | Effect |
|---------|--------|
| `\^cP0` | CLS to colour P0, set cursor to 0,0 |
| `\^g` | Move cursor to home position |
| `\^h` | Set home to current cursor position |
| `\^jP0P1` | Jump to absolute P0\*4, P1\*4 (screen pixels) |
| `\^rP0` | Set right-hand character wrap boundary to P0\*4 |
| `\^sP0` | Set tab stop width to P0 pixels |
| `\^xP0` | Set character width (default: 4) |
| `\^yP0` | Set character height (default: 6) |

### Timing

| Command | Effect |
|---------|--------|
| `\^1`..`\^9` | Skip 1, 2, 4, 8, 16, 32, 64, 128, 256 frames |
| `\^dP0` | Set delay to P0 frames per character (typewriter effect) |

### Rendering Modes

Prefix with `-` to disable (e.g. `\^-i` to turn off invert).

| Command | Effect |
|---------|--------|
| `\^w` | Wide mode (2x1 scale) |
| `\^t` | Tall mode (1x2 scale) |
| `\^=` | Stripey mode (draw only even pixels when wide/tall) |
| `\^p` | Pinball mode (wide + tall + stripey) |
| `\^i` | Invert |
| `\^b` | Border: toggle 1px padding on left and top (on by default) |
| `\^#` | Solid background (off by default, enabled automatically by `\#`) |
| `\^u` | Underline |

```lua
?"\^w\^tBIG"           -- 2x2 scaled text
?"\^i inverted \^-i normal"
?"\^pPINBALL MODE"
```

---

## Outlines (`\^o`)

Format: `\^oCNN` where C is colour and NN is a 2-hex-digit neighbour bitfield.

```
0x01  0x02  0x04
0x08   --   0x10
0x20  0x40  0x80
```

| Example | Effect |
|---------|--------|
| `?"\^o801hey"` | Draw pixel up-left of each foreground pixel |
| `?"\f7\^oc5aoutline"` | Blue outline on left, right, top, bottom |
| `?"\fe\^w\^t\^o7ffchunky"` | Full outline, wide+tall |

Special colour values for the colour parameter:
- `$` -- use current colour
- `!` -- use current colour, skip drawing interior

```lua
?" \^o!ff empty interior"
```

Outline costs ~2x CPU of non-outlined text.

---

## Inline Audio (`\a`)

```lua
?"\a"       -- single beep
?"\a12"     -- play existing SFX 12
```

When no SFX index is given, an unused SFX slot (60..63) is auto-selected.

### SFX Attributes (appear once at start)

| Command | Effect |
|---------|--------|
| `sP0` | Set SFX speed |
| `lP0P1` | Set loop start and end points |

### Note Data

Notes are written as `a`..`g`, optionally followed by `#` (sharp) or `-` (flat) and octave number. `.` for empty/rest notes.

| Command | Effect |
|---------|--------|
| `iP0` | Set instrument (default: 5) |
| `vP0` | Set volume (default: 5) |
| `xP0` | Set effect (default: 0) |

```lua
?"\ace-g"                   -- minor triad
?"\ac..e-..g"               -- staccato minor triad
?"\as4x5c1egc2egc3egc4"     -- speed 4, effect 5, arpeggio from C1
```

---

## Decoration Characters (`\v`)

Format: `\vP0char` -- draws `char` at an offset relative to the previous character, then restores cursor position.

Offset calculation from P0:
- `x = (P0 % 4) - 2`
- `y = (P0 \ 4) - 8`

Starts at (-2, -8) in reading order. P0=3 means (+1, -8), P0=4 means (-2, -7), etc.

```lua
PRINT"\ncafe\vb,!"   -- writes "cafe!" with acute accent on 'e' using a comma
-- P0='b'=11: x=(11%4)-2=1, y=(11\4)-8=-6
```

---

## One-off Characters (`\^.` and `\^:`)

Inline character data (8x8 bitfield, 1 bit/pixel, each byte = one row, low bit on left):

| Command | Format |
|---------|--------|
| `\^.` | 8 bytes of raw binary data |
| `\^:` | 16 hex characters |
| `\^,` and `\^;` | Same but respect padding state |

```lua
?"\^:447cb67c3e7f0106"      -- print a cat
?"\#3\^;447cb67c3e7f0106"   -- cat with background, respecting padding
```

---

## Raw Memory Writes

| Command | Effect |
|---------|--------|
| `\^@addrNNNN[data]` | Poke NNNN bytes to address addr |
| `\^!addr[data]` | Poke all remaining characters to address addr |

```lua
?"\^@70000004xxxxhello"  -- write 4 bytes to video memory at 0x7000
```

---

## Default Attributes (Persistent)

Set defaults via memory so attributes persist across `PRINT()` calls:

### 0x5F58 (bitfield)

| Bit | Effect |
|-----|--------|
| 0x1 | Enable bits 1..7 below |
| 0x2 | Padding |
| 0x4 | Wide |
| 0x8 | Tall |
| 0x10 | Solid background |
| 0x20 | Invert |
| 0x40 | Stripey (when wide or tall) |
| 0x80 | Use custom font |

```lua
POKE(0x5F58, 0x1 | 0x2 | 0x4 | 0x8 | 0x20 | 0x40)  -- pinball everywhere
```

### Other Default Addresses

| Address | Low nibble | High nibble |
|---------|------------|-------------|
| 0x5F59 | char_w | char_h |
| 0x5F5A | char_w2 | tab_w |
| 0x5F5B | offset_x | offset_y |

Nibbles equal to 0 are ignored. tab_w values map to 4..60.

---

## Custom Font

Defined at `0x5600`: 8 bytes per character * 256 characters = 2048 bytes. Each character is 8x8 (1 bit/pixel), low bit on left.

### Font Attributes (first 128 bytes, chars 0-15)

| Address | Meaning |
|---------|---------|
| 0x5600 | Character width in pixels |
| 0x5601 | Character width for char 128+ |
| 0x5602 | Character height in pixels |
| 0x5603 | Draw offset X |
| 0x5604 | Draw offset Y |
| 0x5605 | Flags: 0x1 apply size adjustments, 0x2 tabs relative to home |
| 0x5606 | Tab width in pixels |

Remaining 120 bytes adjust width/vertical offset per character (nibble-packed).
