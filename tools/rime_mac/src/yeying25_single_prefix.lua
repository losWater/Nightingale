-- Keep valid Nightingale prefixes intact while retaining Tiger manual clearing
-- for genuinely invalid input. No completion candidates are added.
local valid = require('yeying25_single_prefix_data')
local M = {}
function M.func(key, env)
  if key:release() or key:ctrl() or key:alt() or key:super() or key:shift() then return 2 end
  local ctx = env.engine.context
  if ctx:get_option('ascii_mode') or ctx:has_menu() then return 2 end
  if key.keycode >= 97 and key.keycode <= 122 and valid[ctx.input .. string.char(key.keycode)] then
    ctx:push_input(string.char(key.keycode))
    return 1
  end
  return 2
end
return M
