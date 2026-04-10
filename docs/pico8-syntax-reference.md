# PICO-8 Programming Syntax Quick Reference

> Extracted from the PICO-8 v0.2.7 Manual

---

## Lua Syntax Primer

PICO-8 programs use Lua syntax but **not** the standard Lua library.

### Comments

```lua
-- single line comment
--[[ multi-line
comment ]]
```

### Types and Assignment

```lua
NUM = 12/100
S = "THIS IS A STRING"
B = FALSE
T = {1,2,3}
```

- Numbers are **16:16 fixed point**, range: `-32768.0` to `32767.99999`
- Hex notation: `0x11` (17), `0x11.4000` (17.25)
- Dividing by zero evaluates to `0x7fff.ffff` (positive) or `-0x7fff.ffff` (negative)

### Conditionals

```lua
IF NOT B THEN
    PRINT("B IS FALSE")
ELSEIF X < 0 THEN
    PRINT("X IS NEGATIVE")
ELSE
    PRINT("X IS POSITIVE")
END
```

Operators: `==`, `~=` (or `!=`), `<`, `>`, `<=`, `>=`

### Loops

```lua
FOR X=1,5 DO PRINT(X) END           -- 1,2,3,4,5
FOR X=1,10,3 DO PRINT(X) END        -- 1,4,7,10
FOR X=5,1,-2 DO PRINT(X) END        -- 5,3,1

WHILE(X <= 5) DO
    X = X + 1
END
```

Loop ranges are **inclusive**.

### Functions and Local Variables

```lua
FUNCTION PLUSONE(X)
    LOCAL Y = X+1
    RETURN Y
END
```

`LOCAL` variables are scoped to their containing block.

### Tables

```lua
A = {}              -- empty table
A[1] = "BLAH"
A["FOO"] = {1,2,3}
A = {11,12,13,14}   -- 1-based indexing by default
A = {[0]=10,11,12}  -- 0-based if you write slot 0

#A                   -- length of array
PLAYER.X = 2        -- dot notation (same as PLAYER["X"])
```

### PICO-8 Shorthand

**1. Single-line IF/WHILE** (brackets required):

```lua
IF (NOT B) I=1 J=2      -- equivalent to: IF NOT B THEN I=1 J=2 END
```

**2. Assignment operators** (single line only):

```lua
A += 2    -- A = A + 2
A -= 1    A *= 2    A /= 2
A \= 2    -- integer divide assign
A &= 0xf  A |= 0x1  A ^^= 0x3
A ..= "X" -- string concat assign
```

**3. Not-equal operator:**

```lua
PRINT(1 != 2)  -- TRUE (alternative to ~=)
```

**4. Print shortcut:**

```lua
?"HELLO"  -- same as PRINT("HELLO")
```

**5. Integer division:**

```lua
PRINT(9\2)  -- 4 (equivalent to FLR(9/2))
```

**6. Peek operators:**

```lua
@ADDR   -- PEEK(ADDR)
%ADDR   -- PEEK2(ADDR)
$ADDR   -- PEEK4(ADDR)
```

---

## Program Structure

```lua
FUNCTION _INIT()       -- called once on startup
END

FUNCTION _UPDATE()     -- called once per update at 30fps
END

FUNCTION _DRAW()       -- called once per visible frame
END

FUNCTION _UPDATE60()   -- use INSTEAD of _UPDATE for 60fps mode
END
```

### #INCLUDE

```lua
#INCLUDE SOMECODE.LUA   -- include a lua file
#INCLUDE ONETAB.P8:1    -- include tab 1 from another cart
#INCLUDE ALLTABS.P8     -- include all tabs from another cart
```

### Quirks

- Bottom half of sprite sheet and bottom half of map share memory
- `COS()` and `SIN()` take 0..1 (not 0..PI*2), and `SIN()` is inverted
- `SGN(0)` returns 1
- Lua arrays are 1-based; `FOREACH` starts at `TBL[1]`

---

## API Reference

### System

