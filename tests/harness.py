"""Offline harness: runs the randomizer's real Lua scripts in Lua 5.4 (lupa) against
tests/sim/rivet_sim.lua, a simulated rivet_hook API and game.

What this proves: the scripts' own logic (generation, state, rewards, shop, saving, delivery
decisions) behaves as intended against the simulated behaviour. What it cannot prove: that the
real game behaves like the simulation. Every behaviour the simulator models is listed at the top
of rivet_sim.lua with the log evidence it is based on.
"""
import json
import os
import pathlib

from lupa import lua54

ROOT = pathlib.Path(__file__).resolve().parents[1]
MOD = pathlib.Path(os.environ.get("RANDO_MOD_DIR", ROOT / "mod" / "RiftApartRandomizer"))
# v0.60: the release validator runs suites against an INSTALLED player copy (no boss.lua / chaos.lua, no dev files)
INSTALLED = "RANDO_MOD_DIR" in os.environ
PLAYER_EXCLUDED = ("boss.lua", "chaos.lua")
SIM = ROOT / "tests" / "sim" / "rivet_sim.lua"

# 9.0: the tests were written for the 7.0-8.5 defaults (no Coordinates, the game's own order,
# Raritanium 20-150); the user's defaults since 8.5.1 differ (02's G.DEFAULTS). Tests pin the
# settings they were written for; tests/test_v90.py runs the user's real defaults and 04 file.
# A pinned value never overrides what the test itself or its preset sets.
CLASSIC_TEST_SETTINGS = {"planet_locks": False, "campaign_mode": "vanilla", "raritanium_min": 20, "raritanium_max": 150,
                         # 10.0: the suites before 10.0 were written without the hub, with the Gold-Bolts-first
                         # fill and all 15 vendor slots selling a weapon (tests/test_v100.py runs the 10.0 defaults)
                         "hub": False, "distribution": "goldbolts_first", "shop_weapons": 15,
                         "shop_close_slots": False}
DEFAULT_SETTINGS = {"seed": "test-seed-2", "preset": "standard"}
# settings that also set a pinned key (7.0 names)
_SETS_TOO = {"levels": ("planet_locks",), "mission_order": ("campaign_mode",), "filler_raritanium": ("raritanium_min", "raritanium_max")}
_PRESET_KEYS = None


def preset_keys(preset):
    """the settings a preset of the kit's generator sets (read from 02_rando_generator.lua)"""
    global _PRESET_KEYS
    if _PRESET_KEYS is None:
        L = lua54.LuaRuntime(unpack_returned_tuples=True)
        L.execute("rivet = {}")
        for f in ("01_rando_data.lua", "02_rando_generator.lua"):
            L.execute((MOD / "scripts" / f).read_text(encoding="utf-8"))
        P = L.globals().RANDO_GEN.PRESETS
        _PRESET_KEYS = {name: set(P[name].keys()) for name in P.keys()}
    return _PRESET_KEYS.get(preset, set())


def classic_settings(settings=None):
    """settings with CLASSIC_TEST_SETTINGS filled in where neither they nor their preset decide"""
    st = dict(DEFAULT_SETTINGS)
    st.update(settings or {})
    taken = set(st) | preset_keys(st.get("preset") or "balanced")
    for k in list(st):
        taken |= set(_SETS_TOO.get(k, ()))
    for k, v in CLASSIC_TEST_SETTINGS.items():
        if k not in taken:
            st[k] = v
    return st


# developer files (scripts/dev(name).lua). The development setup the tests were written for has the
# developer keys and test travel installed; test mode and the probe tools only when a test asks.
DEV_ALWAYS = ("dev(keys).lua", "dev(testtravel).lua")
DEV_TEST_MODE = ("dev(testmode).lua",)
DEV_TOOLS = ("dev(item_ids).lua", "dev(probe).lua", "dev(vtables).lua")
DEV_SPAWNPROBE = ("dev(spawnprobe).lua",)     # dev 10.20: the read-only spawner evidence collector
DEV_SPAWNPROOF = ("dev(spawnproof).lua",)     # dev 10.21: one controlled Template-variable replacement


def is_dev(name):
    return name.startswith("dev(") and name.endswith(").lua")


# where developer files come from when the release scripts are an installed copy (the release
# validator points RANDO_MOD_DIR at a game folder that has no developer file)
DEV_DIR = pathlib.Path(os.environ.get("RANDO_DEV_SCRIPTS", MOD / "dev_scripts"))   # dev 10.30: out of scripts\


def script_files(test_mode=False, dev_tools=False, scripts_dir=None, release=False, without=(), spawnprobe=False, spawnproof=False):
    """release=True: only what a release ships (no dev(name).lua file). without: file names left out."""
    d = pathlib.Path(scripts_dir) if scripts_dir else MOD / "scripts"
    dev_dir = d if scripts_dir else DEV_DIR
    want = set()
    if not release:
        want |= set(DEV_ALWAYS)
        if test_mode:
            want |= set(DEV_TEST_MODE)
        if dev_tools:
            want |= set(DEV_TOOLS)
        if spawnprobe:
            want |= set(DEV_SPAWNPROBE)
        if spawnproof:
            want |= set(DEV_SPAWNPROOF)
    files = [f for f in d.glob("*.lua") if not is_dev(f.name) and f.name not in without]
    files += [dev_dir / n for n in sorted(want) if (dev_dir / n).exists() and n not in without]
    return sorted(files, key=lambda p: p.name)        # rivet_hook loads in file name order


