-- Control+数字：把当前页第 N 个候选提到首选
-- Control+U：上移；Control+J（或 D）：下移；Control+0：撤销上一步
local D = require('yeying_tune_adjust_data')

local function init(env) D.load() end

local function func(key, env)
  if key:release() then return 2 end
  if not (key:super() or key:ctrl()) then return 2 end
  local ctx = env.engine.context
  if not ctx:has_menu() then return 2 end
  local kc = key.keycode
  local code = ctx.input
  local seg = ctx.composition:back()
  local function cur() local c = seg:get_candidate_at(seg.selected_index); return c and c.text end
  if kc == 0x75 or kc == 0x55 then                                         -- U：上移
    local a = cur(); if a then D.record(code, a, '', 'up') end
  elseif kc == 0x6a or kc == 0x4a or kc == 0x64 or kc == 0x44 then         -- J / D：下移
    local a = cur(); if a and #code >= 2 then D.record(code, a, '', 'down') end
  elseif kc == 0x30 then                                                   -- 0：撤销上一步
    D.record(code, '', '', 'undo')
  elseif kc >= 0x31 and kc <= 0x39 then                                    -- 1–9：提到首选
    local ps = env.engine.schema.page_size
    local start = math.floor(seg.selected_index / ps) * ps
    local c = seg:get_candidate_at(start + kc - 0x31)
    if not c then return 1 end
    D.record(code, c.text, tostring(start + kc - 0x30), 'top')
  else
    return 2
  end
  ctx:refresh_non_confirmed_composition()
  return 1
end

return { init = init, func = func }
