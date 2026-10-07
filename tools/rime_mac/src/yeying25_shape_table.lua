-- Exact fixed-table lookup only: no script translator or model dependency.
local pin = require('yeying25_mac_pin')
local shape_words = require('yeying25_shape_words')   -- 形码版独立词表（录词）
local M = {}
function M.init(env)
  env.table = Component.Translator(env.engine, '', 'table_translator@translator')
end
function M.func(input, seg, env)
  if not seg:has_tag('abc') or not input:match('^[a-z]+$') then return end
  local list, seen = {}, {}
  local candidates = env.table:query(input, seg)
  if candidates then
    for cand in candidates:iter() do
      list[#list+1] = cand
      seen[cand.text] = true
    end
  end
  for _, text in ipairs(shape_words.words(input)) do
    if not seen[text] then
      list[#list+1] = Candidate('user_table', seg.start, seg._end, text, pin.MADE)
      seen[text] = true
    end
  end
  for _, cand in ipairs(pin.order(input, list)) do yield(cand) end
end
return M
