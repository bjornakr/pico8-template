#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# ///
"""
PICO-8 Lua linter.

Usage:
  uv run tools/p8lint.py game.p8

Reads a .p8 cart, resolves #include directives, and checks for:
  - missing-local: variable assigned without 'local' inside a function body
  - global-outside-init: global variable first assigned outside _init()
  - duplicate-function: non-local function defined more than once
  - unused-variable: local variable declared but never read
  - unreachable-code: code after exhaustive if/else where all branches return/break
  - missing-callback: _init, _update/_update60, or _draw not defined
  - undefined-variable: variable used but never assigned/declared anywhere

Suppress a warning on a specific line with an inline comment:
  mode = "game"  -- p8lint: ignore
"""

import os
import re
import sys
from dataclasses import dataclass, field
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PICO8_BUILTINS = frozenset({
    # graphics
    "cls", "print", "spr", "sspr", "pset", "pget", "line", "circ", "circfill",
    "oval", "ovalfill", "rect", "rectfill", "rrect", "rrectfill", "clip",
    "camera", "color", "cursor", "pal", "palt", "fillp", "sget", "sset",
    "fget", "fset", "flip",
    # map
    "map", "mget", "mset", "tline",
    # input
    "btn", "btnp",
    # audio
    "sfx", "music",
    # math
    "max", "min", "mid", "flr", "ceil", "abs", "sqrt", "sin", "cos",
    "atan2", "rnd", "srand", "sgn",
    # bitwise
    "band", "bor", "bxor", "bnot", "shl", "shr", "lshr", "rotl", "rotr",
    # table
    "add", "del", "deli", "count", "all", "foreach", "pairs", "ipairs",
    "pack", "unpack",
    # string
    "sub", "chr", "ord", "tostr", "tonum", "split", "type",
    # memory
    "peek", "peek2", "peek4", "poke", "poke2", "poke4",
    "memcpy", "memset", "reload", "cstore",
    # system
    "stat", "time", "t", "printh", "extcmd", "menuitem",
    "assert", "stop", "run", "reboot", "reset", "load", "save",
    "ls", "folder", "serial",
    # persistent storage
    "cartdata", "dget", "dset",
    # meta
    "setmetatable", "getmetatable", "rawset", "rawget", "rawequal", "rawlen",
    # coroutines
    "cocreate", "coresume", "costatus", "yield", "select",
})

PICO8_CALLBACKS = frozenset({
    "_init", "_update", "_update60", "_draw",
})

LUA_KEYWORDS = frozenset({
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "goto", "if", "in", "local", "nil", "not", "or",
    "repeat", "return", "then", "true", "until", "while",
})

# All known names that should never trigger undefined-variable
KNOWN_GLOBALS = PICO8_BUILTINS | PICO8_CALLBACKS | LUA_KEYWORDS

# Compound assignment operators, longest first for regex
COMPOUND_OPS = [
    ">>>=", "<<>=", ">><=",
    "<<=", ">>=", "^^=", "..=",
    "+=", "-=", "*=", "/=", "\\=", "&=", "|=",
]

COMPOUND_RE = "|".join(re.escape(op) for op in COMPOUND_OPS)

# Section headers in .p8 files
P8_SECTIONS = {"__lua__", "__gfx__", "__gff__", "__map__", "__sfx__", "__music__", "__label__", "__meta__"}

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class SourceLine(NamedTuple):
    file: str
    lineno: int
    text: str


@dataclass
class Warning:
    file: str
    lineno: int
    message: str
    rule: str


@dataclass
class MultilineState:
    in_block_comment: bool = False
    in_block_string: bool = False
    bracket_level: int = 0  # number of = signs in long bracket (e.g. [=[ is level 1)


@dataclass
class Scope:
    locals: dict[str, int] = field(default_factory=dict)  # name -> decl_id
    is_function: bool = False
    func_name: str | None = None      # name of function that opened this scope
    terminated: bool = False          # scope hit return/break
    is_branch: bool = False           # part of if/elseif/else chain
    is_final_branch: bool = False     # True only for else body
    prior_branches_terminated: bool = True  # all prior branches in chain terminated
    unreachable_warned: bool = False  # already warned about unreachable code

# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------

def extract_lua_section(p8_path: str) -> list[str]:
    """Extract raw lines from the __lua__ section of a .p8 file."""
    lines = []
    in_lua = False
    with open(p8_path, "r") as f:
        for line in f:
            stripped = line.rstrip("\n\r")
            if stripped.strip() in P8_SECTIONS:
                if stripped.strip() == "__lua__":
                    in_lua = True
                    continue
                elif in_lua:
                    break
            if in_lua:
                lines.append(stripped)
    return lines


def resolve_includes(lines: list[str], cart_dir: str, cart_name: str) -> list[SourceLine]:
    """Resolve #include directives and return SourceLines with origin tracking."""
    result = []
    lua_lineno = 0
    for line in lines:
        lua_lineno += 1
        m = re.match(r"^\s*#include\s+(.+)$", line, re.IGNORECASE)
        if m:
            include_path = m.group(1).strip()
            full_path = os.path.join(cart_dir, include_path)
            if os.path.exists(full_path):
                with open(full_path, "r") as f:
                    for i, inc_line in enumerate(f, 1):
                        result.append(SourceLine(include_path, i, inc_line.rstrip("\n\r")))
            else:
                result.append(SourceLine(cart_name, lua_lineno, line))
        else:
            result.append(SourceLine(cart_name, lua_lineno, line))
    return result

# ---------------------------------------------------------------------------
# Comment/string stripping
# ---------------------------------------------------------------------------

def _find_long_close(line: str, start: int, level: int) -> int:
    """Find closing long bracket ]=*] with the given level. Returns index or -1."""
    close = "]" + "=" * level + "]"
    return line.find(close, start)


def strip_comments_and_strings(line: str, state: MultilineState) -> tuple[str, MultilineState]:
    """Remove comments and string literals. Returns cleaned line and updated state."""
    if state.in_block_comment:
        end = _find_long_close(line, 0, state.bracket_level)
        if end >= 0:
            close_len = 2 + state.bracket_level
            state = MultilineState()
            return strip_comments_and_strings(line[end + close_len:], state)
        return "", state

    if state.in_block_string:
        end = _find_long_close(line, 0, state.bracket_level)
        if end >= 0:
            close_len = 2 + state.bracket_level
            state = MultilineState()
            return strip_comments_and_strings(line[end + close_len:], state)
        return "", state

    result = []
    i = 0
    while i < len(line):
        # Block comment: --[=*[
        if line[i:i+2] == "--":
            m = re.match(r"\[(=*)\[", line[i+2:])
            if m:
                level = len(m.group(1))
                open_len = 4 + level  # --[=*[
                end = _find_long_close(line, i + open_len, level)
                if end >= 0:
                    i = end + 2 + level
                else:
                    state = MultilineState(in_block_comment=True, bracket_level=level)
                    break
            else:
                # Line comment
                break
        # Block string: [=*[ (not preceded by -)
        elif line[i] == "[":
            m = re.match(r"\[(=*)\[", line[i:])
            if m and (i == 0 or line[i-1] != "-"):
                level = len(m.group(1))
                open_len = 2 + level
                end = _find_long_close(line, i + open_len, level)
                if end >= 0:
                    result.append('""')  # placeholder
                    i = end + 2 + level
                else:
                    state = MultilineState(in_block_string=True, bracket_level=level)
                    break
            else:
                result.append(line[i])
                i += 1
        # String literals
        elif line[i] in ('"', "'"):
            quote = line[i]
            j = i + 1
            while j < len(line):
                if line[j] == "\\" and j + 1 < len(line):
                    j += 2
                elif line[j] == quote:
                    break
                else:
                    j += 1
            result.append('""')  # placeholder
            i = j + 1
        else:
            result.append(line[i])
            i += 1

    return "".join(result), state

