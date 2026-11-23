import sys
import lupa.lua54 as l54
KIT=sys.argv[1]
L=l54.LuaRuntime(unpack_returned_tuples=True)
L.execute('RANDO_FILES = {}; rivet = { log = function() end }')
for f in ("01_rando_data.lua","02_rando_generator.lua","03_rando_campaign.lua"): L.execute(open(f"{KIT}/scripts/{f}",encoding="utf-8").read())
r=L.eval('''function()
  local G = RANDO_GEN
  local ok, fail, coll, placed, total, errs = 0, 0, 0, 0, 0, {}
  for _, preset in ipairs({ "balanced", "casual", "chaos", "campaign" }) do
    for i = 1, 30 do
      local seed, err = G.generate("batch-" .. preset .. "-" .. i, {}, G.PRESETS[preset] and preset or "balanced")
      if seed then
        ok = ok + 1
        for lid, l in pairs(seed.locations) do
          local it = l.item and RANDO_DATA.items[l.item]
          if it and it.category == "omega" then placed = placed + 1; if RANDO_DATA.locations[lid].kind == "collectible" then coll = coll + 1 end end
        end
        for k, w in pairs(seed.registry) do if RANDO_DATA.items[k] and RANDO_DATA.items[k].category == "omega" then total = total + 1 end end
      else fail = fail + 1; if #errs < 3 then errs[#errs+1] = preset .. ": " .. tostring(err) end end
    end
  end
  return string.format("seeds ok %d, failed %d; omega placed on locations %d of %d registered; on collectibles %d; %s", ok, fail, placed, total, coll, table.concat(errs, " | "))
end''')()
print(r)
