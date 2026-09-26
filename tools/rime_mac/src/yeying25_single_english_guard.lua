-- Preserve literal English through empty Nightingale codes (e.g. ct -> ctrl).
-- Like the local single-character setup, five letters begin a literal string.
local M = {}
function M.func(key, env)
  if key:release() or key:ctrl() or key:alt() or key:super() then return 2 end
  local ctx = env.engine.context
  if ctx:get_option('ascii_mode') then return 2 end
  local input = ctx.input or ''
  if not input:match('^[A-Za-z][A-Za-z0-9_%.%-]*$') then return 2 end
  if #input >= 5 and key.keycode == 32 then
    env.engine:commit_text(input)
    ctx:clear()
    return 1
  end
  local code = key.keycode
  if code < 33 or code > 126 then return 2 end
  local ch = string.char(code)
  if not ch:match('[A-Za-z0-9_%.%-]') then return 2 end
  if #input >= 5 or ((#input >= 4 or not ctx:has_menu()) and ch:match('[A-Za-z]')) then
    ctx:push_input(ch)
    return 1
  end
  return 2
end
return M
