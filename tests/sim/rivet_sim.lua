-- Simulated rivet_hook 2.0.x API plus a small simulated game, for offline tests (Lua 5.4).
--
-- This is NOT the game. It models only what the randomizer scripts touch, using the
-- behaviour documented in rivet_hook's docs/LUA_SCRIPTING.md and what the in-game logs
-- (rounds 7-13) showed:
--   * rivet.log joins its arguments with tabs; rivet.notify fails while the HUD is not loaded
--   * events are picked up once per pump; a planet load replays WeaponAddedEvent for every
--     owned weapon and GadgetItemAddedEvent for every owned gadget (log round 13, lines 76-94)
--   * the game's missions and rando_give.dll v4's mission requests (checks from the game's code,
--     round 14/15 dumps; your game runs system 2; what START/REPLAY change is SIMULATED)
--   * rando_give.dll: a mailbox page at 0x7FEF00000000, one request handled per frame; the
--     game answers a give with WeaponAddedEvent{WeaponType} / GadgetItemAddedEvent{ConfigTypeHash}
--     and InventoryChangedEvent, or (failure modes the tests switch on) ignores it, or holds it
--     while the game is paused
--   * rivet.time_scale() errors while loading ("refuse to run while the pump is on the
--     render thread") and reports the applied speed otherwise
--   * rivet.configs / rivet.config_set as rivet_hook's docs and src/configs.cpp describe them:
--     a listing of { id, type }, a write to one numeric field returning the previous value, an
--     error for a field path that does not exist. The game's VendorConfig fields come from the
--     DDL dump (neptuwunium/rivet, Types/VendorConfig.cs). Configs reload with their level, so
--     a planet load puts the authored values back. What a long PurchaseWeaponHoldTime does to
--     the vendor (S.vendor_buy) is SIMULATED: the real effect has not been seen in game.
--   * 5.0, rando_give.dll v5 (rando_give_core.h; its C core is unit-tested in tests/native):
--     kind 6 gives an armor piece and answers at once (MB_RET 1 added / 0 owned); kind 7 finds a
--     config's address; give counts up to 100000 (currency). S.armor_source(bundle) is the game
--     running VanityGiveBundleAction: with the hook on, a listed piece is intercepted (table entry
--     cleared, ring entry 1), otherwise it is given (ring 2/3). What the game's level script does
--     after the success plug is not modelled.
--   * the weapon vendor's ItemDatas array in memory: the layout here (array at +0x88, elements of
--     0x58 bytes, Item at +0x10, Price as a 32-bit integer at +0x18) is INVENTED for the test; the shop script must find it the way
--     it would find the real one (by the item ids). What the vendor UI shows is SIMULATED as
--     "the Item field of each slot". Currency: GainBoltEvent / GainRaritaniumEvent are SIMULATED.
--   * a new game: the game reports MIS_INTRO / OBJ_INTRO_PROLOGUE state 2, then
--     OBJ_INTRO_PARADE_START_CINE state 1 (round 14 lines 193-194, round 15 lines 171-172) and
--     the new save owns only the game's starting kit. S.parade_control() / S.parade_wrench()
--     report the next parade objectives (rounds 14/15: OBJ_INTRO_PARADE_START, then
--     OBJ_INTRO_PARADE_PICKUP_WRENCH 1 -> 2)
--   * 8.0 (all SIMULATED unless noted): with S.auto_travel, rivet.warp / rivet.fly MOVE the hero:
--     the checkpoint's planet loads like a planet change (PlanetChangedEvent pair, loading frames,
--     the replays) - rivet_hook's docs say the warp loads another planet's region; nothing of
--     this has run in your game. A checkpoint name not in S.checkpoint_list raises (rivet_hook's
--     find() answers 0 for a name the level lacks). fly needs S.ship_near and lands after
--     S.fly_frames. rivet.hero_play_as records the swap. rando_give.dll v6: kind 8 writes a
--     mission's state (no event: what the game does after such a write is unknown), kind 12
--     finds it, kinds 9-11 change S.levels / S.travel_flag like the two actions do
SIM = {}
local S = SIM

