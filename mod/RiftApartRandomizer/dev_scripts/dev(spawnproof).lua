-- DEVELOPER TOOL - not part of a release. SPAWN PROOF v6 (dev 10.26): controlled enemy replacements on Zurkon,
-- to prove (or disprove) in your game the mechanism the Enemy / Boss / Chaos Randomizers will use.
--
-- dev 10.27: ITS RESULT (round37: 6/6 factories, 20/20 spawns replaced) is now the Enemy Randomizer itself
-- (16_rando_spawners.lua section SP.V). This file STANDS DOWN - reads and writes nothing - while the Enemy Randomizer
-- is ON (both would write the same factory variables); with it OFF it runs as before.
--
-- WHAT YOUR DEV 10.24 LOG SHOWED (tests/data/round35_rivet.log, real game, v7 helper, SceneManager found):
--   * The arena's enemies are spawned by SunsetSpawnerFactory nodes (the SpawnerSpawnEvent's SpawnFactory). Each
--     factory node has its own script variables: "Templates" (3990217346 = rivet.hash "Templates"), "Locations"
--     (2501629366), sometimes "InitialCount" (2429945776), and itself (3368780241).
--   * Templates IS the enemy: the 11 arena factories of challenge A1 held 3 Templates values, and every factory
--     always spawned the same kind - Templates 1097446 -> enm_pirate_robot_sh (factories 1097948/49/53/57),
--     1097451 -> enm_pirate_robot_me (1097946/54/56), 1097452 -> enm_pirate_bladeball (1097947/51/52/55). The spawn's
--     SpawnLocation equals the factory's Locations value (1097957: 1097478 both).
--   * v4 never armed because it only swapped SpawnerScriptAction variables (Template / Factories); the factories
--     the Factories variables point at are not the ones the events name, and most factory spawns tie to no node.
-- v6 (dev 10.26, your dev 10.25 log round36): v5 armed a factory that had already spawned its 4 enemies and never
-- spawned again (each arena wave has its own factories). v6 only arms factories that have NOT spawned yet, all the
-- fresh factories of one enemy kind at once (one experiment = one kind -> one other kind), each verified on its own.
-- v5 added the FACTORY TEMPLATES ROUTE: it lists the level's SunsetSpawnerFactory nodes, reads each one's Templates
-- variable, learns from every factory spawn which enemy each Templates value makes, then writes ANOTHER learned
-- enemy Templates value (same role, another kind) into ONE factory's Templates variable (checked, read back), and
-- verifies the next spawn of every factory that uses that variable. Put back on the next level / checkpoint load.
--
-- WHY v3 DID NOTHING (your dev 10.23 log, tests/data/round34_rivet.log, real game): the planet fix worked ("level
-- reset (planet Zurkon): ON ZURKON - active", and the randomizer itself said scarstu), but the game folder still had
-- rando_give.dll v6: "no script variables: rando_give.dll is v6, v7 is needed". v7 was only in
-- rando_give_source/dev_build and had to be copied by hand; that one log line was the only sign. Since dev 10.24 the
-- kit's own rando_give.dll IS v7 (it ran in your game in round32), and v4 says it ON SCREEN, on every Zurkon level,
-- whenever it cannot work ("SPAWNPROOF BLOCKED: ...").
--
-- WHY v2 DID NOTHING AT ALL (your dev 10.22 log, tests/data/round33_rivet.log, real game): it loaded ("v2 loaded")
-- and then wrote not one more line. It only acted where RANDO.state.current_planet == "scarstu". The companion
-- started late, so every event waited in 10_rando_runtime's buffer of 500; the buffer filled on NefCity and the
-- PlanetChangedEvent to Zurkon was DROPPED ("replaying 500 event(s)", then only "RANDO-PLANET NefCity", and every
-- checkpoint on Zurkon logged "on nefarious_city"). v2 believed it was on NefCity and stayed silent, so the
-- Factories experiment never ran. v3:
--   * subscribes to PlanetChangedEvent and SpawnerSpawnEvent ITSELF (rivet.on_event, not buffered by the seed),
--     and decides "on Zurkon" from the event's own planet name (the randomizer's state only as a fallback);
--   * never stays silent: every level change logs where it thinks it is and why, and spawns it ignores are counted
--     and reported ("inactive: ...");
--   * shows ARMED and VERIFY on screen, so what you SEE in the game can be matched with the log.
-- (The kit's buffer was fixed too: planet / level / checkpoint / mission / item events are never dropped.)
--
-- WHY v1 NEVER ARMED (your dev 10.21 log, tests/data/round32_rivet.log, real game):
--   * v1 learned a template only from a node's "Template" variable. The Battleplex nodes that spawn ENEMIES have
--     none: their one variable is "Factories" (838143302 = rivet.hash "Factories", the DDL's SpawnerPrius
--     FactoryGroup), holding a SunsetSpawnerFactory node (handles 1087129..1087143 on Zurkon; the SpawnerSpawnEvent
--     SpawnFactory field names the same kind of actor). Their Spawner component says the same: +0x48 = the factory
--     handle, +0x50 (template) and +0x58 (location) = 0. The 104 nodes that do have a Template variable spawned
--     only rift portals (anomaly_portal_*). So "0 regular-enemy template(s) learned" in every scan.
--   * v1's jobs died on "ran past the 8 ms frame budget" (lines 101/133/272/400) during the fight: a budget error
--     outside a pcall ended the job and lost the spawns it was matching.
--   * v1 logged its first 12 spawns per level (the pub's bots and portals) and nothing of the challenges.
--
-- WHAT v2 DOES (only on Zurkon, only in memory, never saved, at most MAX_SWAPS per session):
--   1. Lists the level's SpawnerScriptAction nodes; reads each node's variable plugs (node +0x58 -> ScriptPlugs) and
--      its Spawner component (handle == node +0x60). A node's SLOT is its Template variable ("template") or, when it
--      has none, its Factories variable ("factory").
--   2. Ties every spawn to its node by the node's LastSpawn variable OR by the Spawner's slot list (+0x9C count,
--      +0xDC entries of 12 bytes { spawned handle, location handle, time }: real bytes of 9 nodes in your log).
--      A spawn with a SpawnFactory and no node is still learned for that factory.
--   3. Learns per slot value what it really spawned (actor name, bot family, role) and logs the first 40
--      enemy / boss spawns of each level in full, with each new factory's own variables (rivet.script_node).
--   4. ARM: a node whose slot holds ONE actor (not a group), whose variable no other node shares, whose value was
--      learned to spawn an enemy (or a boss), gets another learned value of the SAME kind and role that spawned
--      another actor. Written: the variable (uid +0x00, actors
--      +0x10; generation, type and value checked right before, read back after) and, if it holds the old value,
--      the Spawner's cached copy (+0x48 factory, +0x50 template). Only nodes not seen spawning on this level.
--   5. VERIFY on that node's next spawn: REPLACEMENT SPAWNED / ORIGINAL SPAWNED / SOMETHING ELSE.
--   6. PUT BACK when the node's Spawner stops, or on a level change (only what still holds what was written).
--   Every unit of work is guarded: a frame-budget error yields and retries on the next frame instead of ending it.
-- Every line starts with "RANDO-SPAWNPROOF". Remove this file and nothing of it runs.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["dev(spawnproof)"] = "10.0.27"   -- the kit check (10_rando_runtime.lua)
if RANDO_DEV_DEBUG and RANDO_DEV_DEBUG.ran and RANDO_DEV_DEBUG.ran["spawnproof"] then return end   -- v0.62-DEV5: dev(debug).lua already holds it
RANDO_SPAWNPROOF = RANDO_SPAWNPROOF or {}
local P = RANDO_SPAWNPROOF
P.version = 6
P.frame = P.frame or 0
P.ENABLED = true
P.PLANET = "scarstu"            -- Zurkon (Zurkie's Battleplex): replayable fights, nothing of the story
P.SCAN_EVERY = 120              -- frames between two listings of the level's nodes
P.NODE_LIMIT = 512
P.MAX_SWAPS = 4                 -- per session
P.MAX_ACTIVE = 2                -- armed at the same time
P.HELPER_MIN = 7                -- rando_give.dll v7 publishes the SceneManager
P.MB_SCENE = 0x128
P.SCENE_VARS = 0x75A0
P.VAR_SIZE = 0x40
P.VAR_TYPE_ACTORS = 5
P.GROUP_BIT = 0x80000000
P.SLICE = 0.0015
P.LEARN_LOG = 40                -- enemy / boss spawns logged in full per level
P.OTHER_LOG = 6                 -- other spawns (portals, props, NPCs) logged per level
P.FACTORY_LOG = 12              -- factories described per level
P.ROLES = { enemy = true, boss = true }
-- the Spawner component (432 bytes), measured on 9 nodes of your dev 10.21 log
P.SP_READ_AT, P.SP_READ_LEN = 0x40, 0x160
P.SP_FACTORY, P.SP_TEMPLATE, P.SP_LOCATION = 0x48, 0x50, 0x58
P.SP_COUNT, P.SP_SLOTS, P.SP_STRIDE, P.SP_SLOT_MAX = 0x9C, 0xDC, 12, 15

local function log(...) pcall(rivet.log, "[rando]", "RANDO-SPAWNPROOF", ...) end
local function say(text) if RANDO and RANDO.say then pcall(RANDO.say, text, { type = "center", duration = 6 }) end end
P.log = log
local function clock() return (os and os.clock and os.clock()) or 0 end

-- ---- the engine's string hash (rivet_hook script_signal.cpp: reflected CRC-32, start 0xEDB88320) ----
local CRC = {}
for i = 0, 255 do
  local c = i
  for _ = 1, 8 do if c & 1 == 1 then c = (c >> 1) ~ 0xEDB88320 else c = c >> 1 end end
  CRC[i] = c
end
function P.hash(text)
  local c = 0xEDB88320
  for k = 1, #text do c = (c >> 8) ~ CRC[(text:byte(k) ~ c) & 0xFF] end
  return c
end
P.PLUG_TEMPLATE = P.hash("Template")      -- 1835115251
P.PLUG_LASTSPAWN = P.hash("LastSpawn")    -- 406637480
P.PLUG_LOCATION = P.hash("Location")      -- 2761897147
P.PLUG_FACTORIES = P.hash("Factories")    -- 838143302 (your dev 10.21 log: the arena's enemy nodes)
P.PLUG_TEMPLATES = P.hash("Templates")    -- 3990217346 (your dev 10.24 log: a SunsetSpawnerFactory's enemy)
P.PLUG_LOCATIONS = P.hash("Locations")    -- 2501629366
P.FACTORY_CLASS = "SunsetSpawnerFactoryScriptAction"
P.AFTER_LOG = 6                 -- spawns of an armed factory logged after its VERIFY
P.PLUG_NAMES = {}
for _, n in ipairs({ "Template", "LastSpawn", "Location", "Factories", "MaxAlive", "NumSpawns", "OnSpawned", "OnAllSpawned",
                    "Templates", "Locations", "InitialCount" }) do
  P.PLUG_NAMES[P.hash(n)] = n
end
local function plug_name(h) return P.PLUG_NAMES[h] or tostring(h) end

-- ---- bytes ---------------------------------------------------------------------------------------
local function bytes_of(text)
  local t = {}
  for x in tostring(text or ""):gmatch("%x%x") do t[#t + 1] = tonumber(x, 16) end
  return t
end
local function u16(b, i) if not b[i + 1] then return nil end return b[i] + b[i + 1] * 0x100 end
local function u32(b, i)
  if not b[i + 3] then return nil end
  return b[i] + b[i + 1] * 0x100 + b[i + 2] * 0x10000 + b[i + 3] * 0x1000000
end
local function hex64(b, i)
  if not b[i + 7] then return nil end
  return string.format("%02X%02X%02X%02X%02X%02X%02X%02X", b[i + 7], b[i + 6], b[i + 5], b[i + 4], b[i + 3], b[i + 2], b[i + 1], b[i])
end
local function ptr64(b, i)
  local h = hex64(b, i)
  if not h or h:sub(1, 1):match("[89A-F]") then return nil end
  return tonumber(h, 16)
end
local function valid_ptr(p) return p ~= nil and p > 0x10000 and p < 0x7FFFFFFFFFFF and p % 8 == 0 end
local function le(hex16) local t = {} for k = 15, 1, -2 do t[#t + 1] = hex16:sub(k, k + 1) end return table.concat(t, " ") end
local function le32(v) return string.format("%02X %02X %02X %02X", v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF) end
P.bytes_of, P.u32, P.hex64, P.le = bytes_of, u32, hex64, le

local function read(addr, len)
  if not (addr and addr > 0x10000) then return nil end
  local ok, text = pcall(rivet.read, string.format("%X", addr), len)
  if not ok or not text then return nil end
  local b = bytes_of(text)
  if #b < len then return nil end
  return b
end
P.read = read

-- one unit of work: a frame-budget error yields (the job goes on next frame) and retries, up to 3 times
local function guard(fn, ...)
  for _ = 1, 3 do
    local res = table.pack(pcall(fn, ...))
    if res[1] then return table.unpack(res, 2, res.n) end
    local err = tostring(res[2])
    if not err:find("frame budget", 1, true) then error(err, 0) end
    P.budget_hits = (P.budget_hits or 0) + 1
    if coroutine.isyieldable() then coroutine.yield() else return nil end
  end
  return nil
end
P.guard = guard
local function pace(t0)
  if clock() - t0 > P.SLICE and coroutine.isyieldable() then coroutine.yield(); return clock() end
  return t0
end

-- ---- the SceneManager and its script variables ------------------------------------------------------
function P.scene()
  local rr = RANDO_REAL
  local n = rr and rr.native
  if not (n and n.addr) then return nil, "rando_give.dll is not answering" end
  local hb = read(n.addr, 0x10)
  local ver = hb and u32(hb, 9)
  if not ver or ver < P.HELPER_MIN then return nil, "rando_give.dll is v" .. tostring(ver) .. ", v" .. P.HELPER_MIN .. " is needed (copy the kit's)" end
  local mb = read(n.addr + P.MB_SCENE, 0x0C)
  local scene, sigs = mb and ptr64(mb, 1), mb and u32(mb, 9)
  if not valid_ptr(scene) then return nil, "rando_give.dll found no SceneManager (signature matched " .. tostring(sigs) .. "x, exactly 1 needed)" end
  local sb = read(scene + P.SCENE_VARS, 0x20)
  local base, max = sb and ptr64(sb, 1), sb and u32(sb, 0x1D)
  if not (valid_ptr(base) and max and max > 0 and max < 0x100000) then
    return nil, string.format("SceneManager %X: no script variable array (%s, max %s)", scene, tostring(base), tostring(max))
  end
  return { scene = scene, base = base, max = max, sigs = sigs }
end

-- one variable: nil and why, or { addr, uid, actors, type, gen, single } (checked against the plug's generation)
function P.var(sc, idx, gen)
  if not (sc and idx and gen) or gen == 0 or idx >= sc.max then return nil, "no such variable" end
  local addr = sc.base + idx * P.VAR_SIZE
  local b = read(addr, P.VAR_SIZE)
  if not b then return nil, "unreadable" end
  local v = { addr = addr, uid = hex64(b, 1), actors = u32(b, 0x11), type = u16(b, 0x35), gen = u16(b, 0x37) }
  if v.gen ~= gen then return nil, string.format("generation %s, the plug says %s", tostring(v.gen), tostring(gen)) end
  v.single = v.type == P.VAR_TYPE_ACTORS and v.actors ~= 0 and (v.actors & P.GROUP_BIT) == 0
  return v
end

-- a node's variable plugs: { spawner (+0x60), uid, vars = { [plug] = { idx, gen } }, order = { plug... } }
function P.plugs_of(addr)
  local nb = read(addr, 0x80)
  if not nb then return nil, "node unreadable" end
  local plugs = ptr64(nb, 0x59)
  if not valid_ptr(plugs) then return nil, "no plug block" end
  local hb = read(plugs, 0x28)
  if not hb then return nil, "plug block unreadable" end
  local var_ptr, n = ptr64(hb, 9), hb[0x1B]
  local out = { spawner = u32(nb, 0x61), uid = hex64(nb, 0x49), vars = {}, order = {}, nvars = n or 0 }
  if not n or n == 0 then return out end
  if not (var_ptr and var_ptr > 0x10000) or n > 32 then return nil, "variable plugs unreadable" end
  local vb = read(var_ptr, n * 8)
  if not vb then return nil, "variable plugs unreadable" end
  for k = 0, n - 1 do
    local plug = u32(vb, k * 8 + 1)
    out.vars[plug] = { idx = u16(vb, k * 8 + 5), gen = u16(vb, k * 8 + 7) }
    out.order[#out.order + 1] = plug
  end
  return out
end

-- the Spawner component's cached factory / template / location and its spawn slots
function P.spawner_state(saddr)
  local b = saddr and read(saddr + P.SP_READ_AT, P.SP_READ_LEN)
  if not b then return nil end
  local at = function(off) return u32(b, off - P.SP_READ_AT + 1) end
  local st = { factory = at(P.SP_FACTORY), template = at(P.SP_TEMPLATE), location = at(P.SP_LOCATION), count = at(P.SP_COUNT), slots = {} }
  local n = math.min(st.count or 0, P.SP_SLOT_MAX)
  for i = 0, n - 1 do
    local h = at(P.SP_SLOTS + i * P.SP_STRIDE)
    if h and h ~= 0 then st.slots[#st.slots + 1] = { spawned = h, location = at(P.SP_SLOTS + i * P.SP_STRIDE + 4) } end
  end
  return st
end

-- ---- actors --------------------------------------------------------------------------------------
function P.actor(h)
  if not h or h == 0 then return nil end
  local a = { handle = h }
  if rivet.name then local ok, n = pcall(rivet.name, h); if ok then a.name = n end end
  local oku, uid = pcall(rivet.uid, h); a.uid = oku and uid or nil
  local SPL = RANDO_SPAWNERS
  if SPL and SPL.classify_actor then
    local okc, fam, cls = pcall(SPL.classify_actor, h, true)
    if okc and fam then a.family, a.class, a.role = fam, cls, SPL.ROLE_OF_FAMILY and SPL.ROLE_OF_FAMILY[fam] end
  end
  return a
end
local function who(a)
  if not a then return "none" end
  return string.format("%s (handle %s, %s/%s)", tostring(a.name), tostring(a.handle), tostring(a.family), tostring(a.class))
end
P.who = who
local function short(name)
  local n = tostring(name):match("([^\\]+)$") or tostring(name)
  return (n:gsub("%.actor$", ""):gsub("%.a$", ""))
end
P.short = short
local function norm_uid(u)
  if type(u) ~= "string" or not u:match("^%x+$") or #u > 16 then return nil end
  return string.rep("0", 16 - #u) .. u:upper()
end

-- a factory actor, said once per level: its classes and its own node's variables (rivet.script_node)
function P.describe_factory(lvl, fac)
  if not fac or fac == 0 or lvl.described[fac] then return end
  lvl.described[fac] = true
  if lvl.ndescribed >= P.FACTORY_LOG then return end
  lvl.ndescribed = lvl.ndescribed + 1
  local okl, names = pcall(rivet.components, fac)
  local classes = (okl and type(names) == "table") and table.concat(names, ",", 1, math.min(#names, 6)) or "?"
  local vars = {}
  for _, cls in ipairs({ "SunsetSpawnerFactoryScriptAction", "SpawnerFactoryScriptAction" }) do
    local okc, c = pcall(rivet.component, fac, cls)
    if okc and type(c) == "table" and c.handle and rivet.script_node then
      local okn, t = pcall(rivet.script_node, c.handle, false)
      if okn and type(t) == "table" then
        for _, v in ipairs(type(t.vars) == "table" and t.vars or {}) do
          local val = v.value
          if type(val) == "table" then
            local hs = {}
            for i = 1, math.min(4, #val) do hs[i] = tostring(val[i]) end
            val = string.format("{%s}%s", table.concat(hs, ","), val.group and " group" or "")
          end
          vars[#vars + 1] = tostring(v.plug_name or plug_name(v.plug or 0)) .. ":" .. tostring(v.type) .. "=" .. tostring(val)
          if #vars >= 8 then break end
        end
        vars[#vars + 1] = "outputs " .. tostring(#(t.outputs or {}))
      end
      break
    end
  end
  log(string.format("factory %s: classes %s; node variables %s", tostring(fac), classes, #vars > 0 and table.concat(vars, ", ") or "-"))
end

-- ---- the level --------------------------------------------------------------------------------------
-- where you are: the last PlanetChangedEvent this file saw itself (not buffered), else the randomizer's state
P.ZURKON_EVENT_NAME = "Zurkon"
local function state_planet()
  local s = RANDO and RANDO.state
  return s and s.current_planet
end
local function planet()
  if P.event_planet then return P.event_planet == P.ZURKON_EVENT_NAME and P.PLANET or ("event:" .. P.event_planet) end
  return state_planet()
end
P.planet = planet
function P.where()
  return string.format("event planet %s, randomizer state %s", tostring(P.event_planet), tostring(state_planet()))
end

P.swaps = P.swaps or 0
P.armed = P.armed or {}
P.spawn_queue = {}

function P.reset(why)
  for _, A in ipairs(P.armed) do
    if not A.restored then
      P.put_back(A, "level changed: " .. tostring(why))
      if not A.verified then P.swaps = math.max(0, P.swaps - 1) end
    end
  end
  if P.lvl and P.lvl.scans > 0 then P.summary() end
  P.armed = {}
  P.lvl = { nodes = {}, order = {}, scans = 0, learned = { template = {}, factory = {}, ftemplate = {} }, logged = 0, other = 0,
            factories = {}, forder = {}, fvar_users = {},
            described = {}, ndescribed = 0, stopped = {}, why = why, untied = 0, ties = 0, ignored = 0 }
  log(string.format("level reset (%s): %s (%s)", tostring(why), planet() == P.PLANET and "ON ZURKON - active" or "not Zurkon - inactive", P.where()))
  P.spawn_queue = {}
  P.next_scan = P.frame + P.SCAN_EVERY
end


-- one new node: plugs, Spawner, slot
function P.read_node(node)
  local okc, c = pcall(rivet.component, node.actor, "SpawnerScriptAction")
  local addr = okc and type(c) == "table" and c.handle == node.component and c.address and tonumber(c.address, 16)
  local pl = addr and P.plugs_of(addr)
  local rec = { component = node.component, actor = node.actor, uid = node.uid, addr = addr, plugs = pl }
  if pl then
    rec.spawner, rec.last = pl.spawner, pl.vars[P.PLUG_LASTSPAWN]
    if pl.vars[P.PLUG_TEMPLATE] then
      rec.slot = { kind = "template", var = pl.vars[P.PLUG_TEMPLATE], plug = P.PLUG_TEMPLATE, cache = P.SP_TEMPLATE }
    elseif pl.vars[P.PLUG_FACTORIES] then
      rec.slot = { kind = "factory", var = pl.vars[P.PLUG_FACTORIES], plug = P.PLUG_FACTORIES, cache = P.SP_FACTORY }
    end
    local oks, s = pcall(rivet.component, node.actor, "Spawner")
    if oks and type(s) == "table" and s.handle == pl.spawner and s.address then rec.saddr = tonumber(s.address, 16) end
  end
  return rec
end

function P.scan()
  local lvl = P.lvl
  if not lvl then return end
  local sc, why = P.scene()
  if not sc then
    if not lvl.blocked_said then
      lvl.blocked_said = true
      log("BLOCKED: no script variables:", why)
      say("SPAWNPROOF BLOCKED: " .. tostring(why))
    end
    return
  end
  if not P.scene_logged then
    P.scene_logged = true
    log(string.format("SceneManager %X (signature matched %s x), script variables at %X, max %d", sc.scene, tostring(sc.sigs), sc.base, sc.max))
  end
  local list = guard(function()
    local ok, l = pcall(rivet.script_nodes, "SpawnerScriptAction", P.NODE_LIMIT)
    if ok and type(l) == "table" then return l end
    if not ok then error(l, 0) end
  end)
  if type(list) ~= "table" then return end
  lvl.scans = lvl.scans + 1
  local new, t0 = 0, clock()
  for _, node in ipairs(list) do
    if node.component and not lvl.nodes[node.component] then
      local rec = guard(P.read_node, node)
      if rec then
        lvl.nodes[node.component] = rec
        lvl.order[#lvl.order + 1] = node.component
        new = new + 1
      end
      t0 = pace(t0)
    end
  end
  if new > 0 then
    local users, kinds = {}, { template = 0, factory = 0, none = 0 }
    for _, k in ipairs(lvl.order) do
      local r = lvl.nodes[k]
      if r.slot then users[r.slot.var.idx] = (users[r.slot.var.idx] or 0) + 1 end
    end
    local single, groups, shared, last, sp = 0, 0, 0, 0, 0
    for _, k in ipairs(lvl.order) do
      local r = lvl.nodes[k]
      kinds[r.slot and r.slot.kind or "none"] = kinds[r.slot and r.slot.kind or "none"] + 1
      if r.last then last = last + 1 end
      if r.saddr then sp = sp + 1 end
      if r.slot then
        r.shared = users[r.slot.var.idx] > 1
        if r.shared then shared = shared + 1 end
        local v = guard(P.var, sc, r.slot.var.idx, r.slot.var.gen)
        if v and v.single then single = single + 1 elseif v and v.actors ~= 0 then groups = groups + 1 end
      end
      t0 = pace(t0)
    end
    log(string.format("scan %d on %s: %d node(s) (%d new): %d Template, %d Factories, %d neither; slots holding one actor %d, groups %d, shared %d; %d with LastSpawn, %d Spawner(s) read",
        lvl.scans, tostring(planet()), #lvl.order, new, kinds.template, kinds.factory, kinds.none, single, groups, shared, last, sp))
  end
  P.scan_factories(sc)
end

-- v5: every SunsetSpawnerFactory node of the level and its Templates variable (also the ones not spawned yet)
function P.scan_factories(sc)
  local lvl = P.lvl
  local list = guard(function()
    local ok, l = pcall(rivet.script_nodes, P.FACTORY_CLASS, P.NODE_LIMIT)
    if ok and type(l) == "table" then return l end
    if not ok then error(l, 0) end
  end)
  if type(list) ~= "table" then return end
  local before, t0 = #lvl.forder, clock()
  for _, node in ipairs(list) do
    if node.actor and lvl.factories[node.actor] == nil then guard(P.factory_rec, lvl, node.actor) end
    t0 = pace(t0)
  end
  if #lvl.forder > before then
    local values, nvals = {}, 0
    for _, fac in ipairs(lvl.forder) do
      local fr = lvl.factories[fac]
      local v = fr and guard(P.var, sc, fr.slot.var.idx, fr.slot.var.gen)
      if v and v.single then
        if not values[v.actors] then nvals = nvals + 1; values[v.actors] = 0 end
        values[v.actors] = values[v.actors] + 1
      end
    end
    local parts = {}
    for val, n in pairs(values) do parts[#parts + 1] = string.format("%d x%d", val, n) end
    table.sort(parts)
    log(string.format("factories on %s: %d with a Templates variable (%d new); %d Templates value(s): %s", tostring(planet()), #lvl.forder,
        #lvl.forder - before, nvals, table.concat(parts, ", ", 1, math.min(#parts, 12))))
  end
end

-- the node that made each spawn: its LastSpawn variable (one 64-byte read a node) first; the Spawner's slot list
-- (one read of its component) only for spawns still not found
function P.tie(sc, wanted)
  local lvl, found, t0 = P.lvl, {}, clock()
  local left = 0
  for _ in pairs(wanted) do left = left + 1 end
  for pass = 1, 2 do
    for _, k in ipairs(lvl.order) do
      if left == 0 then return found end
      local r = lvl.nodes[k]
      guard(function()
        if pass == 1 and r.last then
          local lv = P.var(sc, r.last.idx, r.last.gen)
          if lv and lv.actors and wanted[lv.actors] and not found[lv.actors] then found[lv.actors] = { rec = r, via = "LastSpawn" }; left = left - 1 end
        elseif pass == 2 and r.saddr then
          local st = P.spawner_state(r.saddr)
          r.state = st
          for _, s in ipairs(st and st.slots or {}) do
            if wanted[s.spawned] and not found[s.spawned] then found[s.spawned] = { rec = r, via = "Spawner slot" }; left = left - 1 end
          end
        end
      end)
      t0 = pace(t0)
    end
  end
  return found
end

-- what a value made: never overwritten with nil (an actor already gone answers nil); two kinds = MIXED
local function note(x, a)
  if a.name then
    if x.name and x.name ~= a.name then x.mixed = true end
    x.name = a.name
  end
  if a.role then x.role, x.family, x.class = a.role, a.family, a.class end
  x.count = (x.count or 0) + 1
end
P.note = note

-- one SunsetSpawnerFactory node (the actor the SpawnerSpawnEvent's SpawnFactory names): its Templates variable
function P.factory_rec(lvl, fac)
  if not fac or fac == 0 then return nil end
  local fr = lvl.factories[fac]
  if fr ~= nil then return fr or nil end
  local okc, c = pcall(rivet.component, fac, P.FACTORY_CLASS)
  local addr = okc and type(c) == "table" and c.address and tonumber(c.address, 16)
  local pl = addr and P.plugs_of(addr)
  local tv = pl and pl.vars[P.PLUG_TEMPLATES]
  if not tv then lvl.factories[fac] = false; return nil end
  fr = { uid = "factory " .. tostring(fac), fac = fac, addr = addr, plugs = pl, component = c.handle,
         slot = { kind = "ftemplate", var = tv, plug = P.PLUG_TEMPLATES, cache = 0 } }
  lvl.factories[fac] = fr
  lvl.forder[#lvl.forder + 1] = fac
  lvl.fvar_users[tv.idx] = (lvl.fvar_users[tv.idx] or 0) + 1
  return fr
end

-- the armed record whose variable this factory uses (factories can share one Templates variable)
function P.armed_of_factory(fr)
  for _, A in ipairs(P.armed) do
    if not A.restored and A.slot.kind == "ftemplate" and A.slot.var.idx == fr.slot.var.idx then return A end
  end
  return nil
end

function P.learn(batch)
  local lvl = P.lvl
  local sc = P.scene()
  if not (lvl and sc) then return end
  local wanted = {}
  for _, e in ipairs(batch) do wanted[e.h] = e end
  local found = P.tie(sc, wanted)
  local t0 = clock()
  for _, e in ipairs(batch) do
    guard(function()
      local a = P.actor(e.h)
      local t = found[e.h]
      local r = t and t.rec
      local interesting = a and P.ROLES[a.role or ""]
      local kind, value, v
      if r and r.slot then
        v = P.var(sc, r.slot.var.idx, r.slot.var.gen)
        kind = r.slot.kind
        if kind == "factory" and e.fac and e.fac ~= 0 then value = e.fac          -- the factory the game used
        elseif v and v.single then value = v.actors
        elseif r.state then value = r.state[kind] end                             -- the Spawner's cached copy
      elseif e.fac and e.fac ~= 0 then
        kind, value = "factory", e.fac
      end
      if r then lvl.ties = lvl.ties + 1; r.spawned = (r.spawned or 0) + 1 else lvl.untied = lvl.untied + 1 end
      local mine = r and P.armed_of(r)
      if kind and value and value ~= 0 and a and a.name and not mine then
        local L = lvl.learned[kind]
        local x = L[value] or { handle = value, kind = kind, count = 0 }
        if v and v.single and v.actors == value then x.uid = v.uid end
        if not x.uid and kind == "factory" then local oku, u = pcall(rivet.uid, value); x.uid = oku and norm_uid(u) or nil end
        note(x, a)
        L[value] = x
      end
      if kind == "factory" then P.describe_factory(lvl, value) end
      -- v5: the factory's own Templates variable
      local fnote, fA = "", nil
      local fr = e.fac and e.fac ~= 0 and P.factory_rec(lvl, e.fac)
      if fr then
        fr.spawned = (fr.spawned or 0) + 1
        local fv = P.var(sc, fr.slot.var.idx, fr.slot.var.gen)
        fA = P.armed_of_factory(fr)
        if fv and fv.single then
          fnote = string.format("; factory Templates = %d", fv.actors)
          if a and not fA then
            local x = lvl.learned.ftemplate[fv.actors] or { handle = fv.actors, kind = "ftemplate", count = 0 }
            x.uid = fv.uid
            note(x, a)
            lvl.learned.ftemplate[fv.actors] = x
          end
        elseif fv then
          fnote = string.format("; factory Templates variable %08X (not one actor)", fv.actors or 0)
        end
      end
      local say = (interesting and lvl.logged < P.LEARN_LOG) or (not interesting and lvl.other < P.OTHER_LOG)
      if mine then say = true end
      if fA then
        fA.after = (fA.after or 0) + 1
        say = say or fA.after <= P.AFTER_LOG
      end
      if say then
        if interesting then lvl.logged = lvl.logged + 1 else lvl.other = lvl.other + 1 end
        log(string.format("spawn %s (SpawnFactory %s, location %s): %s; slot %s = %s%s%s; spawned %s%s",
            tostring(e.h), tostring(e.fac), tostring(e.loc),
            r and string.format("node %s via %s", tostring(r.uid), t.via) or "no node",
            kind or "none", tostring(value), v and (v.single and "" or string.format(" (variable %08X)", v.actors or 0)) or "",
            fnote, who(a), fA and string.format(" [ARMED factory variable, spawn %d since]", fA.after) or ""))
      end
      if mine and not mine.verified then P.verify(mine, a, e) end
      if fA and not fA.verified then P.verify(fA, a, e) end
    end)
    t0 = pace(t0)
  end
end

function P.armed_of(r)
  for _, A in ipairs(P.armed) do if A.rec == r and not A.restored then return A end end
  return nil
end

-- ---- arm, verify, put back ------------------------------------------------------------------------------
function P.try_arm()
  local lvl = P.lvl
  if not (P.ENABLED and lvl) or P.swaps >= P.MAX_SWAPS or planet() ~= P.PLANET then return end
  local active = 0
  for _, A in ipairs(P.armed) do if not A.restored then active = active + 1 end end
  if active >= P.MAX_ACTIVE then return end
  local sc = P.scene()
  if not sc then return end
  local pool = { template = {}, factory = {}, ftemplate = {} }
  local counts = {}
  for kind, L in pairs(lvl.learned) do
    for _, x in pairs(L) do
      if P.ROLES[x.role or ""] and not x.mixed then
        pool[kind][#pool[kind] + 1] = x
        counts[#counts + 1] = kind .. " " .. tostring(x.handle) .. "=" .. tostring(x.name):match("([^\\]+)$")
      end
    end
    table.sort(pool[kind], function(a, b) return a.handle < b.handle end)
  end
  local why = string.format("%d template(s), %d factory(ies), %d factory Templates value(s) learned spawning an enemy or boss on this level%s",
      #pool.template, #pool.factory, #pool.ftemplate, #counts > 0 and (" (" .. table.concat(counts, ", ", 1, math.min(#counts, 8)) .. ")") or "")
  if why ~= lvl.waiting_said then lvl.waiting_said = why; log("learned: " .. why) end
  -- v5: the factory Templates route first (the one your dev 10.24 log points at)
  if P.try_arm_factory(sc, pool.ftemplate) then return end
  if #pool.template < 2 and #pool.factory < 2 then return end
  local best
  local t0 = clock()
  for _, k in ipairs(lvl.order) do
    local r = lvl.nodes[k]
    if r.slot and not r.shared and (r.spawned or 0) == 0 and not lvl.stopped[r.spawner or -1] and not P.armed_of(r) and not r.tried
        and #pool[r.slot.kind] >= 2 then
      local v = guard(P.var, sc, r.slot.var.idx, r.slot.var.gen)
      local orig = v and v.single and lvl.learned[r.slot.kind][v.actors]
      if orig and P.ROLES[orig.role or ""] and not orig.mixed then
        for _, rep in ipairs(pool[r.slot.kind]) do
          if rep.handle ~= v.actors and rep.name ~= orig.name and rep.role == orig.role and (rep.uid or v.uid == "0000000000000000") then
            best = { r = r, v = v, orig = orig, rep = rep }
            break
          end
        end
      end
    end
    if best then break end
    t0 = pace(t0)
  end
  if best then P.arm(sc, best.r, best.v, best.orig, best.rep) end
end

-- dev 10.26 (your dev 10.25 log, round36): v5 armed factory 1109878 AFTER its 4 spawns, and it never spawned again:
-- in the arena every wave has its own factories, each spawning once per wave. So a spent factory is never chosen now.
-- One EXPERIMENT = one enemy kind -> one other kind: every factory NOT YET SPAWNED on this level whose Templates holds
-- the original (up to P.EXP_FACTORIES) gets the replacement's value; each verifies on its own first spawn.
P.EXP_FACTORIES = 8
P.MAX_EXPERIMENTS = 3
function P.try_arm_factory(sc, pool)
  local lvl = P.lvl
  for _, A in ipairs(P.armed) do
    if not A.restored and A.slot.kind == "ftemplate" then return true end     -- one experiment at a time
  end
  if (P.experiments or 0) >= P.MAX_EXPERIMENTS or #pool < 2 then return false end
  -- the original kind with the most fresh factories, and a replacement of the same role and another kind
  local fresh_by_value = {}
  for _, fac in ipairs(lvl.forder) do
    local fr = lvl.factories[fac]
    if fr and not fr.tried and (fr.spawned or 0) == 0 then
      local v = guard(P.var, sc, fr.slot.var.idx, fr.slot.var.gen)
      if v and v.single then
        local list = fresh_by_value[v.actors] or {}
        list[#list + 1] = { fr = fr, v = v }
        fresh_by_value[v.actors] = list
      end
    end
  end
  local best
  for value, list in pairs(fresh_by_value) do
    local orig = lvl.learned.ftemplate[value]
    if orig and P.ROLES[orig.role or ""] and not orig.mixed then
      for _, x in ipairs(pool) do
        if x.handle ~= value and x.name ~= orig.name and x.role == orig.role and (x.uid or list[1].v.uid == "0000000000000000") then
          if not best or #list > #best.list then best = { orig = orig, rep = x, list = list } end
          break
        end
      end
    end
  end
  if not best then
    local why = "no factory that has not spawned yet holds a learned enemy"
    if why ~= lvl.fwait_said then lvl.fwait_said = why; log("factory route waiting: " .. why) end
    return false
  end
  P.experiments = (P.experiments or 0) + 1
  local n = math.min(#best.list, P.EXP_FACTORIES)
  local facs = {}
  for i = 1, n do facs[i] = tostring(best.list[i].fr.fac) end
  log(string.format("EXPERIMENT %d: %s -> %s on %d factory(ies) that have not spawned yet: %s", P.experiments,
      tostring(best.orig.name), tostring(best.rep.name), n, table.concat(facs, ", ")))
  P.quiet_arm = 0
  for i = 1, n do P.arm(sc, best.list[i].fr, best.list[i].v, best.orig, best.rep) end
  return true
end

function P.arm(sc, r, v, orig, rep)
  r.tried = true
  local slot = r.slot
  local now = P.var(sc, slot.var.idx, slot.var.gen)
  if not (now and now.actors == v.actors and now.uid == v.uid) then log("not armed: the variable changed while it was checked"); return end
  local new_uid = (now.uid == "0000000000000000") and now.uid or rep.uid
  local okw1 = pcall(rivet.write, string.format("%X", now.addr), le(new_uid))
  local okw2 = pcall(rivet.write, string.format("%X", now.addr + 0x10), le32(rep.handle))
  local back = P.var(sc, slot.var.idx, slot.var.gen)
  local cache = "no Spawner"
  local cache_written = false
  if r.saddr then
    local cb = read(r.saddr + slot.cache, 4)
    local cur = cb and u32(cb, 1)
    if cur == v.actors then
      pcall(rivet.write, string.format("%X", r.saddr + slot.cache), le32(rep.handle))
      local cb2 = read(r.saddr + slot.cache, 4)
      cache_written = cb2 and u32(cb2, 1) == rep.handle
      cache = string.format("Spawner +0x%X %s -> %s %s", slot.cache, tostring(cur), tostring(rep.handle), cache_written and "OK" or "FAILED")
    else
      cache = string.format("Spawner +0x%X holds %s (not activated yet): left alone", slot.cache, tostring(cur))
    end
  end
  if slot.kind ~= "ftemplate" then P.swaps = P.swaps + 1 end
  local function copy(t) local c = {} for k, x in pairs(t) do c[k] = x end return c end
  local A = { rec = r, slot = slot, orig = copy(orig), rep = copy(rep), orig_uid = v.uid, orig_handle = v.actors, new_uid = new_uid,
              cache_written = cache_written, frame = P.frame, spawned_before = r.spawned or 0 }
  P.armed[#P.armed + 1] = A
  local ok = okw1 and okw2 and back and back.uid == new_uid and back.actors == rep.handle
  log(string.format("ARMED %d/%d node %s (Spawner %X, %s, spawned %d time(s) so far): %s variable %d at %X: %s -> %s; read back %s; %s",
      P.swaps, P.MAX_SWAPS, tostring(r.uid), r.spawner or 0, slot.kind, A.spawned_before, plug_name(slot.plug), slot.var.idx, now.addr,
      who(orig), who(rep), ok and "OK" or "FAILED", cache))
  if ok and (slot.kind ~= "ftemplate" or (P.quiet_arm or 0) == 0) then
    P.quiet_arm = (P.quiet_arm or 0) + 1
    say(string.format("SPAWNPROOF ARMED: %s should now come as %s", short(orig.name), short(rep.name)))
  end
  if not ok then A.verified = true; P.put_back(A, "the write did not read back") end
end

function P.verify(A, a, e)
  A.verified = true
  local verdict
  if a and a.name == A.rep.name then verdict = "REPLACEMENT SPAWNED"
  elseif a and a.name == A.orig.name then verdict = "ORIGINAL SPAWNED (the write had no effect on this spawn)"
  else verdict = "SOMETHING ELSE SPAWNED" end
  log(string.format("VERIFY node %s (%s, SpawnFactory %s): requested %s; original %s; spawned %s: %s", tostring(A.rec.uid), A.slot.kind,
      tostring(e and e.fac), who(A.rep), who(A.orig), who(a), verdict))
  A.verdict = verdict
  P.said_verdicts = (P.said_verdicts or 0) + 1
  if P.said_verdicts <= 3 then
    say("SPAWNPROOF: " .. verdict:match("^[A-Z ]+"):gsub("%s+$", "") .. " (" .. (a and a.name and short(a.name) or "?") .. ")")
  end
  P.verdicts = P.verdicts or {}
  P.verdicts[#P.verdicts + 1] = verdict
  -- a factory that ignored the write is put back at once, so another (fresh) factory can be tried in this fight
  if A.slot.kind == "ftemplate" and not verdict:find("REPLACEMENT", 1, true) then P.put_back(A, "not replaced") end
end

function P.put_back(A, why)
  if not A or A.restored then return end
  A.restored = true
  local sc = P.scene()
  local v = sc and P.var(sc, A.slot.var.idx, A.slot.var.gen)
  local parts = {}
  if v and v.uid == A.new_uid and v.actors == A.rep.handle then
    pcall(rivet.write, string.format("%X", v.addr), le(A.orig_uid))
    pcall(rivet.write, string.format("%X", v.addr + 0x10), le32(A.orig_handle))
    local back = P.var(sc, A.slot.var.idx, A.slot.var.gen)
    parts[#parts + 1] = "variable " .. ((back and back.actors == A.orig_handle and back.uid == A.orig_uid) and "OK" or "FAILED")
  else
    parts[#parts + 1] = "variable skipped (it no longer holds what was written)"
  end
  if A.cache_written and A.rec.saddr then
    local cb = read(A.rec.saddr + A.slot.cache, 4)
    if cb and u32(cb, 1) == A.rep.handle then
      pcall(rivet.write, string.format("%X", A.rec.saddr + A.slot.cache), le32(A.orig_handle))
      parts[#parts + 1] = "Spawner copy put back"
    else
      parts[#parts + 1] = "Spawner copy changed by the game: left alone"
    end
  end
  log(string.format("put back (%s): node %s %s = %s: %s", tostring(why), tostring(A.rec.uid), A.slot.kind, tostring(A.orig_handle), table.concat(parts, "; ")))
  if A.slot.kind == "ftemplate" and P.said_putback ~= P.experiments then
    P.said_putback = P.experiments
    say("SPAWNPROOF: put back (" .. tostring(why) .. ")")
  end
end

function P.summary()
  local lvl = P.lvl
  local L = {}
  for kind, t in pairs(lvl.learned) do
    for _, x in pairs(t) do
      L[#L + 1] = string.format("%s %s x%d %s/%s %s%s", kind, tostring(x.handle), x.count, tostring(x.family), tostring(x.role),
          tostring(x.name):match("([^\\]+)$") or "?", x.mixed and " (MIXED)" or "")
      if #L >= 16 then break end
    end
  end
  log(string.format("level summary (%s): %d node(s), %d spawn(s) tied, %d not tied, %d budget retries; learned: %s; verdicts: %s",
      tostring(lvl.why), #lvl.order, lvl.ties, lvl.untied, P.budget_hits or 0, #L > 0 and table.concat(L, " | ") or "-",
      P.verdicts and table.concat(P.verdicts, " | ") or "-"))
end

-- ---- events (through the spawner layer: no rivet callback of its own) ------------------------------------
function P.on_spawn(f)
  local h = math.tointeger(tonumber(f.SpawnedHandle))
  if not (h and P.lvl) then return end
  if P.seen_spawn[h] then return end                        -- direct and buffered deliveries of the same spawn
  P.seen_spawn[h] = true
  if planet() ~= P.PLANET then
    P.lvl.ignored = P.lvl.ignored + 1
    if P.lvl.ignored == 1 or P.lvl.ignored == 50 then
      log(string.format("inactive: %d spawn(s) ignored on this level - not Zurkon (%s)", P.lvl.ignored, P.where()))
    end
    return
  end
  if #P.spawn_queue < 256 then
    P.spawn_queue[#P.spawn_queue + 1] = { h = h, fac = math.tointeger(tonumber(f.SpawnFactory)), loc = math.tointeger(tonumber(f.SpawnLocation)) }
  end
end
P.seen_spawn = P.seen_spawn or {}
function P.on_planet(f)
  if f.NewPlanetName then
    P.event_planet = tostring(f.NewPlanetName)
    P.seen_spawn = {}
    P.reset("planet " .. P.event_planet)
  end
end
function P.on_stopped(f)
  local h = math.tointeger(tonumber(f.SpawnerComponentHandle))
  if not (h and P.lvl) then return end
  P.lvl.stopped[h] = true
  for _, A in ipairs(P.armed) do
    if not A.restored and A.rec.spawner == h then
      log(string.format("node %s's Spawner %X stopped (%d frame(s) after arming; %s)", tostring(A.rec.uid), h,
          P.frame - A.frame, A.verdict or "no spawn of it was seen"))
      P.put_back(A, "its Spawner stopped")
    end
  end
end

function P.start(fn)
  P.job_fn, P.job_restarts = fn, 0
  P.job = coroutine.create(fn)
end

function P.on_frame()
  P.frame = P.frame + 1
  local V = RANDO_SPAWNERS and RANDO_SPAWNERS.V
  if V and V.enabled and V.enabled() then
    if not P.stood_down then
      P.stood_down = true
      for _, A in ipairs(P.armed) do if not A.restored then P.put_back(A, "the Enemy Randomizer is on") end end
      P.job = nil
      log("standing down: the Enemy Randomizer is ON (it uses this experiment's method); nothing of spawnproof runs")
    end
    return
  end
  if P.stood_down then P.stood_down = nil; log("the Enemy Randomizer is OFF: spawnproof runs again") end
  if P.job then
    local ok, err = coroutine.resume(P.job)
    if not ok then
      -- the budget can also run out outside every guard: the job starts again (at most twice), nothing is lost
      if tostring(err):find("frame budget", 1, true) and (P.job_restarts or 0) < 2 then
        P.job_restarts = (P.job_restarts or 0) + 1
        P.budget_hits = (P.budget_hits or 0) + 1
        P.job = coroutine.create(P.job_fn)
      else
        P.job = nil; log("RANDO-ERROR", tostring(err))
      end
    elseif coroutine.status(P.job) == "dead" then P.job = nil end
    return
  end
  if not P.lvl or planet() ~= P.PLANET then return end      -- nothing is listed or read anywhere else
  local okr, ready = pcall(rivet.scene_ready)
  if okr and ready == false then return end
  if P.lvl.scans > 0 and #P.spawn_queue > 0 then
    local batch = P.spawn_queue
    P.spawn_queue = {}
    P.start(function() guard(P.learn, batch); guard(P.try_arm) end)
    return
  end
  if P.frame >= (P.next_scan or 0) or (P.lvl.scans == 0 and #P.spawn_queue > 0) then
    P.next_scan = P.frame + P.SCAN_EVERY
    P.start(function() guard(P.scan); guard(P.try_arm) end)
  end
end

if not P.subscribed then
  P.subscribed = true
  local SPL = RANDO_SPAWNERS
  -- dev 10.23: planet and spawns straight from rivet (2 of rivet_hook's 64 event callbacks): the spawner layer's
  -- events wait in the randomizer's buffer until the seed is ready, and that buffer once dropped the planet
  local function direct(class, fn)
    local ok, err = pcall(rivet.on_event, class, function(ev) local okf, e = pcall(fn, ev.fields or {}); if not okf then log("RANDO-ERROR", class, tostring(e)) end end)
    if not ok then log("cannot subscribe", class, tostring(err), "- using the spawner layer's (buffered) copy") end
    return ok
  end
  P.direct = { planet = direct("PlanetChangedEvent", P.on_planet), spawn = direct("SpawnerSpawnEvent", P.on_spawn) }
  if SPL and SPL.listen then
    SPL.listen("SpawnerSpawnEvent", P.on_spawn)            -- a second copy is ignored (P.seen_spawn)
    SPL.listen("SpawnerStoppedEvent", P.on_stopped)
    SPL.listen("LevelLoadedEvent", function() P.reset("level loaded") end)
    if not P.direct.planet then SPL.listen("PlanetChangedEvent", P.on_planet) end
    SPL.listen("Checkpoint", function(cp) if cp.loaded then P.reset("checkpoint loaded") end end)
  else
    log("16_rando_spawners.lua (with SP.listen) is missing: nothing runs")
    P.ENABLED = false
  end
  pcall(rivet.on_frame, P.on_frame)
end
P.reset("scripts loaded")
local hash_ok = (not rivet.hash) or (pcall(rivet.hash, "Factories") and rivet.hash("Factories") == P.PLUG_FACTORIES)
log(string.format("v6 loaded (factory Templates route, fresh factories): Template and Factories replacements on Zurkon (%s, at most %d); plugs Template %d Factories %d LastSpawn %d%s; own events: planet %s, spawns %s",
    P.ENABLED and "on" or "off", P.MAX_SWAPS, P.PLUG_TEMPLATE, P.PLUG_FACTORIES, P.PLUG_LASTSPAWN, hash_ok and "" or " - rivet.hash DISAGREES, nothing will match",
    P.direct and P.direct.planet and "yes" or "NO", P.direct and P.direct.spawn and "yes" or "NO"))
