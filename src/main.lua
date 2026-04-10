function _init()
  util_init()
  frame_counter = 0
  test = 0
end

function _update60()


  dbg("test", test)
  dbg_flush()

  test += 1
  frame_counter += 1 -- must be at end
  if (frame_counter >= 60) frame_counter = 0
end

function _draw()
  cls()
  print("hello pico-8!")
end