# ---------------------------------------------------------------------------
# Line parsing
# ---------------------------------------------------------------------------

# Identifier pattern (not preceded by . or :)
IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"

def find_assignments(line: str) -> list[tuple[str, bool]]:
    """Find variable assignments. Returns list of (name, is_local).
    Skips table field assignments (x.y = ..., x[i] = ...).
    """
    results = []

    # local declarations: local a, b, c = ...
    m = re.match(rf"^\s*local\s+({IDENT}(?:\s*,\s*{IDENT})*)", line)
    if m:
        names = re.findall(IDENT, m.group(1))
        for name in names:
            if name not in LUA_KEYWORDS:
                results.append((name, True))
        return results

    # for loop variables (implicit local)
    m = re.match(rf"^\s*for\s+({IDENT}(?:\s*,\s*{IDENT})*)\s*(?:=|in\b)", line)
    if m:
        names = re.findall(IDENT, m.group(1))
        for name in names:
            if name not in LUA_KEYWORDS:
                results.append((name, True))
        return results

    # Multi-variable assignment: a, b, c = ...
    multi_pat = rf"^(\s*)({IDENT}(?:\s*,\s*{IDENT})+)\s*(?<![!=<>~])=(?!=)"
    m = re.match(multi_pat, line)
    if m:
        names = re.findall(IDENT, m.group(2))
        for name in names:
            if name not in LUA_KEYWORDS:
                results.append((name, False))
        return results

    # Regular or compound assignment: name = ... or name += ...
    assign_pat = rf"^(\s*)({IDENT})\s*(?:{COMPOUND_RE}|(?<![!=<>~])=(?!=))"
    m = re.match(assign_pat, line)
    if m:
        name = m.group(2)
        if name not in LUA_KEYWORDS:
            results.append((name, False))
        return results

    # Shorthand if with assignment: if (cond) name = ...
    shorthand_pat = rf"^\s*if\s*\(.*?\)\s*({IDENT})\s*(?:{COMPOUND_RE}|(?<![!=<>~])=(?!=))"
    m = re.match(shorthand_pat, line)
    if m:
        name = m.group(1)
        if name not in LUA_KEYWORDS:
            results.append((name, False))
        return results

    return results


def find_function_def(line: str) -> tuple[str | None, list[str]]:
    """Check if line is a function definition.
    Returns (func_name_or_None, [param_names]).
    """
    def _parse_params(params_str: str) -> list[str]:
        if not params_str.strip():
            return []
        params = [p.strip() for p in params_str.split(",") if p.strip()]
        return [p for p in params if re.match(rf"^{IDENT}$", p) and p not in LUA_KEYWORDS]

    # Method: function obj:method(params) — implicit self, don't assign obj
    m = re.match(rf"^\s*(?:local\s+)?function\s+{IDENT}:{IDENT}\s*\((.*?)\)", line)
    if m:
        params = _parse_params(m.group(1))
        params.insert(0, "self")
        return None, params

    # Dot method: function obj.method(params) — don't assign obj
    m = re.match(rf"^\s*(?:local\s+)?function\s+{IDENT}\.{IDENT}\s*\((.*?)\)", line)
    if m:
        return None, _parse_params(m.group(1))

    # Plain: function name(params)
    m = re.match(rf"^\s*(?:local\s+)?function\s+({IDENT})\s*\((.*?)\)", line)
    if m:
        name = m.group(1)
        params = _parse_params(m.group(2))
        is_local = line.strip().startswith("local")
        return (name if not is_local else None), params

    # Anonymous: local f = function(params) or f = function(params)
    m = re.match(rf"^\s*(?:local\s+)?{IDENT}\s*=\s*function\s*\((.*?)\)", line)
    if m:
        params_str = m.group(1)
        params = [p.strip() for p in params_str.split(",") if p.strip()] if params_str.strip() else []
        params = [p for p in params if re.match(rf"^{IDENT}$", p) and p not in LUA_KEYWORDS]
        return None, params

    return None, []


