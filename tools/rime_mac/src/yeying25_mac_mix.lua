-- Fixed candidates retain the 2.5 release order. Sentence candidates are lazy.
local pin = require('yeying25_mac_pin')
local M = {}

function M.init(env)
  env.fixed = Component.Translator(env.engine, '', 'table_translator@fixed')
  env.smart = Component.Translator(env.engine, '', 'script_translator@translator')
end

function M.func(input, seg, env)
  if not seg:has_tag('abc') or input:match('^[`~]') then return end
  -- The 2.5 table also has a few 5/6/8-key phrase entries. Keep them reachable.
  if #input <= 8 then
    local list, seen = {}, {}
    local fixed = env.fixed:query(input, seg)
    if fixed then
      for cand in fixed:iter() do
        list[#list + 1] = cand
        seen[cand.text] = true
      end
    end
    for _, text in ipairs(pin.words(input)) do
      if not seen[text] then
        list[#list + 1] = Candidate('user_table', seg.start, seg._end, text, pin.MADE)
        seen[text] = true
      end
    end
    for _, cand in ipairs(pin.order(input, list)) do yield(cand) end
  end
  local translator = env.smart
  if env.engine.context:get_option('yeying_short_words') then
    if not env.smart_short then
      env.smart_short = Component.Translator(env.engine, '', 'script_translator@translator_short')
    end
    translator = env.smart_short
  end
  local candidates = translator:query(input, seg)
  if candidates then
    for cand in candidates:iter() do yield(cand) end
  end
end

return M
