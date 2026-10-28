# Useful patterns

## Collision detection

This code checks if any of the corners of the input coordinates
collides with any map cell that has the `flag` set.

```lua
function has_flag_collision(x, y, w, h, flag) -- returns bool
    local margin = 0 -- gives some leverage/overlap if raised
    local x_end = x + w - 1
    local y_end = y + h - 1
    local ulx, uly = x + margin, y + margin         -- upper left corner
    local urx, ury = x_end - margin, y + margin     -- upper right corner
    local llx, lly = x + margin, y_end - margin     -- lower left corner
    local lrx, lry = x_end - margin, y_end - margin -- lower rigth corner

    return fget(mget(ulx / 8, uly / 8), flag)
      or fget(mget(urx / 8, ury / 8), flag)
      or fget(mget(llx / 8, lly / 8), flag)
      or fget(mget(lrx / 8, lry / 8), flag)
end

--example
SOLID_FLAG = 1
has_flag_collision(player.x, player.y, 8, 8, SOLID_FLAG)
```