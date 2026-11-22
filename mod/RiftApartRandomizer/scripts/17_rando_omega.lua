-- Rift Apart Randomizer dev 10.15: OMEGA VERSIONS in the game (OPTIONAL; developer kit only until it has
-- run in your game: tools/build_public_release.py HELD_BACK). Read docs/OMEGA.md first.
--
-- WHAT AN OMEGA WEAPON IS IN YOUR GAME (static research, neptuwunium/rivet's DDL dump):
--   * not an item: your dag has no Omega item config, and AddToInventoryAction only gives item configs;
--   * the bool WeaponItemPrius.Omega (hash 0x534A51FB) of the weapon you own. Its base ItemPrius holds
--     ItemConfigHash, the weapon's 64-bit item config id (the id the randomizer already knows);
--   * the game sets it only when you buy an Omega at Ms. Zurkon in Challenge Mode; no script action does.
-- So 10_rando_runtime.lua keeps the TIER (weapon / Omega) and this file sets the flag of the weapon you
-- own, the one byte the vendor's Omega purchase sets, and nothing else.
--
-- HOW, WITHOUT TRUSTING ANY OFFSET NOT SEEN IN YOUR GAME:
--   1. the hero's inventory component: rivet.component(hero, class) for O.CLASSES (the Prius type is
--      ItemInventoryPrius; which class name rivet_hook answers to has not been seen yet);
--   2. its records: an array { pointer, count, capacity } in the component's first O.HEADER bytes whose
--      elements (pointers to item objects, or inline) hold the 64-bit ids of the weapons (they do not
--      appear by chance) - the same search 12_rando_shop.lua makes for the vendor's slots;
--   3. the Omega byte: LEARNED from the game itself. When you enter a vendor, every weapon record is
--      read; when you then buy an Omega there (PurchaseWeaponEvent for a weapon you already owned), the
--      bytes of that record that went 0 -> 1 are the candidates. Only a byte that every other record
--      holds as 0 or 1 counts. The candidates of O.CONFIRMATIONS (2) Omega purchases of different weapons
--      are intersected; exactly one byte left is the offset (a Raritanium upgrade made in the same visit
--      can add a candidate, never take the real one away, so one purchase alone is not trusted). It is
--      saved (state.omega_cal, kept over a New Game). Or a developer sets omega_flag_offset in
--      04_rando_settings.lua.
--   4. setting it: the record's id is read again, the byte must read 0 or 1, 01 is written, read back.
--      Only for a weapon the game has confirmed in your inventory (09_rando_real.lua: confirmed / owned).
--   5. keeping it: after every load and every 10 s, each Omega the randomizer gave, and each one the
--      game showed as Omega, is read; a cleared flag is set again (the tier never goes down, also if a
--      weapon is sent again by the inventory restore).
-- Until 3. has happened nothing is ever written: an Omega reward stays "pending" (state.omega) and is
-- set the moment the offset is known. omega_runtime = false: never written at all.
-- NOTHING OF THIS HAS RUN IN THE GAME. Simulator only (tests/test_v1015.py).
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["17_rando_omega"] = "10.0.28"   -- the kit check (10_rando_runtime.lua)

RANDO_OMEGA = RANDO_OMEGA or {}
local O = RANDO_OMEGA
local DB = RANDO_DATA
local GEN = RANDO_GEN

local function log(...) pcall(rivet.log, "[rando]", "RANDO-OMEGA", ...) end
local function S() return RANDO and RANDO.state end
local function changed() if RANDO and RANDO.mark_changed then RANDO.mark_changed() end end
local function say(text, opts) if RANDO and RANDO.say then RANDO.say(text, opts) end end
local function cfg(k) return RANDO and RANDO.config and RANDO.config[k] end
local function hexaddr(n) return string.format("%X", n) end

