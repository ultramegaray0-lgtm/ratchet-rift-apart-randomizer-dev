-- DEVELOPER TOOL - not part of a release. SPAWN PROBE v1 (dev 10.20): READ-ONLY evidence for the Enemy /
-- Boss / Chaos Randomizers. It never writes game memory, never fires a node, never changes a setting.
--
-- WHY IT EXISTS. Your dev 10.19 rivet.log (2026-11-17, kept as tests/data/round30_rivet.log) proved:
--   * a SpawnerScriptAction node's u32 at +0x60 IS the handle of the "Spawner" component on the same
--     actor (6 of 6 dumped pairs: node +0x60 == Spawner +0x1C; both +0x10 point at the same Actor), and a
--     SpawnerStoppedEvent's SpawnerComponentHandle is that same handle (0x214EBC, Zurkon);
--   * neither the node nor its Spawner component keeps a Prius: ddlPriusData (+0x08) is 0 in both, and the
--     306 bytes of the Spawner that reached the log hold no pointer except the vtable and the actor.
-- So WHERE the encounter's Templates live at runtime is still unknown; every census since 10.12 read 0
-- nodes. Guessing more offsets would repeat 10.12-10.19. This file collects the missing facts in ONE play
-- session, automatically:
--   1. INDEX (after each level / planet / checkpoint load): every SpawnerScriptAction node, its Spawner
--      component (only if its handle equals the node's +0x60), a byte snapshot of that component, and a
--      histogram of the offsets where a Spawner holds a readable pointer.
--   2. SPAWNS (the first P.SPAWN_LOG of a level): what the game actually created - the spawned actor's
--      handle, uid, name, actor asset (id and name), Template flag and component classes - and the same
--      for SpawnFactory.
--   3. CHANGES: after spawns, every indexed Spawner is read again; the ones whose bytes changed are the
--      encounters that ran. Their changed offsets are logged, and the first ones are probed deeply.
--   4. DEEP PROBE of a node: the ComponentInfo of every component on its actor (class, size, Prius type,
--      Prius size, Prius behaviour), the node and Spawner bytes (whole, in short lines), the node's plug
--      block, every block one pointer away, and a UID SEARCH: each 8-byte value in those blocks is asked
--      rivet.find_uid; a hit names the loaded actor (name, Template flag, classes). A Templates list is a
--      list of template-actor uids, so a hit that is a template bot (or matches a spawned bot's actor
--      asset) shows exactly where the list is.
-- Output lines start with "RANDO-SPAWNPROBE". Remove this file to turn it off; the randomizer does not need it.
RANDO_FILES = RANDO_FILES or {}; RANDO_FILES["dev(spawnprobe)"] = "10.0.17"   -- the kit check (10_rando_runtime.lua)
RANDO_SPAWNPROBE = RANDO_SPAWNPROBE or {}
local P = RANDO_SPAWNPROBE
P.version = 1
P.frame = P.frame or 0

P.NODE_CLASS = "SpawnerScriptAction"
P.SPAWNER_CLASS = "Spawner"
P.HANDLE_AT = 0x60             -- node +0x60 = its Spawner component's handle (proved by the 10.19 log)
P.CHUNK = 96                   -- bytes per dump line (rivet.log keeps 1024 characters of a line)
P.READ_MAX = 512               -- rivet.read's limit per call (rivet_hook MAX_READ_BYTES)
P.INDEX_DELAY = 120            -- frames after a load before the level is indexed
P.INDEX_LIMIT = 512            -- nodes indexed per level
P.INDEX_PROBES = 2             -- deep probes right after an index (nodes whose Spawner holds a pointer first)
P.CHANGE_PROBES = 3            -- deep probes of Spawners that changed while playing, per level
P.SESSION_PROBES = { index = 8, change = 20 }   -- deep probes per session: after an index / of a Spawner that ran
P.SPAWN_LOG = 6                -- spawns per level whose actor is described
P.SWEEP_GAP = 240              -- frames between two re-reads of every indexed Spawner
P.SWEEPS_PER_LEVEL = 4
P.UID_CALLS = 240              -- rivet.find_uid calls per deep probe
P.SLICE = 0.002                -- seconds of work per frame (rivet_hook stops a script after 8 ms)

P.lvl = P.lvl or nil
P.job = nil
P.queue = P.queue or {}
P.spent = P.spent or { index = 0, change = 0 }
P.t0 = 0

local function log(...) pcall(rivet.log, "[rando]", "RANDO-SPAWNPROBE", ...) end
P.log = log
local function clock() return (os and os.clock and os.clock()) or 0 end

-- ---- bytes -----------------------------------------------------------------------------------
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
local function s32(b, i) local v = u32(b, i); if v and v >= 0x80000000 then v = v - 0x100000000 end; return v end
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
P.bytes_of, P.u32, P.hex64, P.ptr64, P.valid_ptr = bytes_of, u32, hex64, ptr64, valid_ptr

-- a rivet call; nil on failure. Inside the job a stop by the frame budget is raised again, so that
-- guarded() can retry the step on the next frame instead of taking the failure for an answer.
local function rcall(fn, ...)
  local ok, a, b = pcall(fn, ...)
  if ok then return a, b end
  if coroutine.isyieldable() and tostring(a):find("budget", 1, true) then error(a, 0) end
  return nil
end
P.rcall = rcall

-- rivet.read in pieces of at most P.READ_MAX bytes; nil when the first piece is unreadable
local function read(addr, len)
  if not valid_ptr(addr) and not (addr and addr > 0x10000) then return nil end
  local out = {}
  local at = 0
  while at < len do
    local n = math.min(P.READ_MAX, len - at)
    local text = rcall(rivet.read, string.format("%X", addr + at), n)
    if not text then break end
    local b = bytes_of(text)
    for _, v in ipairs(b) do out[#out + 1] = v end
    if #b < n then break end
    at = at + n
  end
  if #out == 0 then return nil end
  return out
end
P.read = read

local function hexrange(b, from, n)
  local t = {}
  for k = from, math.min(#b, from + n - 1) do t[#t + 1] = string.format("%02x", b[k]) end
  return table.concat(t, " ")
end
-- a block in lines of P.CHUNK bytes ("<head> +0x060: aa bb ...")
function P.dump(head, b)
  if not b then log(head .. ": unreadable"); return end
  for from = 1, #b, P.CHUNK do log(string.format("%s +0x%03X: %s", head, from - 1, hexrange(b, from, P.CHUNK))) end
end

-- a C string (printable ASCII only), or nil. Read 8 bytes at a time: a string can end just before
-- unreadable memory, and rivet.read answers nil for a block that runs into it.
local function cstr(p)
  if not (p and p > 0x10000 and p < 0x7FFFFFFFFFFF) then return nil end
  local t = {}
  for at = 0, 88, 8 do
    local b = read(p + at, 8)
    if not b then break end
    for _, c in ipairs(b) do
      if c == 0 then return #t > 0 and table.concat(t) or nil end
      if c < 32 or c > 126 then return nil end
      t[#t + 1] = string.char(c)
    end
  end
  return #t > 0 and table.concat(t) or nil
end
P.cstr = cstr

-- ---- engine structures (rivet_hook src/game/actor.hpp, ddl.hpp, script.hpp @ develop 0bdb394) --------
-- Actor (0xC0): flags +0x10, actorAsset +0x30, components +0x68, componentCount u16 +0x70, name +0xB0
-- Asset: assetId +0x08, name +0x10, nameOffset u16 +0x18
-- ComponentPointer { ComponentInfo *type; Component *instance } (0x10)
-- ComponentInfo: prius_info.size +0x58, name +0x60, size i32 +0x78, id u32 +0x7C, prius (DDLTypeInfo*)
--   +0xC8, parent_count u8 +0xE6, prius_behavior u8 +0xE7 (0 ReadOnly, 1 Local, 2 ReadWrite)
-- Component: vtable +0, ddlPriusData +0x08, actor +0x10, handle +0x1C
-- ScriptAction: instanceUid +0x48, graphUid +0x50, plugs +0x58 (ScriptPlugs 0x28: zone +0x1C, owner +0x24)
P.TEMPLATE_FLAG = 4
P.BEHAVIOR = { [0] = "ReadOnly", [1] = "Local", [2] = "ReadWrite" }

function P.actor_info(actor)
  local a = read(actor, 0xC0)
  if not a or #a < 0xC0 then return nil end
  local info = { flags = u32(a, 0x11), asset = ptr64(a, 0x31), comps = ptr64(a, 0x69), ncomp = u16(a, 0x71),
                 name = cstr(ptr64(a, 0xB1)) }
  if info.asset then
    local ab = read(info.asset, 0x20)
    if ab and #ab >= 0x1A then
      info.asset_id = hex64(ab, 9)
      local full = cstr(ptr64(ab, 0x11))
      local off = u16(ab, 0x19) or 0
      info.asset_name = full and (off > 1 and off < #full and full:sub(off + 1) or full) or nil
    end
  end
  info.template = info.flags and (info.flags & P.TEMPLATE_FLAG) ~= 0
  return info
end

-- every component of an actor: class, instance, handle, ddlPriusData, size, prius type / size / behaviour
function P.components_of(actor)
  local a = P.actor_info(actor)
  if not a or not valid_ptr(a.comps) or not a.ncomp or a.ncomp < 1 or a.ncomp > 64 then return nil, a end
  local list = read(a.comps, a.ncomp * 0x10)
  if not list then return nil, a end
  local out = {}
  for k = 0, a.ncomp - 1 do
    local ti, inst = ptr64(list, k * 0x10 + 1), ptr64(list, k * 0x10 + 9)
    local e = { info = ti, inst = inst }
    local ib = valid_ptr(ti) and read(ti, 0xE8)
    if ib and #ib >= 0xE8 then
      e.class = cstr(ptr64(ib, 0x61))
      e.size = s32(ib, 0x79)
      e.id = u32(ib, 0x7D)
      e.prius_type = ptr64(ib, 0xC9)
      e.prius_size = s32(ib, 0x59)
      e.behavior = P.BEHAVIOR[ib[0xE8]] or tostring(ib[0xE8])
    end
    local cb = valid_ptr(inst) and read(inst, 0x20)
    if cb and #cb >= 0x20 then e.ddl = hex64(cb, 9); e.handle = u32(cb, 0x1D) end
    out[#out + 1] = e
  end
  return out, a
end

-- a handle's actor pointer (through one of its components), or nil
function P.actor_ptr(handle)
  local okn, names = pcall(rivet.components, handle)
  if not okn or type(names) ~= "table" then return nil end
  for k, n in ipairs(names) do
    if k > 4 then break end              -- dev 10.21: your log: a long component list ran past the frame budget
    local ok, c = pcall(rivet.component, handle, tostring(n))
    if ok and type(c) == "table" and c.address then
      local b = read(tonumber(c.address, 16), 0x18)
      local a = b and ptr64(b, 0x11)
      if valid_ptr(a) then return a, names end
    end
  end
  return nil, names
end

-- one line about an actor handle: uid, name, actor asset, Template flag, classes
function P.describe(handle)
  handle = math.tointeger(tonumber(handle)) or handle
  if not handle or handle == 0 then return "none" end
  local oku, uid = pcall(rivet.uid, handle)
  local nm
  if rivet.name then local okn, n = pcall(rivet.name, handle); if okn then nm = n end end
  local actor, names = P.actor_ptr(handle)
  local a = actor and P.actor_info(actor)
  local cls = {}
  for k, n in ipairs(type(names) == "table" and names or {}) do if k <= 14 then cls[#cls + 1] = tostring(n) end end
  return string.format("handle %s uid %s name %s asset %s %s%s classes %s", tostring(handle), tostring(oku and uid),
      tostring(nm or (a and a.name)), tostring(a and a.asset_id), tostring(a and a.asset_name),
      (a and a.template) and " TEMPLATE" or "", #cls > 0 and table.concat(cls, ",") or "?"), a
end

-- ---- the level index ----------------------------------------------------------------------------
local function pause()
  if coroutine.isyieldable() and clock() - P.t0 > P.SLICE then coroutine.yield(); P.t0 = clock() end
end
P.pause = pause

-- a call that rivet_hook's frame budget may stop: tried again on the next frames (3 times)
local function guarded(fn, ...)
  local ok, a, b, c
  for _ = 1, 3 do
    ok, a, b, c = pcall(fn, ...)
    if ok then return a, b, c end
    if not tostring(a):find("budget", 1, true) or not coroutine.isyieldable() then error(a, 0) end
    coroutine.yield(); P.t0 = clock()
  end
  log("a step was stopped by the frame budget three times; skipped")
  return nil
end
P.guarded = guarded

-- pointer offsets (beyond the vtable +0 and the actor +0x10) whose target is readable
local function readable_pointers(b, from)
  local out = {}
  for off = from or 0x18, #b - 8, 8 do
    local p = ptr64(b, off + 1)
    if valid_ptr(p) and read(p, 8) then out[#out + 1] = { off = off, p = p } end
  end
  return out
end
P.readable_pointers = readable_pointers

function P.index(why)
  local lvl = { nodes = {}, order = {}, why = why, probes = 0, spawns = 0, sweeps = 0, spawned_assets = {},
                id = (P.lvl and P.lvl.id or 0) + 1 }
  local okl, list = pcall(rivet.script_nodes, P.NODE_CLASS, P.INDEX_LIMIT)
  if not okl or type(list) ~= "table" then log("index: the spawner nodes cannot be listed:", tostring(list)); return end
  local n, matched, mismatch, nospawner, sizes, ptr_hist = 0, 0, 0, 0, {}, {}
  local function one(node)
    local c = rcall(rivet.component, node.actor, P.NODE_CLASS)
    local addr = type(c) == "table" and c.handle == node.component and c.address and tonumber(c.address, 16)
    local hb = addr and read(addr + P.HANDLE_AT, 4)
    local want = hb and u32(hb, 1)
    local s = rcall(rivet.component, node.actor, P.SPAWNER_CLASS)
    if not (type(s) == "table" and s.address) then nospawner = nospawner + 1
    elseif s.handle ~= want then mismatch = mismatch + 1
    else
      matched = matched + 1
      local saddr = tonumber(s.address, 16)
      local ssize = math.min(P.READ_MAX, (s.size and s.size > 0) and s.size or 0x200)
      local snap = read(saddr, ssize)
      sizes[tostring(s.size)] = (sizes[tostring(s.size)] or 0) + 1
      local ptrs = snap and readable_pointers(snap) or {}
      for _, e in ipairs(ptrs) do local k = string.format("+0x%X", e.off); ptr_hist[k] = (ptr_hist[k] or 0) + 1 end
      local rec = { uid = node.uid, actor = node.actor, component = node.component, addr = addr, handle = want,
                    saddr = saddr, ssize = ssize, snap = snap, nptr = #ptrs }
      lvl.nodes[want] = rec
      lvl.order[#lvl.order + 1] = want
    end
  end
  for _, node in ipairs(list) do
    pause()
    if node.class == P.NODE_CLASS and node.actor then n = n + 1; guarded(one, node) end
  end
  P.lvl = lvl
  local sz, hist = {}, {}
  for k, v in pairs(sizes) do sz[#sz + 1] = k .. " x" .. v end
  table.sort(sz)
  for k, v in pairs(ptr_hist) do hist[#hist + 1] = { k = k, v = v } end
  table.sort(hist, function(a, b) if a.v ~= b.v then return a.v > b.v end return a.k < b.k end)
  local ht = {}
  for i = 1, math.min(16, #hist) do ht[#ht + 1] = hist[i].k .. " x" .. hist[i].v end
  log(string.format("index %d (%s): %d node(s); Spawner handle == node +0x%X for %d, another handle %d, no Spawner %d; Spawner sizes %s; readable pointers at %s",
      lvl.id, tostring(why), n, P.HANDLE_AT, matched, mismatch, nospawner, #sz > 0 and table.concat(sz, ", ") or "-",
      #ht > 0 and table.concat(ht, ", ") or "no offset"))
  -- the first deep probes: nodes whose Spawner holds a pointer first (the likeliest to lead to the lists)
  local pick = {}
  for _, h in ipairs(lvl.order) do if lvl.nodes[h].nptr > 0 then pick[#pick + 1] = h end end
  for _, h in ipairs(lvl.order) do if lvl.nodes[h].nptr == 0 then pick[#pick + 1] = h end end
  for i = 1, math.min(P.INDEX_PROBES, #pick) do guarded(P.probe, lvl.nodes[pick[i]], "index") end
end

-- ---- the deep probe -----------------------------------------------------------------------------
-- 8-byte values worth asking rivet.find_uid: not 0, not -1, not a pointer, not two equal floats
local function uid_candidate(h)
  if not h or h == "0000000000000000" or h == "FFFFFFFFFFFFFFFF" then return false end
  if h:sub(1, 4) == "0000" then return false end           -- small numbers and user-space pointers
  if h:sub(1, 8) == h:sub(9, 16) then return false end      -- two equal u32 / floats
  if h:sub(1, 8) == "FFFFFFFF" then return false end
  return true
end
P.uid_candidate = uid_candidate

function P.uid_search(blocks, lvl, skip)
  local asked, hits, seen = 0, 0, {}
  for _, h in ipairs(skip or {}) do seen[tostring(h):upper()] = true end
  for _, blk in ipairs(blocks) do
    for off = 0, #blk.b - 8, 8 do
      local h = hex64(blk.b, off + 1)
      if uid_candidate(h) and not seen[h] and asked < P.UID_CALLS then
        seen[h] = true
        asked = asked + 1
        pause()
        local handle = rcall(rivet.find_uid, h)
        if handle then
          hits = hits + 1
          local text, a = P.describe(handle)
          local match = ""
          if a and a.asset_id and lvl and lvl.spawned_assets[a.asset_id] then
            match = " - SAME ACTOR ASSET AS SPAWNED " .. lvl.spawned_assets[a.asset_id]
          end
          log(string.format("UID HIT %s+0x%X = %s -> %s%s", blk.path, off, h, text, match))
        end
      end
    end
  end
  return asked, hits
end

function P.probe(rec, why)
  local lvl = P.lvl
  local kind = (why == "index") and "index" or "change"
  if not rec or P.spent[kind] >= P.SESSION_PROBES[kind] then return end
  P.spent[kind] = P.spent[kind] + 1
  if lvl then lvl.probes = lvl.probes + 1; if kind == "change" then lvl.change_probes = (lvl.change_probes or 0) + 1 end end
  local tag = string.format("probe %s node %s", tostring(why), tostring(rec.uid))
  log(string.format("%s: node component %s at %X, Spawner handle %X at %X (%d bytes read)", tag, tostring(rec.component),
      rec.addr or 0, rec.handle or 0, rec.saddr or 0, rec.ssize or 0))
  -- the actor's components and their type data
  local node = rec.addr and read(rec.addr, 0x80)
  local actor = node and ptr64(node, 0x11)
  if valid_ptr(actor) then
    local comps, a = P.components_of(actor)
    if a then
      log(string.format("%s: actor %X flags %s asset %s %s name %s, %s component(s)", tag, actor, tostring(a.flags),
          tostring(a.asset_id), tostring(a.asset_name), tostring(a.name), tostring(a.ncomp)))
    end
    for _, e in ipairs(comps or {}) do
      log(string.format("%s: component %s handle %s inst %X ddlPriusData %s | class size %s id %s prius type %s prius size %s %s",
          tag, tostring(e.class), e.handle and string.format("%X", e.handle) or "?", e.inst or 0, tostring(e.ddl),
          tostring(e.size), e.id and string.format("%08X", e.id) or "?", e.prius_type and string.format("%X", e.prius_type) or "none",
          tostring(e.prius_size), tostring(e.behavior)))
    end
  end
  -- what rivet_hook knows about the node's wiring (outputs and variables)
  if rivet.script_node then
    local ok, t = pcall(rivet.script_node, rec.component, false)
    if ok and type(t) == "table" then
      local parts = {}
      for _, k in ipairs({ "graph_uid", "zone", "connections_in" }) do if t[k] ~= nil then parts[#parts + 1] = k .. "=" .. tostring(t[k]) end end
      local outs = {}
      for _, o in ipairs(type(t.outputs) == "table" and t.outputs or {}) do
        if type(o) == "table" then outs[#outs + 1] = tostring(o.plug_name or o.plug) .. "->" .. tostring(o.target_class or o.target) end
        if #outs >= 8 then break end
      end
      local vars = {}
      for _, v in ipairs(type(t.vars) == "table" and t.vars or {}) do
        if type(v) == "table" then
          local val = v.value
          if type(val) == "table" then      -- dev 10.21: an actors var: its handles, group flag, count and uid
            local hs = {}
            for i = 1, math.min(4, #val) do hs[i] = tostring(val[i]) end
            val = string.format("{%s}%s count %s uid %s", table.concat(hs, ","), val.group and " group" or "", tostring(val.count), tostring(val.uid))
          end
          vars[#vars + 1] = tostring(v.plug_name or v.plug) .. ":" .. tostring(v.type) .. "=" .. tostring(val)
        end
        if #vars >= 8 then break end
      end
      log(string.format("%s: script_node %s; outputs %s; vars %s", tag, table.concat(parts, " "),
          #outs > 0 and table.concat(outs, ", ") or "-", #vars > 0 and table.concat(vars, ", ") or "-"))
    end
  end
  -- the bytes: node, Spawner, plugs, one pointer away
  local blocks = {}
  if node then P.dump(tag .. " node", node); blocks[#blocks + 1] = { path = "node", b = node } end
  local sp = rec.saddr and read(rec.saddr, rec.ssize or 0x200)
  if sp then P.dump(tag .. " Spawner", sp); blocks[#blocks + 1] = { path = "Spawner", b = sp } end
  if node then
    local plugs = ptr64(node, 0x59)
    local pb = valid_ptr(plugs) and read(plugs, 0x28)
    if pb then P.dump(string.format("%s plugs at %X", tag, plugs), pb) end
  end
  local followed, seen = 0, { [rec.addr or 0] = true, [rec.saddr or 0] = true, [actor or 0] = true }
  local second = {}
  for _, src in ipairs({ { "node", node, 0x60 }, { "Spawner", sp, 0x48 } }) do
    if src[2] then
      for _, e in ipairs(readable_pointers(src[2], src[3])) do
        if not seen[e.p] and followed < 12 then
          seen[e.p] = true
          followed = followed + 1
          pause()
          local b = read(e.p, 0x100)
          if b then
            local path = string.format("%s+0x%X->%X", src[1], e.off, e.p)
            P.dump(tag .. " " .. path, b)
            blocks[#blocks + 1] = { path = path, b = b }
            for _, q in ipairs(readable_pointers(b, 0)) do second[#second + 1] = { path = path .. "+0x" .. string.format("%X", q.off), p = q.p } end
          end
        end
      end
    end
  end
  -- two pointers away: searched for uids, not dumped (only their hits are logged)
  local n2 = 0
  for _, e in ipairs(second) do
    if not seen[e.p] and n2 < 16 then
      seen[e.p] = true; n2 = n2 + 1
      pause()
      local b = read(e.p, 0x80)
      if b then blocks[#blocks + 1] = { path = e.path .. "->" .. string.format("%X", e.p), b = b } end
    end
  end
  -- the node's own uid (+0x48) and graph uid (+0x50) are not asked: they name the node itself
  local skip = { tostring(rec.uid) }
  if node then skip[2] = hex64(node, 0x49); skip[3] = hex64(node, 0x51) end
  local asked, hits = P.uid_search(blocks, lvl, skip)
  log(string.format("%s: %d block(s) searched (%d one pointer away, %d two away), %d value(s) asked rivet.find_uid, %d loaded actor(s) found",
      tag, #blocks, followed, n2, asked, hits))
end

-- what changed in a Spawner since the last read: "+0x0C8 a6000000->e2001234 ..." (8-byte steps)
function P.diff(old, new)
  local out = {}
  if not (old and new) then return out end
  for off = 0, math.min(#old, #new) - 8, 8 do
    local a, b = hex64(old, off + 1), hex64(new, off + 1)
    if a ~= b then out[#out + 1] = string.format("+0x%03X %s->%s", off, a, b) end
  end
  return out
end

function P.sweep()
  local lvl = P.lvl
  if not lvl then return end
  lvl.sweeps = lvl.sweeps + 1
  local changed = 0
  for _, h in ipairs(lvl.order) do
    pause()
    local rec = lvl.nodes[h]
    local now = guarded(read, rec.saddr, rec.ssize)
    local d = P.diff(rec.snap, now)
    if #d > 0 then
      changed = changed + 1
      if changed <= 8 then
        local shown = {}
        for i = 1, math.min(12, #d) do shown[i] = d[i] end
        log(string.format("sweep %d: Spawner of node %s changed at %d place(s): %s", lvl.sweeps, tostring(rec.uid), #d, table.concat(shown, " ")))
      end
      rec.snap = now
      if (lvl.change_probes or 0) < P.CHANGE_PROBES and not rec.probed then rec.probed = true; guarded(P.probe, rec, "changed") end
    end
  end
  log(string.format("sweep %d: %d of %d Spawner(s) changed since the last read", lvl.sweeps, changed, #lvl.order))
end

-- ---- events ---------------------------------------------------------------------------------------
function P.on_spawn(f, ev)
  local lvl = P.lvl
  if not lvl then return end
  lvl.spawns = lvl.spawns + 1
  local h = math.tointeger(tonumber(f.SpawnedHandle)) or f.SpawnedHandle
  if lvl.spawns <= P.SPAWN_LOG then
    local text, a = P.describe(h)
    if a and a.asset_id then lvl.spawned_assets[a.asset_id] = tostring(a.asset_name or h) end
    local loc = math.tointeger(tonumber(f.SpawnLocation))
    local okl, lid = false, nil
    if loc and loc ~= 0 then okl, lid = pcall(rivet.uid, loc) end
    local fac = math.tointeger(tonumber(f.SpawnFactory))
    log(string.format("spawn %d: index %s location %s (uid %s); spawned %s", lvl.spawns, tostring(f.SpawnIndex), tostring(loc),
        tostring(okl and lid), text))
    if fac and fac ~= 0 then log(string.format("spawn %d: SpawnFactory %s", lvl.spawns, (P.describe(fac)))) end
  end
  if lvl.sweeps < P.SWEEPS_PER_LEVEL and (P.sweep_at == nil) and P.frame - (P.last_sweep or -10000) >= P.SWEEP_GAP then
    P.sweep_at = P.frame + 30
  end
end

function P.on_spawner_event(kind, f)
  local lvl = P.lvl
  local h = math.tointeger(tonumber(f.SpawnerComponentHandle))
  local rec = lvl and h and lvl.nodes[h]
  if not rec then return end
  if (lvl.events or 0) < 6 then
    lvl.events = (lvl.events or 0) + 1
    local now = read(rec.saddr, rec.ssize)
    local d = P.diff(rec.snap, now)
    local shown = {}
    for i = 1, math.min(12, #d) do shown[i] = d[i] end
    log(string.format("%s: SpawnerComponentHandle %X = node %s (its +0x%X); Spawner changed at %d place(s) since the index%s%s",
        kind, h, tostring(rec.uid), P.HANDLE_AT, #d, #shown > 0 and ": " or "", table.concat(shown, " ")))
    rec.snap = now or rec.snap
  end
  if not rec.probed and (lvl.change_probes or 0) < P.CHANGE_PROBES then
    rec.probed = true
    P.queue[#P.queue + 1] = function() guarded(P.probe, rec, kind) end
  end
end

function P.schedule(why)
  P.lvl = nil
  P.job = nil
  P.queue = {}
  P.sweep_at = nil
  P.index_at = P.frame + P.INDEX_DELAY
  P.index_why = why
end

local function run(fn)
  P.job = coroutine.create(fn)
end

function P.on_frame()
  P.frame = P.frame + 1
  P.t0 = clock()
  if P.job then
    local ok, err = coroutine.resume(P.job)
    if not ok then
      P.job = nil
      if tostring(err):find("budget", 1, true) then log("a step ran past the frame budget; it is dropped") else log("RANDO-ERROR", tostring(err)) end
    elseif coroutine.status(P.job) == "dead" then P.job = nil end
    return
  end
  local okr, ready = pcall(rivet.scene_ready)
  if okr and ready == false then return end
  if P.index_at and P.frame >= P.index_at then
    P.index_at = nil
    local why = P.index_why
    run(function() P.index(why) end)
    return
  end
  if #P.queue > 0 then run(table.remove(P.queue, 1)); return end
  if P.sweep_at and P.frame >= P.sweep_at then
    P.sweep_at = nil
    P.last_sweep = P.frame
    run(P.sweep)
  end
end

-- ---- wiring (rivet.on_event directly: this works whatever the randomizer's switches are) ------------
-- dev 10.21: the events come through the spawner layer's listeners (16_rando_spawners SP.listen): rivet_hook
-- allows 64 event callbacks in all and your dev 10.20 log hit that limit (PlanetChanged / Checkpoint lost)
if not P.subscribed then
  P.subscribed = true
  local SPL = RANDO_SPAWNERS
  if SPL and SPL.listen then
    SPL.listen("SpawnerSpawnEvent", P.on_spawn)
    SPL.listen("SpawnerStartedEvent", function(f) P.on_spawner_event("started", f) end)
    SPL.listen("SpawnerStoppedEvent", function(f) P.on_spawner_event("stopped", f) end)
    SPL.listen("LevelLoadedEvent", function() P.schedule("level loaded") end)
    SPL.listen("PlanetChangedEvent", function(f) if f.NewPlanetName then P.schedule("planet " .. tostring(f.NewPlanetName)) end end)
    SPL.listen("Checkpoint", function(cp) if cp.loaded then P.schedule("checkpoint loaded") end end)
  else
    log("16_rando_spawners.lua (with SP.listen) is missing: no events")
  end
  pcall(rivet.on_frame, P.on_frame)
end
P.schedule("scripts loaded")
log("v1 loaded: read-only spawner evidence (index after each load, spawned actors, changed Spawners, deep probes); remove the file to turn it off")