def find_variable_uses(line: str) -> set[str]:
    """Find all identifier uses in a line, excluding field names after . or :
    and table constructor keys ({key=val})."""
    # Remove identifiers that follow . or :
    cleaned = re.sub(rf"[.:]{IDENT}", "", line)
    # Remove table constructor keys: word followed by = (but not ==)
    cleaned = re.sub(rf"\b({IDENT})\s*(?<![!=<>~])=(?!=)", "", cleaned)
    # Find all remaining identifiers
    idents = set(re.findall(rf"\b({IDENT})\b", cleaned))
    return idents - LUA_KEYWORDS


def is_single_line_block(line: str) -> bool:
    """Check if a line is a self-contained block (opens and closes on same line)."""
    stripped = line.strip()
    if re.match(r"^\s*(?:local\s+)?function\b.*\bend\s*$", stripped):
        return True
    if re.match(r"^\s*if\b.*\bthen\b.*\bend\s*$", stripped):
        return True
    if re.match(r"^\s*for\b.*\bdo\b.*\bend\s*$", stripped):
        return True
    if re.match(r"^\s*while\b.*\bdo\b.*\bend\s*$", stripped):
        return True
    return False


def count_scope_changes(line: str) -> tuple[int, int]:
    """Count scope opens and closes on a line.
    Returns (opens, closes).
    """
    opens = 0
    closes = 0

    stripped = line.strip()

    # Self-contained single-line blocks → no net scope change
    if is_single_line_block(stripped):
        return 0, 0

    # Shorthand if: if (...) stmt — no scope change
    if re.match(r"^\s*if\s*\(.*?\)\s*\S", stripped):
        # Check it's not `if (...) then`
        if not re.search(r"\bthen\s*$", stripped):
            return 0, 0

    # Count scope-opening keywords
    # function definition
    if re.match(rf"^\s*(?:local\s+)?function\b", stripped):
        opens += 1
    elif re.search(r"\bfunction\s*\(", stripped):
        opens += 1

    # for/while/do blocks
    if re.match(r"^\s*for\b", stripped) and re.search(r"\bdo\s*$", stripped):
        opens += 1
    elif re.match(r"^\s*while\b", stripped) and re.search(r"\bdo\s*$", stripped):
        opens += 1
    elif re.match(r"^\s*do\s*$", stripped):
        opens += 1

    # if/then (but not elseif — handled separately below)
    if re.search(r"\bthen\s*$", stripped) and not re.match(r"^\s*elseif\b", stripped):
        opens += 1

    # repeat
    if re.match(r"^\s*repeat\s*$", stripped):
        opens += 1

    # end
    for _ in re.finditer(r"\bend\b", stripped):
        # Safe: comments and strings already stripped by caller
        closes += 1

    # until
    if re.match(r"^\s*until\b", stripped):
        closes += 1

    # else/elseif close + reopen
    if re.match(r"^\s*else\s*$", stripped):
        closes += 1
        opens += 1
    elif re.match(r"^\s*elseif\b", stripped) and re.search(r"\bthen\s*$", stripped):
        closes += 1
        opens += 1

    return opens, closes

# ---------------------------------------------------------------------------
# Pre-pass
# ---------------------------------------------------------------------------

def _collect_globals_in_function(func_name: str, source_lines: list[SourceLine]) -> tuple[set[str], set[str]]:
    """Collect globals assigned and functions called inside a named function.

    Returns (globals_assigned, functions_called).
    """
    state = MultilineState()
    in_func = False
    depth = 0
    globals_assigned: set[str] = set()
    functions_called: set[str] = set()
    pattern = re.compile(r"^\s*function\s+" + re.escape(func_name) + r"\s*\(")
    call_pattern = re.compile(r"\b([a-zA-Z_]\w*)\s*\(")
    for sl in source_lines:
        cleaned, state = strip_comments_and_strings(sl.text, state)
        if not cleaned.strip():
            continue
        if not in_func:
            if pattern.match(cleaned):
                in_func = True
                depth = 1
                continue
        else:
            opens, closes = count_scope_changes(cleaned)
            depth += opens - closes
            if depth <= 0:
                in_func = False
                continue
            assignments = find_assignments(cleaned)
            for name, is_local in assignments:
                if not is_local:
                    globals_assigned.add(name)
            for m in call_pattern.finditer(cleaned):
                functions_called.add(m.group(1))
    return globals_assigned, functions_called


