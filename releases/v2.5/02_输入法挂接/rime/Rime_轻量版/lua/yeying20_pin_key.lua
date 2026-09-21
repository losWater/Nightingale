-- Ctrl+N 钉选处理器（逻辑在 yeying20_pin.lua）
local pin = require('yeying20_pin')
local M = {}
function M.func(key, env)
  return pin.key(key, env)
end
return M
