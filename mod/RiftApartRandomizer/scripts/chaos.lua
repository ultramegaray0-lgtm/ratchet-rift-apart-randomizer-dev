-- Rift Apart Randomizer dev 10.13: CHAOS RANDOMIZER. OPTIONAL, OFF by default. NO SAFETY GUARDS.
--
-- In the game: the BACKSPACE key turns it ON / OFF (key_chaos; remembered in the save, kept over a New
-- Game). Ctrl+BACKSPACE shows what it changed here. The setting chaos_randomizer = true in
-- 04_rando_settings.lua only decides the start for a save that never used the key.
--
-- ANYTHING CAN BECOME ANYTHING. Every enemy template of every spawner node of the level (regular,
-- elite, flying, ground, turret, large, mini-boss, boss, story boss, and templates nobody has
-- classified yet) can become any template the randomizer has seen on ANY planet of this save. No
-- family, size, tier, planet or encounter rule. Different enemies of one encounter become different
-- enemies. Picks are spread so the same replacement repeats as little as the pool allows, and they
-- come from the seed (same seed, same planets seen, same spawners -> the same chaos).
--
-- WHAT CHAOS DOES NOT DO (on purpose, as asked): it never checks that a replacement can spawn, move,
-- fight, die or finish the encounter; it never puts an encounter back by itself (no 20 s timeout, no
-- 3 minute stuck check, no death/reload limit, no story boss area protection, no family check), and it
-- changes encounters that already started. A door may never open, a boss may not be beatable, a run
-- may become impossible. Switch Chaos OFF (BACKSPACE) to get the original enemies back, then load the
-- last checkpoint. See docs/CHAOS.md.
--
-- WHAT STAYS (code integrity, not gameplay protection): only template ids the game itself used in a
-- spawner node are written, only into a node that is still the same live instance, only over the id
-- that was read there, and every write is read back. A Templates list shared by two nodes is not
-- written (the randomizer could not tell the two encounters apart afterwards). Templates the game has
-- shown to be friendly bots or mounts (16_rando_spawners.lua learned them) are left out: they are not
-- enemies.
--
-- PRIORITY: while Chaos is ON, the Enemy and Boss Randomizers change nothing (their own ON / OFF stays
-- as you set it). Switched OFF, Chaos puts back what it changed and they plan again from their own
-- settings.
--
-- Needs 16_rando_spawners.lua. Removing this file only removes Chaos.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["chaos"] = "10.0.12"   -- the kit check (10_rando_runtime.lua)

RANDO_CHAOS = RANDO_CHAOS or {}
local C = RANDO_CHAOS
local R = RANDO
local SP = RANDO_SPAWNERS

local function log(...) pcall(rivet.log, "[rando]", "RANDO-CHAOS", ...) end
local function S() return RANDO and RANDO.state end
local function changed() if RANDO and RANDO.mark_changed then RANDO.mark_changed() end end

C.SEEN_CAP = 1000                 -- templates remembered across planets (state.chaos_seen)
C.NOT_ENEMIES = { friendly = true, mount = true }   -- learned families that are not enemies

if not (R and R.config) then return end
if not SP then
  log("16_rando_spawners.lua is not installed: the Chaos Randomizer stays off")
  return
end

-- ---------------------------------------------------------------------------------------------
-- the pool: every template seen in a spawner node, on every planet of this save
-- ---------------------------------------------------------------------------------------------
local function seen_t(write)
  local s = S()
  if not s then return {} end
  if write then s.chaos_seen = s.chaos_seen or {} end
  return s.chaos_seen or {}
end
local function planet() local s = S(); return tostring((s and s.current_planet) or "?") end
local function not_enemy(tid)
  local fam = SP.family_of(tid)
  return fam ~= nil and C.NOT_ENEMIES[fam] == true
end
C.not_enemy = not_enemy

-- after each census: remember this level's templates and where they came from (only while ON, so a
-- save that never used Chaos gets nothing new)
function C.on_census(lvl)
  if not C.enabled() then return end
  local seen = seen_t(true)
  local p, n, full = planet(), 0, 0
  for _, tid in ipairs(SP.sorted_keys(lvl.templates or {})) do
    if seen[tid] == nil then
      local cnt = 0
      for _ in pairs(seen) do cnt = cnt + 1 end
      if cnt < C.SEEN_CAP then seen[tid] = p; n = n + 1 else full = full + 1 end
    end
  end
  if n > 0 then changed(); log("pool:", n, "new template(s) from", p, (full > 0) and ("(" .. full .. " over the cap)") or "") end
end

