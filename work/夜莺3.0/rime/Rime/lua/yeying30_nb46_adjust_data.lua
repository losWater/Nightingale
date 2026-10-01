-- 夜莺 3.0 NB46 单字试用：手动调整（共享数据，作者 2026-10-02 定规则）
-- 记录文件：<用户目录>/yeying30_nb46_adjust.tsv，每行：时间 \t 码 \t 字 \t 参数 \t 动作
--   top  ：把字提到该码首选
--   up   ：上移——字从该码挪到长一级的码；那里若是有人的简码位，原占位字被挤上去（只往上挪，最多到全码）；
--          空出来的简码位由“以该码开头、字频最高、还没有更短简码”的核心字接过，接班者原简码位照此继续补
--   down ：下移——字从该码挪到短一级的码，原占位字被挤上去；字原来的简码位空出来后同样按字频补
--   undo ：撤销上一步（整步，涉及的码一起恢复）
local M = { loaded = false, state = {}, base = {}, codes = {}, prefix = {}, freq = {}, core = {}, ops = {} }

local function udir() return rime_api.get_user_data_dir() end
local function logpath() return udir() .. '/yeying30_nb46_adjust.tsv' end

local function st(code)
  local s = M.state[code]
  if not s then s = { order = {}, removed = {} }; M.state[code] = s end
  return s