def lua_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return json.dumps(v)


class Game:
    """One game session (one Lua VM, like one game start or one script reload)."""

    def __init__(self, test_mode=False, dev_tools=False, dll_status=1, dll_version=5, dll=True,
                 scripts_dir=None, before_scripts=None, files=None, settings=None, settings_file=False,
                 extra_lua=None, release=False, without=(), planet_shuffle=False, spawnprobe=False, spawnproof=False):
        self.lua = lua54.LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(SIM.read_text(encoding="utf-8"))
        self.g = self.lua.globals()
        self.sim = self.g.SIM
        if dll:
            self.sim.install_dll(dll_status, dll_version)
        if before_scripts:
            before_scripts(self)
        self.load_errors = []
        self.files = files or script_files(test_mode, dev_tools, scripts_dir, release, without, spawnprobe, spawnproof)
        # planet_shuffle=True: the player turns planet shuffle on (the 0 key's action) right after
        # the companion's first restore - the hub tests were written with it on
        self.planet_shuffle = planet_shuffle
        if not settings_file:
            self.files = [f for f in self.files if not f.name.startswith("04_")]
            st = classic_settings(settings)
            self.lua.execute("RANDO_SETTINGS = {" + ",".join(f"[{json.dumps(k)}]={lua_value(v)}" for k, v in st.items()) + "}")
        loader = self.lua.eval("function(src, name) local f, e = load(src, '@' .. name); if not f then return false, e end;"
                               " local ok, e2 = pcall(f); return ok, tostring(e2) end")
        for f in self.files:
            if f.name.startswith("09_") and self.g.RANDO_DATA is not None:
                self.sim.define_items(self.g.RANDO_DATA.real_items)
                self.install_vendor()
                if extra_lua:
                    self.lua.execute(extra_lua)
            ok, err = loader(f.read_text(encoding="utf-8"), f.name)
            if not ok:
                self.load_errors.append((f.name, err))
        if os.environ.get("RANDO_STRICT_GLOBALS"):
            # audit aid: report any global the scripts create or read after loading (a typo or a
            # missing `local` shows up here); the report goes to the file the variable names
            self.lua.execute(r"""
              local out = io.open(os.getenv("RANDO_STRICT_GLOBALS"), "a")
              local allowed = { RANDO_TEST_MODE = true, RANDO_PROBE = true, RANDO_VTABLES = true, RANDO_DONOR_ROUTE = true,
                                RANDO_EXE = true, RANDO_DEV_KEYS = true, RANDO_TEST_TRAVEL = true, RANDO_HUB = true,
                                RANDO_ITEM_IDS = true, RANDO_OMEGA = true }
              setmetatable(_G, {
                __newindex = function(t, k, v)
                  local info = debug.getinfo(2, "Sl")
                  if info and info.short_src and info.short_src:find("rando_") then out:write("NEW ", tostring(k), " ", info.short_src, ":", tostring(info.currentline), "\n"); out:flush() end
                  rawset(t, k, v)
                end,
                __index = function(t, k)
                  local info = debug.getinfo(2, "Sl")
                  if not allowed[k] and info and info.short_src and info.short_src:find("rando_") then out:write("READ ", tostring(k), " ", info.short_src, ":", tostring(info.currentline), "\n"); out:flush() end
                  return nil
                end })
            """)

    # 5.0: the default vendor's stock in (simulated) memory: the ammo entry, then the vendor's
    # weapons in the data's order, plus the Burst Pistol (owned from the prologue, never moved)
    VENDOR_ID = "A1B2C3D4E5F60718"
    AMMO_ID = "BFC3753A4EE2A47B"

    def install_vendor(self, items=None, prices="vanilla"):
        """prices: "vanilla" = each slot holds its weapon's price from the data (7.0's price
        discovery finds it), None = the 6.0 test layout's made-up prices (1000 * slot)"""
        data = self.g.RANDO_DATA
        if items is None:
            ids = [self.AMMO_ID]
            for key in sorted(data["items"].keys()):
                it = data["items"][key]
                if it["category"] == "weapon" and it["vendor"]:
                    ids.append(it["id"])
            # slots the randomizer never touches: Burst Pistol, Shatterbomb, RYNO 8, and the
            # Challenge Mode Pixelizer / Bouncer slots
            for k in ("weapon:burst_pistol", "weapon:shatterbomb", "weapon:ryno_8", "weapon:pixelizer", "weapon:bouncer"):
                ids.append(data["items"][k]["id"])
            items = ids
        price_list = None
        if prices == "vanilla":
            by_id = {data["items"][k]["id"]: data["items"][k]["price"] for k in data["items"].keys()
                     if data["items"][k]["category"] == "weapon" and data["items"][k]["price"] is not None}
            price_list = self.lua.table_from([by_id.get(i, 99) for i in items])
        self.sim.install_vendor_memory(self.VENDOR_ID, self.lua.table_from(items), price_list)
        return items

    # ---- shortcuts
    @property
    def R(self):
        return self.g.RANDO

    @property
    def real(self):
        return self.g.RANDO_REAL

    @property
    def state(self):
        return self.g.RANDO.state

    @property
    def seed(self):
        return self.g.RANDO_SEED

    @property
    def data(self):
        return self.g.RANDO_DATA

    def step(self, n=1):
        self.sim.step(n)

    def seconds(self, s):
        self.sim.step(int(s * 60))

    def press(self, key, ctrl=False):
        self.sim.press(key, ctrl)

    def fire(self, cls, **fields):
        self.sim.fire(cls, self.lua.table_from(fields))

    def travel(self, name, frames=30):
        self.sim.travel(name, frames)

    def logs(self):
        return list(self.sim.logs.values())

    def notes(self):
        return [n.text for n in self.sim.notes.values()]

    def log_has(self, text):
        return any(text in l for l in self.logs())

    def count_logs(self, text):
        return sum(1 for l in self.logs() if text in l)

    def note_has(self, text):
        return any(text in n for n in self.notes())

    def bridge(self, chunk):
        """script.exec as rivet_hook's bridge does it (answer cut at 4095 characters)"""
        fn = self.lua.eval("function(src) local f, e = load(src); if not f then return false, e end;"
                           " local ok, v = pcall(f); if not ok then return false, tostring(v) end;"
                           " if v == nil then return true, 'ok' end; return true, tostring(v) end")
        ok, v = fn(chunk)
        assert ok, v
        return v[:4095]

    def wait_seed(self, frames=600):
        for _ in range(frames):
            if self.g.RANDO_SEED is not None and self.g.RANDO.state is not None:
                return True
            self.step(1)
        return False

    def companion_restore(self, saved_text=None):
        """What RandoCompanion.ps1 does on connect (after the seed is ready)."""
        assert self.wait_seed(), "seed not ready: " + str(self.logs()[-5:])
        if saved_text is None:
            r = self.bridge("return rando_mark_restored()")
        else:
            r = self.bridge("return tostring(rando_import_state((function() " + saved_text + " end)()))")
        if self.planet_shuffle and self.g.RANDO_HUB is not None and not self.g.RANDO.planet_shuffle_on():
            self.g.RANDO_HUB.set_shuffle(True, "test setup")
        return r

    def companion_export(self):
        status = self.bridge("return rando_bridge_status()")
        parts = status.split("|")
        assert len(parts) == 8 and parts[6] == "ready", status
        chunks = []
        for i in range(1, int(parts[5]) + 1):
            c = self.bridge(f"return rando_export_chunk({i})")
            assert len(c) <= 4095
            chunks.append(c)
        text = "".join(chunks)
        assert len(text) == int(parts[4]) and text.startswith("return {"), (len(text), parts)
        return text

    def item_status(self, item):
        r = self.state.real and self.state.real[item]
        return r.status if r is not None else None

    def item_id(self, item):
        return self.data["items"][item].id

    def owns(self, item):
        info = self.data.real_items[item]
        if info.kind == "weapon":
            return bool(self.sim.weapons_owned[info.id])
        if info.kind == "armor":
            return bool(self.sim.vanity_owned[info.id])
        return bool(self.sim.gadgets_owned[info.id])

    def give_count(self, item):
        info = self.data.real_items[item]
        if info.kind == "armor":                       # 5.0: through the game's armor code
            return sum(1 for b in self.sim.vanity_gives.values() if b == info.id)
        return sum(1 for g in self.sim.give_log.values() if g.id == info.id)

    def ready(self, fresh=True, saved=None, frames=300, planet="NefCity"):
        """game start: seed generated, companion restore, a planet loaded, a few seconds of play"""
        if fresh or saved is not None:
            self.companion_restore(saved)
        self.travel(planet)
        self.step(frames)
        return self

    def location_with(self, pred):
        for lid in sorted(self.seed.locations.keys()):
            if pred(lid, self.seed.locations[lid].item):
                return lid
        return None


# 10.0: the generator suites written before 10.0 (test_generator, test_campaign) check the
# 4.0-9.0 rules: no hub, every Gold Bolt holds an item, all 15 vendor slots sell a weapon. They
# run the real generator with those three settings pinned (anything a test sets wins).
PRE10_SETTINGS = {"hub": False, "distribution": "goldbolts_first", "shop_weapons": 15}


def pre10_engine():
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "tools"))
    import rando as _rando

    class Pre10Engine(_rando.Engine):
        def generate(self, seed, settings=None, preset="balanced"):
            st = dict(PRE10_SETTINGS)
            st.update(settings or {})
            return super().generate(seed, st, preset)

    return Pre10Engine()