function C.pool(lvl)
  local all = {}
  for tid in pairs(lvl.templates or {}) do all[tid] = true end
  if R.config.chaos_cross_planet ~= false then
    for tid in pairs(seen_t()) do all[tid] = true end
    local s = S()
    for tid in pairs((s and s.spawn_learned) or {}) do all[tid] = true end
  end
  local out = {}
  for _, tid in ipairs(SP.sorted_keys(all)) do if not not_enemy(tid) then out[#out + 1] = tid end end
  return out
end

-- every slot gets its own pick: the seed ranks the pool for that slot (rendezvous: a pool that grows
-- changes few picks), and a template already given in this level is passed over while unused ones
-- remain, so one replacement repeats as little as possible. A slot never keeps its own template when
-- anything else exists.
function C.assign(lvl, slots)
  C.on_census(lvl)                    -- this level's templates join the pool of every planet
  local pool = C.pool(lvl)
  C.pool_size = #pool
  if C.client then C.client.pool_size = #pool end
  local picks, used, n_used = {}, {}, 0
  local here = lvl.templates or {}
  local foreign = 0
  for _, sl in ipairs(slots) do
    if not not_enemy(sl.orig) and #pool > 0 then
      local ranked = SP.rank(SP.seed_key() .. "|chaos|" .. tostring(sl.uid) .. "|" .. sl.i, pool)
      if n_used >= #pool then used, n_used = {}, 0 end
      local pick
      for _, t in ipairs(ranked) do
        if t ~= sl.orig and not used[t] then pick = t; break end
      end
      if not pick then
        for _, t in ipairs(ranked) do if t ~= sl.orig then pick = t; break end end
      end
      if pick then
        if not used[pick] then used[pick] = true; n_used = n_used + 1 end
        picks[sl.uid .. "#" .. sl.i] = pick
        if not here[pick] then foreign = foreign + 1 end
      end
    end
  end
  C.last = { slots = #slots, picked = 0, foreign = foreign, pool = #pool }
  for _ in pairs(picks) do C.last.picked = C.last.picked + 1 end
  return picks
end

-- ---------------------------------------------------------------------------------------------
-- the switch
-- ---------------------------------------------------------------------------------------------
C.client = SP.register({ name = "chaos", role = "any", label = "Chaos Randomizer", state_key = "chaos_rando",
                         config_key = "chaos_randomizer", priority = true, guards = false,
                         assign = C.assign, on_census = C.on_census })
-- kept over a New Game, like the other two switches (10_rando_runtime.lua reads this list)
for _, k in ipairs({ "chaos_rando", "chaos_seen" }) do
  local found = false
  for _, x in ipairs(SP.KEEP_OVER_NEW_GAME) do if x == k then found = true end end
  if not found then SP.KEEP_OVER_NEW_GAME[#SP.KEEP_OVER_NEW_GAME + 1] = k end
end
-- what this session saw before the companion's restore is kept
function C.client.after_restore(live)
  local s = S()
  if not (s and type(live) == "table" and live ~= s and type(live.chaos_seen) == "table") then return end
  if next(live.chaos_seen) == nil then return end
  s.chaos_seen = s.chaos_seen or {}
  for t, p in pairs(live.chaos_seen) do if s.chaos_seen[t] == nil then s.chaos_seen[t] = p end end
end

function C.enabled() return SP.enabled(C.client) end
function C.set(on, why) return SP.set(C.client, on, why) end

function C.others_text()
  local parts = {}
  for _, name in ipairs({ "enemy", "boss" }) do
    local c = SP.clients[name]
    if c then parts[#parts + 1] = c.label .. " " .. (SP.enabled(c) and "ON" or "OFF") end
  end
  return #parts > 0 and table.concat(parts, ", ") or "no other enemy randomizer installed"
end

function C.toggle(why)
  local on = not C.enabled()
  SP.set(C.client, on, why)
  if on then
    R.say("CHAOS RANDOMIZER: ON", { type = "center", duration = 7,
          sub = "anything can become anything - no protection, a run may become impossible. Enemy / Boss Randomizer paused" })
  else
    R.say("CHAOS RANDOMIZER: OFF", { type = "center", duration = 6,
          sub = "original enemies are back; " .. C.others_text() .. " as you set them" })
  end
  log((on and "ON" or "OFF") .. " (" .. tostring(why) .. ") - " .. C.others_text() ..
      (on and " (paused while Chaos is ON)" or " (resume)"))
  return on
end

function C.status_text()
  if not C.enabled() then return nil end
  local st = SP.client_status(C.client)
  return string.format("CHAOS ON (%d changed here, pool %d; enemy/boss randomizers paused)", st.slots, C.pool_size or 0)
end

function C.key()
  if not (RANDO_SEED and R.state) then
    R.say("Randomizer: the seed is still being prepared", { type = "corner", duration = 3 }); return
  end
  if R.ctrl_down() then
    local st = SP.client_status(C.client)
    local l = C.last or {}
    local seen = 0
    for _ in pairs(seen_t()) do seen = seen + 1 end
    R.say(string.format("Chaos Randomizer %s: %d slot(s) changed in %d encounter(s) here", C.enabled() and "ON" or "OFF",
                        st.slots, st.encounters),
          { type = "corner", duration = 7,
            sub = string.format("pool %d template(s) (%d seen on all planets), %d from elsewhere here; %s",
                                l.pool or 0, seen, l.foreign or 0, C.others_text()) })
    return
  end
  C.toggle(R.key("key_chaos"))
end
R.bind_key(R.config.key_chaos, C.key, "key_chaos")
log("installed (" .. (C.enabled() and "ON" or "OFF") .. " until the save says otherwise) - " .. R.key("key_chaos") ..
    " turns it on / off, " .. R.key("key_chaos", true) .. " shows what it changed. NO safety guards; priority over the" ..
    " Enemy and Boss Randomizers while ON")
