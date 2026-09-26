-- Four-key topping applies to normal codes, not full-pinyin lookup input.
local M = {}
function M.func(key, env)
  if key:release() or key:ctrl() or key:alt() or key:super() or key:shift() then return 2 end
  local ctx = env.engine.context
  if ctx:get_option('ascii_mode') then return 2 end
  if ctx.input:match('^[`~]') and key.keycode >= 97 and key.keycode <= 122 then
    ctx:push_input(string.char(key.keycode))
    return 1
  end
  return 2
end
return M
