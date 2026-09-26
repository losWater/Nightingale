local M = {}
function M.func(input, env)
  if not env.engine.context:get_option('chaifen') then
    for cand in input:iter() do yield(cand) end
    return
  end
  if not env.splits then
    env.splits = {}
    for _, rows in pairs(require('yeying25_mac_lookup_data').sounds) do
      for _, row in ipairs(rows) do env.splits[row[1]] = row[2] end
    end
  end
  for cand in input:iter() do
    local split = env.splits[cand.text]
    if split and cand.type ~= 'yeying25_mac_lookup' then
      local original = cand.comment or ''
      cand.comment = original .. '〔' .. split .. '〕'
    end
    yield(cand)
  end
end
return M
