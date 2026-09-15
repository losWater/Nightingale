-- 夜莺2.0 · 候选钉选 + 主动造词（2026-09-16 群友需求）
-- Ctrl+N     ：第 N 个候选是码表候选 → 钉为该编码首选并上屏（其余依次后退，写入用户目录 yeying20_pin.txt）；
--              是整句/联想出来的候选（不在码表里）→ 按夜莺词规则造词（写入 yeying20_words.txt）并上屏。
-- Ctrl+Enter ：主动造词。把当前将要上屏的整段文字按夜莺词规则编码（二字 AaAbBaBb，三字 AaBaCa，四字以上 AaBaCaZa，
--              多音字取全部读音组合，最多 8 个码），写入用户目录 yeying20_words.txt，同时上屏。不限长度。
-- Shift+Delete：选中的是主动造的词（带〔造〕）时从 yeying20_words.txt 删除；其他候选交给 Rime 原生处理。
-- 顺序规则（由 yeying20_mix.lua 调用 order()）：钉过的在前（最近钉的最前）→ 固定码表原序 → 自动造词/主动造词。
local M = {}
local pins, words = nil, nil
local paths = {}

local function user_path(name)
  if not paths[name] then
    local dir = rime_api and rime_api.get_user_data_dir and rime_api.get_user_data_dir() or '.'
    paths[name] = dir .. '/' .. name
  end
  return paths[name]
end

