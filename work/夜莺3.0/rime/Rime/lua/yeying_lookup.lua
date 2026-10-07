-- 夜莺 3.0 反查（同 2.5 用法）：`+全拼或双拼 列出该读音的字〔拆分 · 码〕；~~+码 列出以该码开头的常用字（F2 切换）。
-- 数据模块由各方案的包装模块指定，第一次反查时才加载。
local function make(data_module)
  local M = {}
  function M.func(input, seg, env)
    if not input:match('^[`~]') then return end
    local core_only = input:sub(1, 2) == '~~'
    local spelling = input:sub(core_only and 3 or 2)
    if spelling == '' then return end
    if not env.lookup_data then env.lookup_data = require(data_module) end
    local data = env.lookup_data
    local sounds = {}
    local sound_prefix = core_only and spelling:sub(1, 2) or spelling
    if #sound_prefix == 2 and data.sounds[sound_prefix] then sounds[sound_prefix] = true end
    local full = not core_only and data.pinyin[spelling]
    if full then sounds[full] = true end
    local emitted = {}
    for sound in pairs(sounds) do
      for _, row in ipairs(data.sounds[sound] or {}) do
        if not emitted[row[1]] and (not core_only or row[5] == 1) then
          local codes = {}
          for _, code in ipairs(row[3]) do
            if not core_only or code:sub(1, #spelling) == spelling then codes[#codes + 1] = code end
          end
          if #codes > 0 then
            emitted[row[1]] = true
            yield(Candidate('yeying_lookup', seg.start, seg._end, row[1], '〔' .. row[2] .. ' · ' .. table.concat(codes, '/') .. '〕'))
          end
        end
      end
    end
  end
  return M
end
return make
