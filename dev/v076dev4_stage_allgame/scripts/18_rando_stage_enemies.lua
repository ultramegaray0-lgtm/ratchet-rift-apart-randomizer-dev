-- Rift Apart Randomizer v0.76-DEV4: THE .STAGE ENEMY RANDOMIZER - in-game side. OPTIONAL.
--
-- The .stage Enemy Randomizer changes WHICH template actor a spawner's script variable names inside the level's own
-- zone file (tools/stage_enemies/stage_enemies.py builds mods/RandoEnemies.stage; rivet_hook loads it in place of the
-- game's zone). The game then resolves and spawns that template itself, through its normal asset loading - no runtime
-- memory write. This script does NOT change anything. It:
--   * announces the mode (rivet.log "RANDO-STAGE STAGE MODE ON", a corner note) - 16_rando_spawners.lua leaves factory Templates variables to .stage and suppresses runtime writes only for node Template adapters listed in this manifest; other node/group adapters retain the runtime route;
--   * checks every listing of the level's spawners: does a spawner the .stage changed hold the REPLACEMENT uid (the
--     .stage zone was loaded) or still the ORIGINAL one (it was not)? ("STAGE VARIABLE ...", "STAGE VARIABLES ...")
--   * checks every spawn of such a spawner: did the replacement spawn? ("STAGE SPAWN ...")
--   * watches every replacement it saw spawn until it dies or is gone ("STAGE DEATH", "STAGE GONE", "STAGE ALIVE")
--   * sums it up per level ("STAGE SUMMARY ...").
-- The Enemy Randomizer (the - key) must be ON for the spawners to be listed; in .stage mode it only looks.
-- Needs 16_rando_spawners.lua (10.0.51; STAGE_LUA 1.1.0 handshake). Without a manifest it only logs "enemy source: Lua runtime route".
-- Scale (stage_allgame 2.0.0, hundreds of changes in many zones): with more than ST.LIST_ALL changes the start lists one
-- "STAGE ZONE" line per changed zone, and each "STAGE CHANGE n" line is written when its spawner is first listed in a
-- level (only the changes you meet are logged); the "STAGE VARIABLES" counts cover the spawners listed in this level.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["18_rando_stage_enemies"] = "10.0.51"   -- the kit check (10_rando_runtime.lua)

local SP = RANDO_SPAWNERS
local function slog(...) pcall(rivet.log, "[rando]", "RANDO-STAGE", ...) end
if not (SP and SP.V and SP.V.stage_mode) then
  slog("16_rando_spawners.lua (10.0.51) is not installed: the .stage check is off")
  return
end
local V = SP.V
local ST = RANDO_STAGE or {}
RANDO_STAGE = ST
-- stage tool 1.1.0: this file and 16_rando_spawners.lua must both be the 1.1.0 Lua (handle/uid check, no false MIXED);
-- tools/stage_enemies verify / install check both files for this value
ST.STAGE_LUA = "1.1.0"
if V.STAGE_LUA ~= ST.STAGE_LUA then
  slog(string.format("RANDO-ERROR 16_rando_spawners.lua is stage Lua %s, this file is %s: copy BOTH from the same kit " ..
      "(the handle/uid check of the patched spawner is off)", tostring(V.STAGE_LUA or "before 1.1.0"), ST.STAGE_LUA))
end
local function handle_uid(h) return V.handle_uid and V.handle_uid(h) or nil end

local function say(text, opts) if RANDO and RANDO.say then RANDO.say(text, opts) end end
local function up(x) if x == nil then return nil end return tostring(x):upper() end
local function short(n) return tostring(V.short and V.short(n) or n) end

