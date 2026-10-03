-- 用法：lua corr.lua <数据目录> <模块名> <档位> <输入文件(目标\t类型\t编码)> 输出：类型\t首选对\t前5含目标\t首选是纠错
local dir, mod, level, input = arg[1], arg[2], arg[3], arg[4]
package.path = dir .. "/lua/?.lua;" .. package.path
rime_api = { get_user_data_dir = function() return dir end, get_shared_data_dir = function() return dir end }
local M = require(mod)
M.ensure_lexicon(nil)
M.correction.set_level(level)
for line in io.lines(input) do
  local target, kind, raw = line:match("^(.-)\t(.-)\t(.*)$")
  local r = M.decode_full(raw) or {}
  local top = r[1] and r[1].text or ""
  local in5 = 0
  for i = 1, math.min(5, #r) do if r[i].text == target then in5 = 1 end end
  local fixed = (r[1] and ((r[1].correction_count or 0) > 0 or r[1].corrected_code or (r[1].path and r[1].path.correction_history))) and 1 or 0
  io.write(kind, "\t", top == target and 1 or 0, "\t", in5, "\t", fixed, "\n")
end
