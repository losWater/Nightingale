-- Nightingale: fixed short-code lookup + lazy sentence translator.
-- Inspired by WhaleCold's table/script split; no candidate-stream exhaustion.
-- 2026-09-16：
--   fixed      = 纯码表翻译器（无用户词典），候选顺序就是码表顺序；
--   learn      = 同一词典 + 用户词典 yeying20_fixed_user，只负责承接"二字自动造词"，只取它给出的、码表里没有的新词；
--   主动造词  = yeying20_words.txt（Ctrl+Enter / Ctrl+N 对联想候选），以〔造〕标记出候选。
--   最终顺序由 yeying20_pin.order 决定：钉选在前 → 码表原序 → 自动造词/主动造词。不按使用频率乱序。
--   开关 yeying_short_words（默认关）：整句是否混入简词。
--     关：Rime 原生整句用 yeying20_rime（不含简词），V5 引擎用 tiger/lexicon；
--     开：Rime 原生整句用 yeying20_rime_short（含简词），V5 引擎释放后按 tiger/lexicon_short 重建（约几秒）。
local pin = require('yeying20_pin')
local M = {}
local OPTION = 'yeying_short_words'

local function apply_native_lexicon(env, on)
  if not env.impl then return end
  local cfg = env.engine.schema.config
  local want = on and env.lexicon_short or env.lexicon_base
  if not want or want == env.lexicon_active then return end
  env.impl.fini(env)
  cfg:set_string('tiger/lexicon', want)
  env.lexicon_active = want
  env.impl.init(env)
end

function M.init(env)
  env.fixed = Component.Translator(env.engine, '', 'table_translator@fixed')
  env.learn = Component.Translator(env.engine, '', 'table_translator@fixed_user')
  env.smart = Component.Translator(env.engine, '', 'script_translator@translator')
  env.smart_short = Component.Translator(env.engine, '', 'script_translator@translator_short')
  env.native = env.engine.schema.config:get_bool('yeying/native')
  env.model_max_input = env.engine.schema.config:get_int('yeying/model_max_input') or 36
  local ctx = env.engine.context
  if env.native then
    local cfg = env.engine.schema.config
    env.lexicon_base = cfg:get_string('tiger/lexicon')
    env.lexicon_short = cfg:get_string('tiger/lexicon_short')
    if ctx:get_option(OPTION) and env.lexicon_short then cfg:set_string('tiger/lexicon', env.lexicon_short); env.lexicon_active = env.lexicon_short
    else env.lexicon_active = env.lexicon_base end
    env.impl = require('mohu_tiger_sentence').translator
    env.impl.init(env)
  end
  env.option_conn = ctx.option_update_notifier:connect(function(c, name)
    if name == OPTION then apply_native_lexicon(env, c:get_option(OPTION)) end
  end)
end
function M.fini(env)
  if env.option_conn then env.option_conn:disconnect() end
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
  local smart = (env.engine.context:get_option(OPTION) and env.smart_short or env.smart):query(input, seg)
  if smart then for cand in smart:iter() do yield(cand) end end
end
return M
