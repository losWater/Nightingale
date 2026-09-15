-- Nightingale: fixed short-code lookup + lazy sentence translator.
-- Inspired by WhaleCold's table/script split; no candidate-stream exhaustion.
-- 2026-09-16：固定表候选 + 主动造词（yeying20_words.txt）经 yeying20_pin.order 重排
--   （钉选在前 → 码表原序 → 自动造词/主动造词），不按使用频率乱序。
local pin = require('yeying20_pin')
local M = {}
function M.init(env)
  env.fixed = Component.Translator(env.engine, '', 'table_translator@fixed')
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
    local list = {}
    local fixed = env.fixed:query(input, seg)
    if fixed then for cand in fixed:iter() do list[#list + 1] = cand end end
    for _, text in ipairs(pin.words(input)) do
      list[#list + 1] = Candidate('user_table', seg.start, seg._end, text, pin.MADE)
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
