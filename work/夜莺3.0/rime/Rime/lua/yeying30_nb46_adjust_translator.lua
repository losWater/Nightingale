-- 调整过的码：直接按“当前显示顺序”生成候选（码表里原本没有该码时也能出字，如下移后被挤到 uep 的“射”）
local D = require('yeying30_nb46_adjust_data')

local function init(env) D.load() end

local function func(input, seg, env)
  if not D.state[input] then return end
  for _, t in ipairs(D.display(input)) do
    yield(Candidate('table', seg.start, seg._end, t, ''))
  end
end

return { init = init, func = func }