| Function | Description |
|----------|-------------|
| `LOAD(FILENAME, [BREADCRUMB], [PARAM_STR])` | Load a cartridge |
| `SAVE(FILENAME)` | Save a cartridge |
| `RUN([PARAM_STR])` | Run from start (param accessible via `STAT(6)`) |
| `STOP([MESSAGE])` | Stop the cart |
| `RESUME` / `R` | Resume the program |
| `ASSERT(CONDITION, [MESSAGE])` | Stop if condition is false |
| `REBOOT` | Reboot the machine |
| `RESET()` | Reset draw state (palette, camera, clip, fill) |
| `INFO()` | Print cart info (code size, tokens, compressed) |
| `FLIP()` | Flip back buffer to screen, wait for next frame |
| `PRINTH(STR, [FILENAME], [OVERWRITE], [SAVE_TO_DESKTOP])` | Print to host console or file |
| `TIME()` / `T()` | Seconds elapsed since cart started |
| `STAT(X)` | Get system status (see table below) |
| `EXTCMD(CMD_STR, [P1, P2])` | Special system commands |

#### STAT values

| X | Returns |
|---|---------|
| 0 | Memory usage (0..2048) |
| 1 | CPU used since last flip (1.0 = 100%) |
| 4 | Clipboard contents (after CTRL-V) |
| 6 | Parameter string |
| 7 | Current framerate |
| 46..49 | Currently playing SFX on channels 0..3 |
| 50..53 | Note number (0..31) on channels 0..3 |
| 54 | Currently playing pattern index |
| 55 | Total patterns played |
| 56 | Ticks played on current pattern |
| 57 | TRUE when music is playing |
| 80..85 | UTC time: year, month, day, hour, minute, second |
| 90..95 | Local time |
| 100 | Current breadcrumb label or nil |
| 110 | TRUE when in frame-by-frame mode |

#### EXTCMD commands

`"pause"`, `"reset"`, `"go_back"`, `"label"`, `"screen"`, `"rec"`, `"rec_frames"`, `"video"`, `"audio_rec"`, `"audio_end"`, `"shutdown"`, `"folder"`, `"set_filename"`, `"set_title"`

---

### Graphics

#### Colours

```
 0 black       1 dark_blue    2 dark_purple   3 dark_green
 4 brown       5 dark_gray    6 light_gray    7 white
 8 red         9 orange      10 yellow       11 green
12 blue       13 indigo      14 pink         15 peach
```

#### Drawing Functions

| Function | Description |
|----------|-------------|
| `CLS([COL])` | Clear screen (default: 0 black) |
| `PSET(X, Y, [COL])` | Set pixel |
| `PGET(X, Y)` | Get pixel colour |
| `LINE(X0, Y0, [X1, Y1, [COL]])` | Draw line |
| `CIRC(X, Y, R, [COL])` | Draw circle outline |
| `CIRCFILL(X, Y, R, [COL])` | Draw filled circle |
| `OVAL(X0, Y0, X1, Y1, [COL])` | Draw oval outline |
| `OVALFILL(X0, Y0, X1, Y1, [COL])` | Draw filled oval |
| `RECT(X0, Y0, X1, Y1, [COL])` | Draw rectangle outline |
| `RECTFILL(X0, Y0, X1, Y1, [COL])` | Draw filled rectangle |
| `RRECT(X, Y, W, H, R, [COL])` | Draw rounded rectangle outline |
| `RRECTFILL(X, Y, W, H, R, [COL])` | Draw filled rounded rectangle |
| `PRINT(STR, X, Y, [COL])` | Print string at position |
| `PRINT(STR, [COL])` | Print string at cursor |
| `CURSOR(X, Y, [COL])` | Set cursor position |
| `COLOR([COL])` | Set current draw colour (default: 6) |

#### Sprite Functions

| Function | Description |
|----------|-------------|
| `SPR(N, X, Y, [W, H], [FLIP_X], [FLIP_Y])` | Draw sprite N at X,Y |
| `SSPR(SX, SY, SW, SH, DX, DY, [DW, DH], [FLIP_X], [FLIP_Y])` | Stretch-blit from sprite sheet |
| `SGET(X, Y)` | Get sprite sheet pixel colour |
| `SSET(X, Y, [COL])` | Set sprite sheet pixel colour |
| `FGET(N, [F])` | Get sprite flag |
| `FSET(N, [F], VAL)` | Set sprite flag |

#### Draw State