function S.reset()
  S.frame, S.clock = 0, 0
  S.logs, S.notes, S.published = {}, {}, {}
  S.hud, S.scene, S.hero_handle, S.loading = true, true, 1234, false
  S.speed, S.has_time_scale = 1.0, true
  S.events, S.queue, S.frame_cbs, S.key_cbs, S.down = {}, {}, {}, {}, {}
  S.events_unavailable, S.unknown_classes = false, {}
  S.mem = {}                      -- address -> byte
  S.errors = {}                   -- calls that raised (for assertions)
  S.planet = nil
  S.warps = {}
  -- inventory
  S.weapons_owned, S.gadgets_owned = {}, {}
  S.weapon_type = {}              -- item config id (hex) -> WeaponType number
  S.next_weapon_type = 1001
  S.gadget_type = {}              -- item config id (hex) -> ConfigTypeHash
  S.item_kind = {}                -- id -> "weapon" | "gadget"
  -- delivery behaviour knobs
  S.accept_modes = { [0] = true } -- which targets the game reacts to (0 hero, k group k-1)
  S.group_sizes = { [0] = 1, [1] = 1, [2] = 0, [3] = 0 }
  S.ignore_items = {}             -- id -> true: the game never reacts to this item
  S.hold_while_paused = true      -- messages wait until the game runs again
  S.held = {}
  S.inv_changed_on_owned = true
  S.give_log = {}
  -- script nodes (route 1)
  S.nodes = {}
  S.mailbox = nil
  S.vanity_owned = {}              -- armor bundle id (hex) -> true
  S.vanity_calls = 0
  S.vanity_gives = {}              -- bundles the game's armor code added (5.0)
  S.currency = {}                  -- currency item id -> amount received (5.0)
  S.config_objects = {}            -- config id -> object address (5.0, kind 7)
  S.vendor_mem = {}                -- config id -> { obj, data, authored = { id... } }
  S.armor_hook = true              -- v5 hook installed (MB_ARMOR_HOOK = 1)
  -- the game's mission manager, laid out in memory the way the game's code reads it (research
  -- zip 2026-11-11, see rando_give_core.h). What START does to the state (-> 3) is SIMULATED:
  -- the real effect is what lab test 2 shows.
  S.mission_state = setmetatable({}, { __index = function(_, name) return S.get_mission(name) end })
  S.missions, S.mstate = nil, nil  -- name -> index / state (S.install_missions)
  S.hash_names = {}
  S.travels = {}
  -- 8.0
  S.auto_travel = false
  S.travel_queue = {}
  S.ship_near = false
  S.fly_frames = 120
  S.heroes = {}
  S.playing, S.swap_pending, S.swap_frames, S.swap_refuse = "ratchet", nil, 0, nil
  S.go_to, S.goto_on_start = {}, true
  S.levels, S.levels_other, S.level_current = 0x6, 0x2, 2
  S.travel_flag = 0
  S.v6_bits = 7
  S.set_state_calls = {}
  S.warp_fails = {}                -- checkpoint -> true: rivet.warp raises for it
  -- 8.1: the names your game lists (round 17 rivet.log research), plus SIMULATED ones for the
  -- planets whose names were not listed (Torren IV, Cordelion, Ardolis have no LANDING / SHIP /
  -- DEFAULT checkpoint in your game; Cordelion's are named after Kedaro Station, not CORD)
  S.checkpoint_list = {
    "CHK_ZURK_00_DEFAULT", "CHK_ZURK_LANDING_SHIP", "CHK_ZURK_LANDING_ENTRANCE", "CHK_ZURK_01_LAND_RATCHET_VISIT_1",
    "CHK_ZURK_05_ARENA_INTRO_CINE", "CHK_NEFCITY_SHIP", "CHK_SAV_01_LANDING",
    "CHK_BLIZAR_A_LANDINGPAD", "CHK_BLIZAR_B_LANDINGPAD_DESTROYED",
    "CHK_SARG_GELFACTORY_LANDINGPAD", "CHK_SARG_02_MININGPLATFORM_LANDINGPAD",
    "CHK_ZORDOOM_POSTMISSION_LANDINGPAD", "CHK_MEGA_01_RIVET_START", "CHK_MEGA_FINALE_START",
    "CHK_MALINON_PARADE_START",
    "CHK_MOL_02_FIXER_CHASE_CINE", "CHK_MOL_01_START",                      -- SIMULATED
    "CHK_STATION_01_START", "CHK_STATION_FORGE_BOSS",                       -- SIMULATED (Cordelion)
    "CHK_ARD_01_ARRIVAL", "CHK_ZORD_01_START",                              -- SIMULATED
    -- 8.4: listed by your game in rounds 19-20 (test travel and the catalog)
    "CHK_ARD_START", "CHK_ARD_QWARKSHIP_ENTRANCE", "CHK_CORD_A_START", "CHK_CORD_A_TELE_SHIP", "CHK_CORD_B_HAX_START",
    "CHK_ZORDOOM_START", "CHK_ZORDOOM_LANDING_COMBAT", "CHK_MOL_SALVAGE_PIRATES_COMMAND_SHIP",
    "CHK_MOL_SALVAGE_PIRATES_COMMAND_SHIP_SCUTTLE",
    "CHK_TRANSITION_TO_MOL", "CHK_TRANSITION_TO_SARG", "CHK_TRANSITION_TO_KEDARO", "CHK_TRANSITION_TO_ARDOLIS",
    "CHK_TRANSITION_TO_BLIZAR", "CHK_TRANSITION_TO_NEFARIOUS_CITY", "CHK_TRANSITION_TO_SAVALI",
    "CHK_TRANSITION_TO_ZORDOOM", "CHK_TRANSITION_TO_ZURKIES",
  }
  S.mgr_ready, S.alt_path = true, true   -- alt_path = system 2, as in your game
  S.can_start = true
  S.start_effect = 2                     -- SIMULATED
  S.replay_effect = nil                  -- SIMULATED: replay changes nothing
  -- configs (rivet.configs / rivet.config / rivet.config_set)
  S.configs = {}
  S.config_api = true
  S.add_vendor("A1B2C3D4E5F60718", "Weapons")
  S.purchases = {}
end
local VENDOR_DEFAULTS = { PurchaseWeaponHoldTime = 1.0, UpgradeCellHoldTime = 0.5, TabChangeDelayDuration = 0.25,
                          IdleVOTriggerTime = 20.0, UpgradeCellYOffset = 31.0 }
function S.add_vendor(id, kind)
  local f = { Type = kind }
  for k, v in pairs(VENDOR_DEFAULTS) do f[k] = v end
  S.configs[id] = { type = "VendorConfig", fields = f }
end
function S.reload_configs()
  for id, c in pairs(S.configs) do
    if c.type == "VendorConfig" then for k, v in pairs(VENDOR_DEFAULTS) do c.fields[k] = v end end
    local vm = S.vendor_mem[id]
    if vm then for i, item in ipairs(vm.authored) do S.put_hex_id(vm.slot(i) + 0x10, item) end end
  end
end
-- 5.0: the vendor's stock in memory (INVENTED layout, see the top of this file).
-- 8.4: S.vendor_pointers = true lays ItemDatas out as the game's DDL declares it (List<VendorItemData?>,
-- rivet's VendorConfig.cs): an array of POINTERS, with the slot objects allocated right after the
-- array - which is why 7.0-8.3 found the ids "past the end of the array" (rounds 18-20)
S.VENDOR_OBJ = 0x23400000
function S.install_vendor_memory(id, items, prices)
  local obj = S.VENDOR_OBJ + 0x10000 * (#S.config_objects + (S.vendor_count or 0))
  S.vendor_count = (S.vendor_count or 0) + 1
  local data = obj + 0x1000
  S.map(obj, 0x200)
  S.put_u64(obj, 0x7FF6C4A00000)                 -- a vtable pointer
  S.put_u64(obj + 0x88, data)
  S.put_u32(obj + 0x90, #items)
  S.put_u32(obj + 0x94, #items + 3)
  local slot
  if S.vendor_pointers then
    local objs = data + #items * 8 + 0x20
    S.map(data, #items * 8 + 0x20 + #items * 0x60 + 0x400)
    slot = function(i) return objs + (i - 1) * 0x60 end
    for i = 1, #items do S.put_u64(data + (i - 1) * 8, slot(i)) end
  else
    S.map(data, #items * 0x58 + 0x400)
    slot = function(i) return data + (i - 1) * 0x58 end
  end
  for i, item in ipairs(items) do
    local e = slot(i)
    S.put_u64(e + 0x08, 0x40000 + i)              -- some other field
    S.put_hex_id(e + 0x10, item)
    S.put_u32(e + 0x18, (prices and prices[i]) or 1000 * i)  -- Price (7.0: the weapon's vanilla price when given)
  end
  S.vendor_mem[id] = { obj = obj, data = data, authored = items, slot = slot }
  S.config_objects[id] = obj
end
function S.vendor_slot_item(id, i) return S.get_hex_id(S.vendor_mem[id].slot(i) + 0x10) end
function S.vendor_slot_price(id, i)
  local a = S.vendor_mem[id].slot(i) + 0x18
  return S.mem[a] + S.mem[a + 1] * 0x100 + S.mem[a + 2] * 0x10000 + S.mem[a + 3] * 0x1000000
end
-- the player holds the vendor's buy button for `seconds` on a weapon (SIMULATED behaviour)
function S.vendor_buy(weapon_id, seconds)
  for _, c in pairs(S.configs) do
    if c.type == "VendorConfig" and c.fields.Type == "Weapons" then
      if (seconds or 1.0) >= c.fields.PurchaseWeaponHoldTime then
        S.purchases[#S.purchases + 1] = weapon_id
        S.weapons_owned[weapon_id] = true
        return true
      end
      return false
    end
  end
  return false
end

-- ---------------------------------------------------------------------------- memory
local function addr_of(text)
  if type(text) == "number" then return text end
  return tonumber(text, 16)
end
function S.map(addr, size) for i = 0, size - 1 do S.mem[addr + i] = S.mem[addr + i] or 0 end end
function S.put_u32(addr, v) for i = 0, 3 do S.mem[addr + i] = (v >> (8 * i)) & 0xFF end end
function S.get_u32(addr) local v = 0 for i = 3, 0, -1 do v = (v << 8) | (S.mem[addr + i] or 0) end return v end
function S.put_u64(addr, v) for i = 0, 7 do S.mem[addr + i] = (v >> (8 * i)) & 0xFF end end
function S.get_u64(addr) local v = 0 for i = 7, 0, -1 do v = (v << 8) | (S.mem[addr + i] or 0) end return v end
function S.mem_hex(addr, len)          -- bridge mem.read (rivet_hook's ddl::hex_dump style)
  local out = {}
  for i = 0, len - 1 do
    local b = S.mem[addr + i]
    if b == nil then
      if i == 0 then return nil end
      break
    end
    out[#out + 1] = string.format("%02X", b)
  end
  return table.concat(out, " ")
end
function S.put_hex_id(addr, hex) S.put_u64(addr, math.tointeger(tonumber(hex:sub(1, 8), 16) << 32 | tonumber(hex:sub(9, 16), 16))) end
function S.get_hex_id(addr) return string.format("%016X", S.get_u64(addr)) end

-- ---------------------------------------------------------------------------- rivet API
local function raise(msg) S.errors[#S.errors + 1] = msg; error(msg, 2) end
rivet = {}
function rivet.log(...)
  local parts = {}
  for i = 1, select("#", ...) do parts[#parts + 1] = tostring((select(i, ...))) end
  S.logs[#S.logs + 1] = table.concat(parts, "\t")
end
print = rivet.log
function rivet.notify(text, opts)
  if not S.hud then raise("the player hud is not loaded") end
  S.notes[#S.notes + 1] = { text = text, opts = opts, frame = S.frame }
  return true
end
function rivet.on_event(class, fn)
  if S.events_unavailable then raise("events are unavailable") end
  if S.unknown_classes[class] then raise("there is no event class named " .. class) end
  S.events[class] = S.events[class] or {}
  table.insert(S.events[class], fn)
end
function rivet.on_frame(fn) S.frame_cbs[#S.frame_cbs + 1] = fn end
local VK = { F1 = 0x70, F2 = 0x71, F3 = 0x72, F4 = 0x73, F5 = 0x74, F6 = 0x75, F7 = 0x76, F8 = 0x77,
             F9 = 0x78, F10 = 0x79, F11 = 0x7A, F12 = 0x7B, CONTROL = 0x11, PAUSE = 0x13 }
for i = 0, 9 do VK["NUMPAD" .. i] = 0x60 + i end
function rivet.key(name) local k = VK[name]; if not k then raise("unknown key " .. tostring(name)) end return k end
function rivet.on_key(vk, fn) S.key_cbs[vk] = S.key_cbs[vk] or {}; table.insert(S.key_cbs[vk], fn) end
function rivet.is_key_down(vk) return S.down[vk] == true end
function rivet.time() return S.clock end
function rivet.frame() return S.frame end
function rivet.scene_ready() return S.scene end
function rivet.hero() if S.scene then return S.hero_handle end return nil end
function rivet.time_scale(...)
  if not S.has_time_scale then raise("attempt to call a nil value") end
  if select("#", ...) > 0 then raise("the simulator does not set time scales") end
  if S.loading then raise("time scale is unavailable: the pump is on the render thread") end
  return S.speed
end
function rivet.read(address, length)
  local a = addr_of(address)
  local out = {}
  for i = 0, length - 1 do
    local b = S.mem[a + i]
    if b == nil then return nil end
    out[#out + 1] = string.format("%02x", b)
  end
  return table.concat(out, " ")
end
function rivet.write(address, hex)
  local a = addr_of(address)
  local i = 0
  for x in hex:gmatch("%x%x") do
    if S.mem[a + i] == nil then raise("address is not writable") end
    S.mem[a + i] = tonumber(x, 16); i = i + 1
  end
  return true
end
function rivet.vanity_owns(bundle, actor)
  S.vanity_calls = S.vanity_calls + 1
  if not S.scene then raise("outfits can only change on the game thread, and it is not pumping (loading?)") end
  return S.vanity_owned[bundle] == true
end
-- the engine's 32-bit string hash: CRC-32 table, start value 0xEDB88320, no final xor (RVA
-- 0x1595870; matches rivet.hash for MIS_INTRO = 1000115474 in the round 14 research)
local CRC = {}
for i = 0, 255 do
  local c = i
  for _ = 1, 8 do c = (c & 1 == 1) and ((c >> 1) ~ 0xEDB88320) or (c >> 1) end
  CRC[i] = c
end
function rivet.hash(text)
  local c = 0xEDB88320
  for i = 1, #text do c = (c >> 8) ~ CRC[(c ~ text:byte(i)) & 0xFF] end
  S.hash_names[c] = text
  return c
end
function rivet.fly(cp, via)
  if S.auto_travel then
    if not S.ship_near then raise("no ship's planet menu is loaded near the hero") end
    if not S.known_cp(cp) then raise("no checkpoint " .. tostring(cp)) end
    S.travel_queue[#S.travel_queue + 1] = { planet = S.planet_of_cp(cp), at = S.frame + S.fly_frames, cp = cp }
  end
  S.travels[#S.travels + 1] = { how = "fly", to = cp }
  return "flying"
end
-- the game's missions (round 15: your game runs "system 2"; state numbers as its actions use
-- them: start needs 1, complete needs 3 and sets 4). What START and REPLAY change is SIMULATED.
S.EXE = 0x7FF6C17E0000
function S.install_missions(list)       -- list = { { name, state }, ... }
  S.missions = {}
  S.mstate = {}
  for i, m in ipairs(list) do S.missions[m[1]] = i; S.mstate[m[1]] = m[2] or 0 end
end
function S.get_mission(name) return S.mstate and S.mstate[name] end
-- a state change in the game; reported as an event only when `report` is not false
function S.set_mission(name, state, report)
  if not (S.mstate and S.mstate[name] ~= nil) then error("no mission " .. name) end
  local prev = S.mstate[name]
  S.mstate[name] = state
  if report ~= false then S.emit("MissionStateChangedEvent", { MissionName = name, MissionState = state, PreviousState = prev }) end
end
function rivet.configs(kind, limit)
  if not S.config_api then raise("the config asset manager was not found, rivet.configs is unavailable") end
  local ids = {}
  for id, c in pairs(S.configs) do
    if kind == nil or kind == "" or c.type == kind or c.type:find(kind, 1, true) then ids[#ids + 1] = id end
  end
  table.sort(ids)
  local out = {}
  for i = 1, math.min(#ids, limit or 200) do out[i] = { id = ids[i], type = S.configs[ids[i]].type } end
  return out
end
function rivet.config(id)
  local c = S.configs[id]
  if not c then raise("no loaded config " .. tostring(id)) end
  local t = { _type = c.type }
  for k, v in pairs(c.fields) do t[k] = v end
  return t
end
function rivet.config_set(id, path, value)
  local c = S.configs[id]
  if not c then raise("no loaded config " .. tostring(id)) end
  local prev = c.fields[path]
  if type(prev) ~= "number" and type(prev) ~= "boolean" then raise("the config has no field by that path") end
  c.fields[path] = value
  return prev
end
-- a new game started from the main menu (what rounds 14 and 15 logged)
function S.new_game()
  S.weapons_owned, S.gadgets_owned = {}, {}
  S.emit("ObjectiveStateChangedEvent", { MissionName = "MIS_INTRO", ObjectiveName = "OBJ_INTRO_PROLOGUE", ObjectiveState = 2 })
  S.emit("ObjectiveStateChangedEvent", { MissionName = "MIS_INTRO", ObjectiveName = "OBJ_INTRO_PARADE_START_CINE", ObjectiveState = 1 })
  S.step(1)
  S.travel("Malinon")
end
-- loading a save from the menu: only the boot defaults (rounds 13-15)
function S.load_save(planet)
  S.emit("ObjectiveStateChangedEvent", { MissionName = "MIS_INTRO", ObjectiveName = "OBJ_INTRO_PROLOGUE", ObjectiveState = 1 })
  S.emit("SaveDataAppliedEvent", {})
  S.step(1)
  S.travel(planet or "NefCity")
end
function rivet.ui_publish(slot, text) S.published[slot] = text; return true end
-- 8.0: which planet a checkpoint loads (by its name's code), as PlanetChangedEvent names it
S.CP_PLANET = { { "ZURK", "Zurkon" }, { "NEFCITY", "NefCity" }, { "SAV", "Savali" }, { "SARG", "Sargasso" },
                { "BLIZAR", "Blizar" }, { "MOL", "Torren" }, { "CORD", "Cordelion" }, { "ARD", "Ardolis" },
                { "ZORD", "Viceron" }, { "MEGA", "Malinon" }, { "MALINON", "Malinon" } }
-- the area rivet.checkpoints() reports (round 17: "Zurkons", "Sargasso (open world)", ...);
-- Torren IV's and Cordelion's are SIMULATED
S.AREA = { Zurkon = "Zurkons", NefCity = "NefCity", Savali = "Savali", Sargasso = "Sargasso (open world)",
           Blizar = "Blizar_Intact (open world)", Torren = "Molonoth", Cordelion = "Kedaro_Station",
           Ardolis = "Ardolis", Viceron = "Zordoom (open world)", Malinon = "Megalopolis (open world)" }
function S.planet_of_cp(cp)
  if cp:find("TRANSITION_TO", 1, true) then return nil end
  if cp:find("_STATION", 1, true) then return "Cordelion" end
  for _, pair in ipairs(S.CP_PLANET) do if cp:find("_" .. pair[1], 1, true) then return pair[2] end end
  return nil
end
function S.area_of_cp(cp)
  if cp:find("TRANSITION_TO", 1, true) then return "interplanetary_space" end
  local p = S.planet_of_cp(cp)
  return p and S.AREA[p] or ""
end
local function known_cp(cp)
  for _, c in ipairs(S.checkpoint_list) do if c == cp then return true end end
  return false
end
S.known_cp = known_cp
function rivet.warp(cp)
  if S.auto_travel then
    if S.warp_fails[cp] or not known_cp(cp) then raise("no checkpoint " .. tostring(cp)) end
  end
  S.warps[#S.warps + 1] = cp; S.travels[#S.travels + 1] = { how = "warp", to = cp }
  if S.auto_travel then S.travel_queue[#S.travel_queue + 1] = { planet = S.planet_of_cp(cp), at = S.frame + 1, cp = cp } end
  return true
end
function rivet.checkpoints(filter)
  local out = {}
  if not S.auto_travel then return out end      -- the 7.0 tests' level: no checkpoint listing
  for _, c in ipairs(S.checkpoint_list) do
    if not filter or filter == "" or c:find(filter, 1, true) then out[#out + 1] = { name = c, hash = 0, region = 0, area = S.area_of_cp(c) } end
  end
  return out
end
-- 8.4: rivet_hook's play_as (hero_look.cpp): raises "already playing as that hero" when the hero
-- is that one (the randomizer's check), else asks the game for the swap ("applied"). The swap
-- lands after S.swap_frames frames (SIMULATED: round 17's swaps were logged "applied"; how long
-- the game takes is not known). S.swap_refuse = "reason" makes it raise that instead.
local HEROES = { ratchet = true, clank = true, rivet = true, kit = true }
function rivet.hero_play_as(name)
  if not HEROES[name] then raise("the hero is ratchet, clank, rivet or kit") end
  if not S.scene then raise("no hero") end
  if S.swap_refuse then raise(S.swap_refuse) end
  if S.playing == name and not S.swap_pending then raise("already playing as that hero") end
  if S.swap_pending and S.swap_pending.name == name then return "applied" end
  S.heroes[#S.heroes + 1] = name
  if (S.swap_frames or 0) <= 0 then S.playing = name
  else S.swap_pending = { name = name, at = S.frame + S.swap_frames } end
  return "applied"
end
-- 8.4 the story's first step ("go to <planet>"), SIMULATED from rounds 17 and 20:
-- S.go_to[mission] = { o = objective, planet = event planet name, hero = hero }. A start (or a
-- load of the planet while the mission is active) reports the objective; it finishes only when
-- the hero is the mission's hero and the hero is on the planet: at once on a start there if
-- S.goto_on_start (Ardolis, round 20), and on any load of the planet (Savali, Viceron, round 20).
S.go_to = {}
S.goto_on_start = true
function S.goto_check(name, why)
  local g = S.go_to[name]
  if not g or S.mstate == nil or S.mstate[name] ~= 2 or g.done then return end
  if S.planet == g.planet and S.playing == g.hero then
    g.done = true
    S.emit("ObjectiveStateChangedEvent", { MissionName = name, ObjectiveName = g.o, ObjectiveState = 2 })
    if g.next then S.emit("ObjectiveStateChangedEvent", { MissionName = name, ObjectiveName = g.next, ObjectiveState = 1 }) end
  end
end
function S.parade_control()
  S.emit("ObjectiveStateChangedEvent", { MissionName = "MIS_INTRO", ObjectiveName = "OBJ_INTRO_PARADE_START_CINE", ObjectiveState = 2 })
  S.emit("ObjectiveStateChangedEvent", { MissionName = "MIS_INTRO", ObjectiveName = "OBJ_INTRO_PARADE_START", ObjectiveState = 1 })
  S.step(1)
end
function S.parade_wrench()
  S.emit("ObjectiveStateChangedEvent", { MissionName = "MIS_INTRO", ObjectiveName = "OBJ_INTRO_PARADE_PICKUP_WRENCH", ObjectiveState = 1 })
  S.emit("ObjectiveStateChangedEvent", { MissionName = "MIS_INTRO", ObjectiveName = "OBJ_INTRO_PARADE_PICKUP_WRENCH", ObjectiveState = 2 })
  S.step(1)
end
-- level script nodes (route 1): S.nodes[i] = { component, actor, uid, class, addr, outputs }
function rivet.script_nodes(filter, limit)
  local out = {}
  for _, n in ipairs(S.nodes) do
    if (not filter or n.class:find(filter, 1, true)) and #out < (limit or 64) then
      out[#out + 1] = { component = n.component, actor = n.actor, uid = n.uid, class = n.class }
    end
  end
  return out
end
local function node_by_comp(c) for _, n in ipairs(S.nodes) do if n.component == c then return n end end end
function rivet.component(actor, class)
  for _, n in ipairs(S.nodes) do
    if n.actor == actor and n.class == class then
      return { address = string.format("%X", n.addr), size = 0x80, handle = n.component }
    end
  end
  return nil
end
function rivet.script_node(component)
  local n = node_by_comp(component)
  if not n then return nil, "no such node" end
  return { component = n.component, outputs = n.outputs or {}, vars = n.vars or {} }
end
function rivet.signal(component, plug)
  local n = node_by_comp(component)
  if not n then raise("no such node") end
  if n.class == "AddToInventoryAction" and plug == "In" then
    S.give(S.get_hex_id(n.addr + 0x60), "node")
  end
  return true
end

-- ---------------------------------------------------------------------------- game model
function S.define_items(real_items)
  for _, info in pairs(real_items) do
    S.item_kind[info.id] = info.kind
    if info.type_id then S.gadget_type[info.id] = math.tointeger(info.type_id) end
    if info.kind == "currency" then
      S.currency_event = S.currency_event or {}
      S.currency_event[info.id] = info.config:find("raritanium", 1, true) and "GainRaritaniumEvent" or "GainBoltEvent"
    end
  end
end
function S.weapon_type_of(id)
  if not S.weapon_type[id] then S.weapon_type[id] = S.next_weapon_type; S.next_weapon_type = S.next_weapon_type + 1 end
  return S.weapon_type[id]
end
function S.emit(class, fields, opts)
  S.queue[#S.queue + 1] = { class = class, fields = fields or {}, sender = opts and opts.sender }
end
local function dispatch()
  local q = S.queue; S.queue = {}
  for _, ev in ipairs(q) do
    for _, fn in ipairs(S.events[ev.class] or {}) do
      local ok, err = pcall(fn, { class = ev.class, fields = ev.fields, sender = ev.sender })
      if not ok then rivet.log("[sim] event callback error", ev.class, tostring(err)) end
    end
  end
end
-- the game handling one AddToInventoryHandle message
function S.apply_give(id)
  S.give_log[#S.give_log + 1] = { id = id, frame = S.frame }
  local kind = S.item_kind[id]
  if kind == "weapon" then
    if S.weapons_owned[id] then
      if S.inv_changed_on_owned then S.emit("InventoryChangedEvent", {}) end
      return "owned"
    end
    S.weapons_owned[id] = true
    S.emit("WeaponAddedEvent", { WeaponType = S.weapon_type_of(id) })
    S.emit("InventoryChangedEvent", {})
    return "added"
  elseif kind == "gadget" then
    if S.gadgets_owned[id] then return "owned" end
    S.gadgets_owned[id] = true
    S.emit("GadgetItemAddedEvent", { ConfigTypeHash = S.gadget_type[id], InventoryHandle = 77, ItemHandle = 9000 + #S.give_log })
    S.emit("InventoryChangedEvent", {})
    return "added"
  elseif kind == "currency" then
    local n = S.last_count or 1
    S.currency[id] = (S.currency[id] or 0) + n
    S.emit(S.currency_event and S.currency_event[id] or "GainBoltEvent", { NewBolts = n })
    S.emit("InventoryChangedEvent", {})
    return "added"
  end
  return "unknown"
end
-- 5.0: the game runs VanityGiveBundleAction for one armor piece (a pocket dimension reward)
function S.armor_source(bundle)
  local mb = S.MB
  local function note(what)
    local seq = S.get_u32(mb + 0x10C) + 1
    local at = mb + 0x300 + 16 * (seq % 16)
    S.put_hex_id(at, bundle); S.put_u32(at + 12, what); S.put_u32(at + 8, seq)
    S.put_u32(mb + 0x10C, seq)
  end
  local hooked = S.mailbox and (S.dll_version or 0) >= 5 and S.get_u32(mb + 0x104) == 1
  if hooked then
    S.put_u32(mb + 0x110, S.get_u32(mb + 0x110) + 1)
    if S.get_u32(mb + 0x100) == 1 then
      for i = 0, 47 do
        if S.get_hex_id(mb + 0x180 + 8 * i) == bundle then
          S.put_u64(mb + 0x180 + 8 * i, 0)
          note(1)
          return "intercepted"
        end
      end
    end
  end
  local new = not S.vanity_owned[bundle]
  S.vanity_owned[bundle] = true
  if hooked then note(new and 2 or 3) end
  return new and "given" or "owned"
end
function S.give(id, via)
  if S.ignore_items[id] then return "ignored" end
  if S.hold_while_paused and S.speed < 0.5 then S.held[#S.held + 1] = id; return "held" end
  return S.apply_give(id)
end

-- rando_give.dll mailbox (rando_give_core.h layout)
S.MB = 0x7FEF00000000
function S.install_dll(status, version, missions_ok)
  local mb = S.MB
  S.map(mb, 0x1000)
  S.put_u64(mb, 0x31564947444E4152)       -- "RANDGIV1"
  S.put_u32(mb + 0x08, version or 5)
  S.put_u32(mb + 0x0C, status or 1)
  S.put_u64(mb + 0x30, S.EXE)
  S.put_u32(mb + 0x60, (missions_ok ~= false and (version or 5) >= 3) and 1 or 0)
  if (version or 5) >= 6 then S.put_u32(mb + 0x78, S.v6_bits) end
  S.dll_version = version or 5
  if S.dll_version >= 5 then
    S.put_u32(mb + 0x74, 1)                                  -- armor give verified
    S.put_u32(mb + 0x104, S.armor_hook and 1 or 2)           -- armor sources hooked
    S.put_u64(mb + 0x118, S.EXE + 0x52EBFE0)                 -- config manager found
    S.put_u32(mb + 0x120, 1)
  end
  S.mailbox = { pump = (status or 1) == 1 }
  S.mission_calls = {}
end
-- v4 mission request: the same checks as rg_mission() (system 2 when alt_path, as in your game)
local function dll_mission(kind, name, flag)
  if S.get_u32(S.MB + 0x60) ~= 1 then return 5 end
  if kind == 8 or kind == 12 then
    if (S.dll_version or 0) < 6 or not name then return 4 end
    if (kind == 8 and flag > 5) or (kind == 12 and flag ~= 0) then return 4 end
    if not S.alt_path then return 12, nil, nil, nil, 1 end
    if not S.missions then return 6, nil, nil, nil, 2 end
    local i = S.missions[name]
    if i == nil then return 9, nil, nil, 0xFFFFFFFF, 2 end
    local before = S.get_mission(name)
    if S.get_u32(S.MB + 0x78) & 1 == 0 then return 5, before, before, i, 2 end
    if kind == 8 then
      S.set_state_calls[#S.set_state_calls + 1] = { name = name, state = flag }
      S.set_mission(name, flag, false)
    end
    return 11, before, S.get_mission(name), i, 2
  end
  if not name or kind < 1 or kind > 5 or flag > 1 then return 4 end
  local system = S.alt_path and 2 or 1
  if not S.missions then return 6, nil, nil, nil, system end
  if system == 1 and not S.mgr_ready then return 7, nil, nil, nil, system end
  local i = S.missions[name]
  if i == nil then return 9, nil, nil, 0xFFFFFFFF, system end
  local before = S.get_mission(name)
  S.mission_calls[#S.mission_calls + 1] = { kind = kind, name = name }
  if kind == 2 then
    if system == 2 then return 12, before, before, i, system end
    if before ~= 0 then return 10, before, before, i, system end
    S.set_mission(name, 1)
  elseif kind == 3 then
    if system == 2 and (before ~= 1 or not S.can_start) then return 10, before, before, i, system end
    S.set_mission(name, S.start_effect)
    S.started_as = S.started_as or {}
    S.started_as[name] = S.playing
    local g = S.go_to[name]
    if g and S.start_effect == 2 then
      g.done = false
      S.emit("ObjectiveStateChangedEvent", { MissionName = name, ObjectiveName = g.o, ObjectiveState = 1 })
      if S.goto_on_start then S.goto_check(name, "start") end
    end
  elseif kind == 4 then
    if before ~= 3 then return 10, before, before, i, system end
    S.set_mission(name, 4)
  elseif kind == 5 then
    if system == 1 then return 12, before, before, i, system end
    if S.replay_effect then S.set_mission(name, S.replay_effect) end
  end
  return 11, before, S.get_mission(name), i, system
end
local function dll_pump()
  local mb = S.MB
  if not S.mailbox or not S.mailbox.pump then return end
  S.put_u32(mb + 0x28, S.get_u32(mb + 0x28) + 1)
  if S.get_u32(mb + 0x0C) ~= 1 then return end
  local req = S.get_u32(mb + 0x10)
  if req == S.get_u32(mb + 0x14) then return end
  local kind = S.get_u32(mb + 0x48)
  if kind == 6 or kind == 7 then
    local id = S.get_hex_id(mb + 0x18)
    if (S.dll_version or 0) < 5 then
      S.put_u32(mb + 0x24, 4)
    elseif kind == 6 then
      if not S.scene then S.put_u32(mb + 0x24, 2); S.put_u32(mb + 0x5C, 0xFFFFFFFF)
      elseif id == "0000000000000000" then S.put_u32(mb + 0x24, 4)
      else
        local new = not S.vanity_owned[id]
        S.vanity_owned[id] = true
        if new then S.vanity_gives[#S.vanity_gives + 1] = id end
        S.put_u32(mb + 0x24, 11); S.put_u32(mb + 0x5C, new and 1 or 0)
      end
    else
      local obj = S.config_objects[id]
      S.put_u32(mb + 0x24, obj and 11 or 13)
      S.put_u64(mb + 0x68, obj or 0)
    end
    S.put_u32(mb + 0x14, req)
    return
  end
  if kind == 9 or kind == 10 or kind == 11 then
    local flag, level = S.get_u32(mb + 0x50), S.get_u32(mb + 0x20)
    local bits = (S.dll_version or 0) >= 6 and S.get_u32(mb + 0x78) or 0
    local result, before, after, ret, index = 11, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF
    if (S.dll_version or 0) < 6 then result = 4
    elseif kind == 11 then
      if bits & 4 == 0 then result = 5
      elseif flag > 1 then result = 4
      else before = S.travel_flag; S.travel_flag = flag; after = flag end
    else
      if bits & 2 == 0 then result = 5
      else
        before, ret, index = S.levels, S.levels_other, S.level_current
        if kind == 9 then
          if level < 1 or level > 10 or flag > 1 then result = 4
          elseif flag == 1 then S.levels = S.levels | (1 << level) else S.levels = S.levels & ~(1 << level) end
        end
        after = S.levels
      end
    end
    S.put_u32(mb + 0x24, result)
    S.put_u32(mb + 0x54, before); S.put_u32(mb + 0x58, after); S.put_u32(mb + 0x5C, ret); S.put_u32(mb + 0x64, index)
    S.put_u64(mb + 0x68, 0); S.put_u32(mb + 0x70, 0)
    S.put_u32(mb + 0x14, req)
    return
  end
  if kind ~= 0 then
    local slot = S.get_u32(mb + 0x4C)
    local name
    if slot < 48 then
      local chars = {}
      for k = 0, 0x3F do
        local b = S.mem[mb + 0x400 + slot * 0x40 + k]
        if b == 0 then break end
        chars[#chars + 1] = string.char(b)
      end
      if #chars > 0 and #chars < 0x40 then name = table.concat(chars) end
    end
    local result, before, after, index, system = dll_mission(kind, name, S.get_u32(mb + 0x50))
    S.put_u32(mb + 0x24, result)
    S.put_u32(mb + 0x54, before or 0xFFFFFFFF)
    S.put_u32(mb + 0x58, after or 0xFFFFFFFF)
    S.put_u32(mb + 0x5C, (kind >= 3 and result == 11) and 1 or 0xFFFFFFFF)
    S.put_u32(mb + 0x64, index or 0xFFFFFFFF)
    S.put_u64(mb + 0x68, (result == 11 or result == 10 or result == 12) and (0x50000000 + (index or 0) * 0x100) or 0)
    S.put_u32(mb + 0x70, system or 0)
    S.put_u32(mb + 0x14, req)
    return
  end
  local id, count, hero, mode = S.get_hex_id(mb + 0x18), S.get_u32(mb + 0x20), S.get_u32(mb + 0x38), S.get_u32(mb + 0x44)
  local result, targets = 1, 0
  if count == 0 or count > ((S.dll_version or 4) >= 5 and 100000 or 100) or id == "0000000000000000" or mode > 64 then
    result = 4
  elseif mode == 0 then
    if hero == 0 then result = 2 else targets = 1 end
  else
    targets = S.group_sizes[mode - 1] or 0
    if targets == 0 then result = 2 end
  end
  if result == 1 then
    S.put_u32(mb + 0x3C, S.get_u32(mb + 0x3C) + 1)
    S.last_count = count
    if S.accept_modes[mode] then S.give(id, "dll") end
  end
  S.put_u32(mb + 0x24, result)
  S.put_u32(mb + 0x2C, targets)
  S.put_u32(mb + 0x40, result == 1 and mode + 1 or 0)
  S.put_u32(mb + 0x14, req)
end

-- ---------------------------------------------------------------------------- driving
function S.step(n)
  for _ = 1, n or 1 do
    S.frame = S.frame + 1
    S.clock = S.clock + 1 / 60
    if S.swap_pending and S.frame >= S.swap_pending.at then S.playing = S.swap_pending.name; S.swap_pending = nil end
    if S.speed >= 0.5 and #S.held > 0 then
      local held = S.held; S.held = {}
      for _, id in ipairs(held) do S.apply_give(id) end
    end
    dll_pump()
    dispatch()
    for _, fn in ipairs(S.frame_cbs) do
      local ok, err = pcall(fn, 1 / 60)
      if not ok then rivet.log("[sim] frame callback error", tostring(err)) end
    end
    dispatch()
    -- 8.0: a warp or a flight lands (outside the frame callbacks, like a load)
    if #S.travel_queue > 0 and not S.in_travel then
      local t = S.travel_queue[1]
      if S.frame >= t.at then
        table.remove(S.travel_queue, 1)
        S.last_cp = t.cp
        if t.planet and t.planet ~= S.planet then
          S.in_travel = true
          S.travel(t.planet)
          S.in_travel = false
        end
      end
    end
  end
end
-- 8.3: keyboard keys the randomizer maps itself (Windows virtual-key codes; rivet.key() above
-- knows only rivet_hook-style names, as the real one may)
S.KEYS = { [";"] = 0xBA, ["="] = 0xBB, [","] = 0xBC, ["-"] = 0xBD, ["."] = 0xBE, ["/"] = 0xBF, ["`"] = 0xC0,
           ["["] = 0xDB, ["\\"] = 0xDC, ["]"] = 0xDD, ["'"] = 0xDE }
for c = string.byte("A"), string.byte("Z") do S.KEYS[string.char(c)] = c end
for i = 0, 9 do S.KEYS[tostring(i)] = 0x30 + i end
function S.press(name, ctrl)
  local vk = S.KEYS[name] or rivet.key(name)
  if ctrl then S.down[VK.CONTROL] = true end
  for _, fn in ipairs(S.key_cbs[vk] or {}) do
    local ok, err = pcall(fn)
    if not ok then rivet.log("[sim] key callback error", tostring(err)) end
  end
  S.down[VK.CONTROL] = nil
  S.step(1)
end
function S.fire(class, fields) S.emit(class, fields); S.step(1) end

-- a planet load as the log shows it: old/new PlanetChangedEvent, a few loading frames (no hero,
-- no HUD, time scale unavailable), then the inventory replay and LevelLoadedEvent
function S.travel(new_name, loading_frames)
  if S.planet then S.emit("PlanetChangedEvent", { OldPlanetName = S.planet }) end
  S.scene, S.hud, S.loading = false, false, true
  S.reload_configs()
  S.step(1)
  S.emit("PlanetChangedEvent", { NewPlanetName = new_name })
  S.planet = new_name
  S.step(loading_frames or 30)
  S.scene, S.hud, S.loading = true, true, false
  S.emit("LevelLoadedEvent", {})
  local ids = {}
  for id in pairs(S.gadgets_owned) do ids[#ids + 1] = id end
  table.sort(ids)
  for _, id in ipairs(ids) do S.emit("GadgetItemAddedEvent", { ConfigTypeHash = S.gadget_type[id], InventoryHandle = 77, ItemHandle = 1 }) end
  ids = {}
  for id in pairs(S.weapons_owned) do ids[#ids + 1] = id end
  table.sort(ids)
  for _, id in ipairs(ids) do S.emit("WeaponAddedEvent", { WeaponType = S.weapon_type_of(id) }) end
  local gnames = {}
  for name in pairs(S.go_to) do gnames[#gnames + 1] = name end
  table.sort(gnames)
  for _, name in ipairs(gnames) do S.goto_check(name, "load") end
  S.step(1)
end

function S.log_has(pattern, plain)
  for _, l in ipairs(S.logs) do if l:find(pattern, 1, plain ~= false) then return true end end
  return false
end
function S.note_has(pattern)
  for _, n in ipairs(S.notes) do if n.text:find(pattern, 1, true) then return true end end
  return false
end
function S.count_logs(pattern)
  local c = 0
  for _, l in ipairs(S.logs) do if l:find(pattern, 1, true) then c = c + 1 end end
  return c
end

S.reset()
