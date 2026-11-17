-- DEVELOPER TOOL - not part of a release. SPAWN PROOF v1 (dev 10.21): ONE controlled enemy replacement,
-- to prove (or disprove) in your game the mechanism the Enemy / Boss / Chaos Randomizers will use.
--
-- WHAT YOUR DEV 10.20 LOG SHOWED (tests/data/round31_rivet.log), real game:
--   * A SpawnerScriptAction node keeps no Prius (ComponentInfo: prius type set, ddlPriusData 0 on both the
--     node and its Spawner component) - every Templates-list route since 10.12 looked in the wrong place.
--   * rivet.script_node lists the node's VARIABLE PLUGS: "Template" (1835115251, actors), "Location"
--     (2761897147, actors), "MaxAlive" (161848772, float 1.0), "NumSpawns" (1830449615, float 1.0) and
--     "LastSpawn" (406637480, actors); output "OnSpawned" (2046202852). The names are the engine hash
--     (rivet.hash: reflected CRC-32, start 0xEDB88320) of these words - checked below at load.
--   So the template a node spawns is (at least for the nodes probed) a SCRIPT VARIABLE of type actors,
--   and the node reports each spawn in its "LastSpawn" variable. That is the lead this file tests.
--
-- WHAT IT DOES (only on Zurkon, at most ONE node per session, only in memory, never saved):
--   1. Every 2 s it lists the level's SpawnerScriptAction nodes and reads each new node's variable plugs
--      (node +0x58 -> ScriptPlugs: varPlugs +0x08, varCount +0x1A; entries { u32 plug, u16 index,
--      u16 generation }: rivet_hook src/game/script.hpp).
--   2. The variables themselves are in the SceneManager's script variable array (+0x75A0, 0x40 bytes each:
--      actorUid +0x00, actors +0x10, type +0x34, generation +0x36: rivet_hook scene_manager.hpp,
--      script.hpp). The SceneManager's address comes from rando_give.dll v7, which finds it with
--      rivet_hook's own signature (exactly one match, as rivet_hook requires). No address is guessed.
--   3. Spawns are tied to their node by the node's LastSpawn variable (it holds the spawned actor). What
--      a template is (a regular enemy, a flyer, a friendly NPC ...) is learned from what it really spawned.
--   4. ARM: one node that has not spawned yet (LastSpawn empty), whose Template variable holds one actor,
--      is not shared with another node, and whose template has spawned a regular enemy here. Its
--      replacement: another template that has spawned a regular enemy of ANOTHER actor asset here.
--      The variable is checked (generation, type, value) right before the write and read back after it.
--   5. VERIFY: the node's next spawn is compared with the requested template (actor asset name and
--      bot class). The log says REPLACEMENT SPAWNED, ORIGINAL SPAWNED or something else.
--   6. PUT BACK when the node's Spawner stops (SpawnerStoppedEvent with its +0x60 handle), only if the
--      variable still holds what was written (a level load drops the record without writing).
-- Every line starts with "RANDO-SPAWNPROOF". Remove this file and nothing of it runs.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["dev(spawnproof)"] = "10.0.16"   -- the kit check (10_rando_runtime.lua)
RANDO_SPAWNPROOF = RANDO_SPAWNPROOF or {}
local P = RANDO_SPAWNPROOF
P.version = 1
P.frame = P.frame or 0
P.ENABLED = true
P.PLANET = "scarstu"            -- Zurkon (Zurkie's Battleplex): replayable fights, nothing of the story
P.SCAN_EVERY = 120              -- frames between two listings of the level's nodes
P.NODE_LIMIT = 512
P.MAX_SWAPS = 1                 -- per session
P.HELPER_MIN = 7                -- rando_give.dll v7 publishes the SceneManager
P.MB_SCENE, P.MB_SCENE_SIGS = 0x128, 0x130
P.SCENE_VARS, P.SCENE_VAR_MAX = 0x75A0, 0x75BC
P.VAR_SIZE = 0x40
P.VAR_TYPE_ACTORS = 5
P.GROUP_BIT = 0x80000000
P.SLICE = 0.002
P.LEARN_LOG = 12                -- learned spawns written to rivet.log per level

local function log(...) pcall(rivet.log, "[rando]", "RANDO-SPAWNPROOF", ...) end
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
P.PLUG_TEMPLATE = P.hash("Template")      -- 1835115251 in your log
P.PLUG_LASTSPAWN = P.hash("LastSpawn")    -- 406637480
P.PLUG_LOCATION = P.hash("Location")      -- 2761897147

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

-- ---- the SceneManager and its script variables ------------------------------------------------------
-- nil and why, or the variable array { base, max }
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

-- one variable: nil and why, or { addr, uid, actors, type, gen } (checked against the plug's generation)
function P.var(sc, idx, gen)
  if not (sc and idx and gen) or gen == 0 or idx >= sc.max then return nil, "no such variable" end
  local addr = sc.base + idx * P.VAR_SIZE
  local b = read(addr, P.VAR_SIZE)
  if not b then return nil, "unreadable" end
  local v = { addr = addr, uid = hex64(b, 1), actors = u32(b, 0x11), type = u16(b, 0x35), gen = u16(b, 0x37) }
  if v.gen ~= gen then return nil, string.format("generation %s, the plug says %s", tostring(v.gen), tostring(gen)) end
  return v
end

-- a node's variable plugs: { [plug] = { idx, gen } }, its Spawner handle (+0x60), or nil and why
function P.plugs_of(addr)
  local nb = read(addr, 0x80)
  if not nb then return nil, "node unreadable" end
  local plugs = ptr64(nb, 0x59)
  if not valid_ptr(plugs) then return nil, "no plug block" end
  local hb = read(plugs, 0x28)
  if not hb then return nil, "plug block unreadable" end
  local var_ptr, n = ptr64(hb, 9), hb[0x1B]
  local out = { spawner = u32(nb, 0x61), uid = hex64(nb, 0x49), vars = {}, nvars = n or 0 }
  if not n or n == 0 then return out end
  if not (var_ptr and var_ptr > 0x10000) or n > 32 then return nil, "variable plugs unreadable" end
  local vb = read(var_ptr, n * 8)
  if not vb then return nil, "variable plugs unreadable" end
  for k = 0, n - 1 do
    out.vars[u32(vb, k * 8 + 1)] = { idx = u16(vb, k * 8 + 5), gen = u16(vb, k * 8 + 7) }
  end
  return out
end

-- ---- actors --------------------------------------------------------------------------------------
-- { name, family, role, template } of an actor handle (one rivet.components call; rivet.name)
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
  return string.format("%s (handle %s uid %s, %s/%s)", tostring(a.name), tostring(a.handle), tostring(a.uid), tostring(a.family), tostring(a.class))
end
P.who = who

-- ---- the level --------------------------------------------------------------------------------------
P.lvl = P.lvl or nil
P.swaps = P.swaps or 0
P.spawn_queue = {}

function P.reset(why)
  local A = P.armed
  if A and not A.restored then
    -- written only if the variable still holds exactly what was written (generation checked): after a
    -- real reload it does not, and nothing is written
    P.put_back("level changed: " .. tostring(why))
    if not A.verified then P.swaps = math.max(0, P.swaps - 1) end
  end
  P.armed = nil
  P.lvl = { nodes = {}, order = {}, scans = 0, learned = {}, logged = 0, why = why }
  P.spawn_queue = {}
  P.next_scan = P.frame + P.SCAN_EVERY
end

local function planet()
  local s = RANDO and RANDO.state
  return s and s.current_planet
end

-- list the level's nodes and read the new ones' plugs (inside the job: yields between slices)
function P.scan()
  local lvl = P.lvl
  if not lvl then return end
  local sc, why = P.scene()
  if not sc then
    if not P.scene_said then P.scene_said = true; log("no script variables:", why) end
    return
  end
  if not P.scene_logged then
    P.scene_logged = true
    log(string.format("SceneManager %X (signature matched %s x), script variables at %X, max %d", sc.scene, tostring(sc.sigs), sc.base, sc.max))
  end
  local ok, list = pcall(rivet.script_nodes, "SpawnerScriptAction", P.NODE_LIMIT)
  if not ok or type(list) ~= "table" then return end
  lvl.scans = lvl.scans + 1
  local new, t0 = 0, clock()
  for _, node in ipairs(list) do
    if node.component and not lvl.nodes[node.component] then
      local okc, c = pcall(rivet.component, node.actor, "SpawnerScriptAction")
      local addr = okc and type(c) == "table" and c.handle == node.component and c.address and tonumber(c.address, 16)
      local pl = addr and P.plugs_of(addr)
      local rec = { component = node.component, actor = node.actor, uid = node.uid, addr = addr, plugs = pl }
      if pl then rec.tpl, rec.last, rec.spawner = pl.vars[P.PLUG_TEMPLATE], pl.vars[P.PLUG_LASTSPAWN], pl.spawner end
      lvl.nodes[node.component] = rec
      lvl.order[#lvl.order + 1] = node.component
      new = new + 1
      if clock() - t0 > P.SLICE and coroutine.isyieldable() then coroutine.yield(); t0 = clock() end
    end
  end
  if new > 0 then
    local tpl, single, last, shared, users = 0, 0, 0, 0, {}
    for _, k in ipairs(lvl.order) do
      local r = lvl.nodes[k]
      if r.tpl then tpl = tpl + 1; users[r.tpl.idx] = (users[r.tpl.idx] or 0) + 1 end
      if r.last then last = last + 1 end
    end
    for _, k in ipairs(lvl.order) do
      local r = lvl.nodes[k]
      if r.tpl then
        r.shared = users[r.tpl.idx] > 1
        if r.shared then shared = shared + 1 end
        local v = P.var(sc, r.tpl.idx, r.tpl.gen)
        r.tvar = v
        if v and v.type == P.VAR_TYPE_ACTORS and v.actors ~= 0 and (v.actors & P.GROUP_BIT) == 0 then single = single + 1 end
      end
    end
    log(string.format("scan %d on %s: %d node(s) (%d new); %d with a Template variable (%d holding one actor, %d shared), %d with LastSpawn",
        lvl.scans, tostring(planet()), #lvl.order, new, tpl, single, shared, last))
  end
end

-- spawns: which node's LastSpawn holds each of them; learn what that node's template is. One pass over the
-- nodes for every batch of spawns (a node's LastSpawn holds only its latest spawn), sliced over frames.
function P.learn(handles)
  local lvl = P.lvl
  local sc = P.scene()
  if not (lvl and sc) then return end
  local want = {}
  for _, h in ipairs(handles) do want[h] = true end
  local t0 = clock()
  for _, k in ipairs(lvl.order) do
    local r = lvl.nodes[k]
    if r.last then
      local lv = P.var(sc, r.last.idx, r.last.gen)
      local h = lv and lv.actors
      if h and want[h] then
        want[h] = nil
        r.spawned = (r.spawned or 0) + 1
        local a = P.actor(h)
        local tv = r.tpl and P.var(sc, r.tpl.idx, r.tpl.gen)
        local mine = P.armed and P.armed.rec == r          -- its variable holds what this file wrote: not a lesson
        if tv and tv.actors ~= 0 and (tv.actors & P.GROUP_BIT) == 0 and a and not mine then
          local t = lvl.learned[tv.actors] or { handle = tv.actors, uid = tv.uid }
          t.name, t.family, t.role, t.class = a.name, a.family, a.role, a.class
          lvl.learned[tv.actors] = t
        end
        if lvl.logged < P.LEARN_LOG then
          lvl.logged = lvl.logged + 1
          log(string.format("spawn %s is node %s's (its LastSpawn); Template variable %s = %s; spawned %s",
              tostring(h), tostring(r.uid), r.tpl and tostring(r.tpl.idx) or "none", tv and (tostring(tv.actors) .. " uid " .. tostring(tv.uid)) or "-", who(a)))
        end
        if P.armed and P.armed.rec == r and not P.armed.done then P.verify(a) end
      end
    end
    if clock() - t0 > P.SLICE and coroutine.isyieldable() then coroutine.yield(); t0 = clock() end
  end
  local missed = 0
  for _ in pairs(want) do missed = missed + 1 end
  lvl.unmatched = (lvl.unmatched or 0) + missed
end

-- ---- arm, verify, put back ------------------------------------------------------------------------------
function P.try_arm()
  local lvl = P.lvl
  if not (P.ENABLED and lvl) or P.armed or P.swaps >= P.MAX_SWAPS or planet() ~= P.PLANET then return end
  local sc = P.scene()
  if not sc then return end
  -- replacements: templates seen spawning a regular enemy on this level
  local enemies = {}
  for _, t in pairs(lvl.learned) do if t.role == "enemy" then enemies[#enemies + 1] = t end end
  local why = string.format("%d regular-enemy template(s) learned on this level (2 of different assets needed)", #enemies)
  if why ~= lvl.waiting_said then lvl.waiting_said = why; log("not armed yet: " .. why) end
  if #enemies < 2 then return end
  table.sort(enemies, function(a, b) return tostring(a.uid) < tostring(b.uid) end)
  for _, k in ipairs(lvl.order) do
    local r = lvl.nodes[k]
    if r.tpl and r.last and not r.shared and not r.spawned and r.spawner then
      local tv = P.var(sc, r.tpl.idx, r.tpl.gen)
      local lv = P.var(sc, r.last.idx, r.last.gen)
      local orig = tv and lvl.learned[tv.actors]
      if tv and lv and lv.actors == 0 and tv.type == P.VAR_TYPE_ACTORS and (tv.actors & P.GROUP_BIT) == 0 and orig and orig.role == "enemy" then
        for _, rep in ipairs(enemies) do
          if rep.handle ~= tv.actors and rep.name ~= orig.name then return P.arm(sc, r, tv, orig, rep) end
        end
      end
    end
  end
end

function P.arm(sc, r, tv, orig, rep)
  -- right before the write: the same variable, the same value
  local now = P.var(sc, r.tpl.idx, r.tpl.gen)
  if not (now and now.actors == tv.actors and now.uid == tv.uid) then log("not armed: the variable changed while it was checked"); return end
  local okw1 = pcall(rivet.write, string.format("%X", now.addr), le(rep.uid))
  local okw2 = pcall(rivet.write, string.format("%X", now.addr + 0x10), le32(rep.handle))
  local back = P.var(sc, r.tpl.idx, r.tpl.gen)
  P.swaps = P.swaps + 1
  local function copy(t) local c = {} for k, v in pairs(t) do c[k] = v end return c end
  P.armed = { rec = r, var = r.tpl, orig = copy(orig), rep = copy(rep), orig_uid = tv.uid, orig_handle = tv.actors, frame = P.frame }
  local ok = okw1 and okw2 and back and back.uid == rep.uid and back.actors == rep.handle
  log(string.format("ARMED node %s (Spawner %X): Template variable %d at %X: %s -> %s; read back %s",
      tostring(r.uid), r.spawner or 0, r.tpl.idx, now.addr, who(orig), who(rep), ok and "OK" or "FAILED"))
  if not ok then
    P.armed.done = true
    P.put_back("the write did not read back")
  end
end

function P.verify(a)
  local A = P.armed
  if A.verified then return end
  A.verified = true
  local verdict
  if a and a.name == A.rep.name then verdict = "REPLACEMENT SPAWNED"
  elseif a and a.name == A.orig.name then verdict = "ORIGINAL SPAWNED (the write had no effect on this spawn)"
  else verdict = "SOMETHING ELSE SPAWNED" end
  log(string.format("VERIFY node %s: requested %s; original %s; spawned %s: %s", tostring(A.rec.uid), who(A.rep), who(A.orig), who(a), verdict))
  A.verdict = verdict
end

function P.put_back(why)
  local A = P.armed
  if not A or A.restored then return end
  A.restored = true
  local sc = P.scene()
  local v = sc and P.var(sc, A.var.idx, A.var.gen)
  if not (v and v.uid == A.rep.uid and v.actors == A.rep.handle) then
    log("put back: skipped (" .. tostring(why) .. "): the variable no longer holds what was written")
    return
  end
  pcall(rivet.write, string.format("%X", v.addr), le(A.orig_uid))
  pcall(rivet.write, string.format("%X", v.addr + 0x10), le32(A.orig_handle))
  local back = P.var(sc, A.var.idx, A.var.gen)
  log(string.format("put back (%s): node %s Template variable %d = %s: %s", tostring(why), tostring(A.rec.uid), A.var.idx,
      tostring(A.orig_handle), (back and back.actors == A.orig_handle and back.uid == A.orig_uid) and "OK" or "FAILED"))
end

-- ---- events (through the spawner layer: no rivet callback of its own) ------------------------------------
function P.on_spawn(f)
  local h = math.tointeger(tonumber(f.SpawnedHandle))
  if h and P.lvl and planet() == P.PLANET and #P.spawn_queue < 256 then P.spawn_queue[#P.spawn_queue + 1] = h end
end
function P.on_stopped(f)
  local h = math.tointeger(tonumber(f.SpawnerComponentHandle))
  local A = P.armed
  if A and h and A.rec.spawner == h then
    log(string.format("node %s's Spawner %X stopped (its encounter ran %d frame(s) after arming; %s)", tostring(A.rec.uid), h,
        P.frame - A.frame, A.verdict or "no spawn of it was seen"))
    A.done = true
    P.put_back("its Spawner stopped")
  end
end

function P.on_frame()
  P.frame = P.frame + 1
  if P.job then
    local ok, err = coroutine.resume(P.job)
    if not ok then P.job = nil; log("RANDO-ERROR", tostring(err))
    elseif coroutine.status(P.job) == "dead" then P.job = nil end
    return
  end
  if not P.lvl or planet() ~= P.PLANET then return end      -- nothing is listed or read anywhere else
  local okr, ready = pcall(rivet.scene_ready)
  if okr and ready == false then return end
  if #P.spawn_queue > 0 then
    local batch = P.spawn_queue
    P.spawn_queue = {}
    P.job = coroutine.create(function() P.learn(batch) end)
    return
  end
  if P.frame >= (P.next_scan or 0) then
    P.next_scan = P.frame + P.SCAN_EVERY
    P.job = coroutine.create(function() P.scan(); P.try_arm() end)
  end
end

if not P.subscribed then
  P.subscribed = true
  local SPL = RANDO_SPAWNERS
  if SPL and SPL.listen then
    SPL.listen("SpawnerSpawnEvent", P.on_spawn)
    SPL.listen("SpawnerStoppedEvent", P.on_stopped)
    SPL.listen("LevelLoadedEvent", function() P.reset("level loaded") end)
    SPL.listen("PlanetChangedEvent", function(f) if f.NewPlanetName then P.reset("planet " .. tostring(f.NewPlanetName)) end end)
    SPL.listen("Checkpoint", function(cp) if cp.loaded then P.reset("checkpoint loaded") end end)
  else
    log("16_rando_spawners.lua (with SP.listen) is missing: nothing runs")
    P.ENABLED = false
  end
  pcall(rivet.on_frame, P.on_frame)
end
P.reset("scripts loaded")
local hash_ok = (not rivet.hash) or (pcall(rivet.hash, "Template") and rivet.hash("Template") == P.PLUG_TEMPLATE)
log(string.format("v1 loaded: one Template-variable replacement on Zurkon (%s); plugs Template %d LastSpawn %d%s", P.ENABLED and "on" or "off",
    P.PLUG_TEMPLATE, P.PLUG_LASTSPAWN, hash_ok and "" or " - rivet.hash DISAGREES, nothing will match"))