| Function | Description |
|----------|-------------|
| `CAMERA([X, Y])` | Set screen offset (-x, -y). `CAMERA()` to reset |
| `CLIP(X, Y, W, H, [CLIP_PREVIOUS])` | Set clipping rectangle. `CLIP()` to reset |
| `PAL(C0, C1, [P])` | Swap colour c0 for c1 (P: 0=draw, 1=display, 2=secondary) |
| `PAL(TBL, [P])` | Set palette from table |
| `PAL()` | Reset all palettes |
| `PALT(C, [T])` | Set transparency for colour (default: only 0 is transparent) |
| `FILLP(P)` | Set 4x4 fill pattern (bitfield). `FILLP(0)` to reset |

---

### Map

| Function | Description |
|----------|-------------|
| `MGET(X, Y)` | Get map tile value at X,Y |
| `MSET(X, Y, VAL)` | Set map tile value |
| `MAP(TILE_X, TILE_Y, [SX, SY], [TILE_W, TILE_H], [LAYERS])` | Draw map section to screen |
| `TLINE(X0, Y0, X1, Y1, MX, MY, [MDX, MDY], [LAYERS])` | Draw textured line from map |

Map is 128x32 (or 128x64 with shared memory). `LAYERS` is a bitfield matching sprite flags.

---

### Table Functions

| Function | Description |
|----------|-------------|
| `ADD(TBL, VAL, [INDEX])` | Add value to table (at end, or at index) |
| `DEL(TBL, VAL)` | Delete first instance of value |
| `DELI(TBL, [I])` | Delete item at index (default: last) |
| `COUNT(TBL, [VAL])` | Length of table, or count of VAL |
| `ALL(TBL)` | Iterator for FOR loops (1-based order) |
| `FOREACH(TBL, FUNC)` | Call FUNC for each item |
| `PAIRS(TBL)` | Iterator returning key,value (any indexing, unordered) |
| `#TBL` | Length operator |

---

### Input

| Function | Description |
|----------|-------------|
| `BTN([B], [PL])` | Button state. B: 0=left 1=right 2=up 3=down 4=O 5=X |
| `BTNP([B], [PL])` | Button pressed (with repeat: 15 frame delay, then every 4) |

Player 0 keys: cursors + Z/C/N (O) + X/V/M (X)

#### Mouse & Keyboard

Enable with `POKE(0x5F2D, flags)` (0x1=enable, 0x2=mouse->btn, 0x4=pointer lock)

| Stat | Returns |
|------|---------|
| `STAT(30)` | Keypress available (boolean) |
| `STAT(31)` | Character from keyboard (string) |
| `STAT(32)` | Mouse X |
| `STAT(33)` | Mouse Y |
| `STAT(34)` | Mouse buttons (bitfield) |
| `STAT(36)` | Mouse wheel event |
| `STAT(38)` | Relative mouse X (needs flag 0x4) |
| `STAT(39)` | Relative mouse Y (needs flag 0x4) |

---

### Audio

| Function | Description |
|----------|-------------|
| `SFX(N, [CHANNEL], [OFFSET], [LENGTH])` | Play SFX N (0..63) |
| `MUSIC(N, [FADE_LEN], [CHANNEL_MASK])` | Play music from pattern N. -1 to stop |

SFX special values: `SFX(-1, CH)` stop channel, `SFX(-2, CH)` release loop, `SFX(N, -2)` stop SFX N everywhere.

---

### Math

| Function | Description |
|----------|-------------|
| `MAX(X, Y)` | Maximum |
| `MIN(X, Y)` | Minimum |
| `MID(X, Y, Z)` | Middle value |
| `FLR(X)` | Floor |
| `CEIL(X)` | Ceiling |
| `ABS(X)` | Absolute value |
| `SQRT(X)` | Square root |
| `COS(X)` | Cosine (1.0 = full turn) |
| `SIN(X)` | Sine (1.0 = full turn, **inverted** for screenspace) |
| `ATAN2(DX, DY)` | Angle from 0..1 |
| `RND(X)` | Random 0 <= n < X. If X is a table, returns random element |
| `SRAND(X)` | Set random seed |

#### Bitwise Operations

| Function | Operator | Description |
|----------|----------|-------------|
| `BAND(X, Y)` | `&` | AND |
| `BOR(X, Y)` | `\|` | OR |
| `BXOR(X, Y)` | `^^` | XOR |
| `BNOT(X)` | `~` | NOT |
| `SHL(X, N)` | `<<` | Shift left |
| `SHR(X, N)` | `>>` | Arithmetic shift right |
| `LSHR(X, N)` | `>>>` | Logical shift right |
| `ROTL(X, N)` | `<<>` | Rotate left |
| `ROTR(X, N)` | `>><` | Rotate right |