def collect_init_globals(source_lines: list[SourceLine]) -> set[str]:
    """Pre-scan to find all globals assigned inside _init() and functions it calls."""
    # Collect all user-defined function names
    func_pattern = re.compile(r"^\s*function\s+([a-zA-Z_]\w*)\s*\(")
    user_funcs: set[str] = set()
    state = MultilineState()
    for sl in source_lines:
        cleaned, state = strip_comments_and_strings(sl.text, state)
        m = func_pattern.match(cleaned)
        if m:
            user_funcs.add(m.group(1))

    # BFS from _init: collect globals from _init and any user functions it calls
    result: set[str] = set()
    visited: set[str] = set()
    queue = ["_init"]
    while queue:
        fname = queue.pop()
        if fname in visited:
            continue
        visited.add(fname)
        globals_assigned, functions_called = _collect_globals_in_function(fname, source_lines)
        result.update(globals_assigned)
        for called in functions_called:
            if called in user_funcs and called not in visited:
                queue.append(called)
    return result

# ---------------------------------------------------------------------------
# Linter
# ---------------------------------------------------------------------------

def lint(source_lines: list[SourceLine]) -> list[Warning]:
    """Run lint rules over all source lines."""
    warnings = []
    state = MultilineState()
    scope_stack: list[Scope] = []

    # Collection phase
    top_level_assigned: set[str] = set()  # names assigned at top level (functions + vars)
    all_assigned: set[str] = set()  # all names ever assigned (local or global)
    all_uses: dict[str, SourceLine] = {}  # name -> first use location
    missing_local_candidates: list[tuple[str, SourceLine]] = []
    next_decl_id: int = 0
    local_declarations: dict[int, tuple[str, SourceLine]] = {}  # decl_id -> (name, source_line)
    used_decl_ids: set[int] = set()  # declaration IDs that have been referenced
    init_assigned: set[str] = collect_init_globals(source_lines)  # pre-populated
    global_outside_init: dict[str, SourceLine] = {}  # globals first assigned outside _init()
    func_definitions: dict[str, SourceLine] = {}  # full func name -> first definition

    def in_function() -> bool:
        return any(s.is_function for s in scope_stack)

    def current_function_name() -> str | None:
        for scope in reversed(scope_stack):
            if scope.is_function:
                return scope.func_name
        return None

    def is_visible_local(name: str) -> bool:
        for scope in reversed(scope_stack):
            if name in scope.locals:
                return True
        return False

    def resolve_local(name: str) -> int | None:
        """Find the declaration ID for the innermost local with this name."""
        for scope in reversed(scope_stack):
            if name in scope.locals:
                return scope.locals[name]
        return None

    pending_multiline_elseif = False  # True when elseif spans multiple lines (no then yet)

    for sl in source_lines:
        cleaned, state = strip_comments_and_strings(sl.text, state)
        if not cleaned.strip():
            continue

        # Inline suppression: -- p8lint: ignore
        if re.search(r"--\s*p8lint:\s*ignore", sl.text):
            continue

        # Line classification for branch tracking
        is_else_only = bool(re.match(r"^\s*else\s*$", cleaned))
        is_elseif_line = bool(re.match(r"^\s*elseif\b", cleaned))
        is_branch_continuation = is_else_only or is_elseif_line

        # Handle multi-line elseif: condition spans lines, `then` on a later line
        has_then = bool(re.search(r"\bthen\s*$", cleaned))
        if pending_multiline_elseif and has_then:
            is_branch_continuation = True
            pending_multiline_elseif = False
        elif is_elseif_line and not has_then:
            pending_multiline_elseif = True
        elif not is_elseif_line:
            pending_multiline_elseif = False

        is_if_open = has_then and not is_branch_continuation

        # Scope tracking
        opens, closes = count_scope_changes(cleaned)
        # Multi-line branch continuation: the `then` line has opens=1 but no close
        # from count_scope_changes, so inject the close for the prior branch scope
        if is_branch_continuation and closes == 0 and opens > 0:
            closes += 1
        # Process closes first for else/elseif
        chain_state = None
        for _ in range(closes):
            if scope_stack:
                closed = scope_stack.pop()
                if is_branch_continuation and closed.is_branch:
                    # Handing off to else/elseif — carry chain state
                    chain_state = closed.prior_branches_terminated and closed.terminated
                elif closed.is_branch and closed.is_final_branch \
                        and closed.terminated and closed.prior_branches_terminated:
                    # Exhaustive if/else chain completed — propagate to parent
                    if scope_stack:
                        scope_stack[-1].terminated = True

        # Check for unreachable code
        # Lines starting with binary operators are continuations of the previous expression
        is_continuation = bool(re.match(r"^\s*(and|or)\b", cleaned)) \
            or bool(re.match(r"^\s*(\.\.|[+\-*/%^<>=~])", cleaned))
        if is_continuation and scope_stack and scope_stack[-1].terminated:
            scope_stack[-1].terminated = False
        if scope_stack and scope_stack[-1].terminated \
                and not scope_stack[-1].unreachable_warned:
            if not re.match(r"^\s*(end|else|elseif|until)\b", cleaned):
                warnings.append(Warning(sl.file, sl.lineno,
                    "unreachable code", "unreachable-code"))
                scope_stack[-1].unreachable_warned = True

        # Single-line block detection (scope not pushed, but still track names)
        single_line = is_single_line_block(cleaned)

        # Function definitions
        func_name, params = find_function_def(cleaned)
        is_func_open = (func_name is not None or len(params) > 0) and not single_line
        if single_line and params:
            for p in params:
                all_assigned.add(p)
        if func_name:
            all_assigned.add(func_name)
            if not in_function():
                top_level_assigned.add(func_name)
            elif not is_visible_local(func_name):
                missing_local_candidates.append((func_name, sl))

        # Duplicate function detection (non-local definitions only)
        m = re.match(rf"^\s*function\s+({IDENT}(?:[.:]{IDENT})?)\s*\(", cleaned)
        if m:
            full_name = m.group(1)
            if full_name in func_definitions:
                prev = func_definitions[full_name]
                warnings.append(Warning(sl.file, sl.lineno,
                    f"duplicate function '{full_name}' "
                    f"(first defined at {prev.file}:{prev.lineno})",
                    "duplicate-function"))
            else:
                func_definitions[full_name] = sl

        # Assignments
        assignments = find_assignments(cleaned)
        line_locals: dict[str, int] = {}  # name -> decl_id
        for name, is_local in assignments:
            all_assigned.add(name)
            if is_local:
                decl_id = next_decl_id
                next_decl_id += 1
                line_locals[name] = decl_id
                if name != "_":
                    local_declarations[decl_id] = (name, sl)
            elif in_function() and not is_visible_local(name):
                missing_local_candidates.append((name, sl))
                if current_function_name() == "_init":
                    init_assigned.add(name)
                elif name not in global_outside_init:
                    global_outside_init[name] = sl
            elif not in_function():
                top_level_assigned.add(name)

        # Open new scopes and register locals/params
        for idx in range(opens):
            scope = Scope(
                is_function=(idx == 0 and is_func_open),
                func_name=func_name if (idx == 0 and is_func_open) else None,
            )
            if idx == 0:
                if is_func_open:
                    for p in params:
                        p_id = next_decl_id
                        next_decl_id += 1
                        scope.locals[p] = p_id
                        all_assigned.add(p)
                # For-loop vars and other locals on scope-opening lines
                scope.locals.update(line_locals)
                # Branch type tracking
                if is_branch_continuation and chain_state is not None:
                    scope.is_branch = True
                    scope.is_final_branch = is_else_only
                    scope.prior_branches_terminated = chain_state
                elif is_if_open:
                    scope.is_branch = True
            scope_stack.append(scope)

        # Locals on non-scope-opening lines go in current scope
        if opens == 0 and line_locals and scope_stack:
            scope_stack[-1].locals.update(line_locals)

        # Detect return/break — terminate current scope
        if re.match(r"^\s*return\b", cleaned) or re.match(r"^\s*break\b", cleaned):
            if scope_stack:
                scope_stack[-1].terminated = True

        # Uses
        uses = find_variable_uses(cleaned)
        for name in uses:
            if name not in all_uses:
                all_uses[name] = sl
            decl_id = resolve_local(name)
            if decl_id is not None:
                used_decl_ids.add(decl_id)

    # Reporting phase
    # Rule 1: missing-local (suppress for known globals from _init or top level)
    for name, sl in missing_local_candidates:
        if name in KNOWN_GLOBALS:
            continue
        if name in top_level_assigned:
            continue
        if name in init_assigned:
            continue
        warnings.append(Warning(sl.file, sl.lineno, f"missing 'local' for '{name}'", "missing-local"))

    # Rule 2: global-outside-init
    for name, sl in global_outside_init.items():
        if name in KNOWN_GLOBALS:
            continue
        if name in top_level_assigned:
            continue
        if name in init_assigned:
            continue
        warnings.append(Warning(sl.file, sl.lineno,
            f"global '{name}' first assigned outside _init()", "global-outside-init"))

    # Rule: unused-variable (scope-aware via declaration IDs)
    for decl_id, (name, sl) in local_declarations.items():
        if decl_id not in used_decl_ids:
            warnings.append(Warning(sl.file, sl.lineno, f"unused variable '{name}'", "unused-variable"))

    # Rule: undefined-variable
    all_known = all_assigned | KNOWN_GLOBALS
    for name, sl in all_uses.items():
        if name in all_known:
            continue
        warnings.append(Warning(sl.file, sl.lineno, f"undefined variable '{name}'", "undefined-variable"))

    # Rule: missing-callback
    cart_name = source_lines[0].file if source_lines else "?"
    if "_init" not in func_definitions:
        warnings.append(Warning(cart_name, 1, "missing _init() callback", "missing-callback"))
    if "_update" not in func_definitions and "_update60" not in func_definitions:
        warnings.append(Warning(cart_name, 1, "missing _update() or _update60() callback", "missing-callback"))
    if "_draw" not in func_definitions:
        warnings.append(Warning(cart_name, 1, "missing _draw() callback", "missing-callback"))

    return warnings

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: p8lint.py <cart.p8>", file=sys.stderr)
        sys.exit(2)

    p8_path = sys.argv[1]
    if not os.path.exists(p8_path):
        print(f"Error: {p8_path} not found", file=sys.stderr)
        sys.exit(2)

    cart_dir = os.path.dirname(os.path.abspath(p8_path))
    cart_name = os.path.basename(p8_path)

    lines = extract_lua_section(p8_path)
    source_lines = resolve_includes(lines, cart_dir, cart_name)
    results = lint(source_lines)

    use_color = sys.stdout.isatty()

    results.sort(key=lambda w: (w.file, w.lineno))
    for w in results:
        if use_color:
            loc = f"\033[36m{w.file}:{w.lineno}\033[0m"
            warn = f"\033[33mwarning\033[0m"
            rule = f"\033[2m[{w.rule}]\033[0m"
            print(f"{loc}: {warn}: {w.message} {rule}")
        else:
            print(f"{w.file}:{w.lineno}: warning: {w.message} [{w.rule}]")

    if not results and use_color:
        print(f"\033[32mNo warnings found.\033[0m")

    sys.exit(1 if results else 0)


if __name__ == "__main__":
    main()