O.CLASSES = { "ItemInventory", "ItemInventoryPrius", "GridInventory", "GridInventoryPrius" }
-- v0.62-DEV5: round45 (kit 10.0.24, the hero component enumeration): the live hero has NONE of the four names above;
-- its item / weapon components are GameInventoryManager (8552 bytes), HeroWeaponManagerLocal (2080),
-- GameEquipManager (872) and VanityInventoryManager (17640, armor). Rounds 27-45 all logged "inventory not found".
-- These are searched next, the whole component (O.MAX_HEADER at most), for the same proof as before: an array whose
-- elements hold the 64-bit item ids of the weapons. Nothing is written until the Omega byte is learned (step 3).
O.CLASSES_LIVE = { "GameInventoryManager", "HeroWeaponManagerLocal", "GameEquipManager" }
O.HEADER = 0x200                 -- component bytes searched for the record array
O.MAX_HEADER = 0x2200            -- v0.62-DEV5: at most this much of a live component (GameInventoryManager: 0x2168)
O.OBJ = 0x60                     -- bytes of one item object searched for its id (pointer layout)
O.SPAN = 0x180                   -- bytes of a record read from its id on (the Omega byte must be in them)
O.MAX_COUNT = 512
O.CHUNK = 0x100                  -- bytes per rivet.read
O.SLICE_SECONDS = 0.0015         -- the whole randomizer shares rivet_hook's 8 ms frame budget
-- v0.62-DEV8: round48 (DEV7 in the game): the search job was killed 19 times ("ran past the 8 ms frame budget" at the
-- walk's reads) and the walk never finished. rivet_hook (src/scripting.cpp) arms ONE 8 ms deadline per callback - the
-- randomizer's whole frame, Enemy Randomizer included - and checks it from a count hook every 10,000 instructions. A
-- job coroutine inherits that hook with its OWN counter, which carries over from frame to frame, so it is the code that
-- happens to be running when a busy frame is checked. Now: a job runs only when the frame so far has used less than
-- O.FRAME_ROOM (R.frame_t0, set by 10_rando_runtime.lua's frame callback), its slice is short, and a killed walk
-- continues where it stopped (O.wstate) instead of starting over.
O.FRAME_ROOM = 0.003
O.SETTLE = 150                   -- frames after a load before the inventory is searched
O.KEEP_EVERY = 600               -- frames between keep checks
O.REFRESH = 30                   -- frames after a weapon was added before its record is looked for
O.MAX_WRITE_FAILS = 3
O.CONFIRMATIONS = 2              -- Omega purchases of different weapons that must agree on one byte

-- the weapons that have an Omega item, by id
O.BY_ID, O.ID_OF = {}, {}
for _, key in ipairs(GEN.sorted_keys(DB.items)) do
  local it = DB.items[key]
  if it.category == "omega" then
    local w = it.weapon:sub(8)
    O.BY_ID[it.id:upper()] = w
    O.ID_OF[w] = it.id:upper()
  end
end

O.frame = 0
O.inv = nil                      -- { comp, records = { [w] = { id_at } }, visit } of this load
O.inv_why = nil
O.jobs = {}                      -- { kind, co }, run one slice per frame, in order
O.next_search = 0
O.next_keep = 0
O.snap = nil                     -- { [w] = bytes } read when you entered a vendor
O.game_omega = {}                -- weapons the game showed as Omega (flag 1) in this session
O.fails = {}

-- ---- reading (in a job: yields between reads) ------------------------------------------------
local HEXB = {}
for i = 0, 255 do
  local ch = string.char(i)
  HEXB[string.format("%02X", i)] = ch; HEXB[string.format("%02x", i)] = ch
  HEXB[string.format("%X", i // 16) .. string.format("%x", i % 16)] = ch
  HEXB[string.format("%x", i // 16) .. string.format("%X", i % 16)] = ch
end
local function bytes_of(text)
  local hex = (text or ""):gsub("[^%x]", "")
  if #hex % 2 == 1 then hex = hex:sub(1, #hex - 1) end
  if #hex == 0 then return {} end
  return { (hex:gsub("%x%x", HEXB)):byte(1, -1) }
end
local slice_t0 = 0
local function clock() return (os and os.clock and os.clock()) or 0 end
function O.pause()
  if coroutine.isyieldable() and clock() - slice_t0 >= O.SLICE_SECONDS then coroutine.yield(); slice_t0 = clock() end
end
local function read(addr, len)
  local out, at = {}, 0
  while at < len do
    local n = math.min(O.CHUNK, len - at)
    local ok, text = pcall(rivet.read, hexaddr(addr + at), n)
    if not ok or not text then break end
    local b = bytes_of(text)
    table.move(b, 1, #b, #out + 1, out)
    if #b < n then break end
    at = at + n
    O.pause()                                         -- v0.62-DEV8: time-sliced (was: one read per frame)
  end
  return out
end
O.read = read
local function hex64(b, i)
  if not b[i + 7] then return nil end
  return string.format("%02X%02X%02X%02X%02X%02X%02X%02X", b[i + 7], b[i + 6], b[i + 5], b[i + 4], b[i + 3], b[i + 2], b[i + 1], b[i])
end
local function s32(b, i)
  local v = b[i] + b[i + 1] * 0x100 + b[i + 2] * 0x10000 + b[i + 3] * 0x1000000
  if v >= 0x80000000 then v = v - 0x100000000 end
  return v
end
local function valid_ptr(p) return p and p > 0x10000 and p < 0x7FFFFFFFFFFF and p % 8 == 0 end
O.hex64, O.valid_ptr = hex64, valid_ptr
local function gcd(a, b) while b ~= 0 do a, b = b, a % b end; return a end

-- ---- 1 + 2: the inventory component and its weapon records ------------------------------------
-- If the known inventory names are absent, enumerate the live hero once. This is diagnostic
-- only: a similarly named component is never treated as the inventory until its layout is proven.
function O.component_diagnostic(hero)
  if O.component_diag_done then return end
  O.component_diag_done = true
  local ok, classes = pcall(rivet.components, hero)
  if not ok or type(classes) ~= "table" then
    log("hero component enumeration failed:", tostring(classes))
    return
  end
  table.sort(classes)
  log("hero component enumeration:", #classes, "component(s)")
  log("hero component classes:", table.concat(classes, ", "))
  local relevant = 0
  for _, class in ipairs(classes) do
    local name = tostring(class):lower()
    if name:find("item", 1, true) or name:find("invent", 1, true)
      or name:find("weapon", 1, true) or name:find("equip", 1, true)
      or name:find("loadout", 1, true) then
      relevant = relevant + 1
      local okc, c = pcall(rivet.component, hero, class)
      if okc and type(c) == "table" then
        log("hero component candidate", tostring(class), "address", tostring(c.address),
            "size", tostring(c.size), "prius", tostring(c.prius), "prius_size", tostring(c.prius_size),
            "prius_behavior", tostring(c.prius_behavior))
        local size = math.tointeger(tonumber(c.prius_size)) or 0
        if c.prius and size > 0 then
          local n = math.min(size, 0x80, 512)
          local okr, bytes = pcall(rivet.read, tostring(c.prius), n)
          if okr and bytes then log("hero component Prius bytes", tostring(class), tostring(bytes))
          else log("hero component Prius read unavailable", tostring(class), tostring(bytes)) end
        end
      else
        log("hero component candidate metadata unavailable", tostring(class), tostring(c))
      end
    end
  end
  log("hero component candidates:", relevant, "(read-only; no game writes)")
end

function O.component()
  local list = O.components()
  if list[1] then return list[1].addr, list[1].class, list[1].size end
  return nil, "the hero has no component " .. table.concat(O.CLASSES, " / ") .. " / " .. table.concat(O.CLASSES_LIVE, " / ")
end
-- v0.62-DEV6: round46 (tests/data/round46_rivet.log, DEV5 in the game): none of GameInventoryManager /
-- HeroWeaponManagerLocal / GameEquipManager holds the weapon records, and the hero's real inventories are components
-- the name list never reached: InventoryChangedEvent { Actor = hero, Component = 2129937 / 2129951 / 2129975 /
-- 2129997 } and GadgetItemAddedEvent { InventoryHandle = 2129937 } name them by HANDLE (the probe saw 47 of the
-- hero's 132 component names: rivet.log cut the line). So the hero's own component list is walked, the way
-- rivet_hook itself does it (src/game/actor.hpp, src/game/ddl.hpp, develop branch):
--   component instance +0x10 = its Actor*, +0x1C = its handle, +0x25 = flags (2 = destroyed);
--   Actor +0x68 = ComponentPointer* { ComponentInfo* type, Component* instance } (0x10 each), +0x70 = count (u16);
--   ComponentInfo +0x60 = char* name, +0x78 = int32 instance size.
-- It starts from a component rivet.component() answers (GameInventoryManager), reads only, and checks that the walk
-- finds that same component again. Its result: every component's class, handle, address and size.
O.WALK_ANCHORS = { "GameInventoryManager", "GameEquipManager", "HeroWeaponManagerLocal" }
O.COMP_HINT = { "Inventor", "Item", "Weapon", "Loadout", "Equip", "Ammo" }
O.COMP_SKIP = { "Vanity", "Anim", "StateMap", "Aim", "Damage", "Camera" }
O.inv_handles = O.inv_handles or {}   -- component handle -> why (an inventory event named it on the hero)
O.walked = nil                        -- the walk of this load: { [i] = { name, addr, size, handle } }
local function u16(b, i) return b[i] + b[i + 1] * 0x100 end
local function u32(b, i) return b[i] + b[i + 1] * 0x100 + b[i + 2] * 0x10000 + b[i + 3] * 0x1000000 end
local function cstr(b)
  local t = {}
  for i = 1, #b do
    if b[i] == 0 then break end
    if b[i] < 32 or b[i] > 126 then return nil end
    t[#t + 1] = string.char(b[i])
  end
  return #t > 0 and table.concat(t) or nil
end
function O.walk()
  if O.walked then return O.walked end
  local hero = rivet.hero and rivet.hero()
  if not hero then return nil, "no hero" end
  local anchor
  for _, cls in ipairs(O.WALK_ANCHORS) do
    local ok, c = pcall(rivet.component, hero, cls)
    if ok and type(c) == "table" and c.address then anchor = tonumber(tostring(c.address), 16); if anchor then break end end
  end
  if not anchor then return nil, "no anchor component" end
  local hexp = function(b, i) local h = O.hex64(b, i); return h and tonumber(h, 16) end
  local W = O.wstate
  if not (W and W.anchor == anchor) then
    local ab = read(anchor + 0x10, 8)
    local actor = #ab == 8 and hexp(ab, 1)
    if not O.valid_ptr(actor) then return nil, "the anchor's actor pointer is not readable" end
    local hb = read(actor + 0x68, 0x10)
    if #hb < 0x10 then return nil, "the actor's component list is not readable" end
    local list, count = hexp(hb, 1), u16(hb, 9)
    if not O.valid_ptr(list) or count < 1 or count > 1024 then return nil, string.format("component list %s, count %d", tostring(list), count) end
    local arr = read(list, count * 0x10)
    if #arr < count * 0x10 then return nil, "the actor's component list is not readable" end
    W = { anchor = anchor, actor = actor, count = count, arr = arr, k = 0, out = {}, seen_anchor = false }
    O.wstate = W
  end
  local actor, count, arr, out = W.actor, W.count, W.arr, W.out
  while W.k < count do
    local k = W.k
    local tp, inst = hexp(arr, k * 16 + 1), hexp(arr, k * 16 + 9)
    if O.valid_ptr(tp) and O.valid_ptr(inst) then
      local tb = read(tp + 0x60, 0x20)
      local np = #tb >= 0x1C and hexp(tb, 1)
      local name = nil
      if O.valid_ptr(np) then                        -- a short name at the end of readable memory: try shorter reads
        local nb = read(np, 0x50)
        if #nb == 0 then nb = read(np, 0x20) end
        if #nb == 0 then nb = read(np, 0x10) end
        name = cstr(nb)
      end
      local ib = read(inst + 0x18, 0x10)
      if name and #ib >= 0x0E then
        local destroyed = (ib[0x0E] or 0) & 2 ~= 0
        if not destroyed then
          out[#out + 1] = { name = name, addr = inst, size = s32(tb, 0x19), handle = u32(ib, 5) }
          if inst == anchor then W.seen_anchor = true end
        end
      end
    end
    W.k = k + 1                                       -- v0.62-DEV8: a killed job continues from here
    O.pause()
  end
  O.wstate = nil
  if not W.seen_anchor then return nil, "the walk did not find its own anchor again - layout differs; nothing used" end
  O.walked = out
  if not O.walk_logged then
    O.walk_logged = true
    log(string.format("hero component list walked: %d components (actor %X)", #out, actor))
    local line = {}
    for i, c in ipairs(out) do
      line[#line + 1] = c.name
      if #line == 12 or i == #out then log("hero components:", table.concat(line, ", ")); line = {} end
    end
  end
  return out
end
-- v0.62-DEV5: every inventory candidate of the live hero, in order: { addr, class, size }
-- v0.62-DEV6: first the components an inventory event named (by handle), then every walked component whose class
-- name looks like an inventory, then the DEV5 names
function O.components()
  local out = {}
  local hero = rivet.hero and rivet.hero()
  if not hero then return out end
  local have = {}
  local walked, why = O.walk()
  if walked then
    local function take(c, tag)
      if have[c.addr] then return end
      have[c.addr] = true
      local size = math.max(O.HEADER, math.min(c.size or 0, O.MAX_HEADER))
      out[#out + 1] = { addr = c.addr, class = c.name .. "#" .. c.handle, size = size }
      if not (O.cand_logged or {})[c.addr] then
        O.cand_logged = O.cand_logged or {}
        O.cand_logged[c.addr] = true
        log(string.format("inventory candidate %s handle=%d size=%d at %X (%s)", c.name, c.handle, c.size or -1, c.addr, tag))
      end
    end
    for _, c in ipairs(walked) do if O.inv_handles[c.handle] then take(c, O.inv_handles[c.handle]) end end
    for _, c in ipairs(walked) do
      local hit, skip = false, false
      for _, h in ipairs(O.COMP_HINT) do if c.name:find(h, 1, true) then hit = true end end
      for _, k in ipairs(O.COMP_SKIP) do if c.name:find(k, 1, true) then skip = true end end
      if hit and not skip then take(c, "its class name") end
    end
  elseif why and why ~= O.walk_why then
    O.walk_why = why
    log("hero component list not walked:", why)
  end
  local function add(cls, header)
    local ok, c = pcall(rivet.component, hero, cls)
    if ok and type(c) == "table" and c.address then
      local a = tonumber(tostring(c.address), 16)
      local size = math.tointeger(tonumber(c.size or 0)) or 0
      if a then out[#out + 1] = { addr = a, class = cls, size = header or math.max(O.HEADER, math.min(size, O.MAX_HEADER)) } end
    end
  end
  if #out == 0 then
    for _, cls in ipairs(O.CLASSES) do add(cls, O.HEADER) end
    for _, cls in ipairs(O.CLASSES_LIVE) do add(cls) end
  end
  if #out == 0 then O.component_diagnostic(hero) end
  return out
end
-- an array of pointers to item objects: the id's offset in the objects is the one most agree on
local function records_pointers(ptr, count)
  local raw = read(ptr, count * 8)
  if #raw < count * 8 then return nil end
  local hits, votes = {}, {}
  for e = 0, count - 1 do
    local p = tonumber(hex64(raw, e * 8 + 1), 16)
    if p and p ~= 0 then
      if not valid_ptr(p) then return nil end
      local b = read(p, O.OBJ)
      local found = false
      for i = 1, #b - 7, 8 do
        local w = O.BY_ID[hex64(b, i) or ""]
        if w then hits[#hits + 1] = { w = w, at = p + i - 1, off = i - 1 }; votes[i - 1] = (votes[i - 1] or 0) + 1; found = true end
      end
      -- v0.62-DEV6: an item object whose id is in the prius data it points to (+0x08, like every component)
      local q = (not found) and #b >= 16 and tonumber(hex64(b, 9) or "0", 16) or nil
      if q and valid_ptr(q) then
        local b2 = read(q, 0x40)
        for i = 1, #b2 - 7, 8 do
          local w = O.BY_ID[hex64(b2, i) or ""]
          if w then hits[#hits + 1] = { w = w, at = q + i - 1, off = 0x10000 + i - 1 }; votes[0x10000 + i - 1] = (votes[0x10000 + i - 1] or 0) + 1 end
        end
      end
    end
  end
  local off, nv = nil, 0
  for o, v in pairs(votes) do if v > nv or (v == nv and off and o < off) then off, nv = o, v end end
  if not off then return nil end
  local recs, n = {}, 0
  for _, h in ipairs(hits) do
    if h.off == off and not recs[h.w] then recs[h.w] = { id_at = h.at }; n = n + 1 end
  end
  return recs, n
end
-- inline elements: the ids' spacing is the element size
local function records_inline(ptr, count)
  local data = read(ptr, math.min(0x4000, count * 0x200))
  local pos = {}
  for i = 1, #data - 7, 8 do
    local w = O.BY_ID[hex64(data, i) or ""]
    if w then pos[#pos + 1] = { at = i - 1, w = w } end
    if i % 256 == 1 then O.pause() end
  end
  if #pos == 0 then return nil end
  local g = 0
  for k = 2, #pos do g = gcd(g, pos[k].at - pos[1].at) end
  if #pos >= 2 and (g < 0x20 or g > 0x400) then return nil end
  local recs, n = {}, 0
  for _, m in ipairs(pos) do
    if (#pos == 1 or m.at % g == pos[1].at % g) and not recs[m.w] then recs[m.w] = { id_at = ptr + m.at }; n = n + 1 end
  end
  return recs, n
end
function O.find_records()
  local list = O.components()
  if #list == 0 then
    return nil, "the hero has no component " .. table.concat(O.CLASSES, " / ") .. " / " .. table.concat(O.CLASSES_LIVE, " / ")
  end
  local best, why = nil, nil
  for _, c in ipairs(list) do
    local r, w = O.find_records_in(c.addr, c.class, c.size)
    if r and (not best or r.count > best.count) then best = r end
    if not r then why = (why and (why .. "; ") or "") .. tostring(w) end
  end
  if best then return best end
  return nil, why
end
function O.find_records_in(comp, cls, header)
  header = header or O.HEADER
  local head = read(comp, header)
  if #head < 0x40 then return nil, "inventory component not readable (" .. cls .. ")" end
  local best, bn = nil, 0
  for o = 1, #head - 15, 8 do
    if o % 64 == 1 then O.pause() end                -- v0.62-DEV6: round46 overran the budget here 60+ times
    local ptr = tonumber(hex64(head, o) or "0", 16)
    local count, cap = s32(head, o + 8), s32(head, o + 12)
    if valid_ptr(ptr) and count >= 1 and count <= O.MAX_COUNT and cap >= count and cap <= 8192 then
      local recs, n = records_pointers(ptr, count)
      if not recs then recs, n = records_inline(ptr, count) end
      if recs and n > bn then best, bn = { comp = comp, class = cls, array_at = o - 1, records = recs, count = n }, n end
    end
  end
  if not best then
    O.dumped = O.dumped or {}
    if not O.dumped[cls] then
      O.dumped[cls] = true
      local hx = {}
      for i = 1, math.min(#head, 0x100) do hx[#hx + 1] = string.format("%02X", head[i]) end
      log(string.format("no weapon record in the first 0x%X bytes of %s at %X; its first bytes:", header, cls, comp), table.concat(hx, " "))
    end
    return nil, "no array of weapon records in " .. cls
  end
  return best
end

-- v0.62-DEV5: once per session, every weapon record's first O.SPAN bytes (from its id on) - the evidence a developer
-- needs to find the Omega byte from a save that already owns an Omega (compare its record with the others)
function O.dump_records(inv)
  if O.records_dumped then return end
  O.records_dumped = true
  for _, w in ipairs(GEN.sorted_keys(inv.records)) do
    local b = read(inv.records[w].id_at, O.SPAN)
    local hx = {}
    for i = 1, #b do hx[#hx + 1] = string.format("%02X", b[i]) end
    log("record", w, table.concat(hx, " "))
  end
end

-- ---- 3: the Omega byte ------------------------------------------------------------------------
function O.offset()
  local manual = cfg("omega_flag_offset")
  if type(manual) == "number" and manual >= 8 and manual < O.SPAN and math.type(manual) == "integer" then return manual, "omega_flag_offset" end
  local s = S()
  local c = s and s.omega_cal
  if type(c) == "table" and type(c.off) == "number" then return c.off, "learned from " .. tostring(c.from) end
  return nil
end
-- the bytes of every record, from its id on (a job)
local function snapshot(inv)
  local snap = {}
  for _, w in ipairs(GEN.sorted_keys(inv.records)) do snap[w] = read(inv.records[w].id_at, O.SPAN) end
  return snap
end
function O.on_vendor_entered()
  O.snap = nil
  O.start_job("snapshot", function()
    local inv = O.inv
    if not inv then
      local why
      inv, why = O.find_records()
      if not inv then log("vendor: no weapon records -", why); return end
      O.inv = inv
    end
    local snap = snapshot(inv)
    O.snap = { inv = inv, bytes = snap }
    log("vendor: " .. #GEN.sorted_keys(snap) .. " weapon record(s) read")
  end)
end
-- a purchase of a weapon already owned when you entered: an Omega (learn the byte from it)
function O.on_purchase(weapon_name, known_w)
  local item = (not known_w) and RANDO_REAL and RANDO_REAL.weapon_item and RANDO_REAL.weapon_item(weapon_name)
  local w = known_w or (item and item:sub(8))
  local snap = O.snap
  if not (w and snap and snap.bytes[w]) then return end
  O.start_job("learn", function()
    local before = snap.bytes[w]
    local after = read(snap.inv.records[w].id_at, O.SPAN)
    if hex64(after, 1) ~= O.ID_OF[w] then log("learn: the record of", w, "moved - nothing learned"); return end
    local cands = {}
    for i = 9, math.min(#before, #after) do
      if before[i] == 0 and after[i] == 1 then
        -- a flag: 0 or 1 in every other record, and 0 in at least one (a byte every weapon holds as 1,
        -- like a count, is not a flag that a purchase turned on)
        local ok, zero, others = true, false, 0
        for other, b in pairs(snap.bytes) do
          if other ~= w and b[i] ~= nil then
            others = others + 1
            if b[i] ~= 0 and b[i] ~= 1 then ok = false; break end
            if b[i] == 0 then zero = true end
          end
        end
        if ok and (zero or others == 0) then cands[#cands + 1] = i - 1 end
      end
    end
    snap.bytes[w] = after                              -- a second purchase in the same visit compares to this
    O.learn(w, cands)
    O.next_resnap = O.frame + O.OMEGA_WAIT
  end)
end
-- v0.62-DEV6: round46 (DEV5 in the game): an Omega purchase at Ms. Zurkon sends ONLY VendorPurchaseEvent
-- { WeaponName = "MagShield" } (and "Warmonger") - no PurchaseWeaponEvent, no WeaponAddedEvent - and
-- EnteredVendorEvent never came in 20 purchases. So: the records are read (O.snap) as soon as they are found and
-- again after every check and purchase, and a VendorPurchaseEvent for a weapon that is already in that read and
-- brings no PurchaseWeaponEvent within O.OMEGA_WAIT frames is an Omega purchase.
O.OMEGA_WAIT = 20
O.VENDOR_ALIAS = { GOONER = "sheepinator", MRZURKON = "zurkon" }  -- round46 pairs VendorPurchase -> PurchaseWeapon
O.vendor_pending = {}
local function norm(t) return (tostring(t or "")):upper():gsub("[^%w]", "") end
O.BY_VENDOR = {}
for w in pairs(O.ID_OF) do
  local it = DB.items["weapon:" .. w]
  local base = it and it.config and it.config:match("wpn_(.-)_item%.config")
  if base then O.BY_VENDOR[norm(base)] = w end
  O.BY_VENDOR[norm(w)] = O.BY_VENDOR[norm(w)] or w
end
function O.weapon_of_vendor_name(name)
  local n = norm(name)
  local alias = O.VENDOR_ALIAS[n]
  if alias and O.ID_OF[alias] then return alias end
  return O.BY_VENDOR[n]
end
function O.on_vendor_purchase(name)
  local w = O.weapon_of_vendor_name(name)
  if not w then return end
  O.vendor_pending[w] = { at = O.frame, name = name }
end
function O.on_weapon_purchase(weapon_name)
  -- a weapon bought (not an Omega): forget the pending vendor purchase of it, read the records again later
  local item = RANDO_REAL and RANDO_REAL.weapon_item and RANDO_REAL.weapon_item(weapon_name)
  local w = item and item:sub(8)
  if w then O.vendor_pending[w] = nil end
  for k, v in pairs(O.vendor_pending) do if O.frame - v.at <= O.OMEGA_WAIT then O.vendor_pending[k] = nil end end
end
function O.vendor_tick()
  for w, v in pairs(O.vendor_pending) do
    if O.frame - v.at >= O.OMEGA_WAIT then
      O.vendor_pending[w] = nil
      if O.snap and O.snap.bytes[w] then
        log("Omega purchase seen: " .. tostring(v.name) .. " (" .. w .. ") - its record is compared with the read before it")
        O.on_purchase(nil, w)
      else
        log("a purchase of " .. tostring(v.name) .. " without a weapon record read before it - nothing learned" ..
            (O.inv and "" or " (the weapon records are not found yet)"))
      end
    end
  end
end
function O.take_snapshot(why)
  if not O.inv then return end
  O.start_job("snapshot", function()
    if not O.inv then return end
    O.snap = { inv = O.inv, bytes = snapshot(O.inv), why = why }
  end)
end

function O.learn(w, cands)
  local s = S(); if not s then return end
  local prev = type(s.omega_cal) == "table" and s.omega_cal or nil
  if prev and prev.off then return end
  if #cands == 0 then log("purchase of", w, "changed no byte from 0 to 1 - not an Omega purchase; nothing learned"); return end
  local keep, seen = cands, {}
  if prev and type(prev.cands) == "table" and type(prev.seen) == "table" then
    if prev.seen[w] then log("a second Omega purchase of", w, "- only other weapons confirm"); return end
    local was = {}
    for _, c in ipairs(prev.cands) do was[c] = true end
    keep = {}
    for _, c in ipairs(cands) do if was[c] then keep[#keep + 1] = c end end
    if #keep == 0 then
      log("Omega purchase of", w, ": no byte in common with the earlier purchase(s) - starting over from this one")
      keep = cands
    else
      for k in pairs(prev.seen) do seen[k] = true end
    end
  end
  seen[w] = true
  local n = #GEN.sorted_keys(seen)
  local hx = {}
  for _, c in ipairs(keep) do hx[#hx + 1] = string.format("+0x%X", c) end
  for k in pairs(seen) do O.game_omega[k] = true end
  if #keep == 1 and n >= O.CONFIRMATIONS then
    s.omega_cal = { off = keep[1], from = table.concat(GEN.sorted_keys(seen), "+"), at = math.floor((rivet.time and rivet.time()) or 0) }
    changed()
    log(string.format("LEARNED: the Omega flag is the byte at +0x%X from a weapon record's item id (Omega purchases of %s)", keep[1], s.omega_cal.from))
    say("Randomizer: Omega versions can be given now (learned from your Omega purchases)", { type = "corner", duration = 6 })
    O.next_keep = 0
  else
    s.omega_cal = { cands = keep, seen = seen }
    changed()
    log(string.format("Omega purchase %d of %d (%s): candidate byte(s) %s", n, O.CONFIRMATIONS, w, table.concat(hx, " ")) ..
        (#keep > 1 and " - another Omega purchase narrows it down" or " - another weapon's Omega purchase confirms it"))
  end
end

-- ---- 4 + 5: setting and keeping ---------------------------------------------------------------
-- the game has the weapon: confirmed or recognised as owned (09_rando_real.lua), or it refused a give of
-- it ("failed": you probably have it) while its record is in the inventory
local function delivered(w)
  local s = S()
  local r = s and s.real and s.real["weapon:" .. w]
  return r and (r.status == "confirmed" or r.status == "owned" or r.status == "failed")
end
-- one weapon's flag (in a job). Returns "already", "set", or nil and why. only_read: never writes
function O.set_flag(w, off, only_read)
  local rec = O.inv and O.inv.records[w]
  if not rec then return nil, "no record" end
  local b = read(rec.id_at, off + 1)
  if hex64(b, 1) ~= O.ID_OF[w] then return nil, "the record moved" end
  local v = b[off + 1]
  if v == 1 then return "already" end
  if v ~= 0 then return nil, string.format("byte +0x%X holds %s, not a flag", off, tostring(v)) end
  if only_read then return nil, "waits for the weapon" end
  local ok, err = pcall(rivet.write, hexaddr(rec.id_at + off), "01")
  if not ok then return nil, "write refused: " .. tostring(err) end
  local back = read(rec.id_at + off, 1)
  if back[1] ~= 1 then return nil, "read back " .. tostring(back[1]) end
  return "set"
end
function O.pass(why)
  local s = S()
  local off, how = O.offset()
  if not (s and off and O.inv and cfg("omega_runtime") ~= false) then return end
  -- the randomizer's Omegas: set the pending ones, keep the applied ones
  for _, w in ipairs(GEN.sorted_keys(s.omega or {})) do
    local o = s.omega[w]
    if type(o) == "table" and O.inv.records[w] and (O.fails[w] or 0) < O.MAX_WRITE_FAILS then
      local r, err = O.set_flag(w, off, not delivered(w))
      local name = RANDO.item_name("omega:" .. w)
      if r == "set" and o.status == "applied" then
        log("kept " .. name .. " - its flag had been cleared (" .. why .. "), set again")
        say("Randomizer: " .. name .. " kept (the game had cleared it)")
      elseif r == "set" or r == "already" then
        if o.status ~= "applied" then
          RANDO.omega_applied(w, r == "set" and ("flag set, " .. how) or "the game already had it")
          say("Randomizer: " .. name .. " is yours", { type = "pickup", duration = 5 })
        end
      elseif r == nil and err ~= "waits for the weapon" then
        O.fails[w] = (O.fails[w] or 0) + 1
        log("could not set " .. name .. " - " .. tostring(err) .. " (try " .. O.fails[w] .. ")")
      end
      if r then O.game_omega[w] = true end
    end
  end
  -- Omegas the game itself showed (bought, or from a New Game+ save): never lost by a randomizer send
  for _, w in ipairs(GEN.sorted_keys(O.game_omega)) do
    if not (s.omega and s.omega[w]) and O.inv.records[w] and (O.fails[w] or 0) < O.MAX_WRITE_FAILS then
      local r, err = O.set_flag(w, off)
      if r == "set" then log("kept the game's Omega " .. w .. " - its flag had been cleared (" .. why .. "), set again")
      elseif r == nil then O.fails[w] = (O.fails[w] or 0) + 1; log("could not keep " .. w .. " - " .. tostring(err)) end
    end
  end
end
-- which weapons the game holds as Omega right now (once per load, when the offset is known)
function O.read_game_omega()
  local off = O.offset()
  if not (off and O.inv) then return end
  for _, w in ipairs(GEN.sorted_keys(O.inv.records)) do
    local b = read(O.inv.records[w].id_at, off + 1)
    if hex64(b, 1) == O.ID_OF[w] and b[off + 1] == 1 and not O.game_omega[w] then
      O.game_omega[w] = true
      log("the game holds", w, "as Omega")
    end
  end
end

-- ---- jobs -------------------------------------------------------------------------------------
function O.start_job(kind, fn)
  for _, j in ipairs(O.jobs) do if j.kind == kind and (kind == "search" or kind == "keep" or kind == "snapshot") then return false end end
  O.jobs[#O.jobs + 1] = { kind = kind, co = coroutine.create(fn) }
  return true
end
local function run_job()
  local j = O.jobs[1]
  if not j then return end
  slice_t0 = clock()
  local ok, err = coroutine.resume(j.co)
  if coroutine.status(j.co) == "dead" then
    if O.jobs[1] == j then table.remove(O.jobs, 1) end
    if not ok then
      log("RANDO-ERROR", j.kind .. ":", tostring(err))
      -- v0.62-DEV8: a search killed by the frame budget is taken up again soon (the walk continues from O.wstate)
      if j.kind == "search" then O.next_search = math.min(O.next_search, O.frame + 30) end
    end
  end
end
O.run_job = run_job

-- 10_rando_runtime.lua asks after an Omega reward. Returns "applied" | "pending" | "learning" | "off"
function O.request(w)
  if cfg("omega_runtime") == false then return "off" end
  if not O.offset() then
    if not O.told then
      O.told = true
      log("an Omega reward waits: the Omega flag's place is not known yet - buy one Omega at Ms. Zurkon (Challenge Mode)" ..
          " and it is learned, or set omega_flag_offset (docs/OMEGA.md)")
    end
    return "learning"
  end
  O.next_keep = 0                                   -- the next frame looks
  return "pending"
end

function O.forget(why)
  O.inv, O.snap, O.jobs = nil, nil, {}
  O.walked, O.inv_handles, O.cand_logged, O.wstate = nil, {}, nil, nil   -- v0.62-DEV6: handles change with every load
  O.next_search = O.frame + O.SETTLE
  O.inv_why = why
end
function O.new_game()
  O.forget("a new game")
  O.game_omega, O.fails = {}, {}
end
function O.after_restore() O.next_keep = 0 end

function O.tick(frames, ready)
  O.frame = O.frame + 1
  if not ready or cfg("omega_runtime") == false then return end    -- (nothing is read while loading)
  if RANDO and RANDO.frame_t0 and clock() - RANDO.frame_t0 > O.FRAME_ROOM then return end   -- v0.62-DEV8: a busy frame
  if O.jobs[1] then run_job(); return end
  local s = S()
  if not (s and RANDO_SEED) then return end
  if O.inv and O.refresh and O.frame >= O.next_search then
    O.refresh = nil
    O.inv = nil                                     -- searched again below (same load: the snapshot stays)
    O.next_search = O.frame
  end
  if not O.inv then
    if O.frame < O.next_search then return end
    O.next_search = O.frame + O.KEEP_EVERY
    O.start_job("search", function()
      local inv, why = O.find_records()
      if inv then
        O.inv = inv
        log(string.format("inventory: %d weapon record(s) in %s (array at +0x%X)", inv.count, inv.class, inv.array_at))
        O.dump_records(inv)
        O.snap = { inv = inv, bytes = snapshot(inv), why = "found" }   -- v0.62-DEV6: the read an Omega purchase is compared with
        O.read_game_omega()
        O.pass("after a load")
        O.next_keep = O.frame + O.KEEP_EVERY
      elseif why ~= O.inv_why then
        O.inv_why = why
        log("inventory not found:", why)
      end
    end)
    return
  end
  if O.frame >= O.next_keep and O.offset() then
    O.next_keep = O.frame + O.KEEP_EVERY
    O.start_job("keep", function() O.pass("check") end)
  end
  -- v0.62-DEV6: Omega purchases (VendorPurchaseEvent alone) and a fresh read of the records for the next one
  if next(O.vendor_pending) then O.vendor_tick(); return end
  if not O.offset() and (O.frame >= (O.next_resnap or 0)) then
    O.next_resnap = O.frame + O.KEEP_EVERY // 2
    O.take_snapshot("periodic")
  end
end

function O.status_text()
  local s = S()
  if not s then return nil end
  local n, done = 0, 0
  for _, o in pairs(s.omega or {}) do n = n + 1; if type(o) == "table" and o.status == "applied" then done = done + 1 end end
  if n == 0 and not O.offset() then return nil end
  return string.format("Omega %d/%d%s", done, n, O.offset() and "" or " (flag not learned)")
end

if RANDO and RANDO.subscribe then
  local function on(class, fn)
    RANDO.subscribe(class, function(ev)
      local ok, err = pcall(fn, ev.fields or {})
      if not ok then log("RANDO-ERROR", class, tostring(err)) end
    end)
  end
  on("EnteredVendorEvent", function() O.on_vendor_entered() end)
  -- v0.62-DEV6: leaving the vendor no longer drops the read (EnteredVendorEvent never came in round46)
  on("PurchaseWeaponEvent", function(f) O.on_weapon_purchase(f.WeaponName); O.on_purchase(f.WeaponName) end)
  on("VendorPurchaseEvent", function(f) O.on_vendor_purchase(f.WeaponName) end)
  -- v0.62-DEV6: the hero's inventories by handle (round46: Component 2129937 ... on the hero, never by name)
  on("GadgetItemAddedEvent", function(f)
    local h = math.tointeger(tonumber(f.InventoryHandle))
    if h and not O.inv_handles[h] then O.inv_handles[h] = "GadgetItemAddedEvent"; O.walked = nil end
  end)
  on("PlanetChangedEvent", function() O.forget("a planet load") end)
  on("LevelLoadedEvent", function() O.forget("a level load") end)
  -- a weapon added: its record is new, so the records are searched again (soon, not in the event)
  on("WeaponAddedEvent", function() O.refresh = true; O.next_search = math.min(O.next_search, O.frame + O.REFRESH) end)
  -- the inventory changed (a give of a weapon you own reports only this): look at the flags soon
  on("InventoryChangedEvent", function(f)
    O.next_keep = math.min(O.next_keep, O.frame + O.REFRESH)
    local hero = rivet.hero and rivet.hero()
    local h = math.tointeger(tonumber(f.Component))
    if h and hero and math.tointeger(tonumber(f.Actor)) == hero and not O.inv_handles[h] then
      O.inv_handles[h] = "InventoryChangedEvent"
      if not O.inv then O.next_search = math.min(O.next_search, O.frame + O.REFRESH) end
    end
  end)
  log("loaded (Omega flag " .. (O.offset() and "known" or "not learned yet") .. ")")
else
  log("RANDO-ERROR 10_rando_runtime.lua is missing: Omega versions stay records only")
end
