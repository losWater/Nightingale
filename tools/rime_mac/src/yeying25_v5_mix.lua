-- Nightingale fixed codes, then MoHu V5 sentences, then native Rime fallback.
local pin = require('yeying25_mac_pin')
local native = require('yeying25_v5_tiger_sentence').translator
local M = {}

function M.init(env)
  env.fixed = Component.Translator(env.engine, '', 'table_translator@fixed')
  env.smart = Component.Translator(env.engine, '', 'script_translator@translator')
  native.init(env)
end

function M.fini(env)
  native.fini(env)
end

function M.func(input, seg, env)
  if not seg:has_tag('abc') or input:match('^[`~]') then return end
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
  local short = env.engine.context:get_option('yeying_short_words')
  if not short and #env.engine.context.input <= 96 then
    native.func(input, seg, env)
  end
  local translator = env.smart
  if short then
    if not env.smart_short then
      env.smart_short = Component.Translator(env.engine, '', 'script_translator@translator_short')
    end
    translator = env.smart_short
  end
  local candidates = translator:query(input, seg)
  if candidates then for cand in candidates:iter() do yield(cand) end end
end
return M
