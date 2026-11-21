-- DEVELOPER TOOL - not part of a release. Randomizer PROBE v7. Lets you inspect and test the game's own
-- level-script "give item" nodes by hand. Nothing happens unless you press one of these keys
-- (Num Lock on). The randomizer itself does not need this file; 09_rando_real.lua delivers
-- rewards automatically.
--
--   NUMPAD3  survey: list the grant-type script nodes on this planet and pre-select the
--            AddToInventoryAction node that is known to work (log: RANDO-PROBE node ...)
--   NUMPAD4  select the next node that can be fired
--   NUMPAD5  fire the selected node as it is
--   NUMPAD7  choose a test item (your seed's weapons first, then gadgets)
--   NUMPAD6  give the test item through the selected AddToInventoryAction node
--   NUMPAD9  census: find a node that is safe to borrow on this planet (log: RANDO-REAL census)
--   NUMPAD8  give the test item through that borrowed node
-- Removed in v7: the bolt-counter scan (the count is not stored where it searched), the
-- AmmoCost weapon lock (no effect) and the component-index search (exceeded the frame budget).

RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["dev(probe)"] = "10.0.24"   -- the kit check (10_rando_runtime.lua)
RANDO_PROBE = RANDO_PROBE or {}
local P = RANDO_PROBE
P.version = 7
P.frame = P.frame or 0

local function log(...) pcall(rivet.log, "[rando]", "RANDO-PROBE", ...) end
-- every HUD message is also logged
local function say(t) log("HUD:", t); pcall(rivet.notify, "[PROBE] " .. t, { type = "center", duration = 5 }) end
P.log, P.say = log, say

-- ---- helpers -------------------------------------------------------------------------
local function hex_to_bin(h) return (h:gsub("%s", ""):gsub("%x%x", function(x) return string.char(tonumber(x, 16)) end)) end
local function bin_to_hex(b) return (b:gsub(".", function(c) return string.format("%02X ", c:byte()) end)):sub(1, -2) end
local function addr(n) return string.format("%X", n) end
-- 8 little-endian bytes -> "%016X" text (asset ids pass 2^63, so they stay text)
local function le_qword_hex(bin, i) local s = "" for k = i + 7, i, -1 do s = s .. string.format("%02X", bin:byte(k)) end return s end
-- "%016X" text -> "AA BB .." little-endian byte text for rivet.write
local function qword_hex_to_le(hex) local t = {} for k = 15, 1, -2 do t[#t + 1] = hex:sub(k, k + 1) end return table.concat(t, " ") end
P.hex_to_bin, P.bin_to_hex, P.le_qword_hex, P.qword_hex_to_le = hex_to_bin, bin_to_hex, le_qword_hex, qword_hex_to_le

-- ---- script-node grants -----------------------------------------------------------------
P.FILTERS = { "Inventory", "Currency", "Weapon", "Level", "Planetary", "Reward", "Pickup", "Bolt" }
P.FIRE_PLUG = { AddToInventoryAction = "In", AddCurrencyAction = "In", UnlockLevelAction = "Unlock",
                SetWeaponEquipableAction = "In" }
P.DETAIL = { AddToInventoryAction = true, AddCurrencyAction = true, UnlockLevelAction = true,
             SetWeaponEquipableAction = true, SubCurrencyAction = true, SetCurrencyAction = true,
             GetCurrencyAction = true, RemoveFromInventoryAction = true, SetPlanetaryTravelAction = true,
             EquipWeaponAction = true, PickupItemAction = true, SpawnRewardAction = true,
             IsLevelUnlockedAction = true, CheckPlanetaryTravelAction = true, UIArenaRewardAction = true }
P.DETAIL_PER_CLASS = 12
P.nodes, P.targets, P.sel = {}, {}, 0
P.survey = nil
P.pending = {}          -- { at = frame, fn = function } run later in on_frame
P.watch_until = 0

local function later(frames, fn) P.pending[#P.pending + 1] = { at = P.frame + frames, fn = fn } end

local function item_name(hex) return RANDO_ITEM_IDS and RANDO_ITEM_IDS[hex] end

-- decode the node's own fields, whose offsets come from the handlers in your exe
local function decode(info, bin)       -- bin = 0x20 bytes read from node+0x58
  local f = {}
  if info.class == "AddToInventoryAction" then
    f.item = le_qword_hex(bin, 0x60 - 0x58 + 1)
    f.item_name = item_name(f.item)
    f.count = string.unpack("<i4", bin, 0x68 - 0x58 + 1)
  elseif info.class == "SetWeaponEquipableAction" then
    f.weapon = string.unpack("<I4", bin, 0x6c - 0x58 + 1)
    f.equipable = bin:byte(0x70 - 0x58 + 1)
  elseif info.class == "UnlockLevelAction" then
    f.level = string.unpack("<i4", bin, 0x60 - 0x58 + 1)
  end
  return f
end

local function describe(info)
  local f, parts = info.fields or {}, {}
  if f.item then parts[#parts + 1] = "item=" .. f.item .. (f.item_name and (" (" .. f.item_name .. ")") or " (not a known item id)") end
  if f.count then parts[#parts + 1] = "count=" .. f.count end
  if f.weapon then parts[#parts + 1] = "weapon=" .. f.weapon .. " equipable=" .. f.equipable end
  if f.level then parts[#parts + 1] = "level=" .. f.level end
  for _, v in ipairs(info.vars or {}) do parts[#parts + 1] = v end
  return table.concat(parts, " ")
end
P.describe = describe

function P.inspect(node)
  local info = { component = node.component, actor = node.actor, class = node.class, uid = node.uid }
  local ok, c = pcall(rivet.component, node.actor, node.class)
  if ok and c and c.handle == node.component then
    info.addr = tonumber(c.address, 16)
    local okr, text = pcall(rivet.read, addr(info.addr + 0x58), 0x20)
    if okr and text then
      info.raw = text
      info.fields = decode(info, hex_to_bin(text))
    end
  else
    info.why = ok and "the actor holds another node of this class first" or tostring(c)
  end
  local okn, n = pcall(rivet.script_node, node.component, false)
  info.vars, info.outs = {}, {}
  if okn and type(n) == "table" then
    for _, v in ipairs(n.vars or {}) do
      local label = v.name or v.plug_name or string.format("0x%08X", v.plug or 0)
      if v.live then
        local val = v.value
        if type(val) == "table" then val = "{" .. tostring(val.count or #val) .. " actor(s)}" end
        info.vars[#info.vars + 1] = label .. "=" .. tostring(val)
      else
        info.vars[#info.vars + 1] = label .. "=(not live)"
      end
    end
    for _, o in ipairs(n.outputs or {}) do
      info.outs[#info.outs + 1] = (o.plug_name or string.format("0x%08X", o.plug or 0)) .. "->" .. tostring(o.to and o.to.class)
    end
  else
    info.vars[#info.vars + 1] = "script_node: " .. tostring(n)
  end
  log(string.format("node %s comp=%s actor=%s uid=%s %s %s out[%s] raw58=%s", info.class, tostring(info.component),
      tostring(info.actor), tostring(info.uid), info.addr and ("addr=" .. addr(info.addr)) or ("no address: " .. tostring(info.why)),
      describe(info), table.concat(info.outs, ","), tostring(info.raw)))
  return info
end

-- the node is still the same live instance (round 9: a node from before a reload was written to)
function P.still_valid(t)
  local ok, c = pcall(rivet.component, t.actor, t.class)
  return ok and c and c.handle == t.component and t.addr ~= nil and tonumber(c.address, 16) == t.addr
end

function P.start_survey()
  P.survey = { fi = 1, seen = {}, counts = {}, queue = {}, per_class = {} }
  P.nodes, P.targets, P.sel = {}, {}, 0
  say("surveying script nodes on this planet...")
end

function P.survey_step()
  local s = P.survey
  if not s then return end
  if s.fi <= #P.FILTERS then
    local filter = P.FILTERS[s.fi]; s.fi = s.fi + 1
    local ok, list = pcall(rivet.script_nodes, filter, 200)
    if not ok then log("script_nodes(" .. filter .. ") failed:", tostring(list)); return end
    for _, node in ipairs(list) do
      if not s.seen[node.component] then
        s.seen[node.component] = true
        s.counts[node.class] = (s.counts[node.class] or 0) + 1
        if P.DETAIL[node.class] and (s.per_class[node.class] or 0) < P.DETAIL_PER_CLASS then
          s.per_class[node.class] = (s.per_class[node.class] or 0) + 1
          s.queue[#s.queue + 1] = node
        end
      end
    end
    return
  end
  for _ = 1, 3 do
    local node = table.remove(s.queue, 1)
    if not node then break end
    local info = P.inspect(node)
    P.nodes[#P.nodes + 1] = info
    if P.FIRE_PLUG[info.class] then P.targets[#P.targets + 1] = info end
  end
  if #s.queue > 0 then return end
  P.survey = nil
  local names = {}
  for k, v in pairs(s.counts) do names[#names + 1] = k .. "=" .. v end
  table.sort(names)
  log("survey done:", #names == 0 and "no grant-type nodes loaded here" or table.concat(names, " "))
  log("survey fireable:", #P.targets)
  -- pre-select the node that granted Box Breaker + Hoverboots in round 7 (or the safest one)
  P.sel = 0
  local pref = {}
  for i, uid in ipairs((RANDO_DATA and RANDO_DATA.real_nodes and RANDO_DATA.real_nodes.preferred_nodes) or
                       { "98763a0c6fd24259", "b075049b0add2df3" }) do pref[uid] = i end
  local best
  for i, t in ipairs(P.targets) do
    if t.class == "AddToInventoryAction" and pref[t.uid] and (not best or pref[t.uid] < pref[P.targets[best].uid]) then best = i end
  end
  if best then P.sel = best end
  say(#P.targets .. " node(s) can be fired here" .. (best and (" - selected " .. P.targets[best].class .. " " .. P.targets[best].uid) or " - NUMPAD4 to pick one"))
end

function P.select_next()
  if #P.targets == 0 then say("nothing to fire - NUMPAD3 surveys this planet"); return nil end
  P.sel = P.sel % #P.targets + 1
  local t = P.targets[P.sel]
  say(string.format("%d/%d %s %s", P.sel, #P.targets, t.class, describe(t)))
  return t
end

function P.fire(t, what)
  t = t or P.targets[P.sel]
  if not t then say("pick a node first (NUMPAD3, then NUMPAD4)"); return false end
  local plug = P.FIRE_PLUG[t.class]
  local ok, err = pcall(rivet.signal, t.component, plug)
  log("fire", t.class, "comp=" .. tostring(t.component), "plug=" .. plug, what or describe(t), ok and "queued" or ("refused: " .. tostring(err)))
  P.watch_until = P.frame + 600
  say(ok and ("fired " .. t.class .. " - did anything change?") or ("refused: " .. tostring(err)))
  return ok
end

-- test items: every weapon and gadget item config in your dag, reachable through the id table.
-- Built on first use, so dev(item_ids).lua may load before or after this file.
P.test_items, P.test_i, P.item_id = {}, 0, {}
function P.build_test_items()
  if P.built then return end
  P.built = true
  for hex, path in pairs(RANDO_ITEM_IDS or {}) do P.item_id[path] = hex end
  -- the player's weapons and gadgets (from the seed export), weapons first; without a seed,
  -- every weapon/gadget item in the dag
  if RANDO_DATA and RANDO_DATA.real_items then
    for _, info in pairs(RANDO_DATA.real_items) do
      P.item_id[info.config] = info.id
      P.test_items[#P.test_items + 1] = info.config
    end
  else
    for path in pairs(P.item_id) do
      if path:match("^configs/equipment/wpn_.+_item%.config$") or path:match("^configs/equipment/gdgt_.+_item%.config$") then
        P.test_items[#P.test_items + 1] = path
      end
    end
  end
  table.sort(P.test_items, function(a, b)
    local wa, wb = a:find("/wpn_") ~= nil, b:find("/wpn_") ~= nil
    if wa ~= wb then return wa end
    return a < b
  end)
end

function P.next_test_item()
  P.build_test_items()
  if #P.test_items == 0 then say("no test items: dev(item_ids).lua and the seed file are missing"); return nil end
  P.test_i = P.test_i % #P.test_items + 1
  local path = P.test_items[P.test_i]
  local label = path:match("([^/]+)_item%.config$")
  if RANDO_DATA and RANDO_DATA.real_items then
    for item, info in pairs(RANDO_DATA.real_items) do
      if info.config == path then label = label .. " = " .. ((RANDO_DATA.items[item] and RANDO_DATA.items[item].name) or item) end
    end
  end
  say("test item " .. P.test_i .. "/" .. #P.test_items .. ": " .. label .. " - NUMPAD6 gives it")
  return path
end

-- point an AddToInventoryAction node at another item, fire it, then put the node back.
-- Refused unless the node's own +0x60 was recognised as an item id: that proves the layout.
function P.grant_via_node(path, amount)
  P.build_test_items()
  path = path or P.test_items[P.test_i]
  local t = P.targets[P.sel]
  if not path then say("choose a test item with NUMPAD7"); return false end
  if not t or t.class ~= "AddToInventoryAction" then say("select an AddToInventoryAction node with NUMPAD4"); return false end
  if not (t.addr and t.fields and t.fields.item_name) then
    say("this node's item field was not recognised - not writing to it"); log("grant refused: layout unproven", describe(t)); return false
  end
  if not P.still_valid(t) then
    P.targets, P.sel = {}, 0
    say("that node is gone (the level reloaded) - NUMPAD3 again"); return false
  end
  local hex = P.item_id[path]
  local at = addr(t.addr + 0x60)
  local ok0, original = pcall(rivet.read, at, 12)
  if not ok0 or not original then say("cannot read the node: " .. tostring(original)); return false end
  local bytes = qword_hex_to_le(hex) .. " " .. bin_to_hex(string.pack("<i4", amount or 1))
  local okw, err = pcall(rivet.write, at, bytes)
  if not okw then log("grant write failed", tostring(err)); say("write failed: " .. tostring(err)); return false end
  local _, now = pcall(rivet.read, at, 12)
  log("grant: node now holds", tostring(now), "(wanted " .. bytes .. ")")
  local fired = P.fire(t, "giving " .. path)
  later(90, function()
    if not P.still_valid(t) then log("grant: node gone before restore - nothing to put back"); return end
    local okr, e2 = pcall(rivet.write, at, original)
    log("grant: node restored", okr and "ok" or tostring(e2))
  end)
  log("grant", path, "x" .. (amount or 1), "via node comp=" .. tostring(t.component), fired and "fired" or "not fired")
  return fired
end

function P.donor_grant(path)
  P.build_test_items()
  path = path or P.test_items[P.test_i]
  if not path then say("choose a test item with NUMPAD7"); return false end
  if not RANDO_REAL then say("09_rando_real.lua is missing"); return false end
  local item
  for k, info in pairs((RANDO_DATA and RANDO_DATA.real_items) or {}) do if info.config == path then item = k end end
  if not item then say("not a randomizer item: " .. path); return false end
  local ok, err = RANDO_REAL.probe_donor_grant(item)
  P.watch_until = P.frame + 600
  log("donor grant", item, ok and "fired" or ("refused: " .. tostring(err)))
  say(ok and ("fired " .. item .. " through the borrowed node - check your inventory") or tostring(err))
  return ok
end

-- events seen after a fire, so the log shows what the game did with it
local function fields_text(ev)
  local parts = {}
  for k, v in pairs(ev.fields or {}) do
    if type(v) == "number" and math.abs(v) >= 1e15 then v = string.format("%.0f", v) end
    parts[#parts + 1] = tostring(k) .. "=" .. tostring(v)
  end
  table.sort(parts)
  return table.concat(parts, " ")
end
P.WATCH = { "GainBoltEvent", "WeaponAddedEvent", "GadgetItemAddedEvent", "PurchaseWeaponEvent",
            "VendorPurchaseEvent", "GainGoldBoltEvent", "MissionStateChangedEvent", "PlanetChangedEvent",
            "InventoryChangedEvent", "GainRaritaniumEvent" }

-- ---- wiring ------------------------------------------------------------------------------
local function on(class, fn) local ok, err = pcall(rivet.on_event, class, fn); if not ok then log("cannot subscribe", class, err) end; return ok end
local function forget_targets() P.targets, P.sel, P.nodes = {}, 0, {} end
on("PlanetChangedEvent", forget_targets)
on("LevelLoadedEvent", forget_targets)
for _, class in ipairs(P.WATCH) do
  on(class, function(ev) if P.frame <= P.watch_until then log("after fire:", class, fields_text(ev)) end end)
end

local function key(name, fn) pcall(rivet.on_key, rivet.key(name), function()
  local ok, err = pcall(fn); if not ok then log(name, "failed:", tostring(err)) end end) end
key("NUMPAD3", function() P.start_survey() end)
key("NUMPAD4", function() P.select_next() end)
key("NUMPAD5", function() P.fire() end)
key("NUMPAD6", function() P.grant_via_node() end)
key("NUMPAD7", function() P.next_test_item() end)
key("NUMPAD9", function()
  if not RANDO_REAL or not RANDO_REAL.start_donor_search then say("09_rando_real.lua is missing"); return end
  if not RANDO_VTABLES then say("dev(vtables).lua is missing"); return end
  say("census of this planet's script nodes...")
  RANDO_REAL.start_donor_search(true)
end)
key("NUMPAD8", function() P.donor_grant() end)

function P.on_frame()
  P.frame = P.frame + 1
  for i = #P.pending, 1, -1 do
    local p = P.pending[i]
    if P.frame >= p.at then table.remove(P.pending, i); local ok, err = pcall(p.fn); if not ok then log("later:", tostring(err)) end end
  end
  if P.survey then
    local ok, err = pcall(P.survey_step)
    if not ok then log("survey step:", tostring(err)); P.survey = nil end
  end
end
pcall(rivet.on_frame, P.on_frame)
log("v7 loaded: NUMPAD3 survey, NUMPAD4 select, NUMPAD5 fire, NUMPAD7 item, NUMPAD6 give item, NUMPAD9 census, NUMPAD8 give via borrowed node")
