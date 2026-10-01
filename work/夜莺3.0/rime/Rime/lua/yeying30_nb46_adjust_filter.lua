-- 按手动调整重排候选：调整过的码按“当前显示顺序”出字；挪来的字若不在本码上则补一个候选；挪走的字不再出现
local D = require('yeying30_nb46_adjust_data')

local function init(env) D.load() end

local function func(input, env)
  local code = env.engine.context.input
  local s = D.state[code]
  if not s then
    for c in input:iter() do yield(c) end
    return
  end
  local cands, all, first = {}, {}, nil
  for c in input:iter() do
    first = first or c
    all[#all + 1] = c
    if not cands[c.text] then cands[c.text] = c end
  end
  local done = {}
  for _, t in ipairs(D.display(code)) do
    local c = cands[t]
    if not c and first then c = Candidate('table', first.start, first._end, t, '') end
    if c then yield(c); done[t] = true end
  end
  for _, c in ipairs(all) do                      -- 其余候选按原顺序收尾
    if not done[c.text] and not s.removed[c.text] then yield(c); done[c.text] = true end
  end
end

return { init = init, func = func }
