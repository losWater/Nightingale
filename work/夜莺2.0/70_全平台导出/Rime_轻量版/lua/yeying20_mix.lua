-- Nightingale: fixed short-code lookup + lazy sentence translator.
-- Inspired by WhaleCold's table/script split; no candidate-stream exhaustion.
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
    local fixed = env.fixed:query(input, seg)
    if fixed then for cand in fixed:iter() do yield(cand) end end
  end
  if env.impl and #env.engine.context.input <= env.model_max_input then
    env.impl.func(input, seg, env)
  end
  local smart = env.smart:query(input, seg)
  if smart then for cand in smart:iter() do yield(cand) end end
end
return M
