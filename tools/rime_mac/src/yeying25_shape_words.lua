-- 夜莺·形码版录词（2026-10-07 作者需求）
-- 形码版四码顶屏，输入框里攒不出整句，V5 那种 Ctrl+Enter 造词用不上，所以改成“录词”：
--   Ctrl+Enter：开始录词 → 照常一个字一个字打、照常上屏 → 再按 Ctrl+Enter，把录下的字按夜莺词规则编码存为词
--               （二字 AaAbBaBb，三字 AaBaCa，四字以上 AaBaCaZa；多音字取全部读音组合，最多 8 个码）。
--   录词中、没有正在输入的编码时按 Esc：取消录词。
--   Shift+Delete：选中的是形码版造的词（带〔造〕）时删除。
-- 词表独立：用户目录 yeying25_shape_words.txt，不与 V5 版的 yeying25_mac_words.txt 混用。
-- 录词状态在候选的第一项后面显示〔录词：…〕（见 yeying25_shape_words_filter.lua）。
local pin = require('yeying25_mac_pin')
local FILE = 'yeying25_shape_words.txt'
local M = { recording = false, buf = '' }
local words, file_path = nil, nil

local function path()
  if not file_path then
    local dir = rime_api and rime_api.get_user_data_dir and rime_api.get_user_data_dir() or '.'
    file_path = dir .. '/' .. FILE
  end
  return file_path
end

local function load()
  if words then return words end
  words = {}
  local f = io.open(path(), 'r')
  if not f then return words end
  for line in f:lines() do
    local parts = {}
    for x in line:gsub('\r$', ''):gmatch('[^\t]+') do parts[#parts + 1] = x end
    if #parts >= 2 then
      local code = table.remove(parts, 1)
      words[code] = words[code] or {}
      for _, x in ipairs(parts) do words[code][#words[code] + 1] = x end
    end
  end
  f:close()
  return words
end

local function save()
  local f = io.open(path() .. '.tmp', 'w')
  if not f then return false end
  local codes = {}
  for code, list in pairs(words) do if #list > 0 then codes[#codes + 1] = code end end
  table.sort(codes)
  for _, code in ipairs(codes) do f:write(code, '\t', table.concat(words[code], '\t'), '\n') end
  f:close()
  return os.rename(path() .. '.tmp', path()) ~= nil
end

function M.words(code) return load()[code] or {} end

function M.add(code, text)
  load()
  words[code] = words[code] or {}
  for _, t in ipairs(words[code]) do if t == text then return false end end
  words[code][#words[code] + 1] = text
  return save()
end

function M.remove(code, text)
  load()
  local list, hit = {}, false
  for _, t in ipairs(words[code] or {}) do if t == text then hit = true else list[#list + 1] = t end end
  words[code] = list
  if hit then save() end
  return hit
end

-- 只录汉字（标点、字母不进词）
local function hanzi(s)
  local out = {}
  for _, cp in utf8.codes(s) do
    if cp >= 0x2E80 and not (cp >= 0x3000 and cp <= 0x303F) and not (cp >= 0xFF00 and cp <= 0xFFEF) then out[#out + 1] = utf8.char(cp) end
  end
  return table.concat(out)
end

local function codes_of(env)
  if env.yy_rev == nil then
    local ok, rev = pcall(function() return ReverseLookup('yeying25_mac_rime_fixed') end)
    env.yy_rev = ok and rev or false
  end
  return function(ch)
    local out = {}
    if env.yy_rev then
      for c in (env.yy_rev:lookup(ch) or ''):gmatch('%S+') do
        if #c == 4 and c:match('^[a-z]+$') then out[#out + 1] = c end
      end
    end
    return out
  end
end

function M.init(env)
  env.yy_notifier = env.engine.context.commit_notifier:connect(function(ctx)
    if not M.recording then return end
    local ok, text = pcall(function() return ctx:get_commit_text() end)
    if ok and text then M.buf = M.buf .. hanzi(text) end
  end)
end

function M.fini(env)
  if env.yy_notifier then env.yy_notifier:disconnect() end
end

local function plain(key) return not key:alt() and not key:super() end

function M.func(key, env)
  if key:release() then return 2 end
  local kc = key.keycode
  local ctx = env.engine.context
  if key:ctrl() and not key:shift() and plain(key) and (kc == 0xff0d or kc == 0xff8d) then   -- Ctrl+Return / Ctrl+KP_Enter
    if ctx:is_composing() then ctx:commit() end      -- 正在输入的字先上屏（录词中则一并录入）
    if M.recording then
      local text = M.buf
      M.recording, M.buf = false, ''
      if (utf8.len(text) or 0) >= 2 then
        for _, code in ipairs(pin.encode(text, codes_of(env))) do M.add(code, text) end
      end
    else
      M.recording, M.buf = true, ''
    end
    return 1
  end
  if kc == 0xff1b and not key:ctrl() and not key:shift() and plain(key) and M.recording and not ctx:is_composing() then   -- Esc
    M.recording, M.buf = false, ''
    return 1
  end
  if key:shift() and not key:ctrl() and plain(key) and kc == 0xffff and ctx:has_menu() then   -- Shift+Delete
    local cand = ctx:get_selected_candidate()
    if cand and cand.comment == pin.MADE then
      local seg = ctx.composition:back()
      if M.remove(ctx.input:sub(seg.start + 1, seg._end), cand.text) then
        ctx:refresh_non_confirmed_composition()
        return 1
      end
    end
  end
  return 2
end

return M
