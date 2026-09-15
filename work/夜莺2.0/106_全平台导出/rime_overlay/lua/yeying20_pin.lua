-- 夜莺2.0 · 候选钉选（2026-09-16 群友需求）
-- Ctrl+N：把当前页第 N 个候选钉为该编码的首选，其余依次后退；钉选顺序写入用户目录 yeying20_pin.txt，重启不丢。
-- 只对码表候选（固定表 table / 自动造词 user_table）记钉选；整句等不在码表里的候选按 Ctrl+N 直接上屏。
-- 顺序规则（由 yeying20_mix.lua 调用 order()）：钉过的在前（按钉选先后，最近钉的最前）→ 固定码表原序 → 自动造词等用户词。
-- 固定表的用户词典只用来承接自动造词，不让它按使用频率自动乱序。
local M = {}
local pins = nil          -- code -> {text1, text2, ...}
local path = nil

local function file_path()
  if not path then
    local dir = rime_api and rime_api.get_user_data_dir and rime_api.get_user_data_dir() or '.'
    path = dir .. '/yeying20_pin.txt'
  end
  return path
end

local function load()
  if pins then return pins end
  pins = {}
  local f = io.open(file_path(), 'r')
  if not f then return pins end
  for line in f:lines() do
    line = line:gsub('\r$', '')
    local parts = {}
    for x in line:gmatch('[^\t]+') do parts[#parts + 1] = x end
    if #parts >= 2 then
      local code = table.remove(parts, 1)
      pins[code] = parts
    end
  end
  f:close()
  return pins
end

local function save()
  local f = io.open(file_path(), 'w')
  if not f then return false end
  local codes = {}
  for code in pairs(pins) do codes[#codes + 1] = code end
  table.sort(codes)
  for _, code in ipairs(codes) do
    if #pins[code] > 0 then f:write(code, '\t', table.concat(pins[code], '\t'), '\n') end
  end
  f:close()
  return true
end

-- 把 text 钉到 code 的最前，其余已钉的依次后退
function M.pin(code, text)
  load()
  local list = { text }
  for _, t in ipairs(pins[code] or {}) do
    if t ~= text then list[#list + 1] = t end
  end
  pins[code] = list
  return save()
end

function M.get(code)
  return load()[code]
end

local function is_table(cand)
  return cand.type == 'table' or cand.type == 'user_table'
end
M.is_table = is_table

-- list：固定翻译器对 code 给出的候选（已展开成数组）。返回重排后的数组。
function M.order(code, list)
  local pinned = load()[code]
  local out, used = {}, {}
  if pinned then
    for _, text in ipairs(pinned) do
      for i, cand in ipairs(list) do
        if not used[i] and cand.text == text and is_table(cand) then used[i] = true; out[#out + 1] = cand; break end
      end
    end
  end
  for i, cand in ipairs(list) do                       -- 固定码表原序
    if not used[i] and cand.type == 'table' then used[i] = true; out[#out + 1] = cand end
  end
  for i, cand in ipairs(list) do                       -- 自动造词与其他
    if not used[i] then used[i] = true; out[#out + 1] = cand end
  end
  return out
end

-- 处理器：Ctrl+1..9（主键盘或小键盘）
function M.key(key, env)
  if key:release() or not key:ctrl() or key:alt() or key:shift() or key:super() then return 2 end
  local kc = key.keycode
  local n
  if kc >= 0x31 and kc <= 0x39 then n = kc - 0x30
  elseif kc >= 0xffb1 and kc <= 0xffb9 then n = kc - 0xffb0 end
  if not n then return 2 end
  local ctx = env.engine.context
  if not ctx:has_menu() then return 2 end
  local seg = ctx.composition:back()
  local menu = seg.menu
  if not menu then return 2 end
  local page = env.engine.schema.page_size
  if not page or page < 1 then page = 9 end
  local idx = math.floor(seg.selected_index / page) * page + n - 1
  menu:prepare(idx + 1)
  if idx >= menu:candidate_count() then return 1 end
  local cand = menu:get_candidate_at(idx)
  if not cand then return 1 end
  local input = ctx.input
  local whole = seg.start == 0 and seg._end == #input and input:match('^[a-z]+$')
  if whole and is_table(cand) then M.pin(input, cand.text) end
  ctx:select(idx)
  return 1
end

return M