ST.FPS = 60
ST.ALIVE_SECONDS = 45          -- like the combat watch: alive this long while ...
ST.ALIVE_DEATHS = 6            -- ... this many other bots died on the level = reported (never acted on: nothing to undo)
ST.SPAWN_LOG = 120             -- STAGE SPAWN lines per level
ST.CHECK_EVERY = 60            -- frames between two looks at the watched bots / the listed spawners
ST.CHECK_BOTS = 6              -- watched bots asked per look (rivet's 8 ms frame budget is shared)
ST.LIST_ALL = 20               -- up to this many changes: every STAGE CHANGE line at the start (as before)
ST.SCALE = "2.0.0"             -- this file's scale revision (the 16/18 handshake ST.STAGE_LUA is unchanged)

-- ---- the manifest -----------------------------------------------------------------------------------------------
function ST.index()
  local m = V.stage_manifest()
  if m == ST.m_seen and ST.idx then return ST.idx end
  ST.m_seen = m
  local idx = { rep = {}, orig = {}, keys = {}, n = 0, list = {}, zones = {}, zone_order = {} }
  for i, c in ipairs(m and m.changes or {}) do
    if type(c) == "table" and c.original_uid and c.replacement_uid then
      c.i = i
      idx.n = idx.n + 1
      idx.list[#idx.list + 1] = c
      local ru, ou = up(c.replacement_uid), up(c.original_uid)
      idx.rep[ru] = idx.rep[ru] or {}; table.insert(idx.rep[ru], c)
      idx.orig[ou] = idx.orig[ou] or {}; table.insert(idx.orig[ou], c)
      for _, k in ipairs(c.spawner_keys or {}) do idx.keys[up(k)] = c end
      local zk = tostring(c.zone or c.zone_id or "?")
      local z = idx.zones[zk]
      if not z then
        z = { zone = zk, planet = c.planet, n = 0, kinds = {} }
        idx.zones[zk] = z
        idx.zone_order[#idx.zone_order + 1] = zk
      end
      z.n = z.n + 1
      local sw = short(c.original) .. ">" .. short(c.replacement)
      z.kinds[sw] = (z.kinds[sw] or 0) + 1
    end
  end
  ST.idx = idx
  return idx
end

function ST.change_line(c)
  ST.change_said = ST.change_said or {}
  if ST.change_said[c.i] then return end
  ST.change_said[c.i] = true
  slog(string.format("STAGE CHANGE %d: %s %s +%s (entry %s): %s #%s (%s) -> %s #%s (%s) | %s | adapter %s | spawners %s", c.i, tostring(c.zone),
      tostring(c.section), tostring(c.offset), tostring(c.var_index or "?"), tostring(c.original_uid), tostring(c.original_index or "?"),
      short(c.original), tostring(c.replacement_uid), tostring(c.replacement_index or "?"),
      short(c.replacement), tostring(c.pair), tostring(c.adapter or "factory"),
      (#(c.spawner_keys or {}) > 0) and table.concat(c.spawner_keys, ",") or "not named"))
end

-- ---- per level ----------------------------------------------------------------------------------------------------
function ST.level()
  local lvl = V.lvl
  if ST.L and ST.L.lvl == lvl then return ST.L end
  if ST.L then ST.summary("next level / checkpoint") end
  ST.L = { lvl = lvl, watch = {}, watch_order = {}, watch_i = 0, spawns = 0, logged = 0, rep = 0, orig = 0, other = 0,
           died = 0, gone = 0, alive = 0, not_loaded = 0, keys = {}, var_said = {}, counts_said = nil, next_check = 0 }
  return ST.L
end

function ST.summary(why)
  local L = ST.L
  if not L or (L.spawns == 0 and L.not_loaded == 0 and not L.counts_said) then return end
  local still = 0
  for _, w in pairs(L.watch) do if not w.done then still = still + 1 end end
  slog(string.format("STAGE SUMMARY (%s): spawns of .stage-related spawners %d - replacement %d, original %d, other %d | " ..
      "replacements died %d, gone %d, still there %d, reported alive %d | patched spawners still holding the original uid %d",
      why, L.spawns, L.rep, L.orig, L.other, L.died, L.gone, still, L.alive, L.not_loaded))
  for key, k in pairs(L.keys) do
    slog(string.format("STAGE SPAWNER %s: %s | spawned %d (replacement %d, original %d) | %s", key, tostring(k.encounter),
        k.spawned, k.rep, k.orig, tostring(k.verdict)))
  end
end

-- ---- the listing check: did the .stage zone load? ---------------------------------------------------------------
function ST.check_listing(L, idx)
  local lvl = V.lvl
  if not (lvl and lvl.order) then return end
  local held = {}                                     -- uid -> { [var idx] = true }
  for _, r in ipairs(lvl.order) do
    local uid = type(r) == "table" and r.orig and up(r.orig.uid)
    if uid and (idx.rep[uid] or idx.orig[uid]) then
      local vi = r.var and r.var.idx or tostring(r.key)
      held[uid] = held[uid] or {}
      held[uid][vi] = true
    end
    local key = type(r) == "table" and up(r.key)
    local c = key and idx.keys[key]
    if c and uid and not L.var_said[key] then
      L.var_said[key] = true
      ST.change_line(c)
      -- stage tool 1.1.0 (R1): the actor behind the variable's HANDLE is what the factory spawns. Its own uid must be the
      -- variable's uid; the 1.0.1 POC had the replacement's uid with the original's Zone Actors index (handle).
      local h = r.orig and r.orig.actors
      local hu = handle_uid(h)
      L.ref = L.ref or {}
      L.ref[key] = hu
      if not hu then
        slog(string.format("STAGE REFERENCE %s %s: variable uid %s, template handle %s - the game did not answer its actor uid " ..
            "(rivet.uid): the handle/uid agreement is NOT checked", tostring(r.kind), key, uid, tostring(h)))
      elseif hu == uid then
        slog(string.format("STAGE REFERENCE %s %s: variable uid %s, template handle %s is actor uid %s - uid and Zone Actors " ..
            "index AGREE (%s)", tostring(r.kind), key, uid, tostring(h), hu,
            hu == up(c.replacement_uid) and ("the replacement " .. short(c.replacement)) or "not the replacement"))
      else
        slog(string.format("RANDO-ERROR STAGE REFERENCE %s %s: variable uid %s but its template handle %s is actor uid %s - " ..
            "uid and Zone Actors index DISAGREE; the game spawns %s. This .stage is malformed: uninstall it",
            tostring(r.kind), key, uid, tostring(h), hu, hu == up(c.original_uid) and ("the ORIGINAL " .. short(c.original)) or hu))
      end
      if uid == up(c.replacement_uid) then
        slog(string.format("STAGE VARIABLE %s %s: holds %s (%s) = the .stage value - the patched zone %s IS loaded",
            tostring(r.kind), key, uid, short(c.replacement), tostring(c.zone)))
      elseif uid == up(c.original_uid) then
        L.not_loaded = L.not_loaded + 1
        slog(string.format("RANDO-ERROR STAGE VARIABLE %s %s: still holds the ORIGINAL %s (%s) - the patched zone %s was NOT loaded " ..
            "(rivet.toml [assets] paths? an older copy of the zone? see docs/STAGE_ENEMY_RANDOMIZER.md)",
            tostring(r.kind), key, uid, short(c.original), tostring(c.zone)))
      else
        slog(string.format("STAGE VARIABLE %s %s: holds %s, neither the original nor the replacement of change %d",
            tostring(r.kind), key, uid, c.i))
      end
    end
  end
  -- the counts: the zone file had replacement_refs / original_refs variable references; a loaded .stage moves one
  local parts = {}
  for _, c in ipairs(idx.list) do
    local listed = false
    for _, k in ipairs(c.spawner_keys or {}) do if L.var_said[up(k)] then listed = true end end
    local nr, no = 0, 0
    if listed then
      for _ in pairs(held[up(c.replacement_uid)] or {}) do nr = nr + 1 end
      for _ in pairs(held[up(c.original_uid)] or {}) do no = no + 1 end
    end
    if nr + no > 0 then
      parts[#parts + 1] = string.format("change %d: replacement %s held by %d variable(s) (zone file %s, %s expected with the .stage), " ..
          "original %s by %d (zone file %s, %s expected)", c.i, short(c.replacement), nr, tostring(c.replacement_refs or "?"),
          c.replacement_refs and tostring(c.replacement_refs + 1) or "+1", short(c.original), no, tostring(c.original_refs or "?"),
          c.original_refs and tostring(c.original_refs - 1) or "-1")
    end
  end
  local txt = table.concat(parts, " | ")
  if #parts > 0 and txt ~= L.counts_said then
    L.counts_said = txt
    slog("STAGE VARIABLES of the listed spawners: " .. txt)
  end
end

-- ---- hooks called by 16_rando_spawners.lua ------------------------------------------------------------------------
function V.stage_on_spawn(e, r, a, result, why)
  if not V.stage_mode() or not r then return end
  local idx = ST.index()
  if idx.n == 0 then return end
  local L = ST.level()
  local uid, key = r.orig and up(r.orig.uid), up(r.key)
  local c = key and idx.keys[key] or nil
  -- V3 runtime fallback may randomize unpatched factories whose original UID happens
  -- to equal another stage change's replacement UID. Do not misattribute those spawns.
  if not c and V.stage_manifest().profile ~= "v3" and V.stage_manifest().profile ~= "v4" and uid then
    c = idx.rep[uid] and idx.rep[uid][1] or nil
  end
  if not c then return end
  local expected_adapter = c.adapter or "factory"
  local actual_adapter = r.kind == "factory" and "factory" or r.kind == "template" and "node_template" or nil
  if actual_adapter ~= expected_adapter then return end
  local patched_key = key and idx.keys[key] ~= nil
  local name = a and a.name
  local is_rep = V.same_name(name, c.replacement)
  local is_orig = V.same_name(name, c.original)
  local verdict
  local hu = patched_key and ((L.ref and L.ref[key]) or handle_uid(r.orig and r.orig.actors)) or nil
  if uid == up(c.replacement_uid) then
    verdict = is_rep and "REPLACEMENT SPAWNED (the .stage value was used)"
              or is_orig and ("ORIGINAL SPAWNED although the variable holds the replacement" ..
                 ((hu and hu ~= uid) and (" - its handle is actor " .. hu .. ": uid and index disagree (malformed .stage)") or ""))
              or ("something else spawned: " .. short(name))
  elseif uid == up(c.original_uid) then
    verdict = "the variable still holds the ORIGINAL uid: the .stage zone was not loaded"
  else
    verdict = "the variable holds " .. tostring(uid)
  end
  L.spawns = L.spawns + 1
  if is_rep then L.rep = L.rep + 1 elseif is_orig then L.orig = L.orig + 1 else L.other = L.other + 1 end
  local k = L.keys[key or "?"] or { spawned = 0, rep = 0, orig = 0, encounter = V.encounter and V.encounter() or "-" }
  L.keys[key or "?"] = k
  k.spawned = k.spawned + 1
  if is_rep then k.rep = k.rep + 1 elseif is_orig then k.orig = k.orig + 1 end
  k.verdict = (patched_key and "the spawner the .stage changed: " or "a spawner whose variable holds the replacement uid: ") .. verdict
  if is_rep and e and e.h and not L.watch[e.h] then
    L.watch[e.h] = { frame = SP.frame or 0, key = key, name = name, deaths0 = (V.lvl and V.lvl.deaths_seen) or 0 }
    L.watch_order[#L.watch_order + 1] = e.h
  end
  if L.logged < ST.SPAWN_LOG then
    L.logged = L.logged + 1
    slog(string.format("STAGE SPAWN %s | %s | %s %s%s | variable %s | handle uid %s | spawned %s (%s) | change %d %s -> %s | %s",
        tostring(e and e.h), V.encounter and V.encounter() or "-", tostring(r.kind), tostring(key),
        patched_key and " (the patched spawner)" or "", tostring(uid), tostring(hu or "-"), short(name), tostring(a and a.family), c.i,
        short(c.original), short(c.replacement), verdict))
  end
end

function V.stage_on_death(h)
  local L = ST.L
  local w = L and L.watch[h]
  if not w or w.done then return end
  w.done = "died"
  L.died = L.died + 1
  slog(string.format("STAGE DEATH %d: %s (spawner %s) died %.0f s after it spawned", h, short(w.name), tostring(w.key),
      ((SP.frame or 0) - w.frame) / ST.FPS))
end

function V.stage_tick(frame, ready, enabled)
  local m = V.stage_manifest()
  if not ST.announced then
    ST.announced = true
    local src = (RANDO and RANDO.config and RANDO.config.enemy_source) or "auto"
    if m then
      local idx = ST.index()
      slog(string.format("STAGE MODE ON: %s, %d change(s), %s (sha256 %s), built by stage_enemies %s for %s - runtime spawner " ..
          "writes are OFF only for manifest-owned factory/node Template keys; unlisted factory, node and group adapters remain on the runtime route", tostring(m.label), idx.n, tostring(m.stage_file),
          tostring(m.stage_sha256), tostring(m.tool), tostring(m.kit)))
      if idx.n <= ST.LIST_ALL then
        for _, c in ipairs(idx.list) do ST.change_line(c) end
      else
        local planets, np = {}, 0
        for _, zk in ipairs(idx.zone_order) do
          local z = idx.zones[zk]
          if z.planet and not planets[z.planet] then planets[z.planet] = true; np = np + 1 end
          local parts = {}
          for sw, n in pairs(z.kinds) do parts[#parts + 1] = sw .. " x" .. n end
          table.sort(parts)
          slog(string.format("STAGE ZONE %s | %s | %d change(s): %s", tostring(z.planet or "?"), zk, z.n, table.concat(parts, ", ")))
        end
        slog(string.format("STAGE MODE: %d change(s) in %d zone(s) on %d planet(s); each STAGE CHANGE line is written when its " ..
            "spawner is first listed in a level", idx.n, #idx.zone_order, np))
      end
      if m.tool and tostring(m.tool) < "1.1.0" then
        slog(string.format("RANDO-ERROR this .stage was built by stage tool %s, before 1.1.0: it changed only the uid of each " ..
            "reference (the Phase A POC failure). Uninstall it and build again with tool 1.1.0", tostring(m.tool)))
      end
      if src == "lua" then
        slog("enemy_source = \"lua\": the .stage manifest owns only its listed keys; unlisted eligible spawners may still use the runtime route")
      end
      ST.say_pending = string.format("%d manifest-owned spawner change(s) from %s; unlisted eligible spawners remain on the runtime route", idx.n, tostring(m.stage_file))
    elseif src == "stage" then
      slog("STAGE MODE ON without a manifest (enemy_source = \"stage\"): no enemy is changed at all")
    else
      slog("enemy source: Lua runtime route (no .stage manifest installed)")
    end
  end
  if not (m and ready) then return end
  if ST.say_pending then say("[ENEMY RANDOMIZER] .stage mode", { type = "corner", duration = 5, sub = ST.say_pending }); ST.say_pending = nil end
  if not enabled then return end
  local L = ST.level()
  if frame < L.next_check then return end
  L.next_check = frame + ST.CHECK_EVERY
  local idx = ST.index()
  pcall(ST.check_listing, L, idx)
  -- the watched replacements: gone (killed and removed) or still there long after the fight moved on
  local n = #L.watch_order
  for _ = 1, math.min(ST.CHECK_BOTS, n) do
    L.watch_i = L.watch_i % n + 1
    local h = L.watch_order[L.watch_i]
    local w = L.watch[h]
    if w and not w.done then
      local p = V.presence(h)
      if p == "gone" then
        w.done = "gone"
        L.gone = L.gone + 1
        slog(string.format("STAGE GONE %d: %s (spawner %s) is gone %.0f s after it spawned (killed and removed, or despawned)",
            h, short(w.name), tostring(w.key), (frame - w.frame) / ST.FPS))
      elseif p == "present" and not w.alive_said and (frame - w.frame) > ST.ALIVE_SECONDS * ST.FPS
             and ((V.lvl and V.lvl.deaths_seen) or 0) - w.deaths0 >= ST.ALIVE_DEATHS then
        w.alive_said = true
        L.alive = L.alive + 1
        slog(string.format("RANDO-ERROR STAGE ALIVE %d: %s (spawner %s) is alive %.0f s after it spawned while %d other bots died - " ..
            "check it can be killed", h, short(w.name), tostring(w.key), (frame - w.frame) / ST.FPS,
            ((V.lvl and V.lvl.deaths_seen) or 0) - w.deaths0))
      end
    end
  end
end

-- Ctrl+- text addition (enemy.lua shows V.status_text; this is logged on demand by the developer key ;)
function ST.status_text()
  local m = V.stage_manifest()
  if not m then return "enemy source: Lua runtime route" end
  local L = ST.L
  return string.format(".stage mode (%d change(s)); here: %d spawn(s) of changed spawners, replacement %d, original %d, died %d",
      ST.index().n, L and L.spawns or 0, L and L.rep or 0, L and L.orig or 0, L and L.died or 0)
end

slog("loaded (10.0.51, stage Lua " .. ST.STAGE_LUA .. ", scale " .. ST.SCALE .. "): the .stage Enemy Randomizer's check - it changes nothing; the manifest is read on the first frame")