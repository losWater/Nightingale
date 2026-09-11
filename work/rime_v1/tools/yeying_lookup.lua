local M = {}
function M.func(input, seg, env)
  if not input:match('^[`~]') then return end
  local spelling = input:sub(2)
  if spelling == '' then return end
  -- Load only on the first lookup; typing normal sentences never reads this table.
  if not env.lookup_data then env.lookup_data = require('yeying_lookup_data') end
  local data = env.lookup_data
  local sounds = {}
  if #spelling == 2 and data.sounds[spelling] then sounds[spelling] = true end
  local full = data.pinyin[spelling]
  if full then sounds[full] = true end
  local emitted = {}
  for sound in pairs(sounds) do
    for _, row in ipairs(data.sounds[sound] or {}) do
      if not emitted[row[1]] then
        emitted[row[1]] = true
        yield(Candidate('yeying_lookup', seg.start, seg._end, row[1], '〔'..row[2]..' · '..table.concat(row[3],'/')..'〕'))
      end
    end
  end
end
return M
