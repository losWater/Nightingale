-- 夜莺·形码版录词：录词中，在第一个候选后面显示〔录词：已录的字〕，提醒正在录词（逻辑见 yeying25_shape_words.lua）
local words = require('yeying25_shape_words')
return function(input, env)
  local first = true
  for cand in input:iter() do
    if first and words.recording then
      cand.comment = (cand.comment or '') .. '〔录词：' .. words.buf .. '〕'
    end
    first = false
    yield(cand)
  end
end
