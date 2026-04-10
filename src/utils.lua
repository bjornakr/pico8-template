-- shared utility functions

function util_init()
  dbg_parts = {}
  dbg_rate = 10 -- pause # frames between every output
end


function cell(x, y)
  if y then
    return x * 8, y * 8
  else
    return x * 8
  end
end

function has_solid(x, y, w, h)
  local x_end = x + w - 1
  local y_end = y + h - 1
  local SOLID_FLAG = 0
  return fget(mget(x / 8, y / 8), SOLID_FLAG)
      or fget(mget(x_end / 8, y / 8), SOLID_FLAG)
      or fget(mget(x / 8, y_end / 8), SOLID_FLAG)
      or fget(mget(x_end / 8, y_end / 8), SOLID_FLAG)
end

function overlaps(a, b)
  local margin = 4
  return a.x + 8 >= b.x + margin
      and a.x + margin < b.x + 8
      and a.y + 8 >= b.y + margin
      and a.y + margin < b.y + 8
end

-- usage: dbg("player", player)
function dbg(name, t)
  if type(name) == "table" then
    t = name
    name = "?"
  end
  _dbg_collect(name, t, dbg_parts)
end

-- call once after all dbg() calls
function dbg_flush()
  if (frame_counter % dbg_rate == 0) then
    local s = ""
    for i = 1, #dbg_parts do
      if (i > 1) s = s .. "|"
      s = s .. dbg_parts[i]
    end
    if (#s > 0) printh(s)
    dbg_parts = {}
  end
end

function _dbg_collect(prefix, t, parts)
  local tp = type(t)
  if tp == "function" then return end
  if tp ~= "table" then
    add(parts, prefix .. "=" .. tostr(t))
    return
  end
  for k, v in pairs(t) do
    _dbg_collect(prefix .. "." .. tostr(k), v, parts)
  end
end
