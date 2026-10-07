-- 反查输入：只在以 ` 开头时把字母吃进编码（整句方案用；不碰 ~，因为整句引擎用 ~ 作暂存标记）。
local M = {}
function M.func(key, env)
  if key:release() or key:ctrl() or key:alt() or key:super() or key:shift() then return 2 end
  local ctx = env.engine.context
  if ctx:get_option('ascii_mode') then return 2 end
  if ctx.input:match('^`') and key.keycode >= 97 and key.keycode <= 122 then
    ctx:push_input(string.char(key.keycode))
    return 1
  end
  return 2
end
return M
