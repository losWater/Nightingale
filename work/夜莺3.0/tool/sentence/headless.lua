-- 用法：lua headless.lua <数据目录> <模块名> <输入文件>  （每行一个编码，输出每行首选）
local dir, mod, input = arg[1], arg[2], arg[3]
package.path = dir .. "/lua/?.lua;" .. package.path
rime_api = { get_user_data_dir = function() return dir end, get_shared_data_dir = function() return dir end }
local M = require(mod)
M.ensure_lexicon(nil)
for line in io.lines(input) do
  local r = M.decode_full(line)
  io.write((r and r[1] and r[1].text or ""), "\n")
end
