-- Nightingale: fixed short-code lookup + lazy sentence translator.
-- Inspired by WhaleCold's table/script split; no candidate-stream exhaustion.
-- 2026-09-16：
--   fixed      = 纯码表翻译器（无用户词典），候选顺序就是码表顺序；
--   learn      = 同一词典 + 用户词典 yeying20_fixed_user，只负责承接"二字自动造词"，只取它给出的、码表里没有的新词；
--   主动造词  = yeying20_words.txt（Ctrl+Enter），以〔造〕标记出候选。
--   最终顺序由 yeying20_pin.order 决定：钉选在前 → 码表原序 → 自动造词/主动造词。不按使用频率乱序。
local pin = require('yeying20_pin')
local M = {}
function M.init(env)
  env.fixed = Component.Translator(env.engine, '', 'table_translator@fixed')
  env.learn = Component.Translator(env.engine, '', 'table_translator@fixed_user')
  env.smart = Component.Translator(env.engine, '', 'script_translator@translator')
  env.native = env.engine.schema.config:get_bool('yeying/native')
  env.model_max_input = env.engine.schema.config:get_int('yeying/model_max_input') or 36
  if env.native then
    env.impl = require('mohu_tiger_sentence').translator
    env.impl.init(env)
  end
end
function M.fini(env)
  if env.impl then env.impl.fini(env) end
end
function M.func(input, seg, env)
  if input:match('^[`~]') then return end
  if not seg:has_tag('abc') then return end
  if #input > 0 then
    local list, seen = {}, {}
    local fixed = env.fixed:query(input, seg)
    if fixed then
      for cand in fixed:iter() do list[#list + 1] = cand; seen[cand.text] = true end
    end
    local learn = env.learn and env.learn:query(input, seg)
    if learn then
      for cand in learn:iter() do
        if cand.type == 'user_table' and not seen[cand.text] then list[#list + 1] = cand; seen[cand.text] = true end
      end
    end
    for _, text in ipairs(pin.words(input)) do
      if not seen[text] then list[#list + 1] = Candidate('user_table', seg.start, seg._end, text, pin.MADE); seen[text] = true end
    end
    for _, cand in ipairs(pin.order(input, list)) do yield(cand) end
  end
  if env.impl and #env.engine.context.input <= env.model_max_input then
    env.impl.func(input, seg, env)
  end
  local smart = env.smart:query(input, seg)
  if smart then for cand in smart:iter() do yield(cand) end end
end
return M