local function load_tsv(name)
  local t = {}
  local f = io.open(user_path(name), 'r')
  if not f then return t end
  for line in f:lines() do
    line = line:gsub('\r$', '')
    local parts = {}
    for x in line:gmatch('[^\t]+') do parts[#parts + 1] = x end
    if #parts >= 2 then
      local code = table.remove(parts, 1)
      t[code] = t[code] or {}
      for _, x in ipairs(parts) do t[code][#t[code] + 1] = x end
    end
  end
  f:close()
  return t
end

local function save_tsv(name, t)
  local f = io.open(user_path(name), 'w')
  if not f then return false end
  local codes = {}
  for code, list in pairs(t) do if #list > 0 then codes[#codes + 1] = code end end
  table.sort(codes)
  for _, code in ipairs(codes) do f:write(code, '\t', table.concat(t[code], '\t'), '\n') end
  f:close()
  return true
end

local function load_pins() if not pins then pins = load_tsv('yeying20_pin.txt') end return pins end
local function load_words() if not words then words = load_tsv('yeying20_words.txt') end return words end

-- 钉选：把 text 钉到 code 的最前，其余已钉的依次后退
function M.pin(code, text)
  load_pins()
  local list = { text }
  for _, t in ipairs(pins[code] or {}) do if t ~= text then list[#list + 1] = t end end
  pins[code] = list
  return save_tsv('yeying20_pin.txt', pins)
end

-- 主动造词表
function M.words(code) return load_words()[code] or {} end
function M.add_word(code, text)
  load_words()
  words[code] = words[code] or {}
  for _, t in ipairs(words[code]) do if t == text then return false end end
  words[code][#words[code] + 1] = text
  return save_tsv('yeying20_words.txt', words)
end
function M.remove_word(code, text)
  load_words()
  local list, hit = {}, false
  for _, t in ipairs(words[code] or {}) do if t == text then hit = true else list[#list + 1] = t end end
  words[code] = list
  if hit then save_tsv('yeying20_words.txt', words) end
  return hit
end

local MADE = '〔造〕'
M.MADE = MADE
local function is_table(cand)
  return cand.type == 'table' or cand.type == 'user_table'
end
M.is_table = is_table

-- list：固定翻译器对 code 给出的候选（数组，可已含主动造词候选）。返回重排后的数组。
function M.order(code, list)
  local pinned = load_pins()[code]
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
  for i, cand in ipairs(list) do                       -- 自动造词、主动造词与其他
    if not used[i] then used[i] = true; out[#out + 1] = cand end
  end
  return out
end

-- 按夜莺词规则给 text 编码；codes_of(ch) 返回该字在固定表里的全部码
function M.encode(text, codes_of)
  local chars = {}
  for _, cp in utf8.codes(text) do chars[#chars + 1] = utf8.char(cp) end
  local n = #chars
  if n < 2 then return {} end
  local parts = {}
  for i, ch in ipairs(chars) do
    local need = 0
    if n == 2 then need = 2
    elseif n == 3 then need = 1
    elseif i <= 3 or i == n then need = 1 end
    if need > 0 then
      local set, list = {}, {}
      for _, c in ipairs(codes_of(ch)) do
        local p = c:sub(1, need)
        if #p == need and p:match('^[a-z]+$') and not set[p] then set[p] = true; list[#list + 1] = p end
      end
      if #list == 0 then return {} end
      parts[#parts + 1] = list
    end
  end
  local res = { '' }
  for _, list in ipairs(parts) do
    local nxt = {}
    for _, pre in ipairs(res) do
      for _, p in ipairs(list) do if #nxt < 8 then nxt[#nxt + 1] = pre .. p end end
    end
    res = nxt
  end
  return res
end

local function rev_codes(env)
  if env.yy_rev == nil then
    local ok, rev = pcall(function() return ReverseLookup('yeying20_rime_fixed') end)
    env.yy_rev = ok and rev or false
  end
  return function(ch)
    local out = {}
    if env.yy_rev then
      local s = env.yy_rev:lookup(ch) or ''
      for c in s:gmatch('%S+') do out[#out + 1] = c end
    end
    return out
  end
end

local function seg_code(ctx, seg)
  return ctx.input:sub(seg.start + 1, seg._end)
end

-- 处理器：Ctrl+1..9 钉选；Ctrl+Enter 主动造词；Shift+Delete 删主动造的词
function M.key(key, env)
  if key:release() then return 2 end
  local kc = key.keycode
  local ctx = env.engine.context
  if key:ctrl() and not key:alt() and not key:shift() and not key:super() then
    if (kc == 0xff0d or kc == 0xff8d) and ctx:is_composing() then           -- Ctrl+Return / Ctrl+KP_Enter
      local text = ctx:get_commit_text() or ''
      if utf8.len(text) and utf8.len(text) >= 2 and not text:find('[%z\1-\127]') then
        for _, code in ipairs(M.encode(text, rev_codes(env))) do M.add_word(code, text) end
      end
      ctx:commit()
      return 1
    end
    local n
    if kc >= 0x31 and kc <= 0x39 then n = kc - 0x30
    elseif kc >= 0xffb1 and kc <= 0xffb9 then n = kc - 0xffb0 end
    if not n or not ctx:has_menu() then return 2 end
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
    local code = seg_code(ctx, seg)
    if code:match('^[a-z]+$') then
      if is_table(cand) or cand.comment == MADE then
        M.pin(code, cand.text)                        -- 码表候选（含造过的词）：钉为该码首选
      elseif utf8.len(cand.text) and utf8.len(cand.text) >= 2 and not cand.text:find('[%z\1-\127]') then
        for _, c in ipairs(M.encode(cand.text, rev_codes(env))) do M.add_word(c, cand.text) end   -- 联想/整句候选：按夜莺词规则造词
      end
    end
    ctx:select(idx)
    -- select 只是选中；整段输入都已选定时要再提交一次（和按数字键上屏的效果一致）
    local done = false
    local ok, fin = pcall(function() return ctx.composition:has_finished_composition() end)
    if ok then done = fin else done = not ctx:has_menu() end
    if done then ctx:commit() end
    return 1
  end
  if key:shift() and not key:ctrl() and not key:alt() and kc == 0xffff and ctx:has_menu() then   -- Shift+Delete
    local cand = ctx:get_selected_candidate()
    if cand and cand.comment == MADE then
      local seg = ctx.composition:back()
      M.remove_word(seg_code(ctx, seg), cand.text)
      ctx:refresh_non_confirmed_composition()
      return 1
    end
    return 2
  end
  return 2
end

return M
