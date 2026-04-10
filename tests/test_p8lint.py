"""Tests for p8lint.py — covers the 5 bug fixes."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from p8lint import (
    lint, SourceLine, strip_comments_and_strings, MultilineState,
    collect_init_globals,
)


def make_source(lua_code: str, filename: str = "test.p8") -> list[SourceLine]:
    return [
        SourceLine(filename, i + 1, line)
        for i, line in enumerate(lua_code.strip().split("\n"))
    ]


def get_warnings(lua_code: str, rule: str | None = None):
    warnings = lint(make_source(lua_code))
    if rule:
        warnings = [w for w in warnings if w.rule == rule]
    return warnings


CALLBACKS = """\
function _init() end
function _update() end
function _draw() end
"""


# -----------------------------------------------------------------------
# Bug 1: Leveled long brackets
# -----------------------------------------------------------------------

class TestLeveledBrackets:
    def test_level1_block_comment_inline(self):
        cleaned, state = strip_comments_and_strings("x = 1 --[=[ comment ]=] + 2", MultilineState())
        assert "x" in cleaned
        assert "comment" not in cleaned
        assert "+ 2" in cleaned

    def test_level1_block_comment_multiline(self):
        _, state = strip_comments_and_strings("--[=[ start", MultilineState())
        assert state.in_block_comment
        assert state.bracket_level == 1
        cleaned, state = strip_comments_and_strings("still comment ]=] x = 1", state)
        assert "x = 1" in cleaned
        assert not state.in_block_comment

    def test_level2_block_string(self):
        cleaned, state = strip_comments_and_strings("x = [==[hello]==] + 1", MultilineState())
        assert "x" in cleaned
        assert "hello" not in cleaned
        assert "+ 1" in cleaned

    def test_level0_still_works(self):
        cleaned, _ = strip_comments_and_strings("--[[ old comment ]] + y", MultilineState())
        assert "old comment" not in cleaned
        assert "+ y" in cleaned

    def test_mismatched_level_not_closed(self):
        cleaned, state = strip_comments_and_strings("--[=[ not closed by ]]", MultilineState())
        assert state.in_block_comment
        assert state.bracket_level == 1


# -----------------------------------------------------------------------
# Bug 2: Single-line construct scope tracking
# -----------------------------------------------------------------------

class TestSingleLineScope:
    def test_single_line_function_no_scope_corruption(self):
        code = CALLBACKS + """
function outer()
  local a = 1
  function inner() return 1 end
  print(a)
end
"""
        ws = get_warnings(code, "unused-variable")
        names = [w.message for w in ws]
        assert not any("'a'" in m for m in names), "a is used, should not be flagged"

    def test_single_line_if_then_end(self):
        code = CALLBACKS + """
function foo()
  local x = 1
  if x > 0 then return end
  print(x)
end
"""
        ws = get_warnings(code, "unreachable-code")
        # Should NOT flag print(x) as unreachable — the if doesn't have an else
        assert len(ws) == 0

    def test_single_line_for_do_end(self):
        code = CALLBACKS + """
function foo()
  local x = 1
  for i=1,1 do print(i) end
  print(x)
end
"""
        ws = get_warnings(code, "unused-variable")
        assert len(ws) == 0


# -----------------------------------------------------------------------
# Bug 3: self implicit parameter & method detection
# -----------------------------------------------------------------------

class TestMethodDetection:
    def test_colon_method_no_obj_assignment(self):
        code = CALLBACKS + """
obj = {}
function obj:update()
  self.x = 1
end
"""
        ws = get_warnings(code, "undefined-variable")
        names = [w.message for w in ws]
        assert not any("'obj'" in m for m in names)
        assert not any("'self'" in m for m in names)

    def test_dot_method_no_obj_assignment(self):
        code = CALLBACKS + """
obj = {}
function obj.create()
  return {}
end
"""
        ws = get_warnings(code, "undefined-variable")
        names = [w.message for w in ws]
        assert not any("'obj'" in m for m in names)

    def test_self_not_flagged_undefined(self):
        code = CALLBACKS + """
player = {}
function player:move(dx)
  self.x += dx
end
"""
        ws = get_warnings(code, "undefined-variable")
        names = [w.message for w in ws]
        assert not any("'self'" in m for m in names)


# -----------------------------------------------------------------------
# Bug 4: Scope-aware unused variable tracking
# -----------------------------------------------------------------------

class TestScopeAwareUnused:
    def test_same_name_different_scopes(self):
        code = CALLBACKS + """
function a()
  local x = 1
end

function b()
  local x = 2
  print(x)
end
"""
        ws = get_warnings(code, "unused-variable")
        assert len(ws) == 1
        assert "'x'" in ws[0].message
        # Should flag the one in a(), not b()
        # Find line of function a's local x
        lines = code.strip().split("\n")
        a_line = next(i + 1 for i, l in enumerate(lines) if "local x = 1" in l)
        assert ws[0].lineno == a_line

    def test_used_variable_not_flagged(self):
        code = CALLBACKS + """
function foo()
  local y = 10
  print(y)
end
"""
        ws = get_warnings(code, "unused-variable")
        names = [w.message for w in ws]
        assert not any("'y'" in m for m in names)

    def test_nested_scope_shadow(self):
        code = CALLBACKS + """
function foo()
  local x = 1
  if true then
    local x = 2
    print(x)
  end
end
"""
        ws = get_warnings(code, "unused-variable")
        assert len(ws) == 1
        assert "'x'" in ws[0].message


# -----------------------------------------------------------------------
# Bug 5: Order-independent _init global tracking
# -----------------------------------------------------------------------

class TestInitOrderIndependent:
    def test_update_before_init(self):
        code = """
function _update()
  score += 1
end

function _init()
  score = 0
end

function _draw()
  print(score)
end
"""
        ws = get_warnings(code, "global-outside-init")
        names = [w.message for w in ws]
        assert not any("'score'" in m for m in names), \
            "score is assigned in _init, should not be flagged even though _update comes first"

    def test_truly_missing_from_init(self):
        code = """
function _update()
  enemy_count += 1
end

function _init()
  score = 0
end

function _draw()
  print(score)
end
"""
        ws = get_warnings(code, "global-outside-init")
        names = [w.message for w in ws]
        assert any("'enemy_count'" in m for m in names)

    def test_collect_init_globals_prepass(self):
        code = """
function _update()
  score += 1
end
function _init()
  score = 0
  hp = 3
end
"""
        result = collect_init_globals(make_source(code))
        assert "score" in result
        assert "hp" in result