---

### Strings and Type Conversion

| Function | Description |
|----------|-------------|
| `SUB(STR, POS0, [POS1])` | Substring (inclusive) |
| `#STR` | String length |
| `..` | String concatenation |
| `TOSTR(VAL, [FORMAT_FLAGS])` | Convert to string (0x1=hex, 0x2=int32) |
| `TONUM(VAL, [FORMAT_FLAGS])` | Convert to number (0x1=hex, 0x2=int32, 0x4=default 0) |
| `CHR(VAL0, VAL1, ...)` | Ordinal codes to string |
| `ORD(STR, [INDEX], [NUM_RESULTS])` | String character(s) to ordinal codes |
| `SPLIT(STR, [SEP], [CONVERT_NUMBERS])` | Split string to table |
| `TYPE(VAL)` | Type as string ("number", "string", "table", etc.) |

---

### Memory

| Function | Description |
|----------|-------------|
| `PEEK(ADDR, [N])` | Read byte(s) from base RAM |
| `POKE(ADDR, VAL1, ...)` | Write byte(s) to base RAM |
| `PEEK2(ADDR)` / `POKE2(ADDR, VAL)` | 16-bit read/write |
| `PEEK4(ADDR)` / `POKE4(ADDR, VAL)` | 32-bit read/write |
| `MEMCPY(DEST, SRC, LEN)` | Copy bytes in base RAM |
| `MEMSET(DEST, VAL, LEN)` | Fill bytes in base RAM |
| `RELOAD(DEST, SRC, LEN, [FILENAME])` | Copy from cart ROM (or another cart) |
| `CSTORE(DEST, SRC, LEN, [FILENAME])` | Copy from base RAM to cart ROM |

#### Base RAM Layout

```
0x0000  GFX
0x1000  GFX2/MAP2 (shared)
0x2000  MAP
0x3000  GFX FLAGS
0x3100  SONG
0x3200  SFX
0x4300  USER DATA
0x5600  CUSTOM FONT
0x5E00  PERSISTENT CART DATA (256 bytes)
0x5F00  DRAW STATE
0x5F40  HARDWARE STATE
0x5F80  GPIO PINS (128 bytes)
0x6000  SCREEN (8K)
0x8000  USER DATA
```

---

### Cartridge Data (Persistent Storage)

| Function | Description |
|----------|-------------|
| `CARTDATA(ID)` | Open persistent storage slot (call once per cart) |
| `DGET(INDEX)` | Get number at index 0..63 |
| `DSET(INDEX, VALUE)` | Set number at index 0..63 |

---

### Custom Menu Items

```lua
MENUITEM(INDEX, [LABEL], [CALLBACK])
-- INDEX: 1..5, LABEL: up to 16 chars
-- CALLBACK receives bitfield of L,R,X presses
-- Return TRUE from callback to keep menu open
```

---

### Metatables

```lua
SETMETATABLE(TBL, M)       -- set metatable
GETMETATABLE(TBL)          -- get metatable
RAWSET(TBL, KEY, VALUE)    -- raw table set (bypass metamethods)
RAWGET(TBL, KEY)           -- raw table get
RAWEQUAL(TBL1, TBL2)      -- raw equality
RAWLEN(TBL)                -- raw length
```

Common metamethods: `__add`, `__sub`, `__mul`, `__div`, `__mod`, `__pow`, `__eq`, `__lt`, `__le`, `__len`, `__index`, `__newindex`, `__tostring`, `__call`

---

### Coroutines

| Function | Description |
|----------|-------------|
| `COCREATE(F)` | Create coroutine from function |
| `CORESUME(C, [P0, P1..])` | Run/continue coroutine (returns true/false + error) |
| `COSTATUS(C)` | Status: "running", "suspended", "dead" |
| `YIELD(...)` | Suspend execution, return to caller |

```lua
C = COCREATE(FUNCTION()
    PRINT("STEP 1")
    YIELD()
    PRINT("STEP 2")
END)
ASSERT(CORESUME(C))  -- always wrap in assert!
ASSERT(CORESUME(C))
```

---

### Varargs

```lua
FUNCTION FOO(...)
    LOCAL ARGS = {...}
    ?SELECT("#", ...)       -- count arguments
    FOO2(SELECT(3, ...))    -- pass args from 3 onwards
END
```
