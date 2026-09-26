-- In single-character Chinese input, period commits the selected candidate.
-- Run before recognizer/key_binder: the default period binding pages down and
-- the default URL recognizer can retain a dot inside a letter sequence.
local M = {}
function M.func(key, env)
  if key:release() or key:ctrl() or key:alt() or key:super() or key:shift() then return 2 end
  if key.keycode ~= 46 then return 2 end
  local ctx = env.engine.context
  if ctx:get_option('ascii_mode') then return 2 end
  local input = ctx.input or ''
  -- Leave long literal English, URLs, lookup and empty/invalid input alone.
  if #input > 4 or not input:match('^[a-z]+$') or not ctx:has_menu() then return 2 end
  ctx:commit()
  env.engine:commit_text(ctx:get_option('ascii_punct') and '.' or '。')
  return 1
end
return M