end
local function without(list, x)
  local o = {}
  for _, v in ipairs(list) do if v ~= x then o[#o + 1] = v end end
  return o
end
local function front(code, x) local s = st(code); s.order = without(s.order, x); table.insert(s.order, 1, x); s.removed[x] = nil end
local function remove_from(code, x) local s = st(code); s.order = without(s.order, x); s.removed[x] = true end

local function load_dict()
  local f = io.open(udir() .. '/yeying30_nb46_single.dict.yaml', 'r')
  if not f then return end
  local body = false
  for line in f:lines() do
    if body then
      local text, code = line:match('^([^\t]+)\t([^\t]+)\t')
      if text then
        local b = M.base[code]; if not b then b = {}; M.base[code] = b end
        b[#b + 1] = text
        local c = M.codes[text]; if not c then c = {}; M.codes[text] = c end
        c[#c + 1] = code
      end
    elseif line == '...' then body = true end
  end
  f:close()
  local g = io.open(udir() .. '/yeying30_nb46_freq.txt', 'r')
  if g then
    for line in g:lines() do
      local t, syl, fq = line:match('^([^\t]+)\t([^\t]+)\t([^\t]+)$')
      if t then M.freq[t .. '\t' .. syl] = tonumber(fq); M.core[t] = true end
    end
    g:close()
  end
  -- 前缀索引：码前缀 -> 全码以它开头的核心字
  for text, cs in pairs(M.codes) do
    if M.core[text] then
      for _, c in ipairs(cs) do
        if #c == 4 then
          for l = 1, 3 do
            local p = c:sub(1, l)
            local lst = M.prefix[p]; if not lst then lst = {}; M.prefix[p] = lst end
            local dup = false
            for _, x in ipairs(lst) do if x == text then dup = true; break end end
            if not dup then lst[#lst + 1] = text end
          end
        end
      end
    end
  end
end

function M.display(code)
  local base, s = M.base[code] or {}, M.state[code]
  if not s then return base end
  local out, seen = {}, {}
  for _, t in ipairs(s.order) do if not s.removed[t] and not seen[t] then out[#out + 1] = t; seen[t] = true end end
  for _, t in ipairs(base) do if not s.removed[t] and not seen[t] then out[#out + 1] = t; seen[t] = true end end
  return out
end

-- 简码位的占位字：显示顺序里第一个核心字
local function holder(code)
  for _, t in ipairs(M.display(code)) do if M.core[t] then return t end end
  return nil
end

local function fulls(t, prefix)
  local o = {}
  for _, c in ipairs(M.codes[t] or {}) do if #c == 4 and c:sub(1, #prefix) == prefix then o[#o + 1] = c end end
  return o
end

function M.upper(a, s)
  local f = fulls(a, s)[1]
  if f and #s < 4 then return f:sub(1, #s + 1) end
  return nil
end

local function freq_of(t, x)
  local best = 0
  for _, f in ipairs(fulls(t, x)) do
    local v = M.freq[t .. '\t' .. f:sub(1, 2)] or 0
    if v > best then best = v end
  end
  return best
end

-- 字 t 能否接简码位 x：它以 x 开头的读音里，没有长度 ≤ #x 的简码
local function eligible(t, x)
  for _, f in ipairs(fulls(t, x)) do
    for l = 1, #x do if holder(f:sub(1, l)) == t then return false end end
  end
  return true
end

-- 字 t 在以 x 开头的读音上、比 x 更长的现有简码
local function longer_short(t, x)
  for _, f in ipairs(fulls(t, x)) do
    for l = #x + 1, 3 do local c = f:sub(1, l); if holder(c) == t then return c end end
  end
  return nil
end

-- 空出来的简码位 x：交给字频最高的合格核心字，接班者原简码位继续补
function M.fill(x, excl)
  if #x >= 4 or holder(x) then return end
  local best, bf = nil, -1
  for _, t in ipairs(M.prefix[x] or {}) do
    if not excl[t] and eligible(t, x) then
      local f = freq_of(t, x)
      if f > bf then best, bf = t, f end
    end
  end
  if not best then return end
  local y = longer_short(best, x)
  front(x, best)
  excl[best] = true
  if y then remove_from(y, best); M.fill(y, excl) end
end

-- 被挤掉的字 b 离开简码位 s：挪到长一级的码；那里若有占位字，继续往上挤，最多到全码
function M.bump(b, s)
  local u = M.upper(b, s)
  if not u then return end
  if #u == 4 then front(u, b); return end
  local h = holder(u)
  front(u, b)
  if h and h ~= b then remove_from(u, h); M.bump(h, u) end
end

local function apply(code, text, param, act)
  if act == 'reset' then M.state[code] = nil
  elseif act == 'top' then front(code, text)
  elseif act == 'up' then
    local t = M.upper(text, code)
    if not t then return end
    remove_from(code, text)
    if #t == 4 then front(t, text)
    else
      local h = holder(t)
      front(t, text)
      if h and h ~= text then remove_from(t, h); M.bump(h, t) end
    end
    M.fill(code, { [text] = true })
  elseif act == 'down' then
    if #code < 2 then return end
    local s = code:sub(1, #code - 1)
    local h = holder(s)
    if #code == 4 then
      -- 有了简码：在全码上让位，但只让给核心字，扩展字与符号仍排在它后面
      local d, out, placed = without(M.display(code), text), {}, false
      for _, t in ipairs(d) do
        if not placed and not M.core[t] then out[#out + 1] = text; placed = true end
        out[#out + 1] = t
      end
      if not placed then out[#out + 1] = text end
      st(code).order = out
    else remove_from(code, text) end
    front(s, text)
    if h and h ~= text then remove_from(s, h); M.bump(h, s) end
    if #code < 4 then M.fill(code, { [text] = true }) end
  end
end

function M.rebuild()
  M.state = {}
  for _, op in ipairs(M.ops) do apply(op[1], op[2], op[3], op[4]) end
end

local function push(code, text, param, act)
  if act == 'undo' then table.remove(M.ops) else M.ops[#M.ops + 1] = { code, text, param, act } end
end

function M.load()
  if M.loaded then return end
  M.loaded = true
  load_dict()
  local f = io.open(logpath(), 'r')
  if f then
    for line in f:lines() do
      local _, code, text, param, act = line:match('^([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)\t([^\t]*)$')
      if code then push(code, text, param, act) end
    end
    f:close()
  end
  M.rebuild()
end

function M.record(code, text, param, act)
  push(code, text, param, act)
  if act == 'undo' then M.rebuild() else apply(code, text, param, act) end
  local f = io.open(logpath(), 'a')
  if f then
    f:write(os.date('%Y-%m-%d %H:%M:%S') .. '\t' .. code .. '\t' .. text .. '\t' .. param .. '\t' .. act .. '\n')
    f:close()
  end
end

return M
