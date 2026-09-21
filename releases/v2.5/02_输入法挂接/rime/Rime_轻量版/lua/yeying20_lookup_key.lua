local M = {}
function M.func(key, env)
  if key:release() or key:ctrl() or key:alt() or key:shift() or key:super() then return 2 end
  if key.keycode ~= 0xffbf then return 2 end -- F2
  local context = env.engine.context
  if context:get_option('ascii_mode') then return 2 end
  local input = context.input
  if input:match('^[a-z]+$') and #input >= 2 and #input <= 4 then
    context.input = '~~' .. input
    return 1
  end
  if input:match('^~~[a-z]*$') then
    context.input = input:sub(3)
    return 1
  end
  return 2
end
return M
