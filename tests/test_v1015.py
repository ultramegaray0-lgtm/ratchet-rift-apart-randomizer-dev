"""Dev 10.15 (kit 10.0.11), asked for: Omega weapons (Challenge Mode / New Game+) in the randomized item pool,
as items of their own, with the ownership of a weapon and its Omega version kept apart and never downgraded.

What the game does (static research, neptuwunium/rivet's DDL dump; tools/build_data.py has the evidence):
an Omega weapon is NOT an item id of its own (the dag has no Omega item config); it is the bool
WeaponItemPrius.Omega of the weapon you own, set by Ms. Zurkon's Omega purchase. So:
  * generator: omega_weapons puts omega:<weapon> rewards in the seed (off: every seed is the 10.13 seed);
  * runtime (10_rando_runtime.lua): the tier per weapon (weapon / Omega), the prerequisite, no downgrade,
    no duplicate sends, saved and merged;
  * 17_rando_omega.lua: finds the weapon's inventory record, LEARNS the flag's byte from two Omega purchases
    (or omega_flag_offset), sets it, keeps it.

SIMULATOR ONLY for everything in the game (tests/sim/rivet_sim.lua: the inventory layout there is INVENTED).
Nothing here says the real game keeps its records or its Omega flag the way the simulator does.
"""
import os
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game, MOD  # noqa: E402
from luajson import py  # noqa: E402
import rando  # noqa: E402

OMEGA_AT = 0x5B              # the simulator's (invented) Omega byte, from the record's item id
BASE_1013 = "376a8871baf2ec8f8e000f3c7c926451824ab986"   # dev 10.13, the commit this work starts from
NAMES = {"burst_pistol": "WEAPON_BURSTPISTOL", "enforcer": "WEAPON_PROTOSHOTGUN", "ricochet": "WEAPON_RICOCHET",
         "mr_fungi": "WEAPON_MRFUNGUY", "drillhound": "WEAPON_TUNNELER"}
_ENGINE = None


def engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = rando.Engine()
    return _ENGINE


def game(offset=None, settings=None, **kw):
    st = dict(settings or {})
    if offset is not None:
        st["omega_flag_offset"] = offset
    g = Game(settings=st, **kw)
    assert not g.load_errors, g.load_errors
    g.ready()
    return g


def wid(g, w):
    return g.data["items"]["weapon:" + w].id


def deliver(g, frames=600):
    g.step(frames)


def flag(g, w):
    return g.sim.omega_of(wid(g, w))


def tier(g, w):
    return g.R.omega_tier(w)


# ---------------------------------------------------------------------------------------------- data
class DataTests(unittest.TestCase):
    def test_twenty_omega_items_one_per_vanilla_weapon(self):
        db = engine().db()
        om = {k: v for k, v in db["items"].items() if v["category"] == "omega"}
        self.assertEqual(len(om), 20)
        for k, v in om.items():
            w = db["items"][v["weapon"]]
            self.assertEqual(k.split(":", 1)[1], v["weapon"].split(":", 1)[1])
            self.assertEqual(v["id"], w["id"])                       # the same item: no Omega item id exists
            self.assertEqual(w["source"], "vanilla")
            self.assertIn(w["acquisition"], ("pool", "reward"))
            self.assertTrue(v["name"].startswith("Omega "))
            self.assertFalse(v["verified_in_game"])
        # never a real item of its own (09_rando_real.lua never sends an Omega)
        self.assertFalse([k for k in db["real_items"] if k.startswith("omega:")])
        # the ARSENAL_RESTORED and cut weapons have none
        for k, v in db["items"].items():
            if v["category"] == "weapon" and v["source"] != "vanilla":
                self.assertNotIn(k.replace("weapon:", "omega:"), om)

    def test_build_data_reproduces_the_data(self):
        before = (MOD / "scripts" / "01_rando_data.lua").read_bytes()
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_data.py")], check=True, capture_output=True)
        self.assertEqual((MOD / "scripts" / "01_rando_data.lua").read_bytes(), before)


# ----------------------------------------------------------------------------------------- generator
def old_engine():
    """the 10.13 generator from git (skipped when git or the commit is not available)"""
    out = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "rando_1013_scripts"
    if not (out / "02_rando_generator.lua").exists():
        out.mkdir(parents=True, exist_ok=True)
        for f in ("01_rando_data.lua", "02_rando_generator.lua", "03_rando_campaign.lua"):
            r = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_1013}:mod/RiftApartRandomizer/scripts/{f}"],
                               capture_output=True)
            if r.returncode != 0:
                return None
            (out / f).write_bytes(r.stdout)
    return rando.Engine(str(out))


class GeneratorTests(unittest.TestCase):
    def test_private_dev_settings_enable_omega_by_default(self):
        settings = (ROOT / "mod" / "RiftApartRandomizer" / "scripts" / "04_rando_settings.lua").read_text(encoding="utf-8")
        self.assertIn("omega_weapons = true", settings)

    def test_explicit_off_every_seed_is_the_1013_seed(self):
        old = old_engine()
        if old is None:
            self.skipTest("git history with dev 10.13 not available")
        new = engine()
        self.assertFalse(new.defaults()["omega_weapons"])  # fallback remains backward-compatible; dev 04 file opts in
        n = 0
        for preset in ("balanced", "chaos", "full", "campaign", "everything"):
            for i in range(4):
                for extra in ({}, {"hub": False, "distribution": "goldbolts_first"}, {"weapons": False, "armor": False}):
                    a, _ = old.generate(f"v1015-{preset}-{i}", extra, preset)
                    b, _ = new.generate(f"v1015-{preset}-{i}", extra, preset)
                    self.assertEqual(a is None, b is None)
                    if a is None:
                        continue
                    self.assertEqual(a.fingerprint, b.fingerprint)
                    self.assertEqual(old.spoiler(a), new.spoiler(b), (preset, i, extra))
                    n += 1
        self.assertGreater(n, 50)

    def check(self, seed):
        locs = py(seed.locations)
        placed = {l["item"]: lid for lid, l in locs.items() if str(l.get("item", "")).startswith("omega:")}
        start = list(py(seed.start)["items"])
        return placed, start

    def test_on_places_each_omega_once_and_passes_the_audit(self):
        e = engine()
        db = e.db()
        for preset in ("balanced", "chaos", "full", "campaign", "everything"):
            for i in range(6):
                for extra in ({}, {"hub": False, "distribution": "goldbolts_first"}, {"weapons": False}):
                    st = dict(extra, omega_weapons=True)
                    s, audit = e.generate(f"om-{preset}-{i}", st, preset)
                    self.assertIsNotNone(s, audit)
                    self.assertEqual(audit, [], (preset, i, extra))
                    placed, start = self.check(s)
                    reg = py(s.registry)
                    for k in (k for k in db["items"] if k.startswith("omega:")):
                        routes = (1 if k in placed else 0) + start.count(k)
                        self.assertLessEqual(routes, 1, k)
                        if routes == 0:
                            self.assertTrue(reg[k].startswith("excluded"), (k, reg.get(k)))
                    for k, lid in placed.items():
                        self.assertNotEqual(db["locations"][lid]["kind"], "goldbolt")
                        self.assertNotEqual(db["locations"][lid].get("holds"), "filler")
                    self.assertFalse([k for k in start if k.startswith("omega:")])     # never a random start
                    self.assertFalse([w for w in py(s.shop)["slots"].values() if str(w).startswith("omega:")])

    def test_on_keeps_the_seed_and_adds_the_omegas_where_currency_was(self):
        e = engine()
        for preset in ("balanced", "everything", "campaign"):
            for extra in ({}, {"hub": False, "distribution": "goldbolts_first"}):
                off, _ = e.generate("same-" + preset, extra, preset)
                on, _ = e.generate("same-" + preset, dict(extra, omega_weapons=True), preset)
                self.assertNotEqual(off.fingerprint, on.fingerprint)      # its own saves and share code ...
                self.assertEqual(off.attempt, on.attempt)                 # ... but the same placements:
                a, b = py(off.locations), py(on.locations)
                self.assertEqual(sorted(a), sorted(b))
                for lid, l in a.items():
                    item = str(l.get("item") or "")
                    if item.startswith("filler:"):
                        self.assertTrue(str(b[lid].get("item") or "").startswith(("filler:", "omega:")), lid)
                    else:
                        self.assertEqual(b[lid].get("item"), l.get("item"), lid)
                self.assertEqual(list(py(off.start)["items"]), list(py(on.start)["items"]))
                self.assertEqual(py(off.shop)["slots"], py(on.shop)["slots"])

    def test_start_items_and_exclude(self):
        e = engine()
        s, audit = e.generate("om-start", {"omega_weapons": True, "start_items": "omega:burst_pistol,omega:enforcer",
                                           "exclude": "omega:ryno_8"}, "balanced")
        self.assertEqual(audit, [])
        placed, start = self.check(s)
        self.assertIn("omega:burst_pistol", start)
        self.assertIn("omega:enforcer", start)
        self.assertNotIn("omega:ryno_8", placed)
        self.assertNotIn("omega:ryno_8", start)
        self.assertEqual(py(s.registry)["omega:burst_pistol"], "start (chosen)")
        sp = e.spoiler(s)
        self.assertIn("OMEGA VERSIONS", sp)
        self.assertIn("Omega Burst Pistol", sp)
        # off: an Omega in start_items is not an item of the seed
        s2, _ = e.generate("om-start", {"start_items": "omega:burst_pistol"}, "balanced")
        self.assertNotIn("omega:burst_pistol", list(py(s2.start)["items"]))
        self.assertIn("omega:burst_pistol is not an item this seed randomizes", " ".join(py(s2.warnings) or []))
        self.assertNotIn("OMEGA VERSIONS", e.spoiler(s2))
        self.assertNotIn("omega_weapons", e.spoiler(s2))

    def test_audit_rejects_misplaced_omegas(self):
        e = engine()
        s, _ = e.generate("om-audit", {"omega_weapons": True}, "balanced")
        L = e.lua
        bolt = next(lid for lid in sorted(py(s.locations)) if lid.startswith("gb:") or e.db()["locations"][lid]["kind"] == "goldbolt")
        L.execute("function omove(s, lid) local it; for l, v in pairs(s.locations) do if v.item and v.item:sub(1, 6) == 'omega:' then it = v.item; v.item = nil; break end end; s.locations[lid].item = it end")
        L.globals().omove(s, bolt)
        audit = list(py(e.G.audit(s)) or [])
        self.assertTrue(any("is on a Gold Bolt" in a for a in audit), audit)
        s2, _ = e.generate("om-audit", {}, "balanced")
        L.globals().omove(s, bolt)
        L.execute("function oput(s) for l, v in pairs(s.locations) do if v.item and v.item:sub(1, 7) == 'filler:' then v.item = 'omega:enforcer'; return end end end")
        L.globals().oput(s2)
        audit2 = list(py(e.G.audit(s2)) or [])
        self.assertTrue(any("although omega_weapons is off" in a for a in audit2), audit2)


# ------------------------------------------------------------------------- runtime: tiers and sends
class OwnershipTests(unittest.TestCase):
    def test_normal_then_omega_upgrades_without_a_second_send(self):
        g = game(offset=OMEGA_AT)
        g.R.grant("weapon:enforcer")
        deliver(g)
        self.assertTrue(g.owns("weapon:enforcer"))
        self.assertEqual(g.give_count("weapon:enforcer"), 1)
        self.assertEqual(tier(g, "enforcer"), 1)
        self.assertEqual(flag(g, "enforcer"), 0)
        g.R.grant("omega:enforcer")
        deliver(g)
        self.assertEqual(g.give_count("weapon:enforcer"), 1)                 # the weapon is not sent again
        self.assertEqual(flag(g, "enforcer"), 1)
        self.assertEqual(tier(g, "enforcer"), 2)
        self.assertEqual(g.state.omega["enforcer"].status, "applied")
        self.assertIsNone(g.state.omega_prereq["enforcer"])                 # it was owned: no prerequisite
        self.assertTrue(g.note_has("your Enforcer becomes Omega"))
        self.assertTrue(g.note_has("Omega Enforcer is yours"))

    def test_omega_first_gives_the_weapon_then_the_flag(self):
        g = game(offset=OMEGA_AT)
        g.R.grant("omega:burst_pistol")
        self.assertEqual(tier(g, "burst_pistol"), 2)
        self.assertTrue(g.state.omega_prereq["burst_pistol"])
        self.assertTrue(g.state.inventory["omega:burst_pistol"])
        self.assertIsNone(g.state.inventory["weapon:burst_pistol"])        # the reward recorded is the Omega
        deliver(g)
        self.assertTrue(g.owns("weapon:burst_pistol"))
        self.assertEqual(g.give_count("weapon:burst_pistol"), 1)
        self.assertEqual(flag(g, "burst_pistol"), 1)
        self.assertEqual(g.state.omega["burst_pistol"].status, "applied")
        self.assertTrue(g.note_has("Burst Pistol added first (an Omega needs the weapon)"))

    def test_omega_then_normal_never_downgrades(self):
        g = game(offset=OMEGA_AT)
        g.R.grant("omega:burst_pistol")
        deliver(g)
        self.assertEqual(flag(g, "burst_pistol"), 1)
        g.R.grant("weapon:burst_pistol")
        deliver(g)
        self.assertEqual(g.give_count("weapon:burst_pistol"), 1)              # nothing sent: no downgrade possible
        self.assertEqual(flag(g, "burst_pistol"), 1)
        self.assertEqual(tier(g, "burst_pistol"), 2)
        self.assertTrue(g.state.inventory["weapon:burst_pistol"])            # both rewards are recorded
        self.assertTrue(g.state.inventory["omega:burst_pistol"])
        self.assertTrue(g.note_has("Burst Pistol - you have its Omega version already (kept)"))

    def test_normal_reward_while_the_prerequisite_is_still_in_flight(self):
        g = game(offset=OMEGA_AT)
        g.R.grant("omega:ricochet")
        g.R.grant("weapon:ricochet")                                         # same frame: still queued
        deliver(g)
        self.assertEqual(g.give_count("weapon:ricochet"), 1)
        self.assertEqual(flag(g, "ricochet"), 1)

    def test_repeated_rewards_are_recorded_once_and_send_nothing_more(self):
        g = game(offset=OMEGA_AT)
        for key in ("omega:mr_fungi", "weapon:mr_fungi", "omega:mr_fungi", "weapon:mr_fungi", "omega:mr_fungi"):
            g.R.grant(key)
            deliver(g, 200)
        deliver(g)
        self.assertEqual(g.give_count("weapon:mr_fungi"), 1)
        self.assertEqual(flag(g, "mr_fungi"), 1)
        self.assertEqual(tier(g, "mr_fungi"), 2)
        self.assertTrue(g.note_has("Omega Mr. Fungi (you have it already)"))
        self.assertEqual(sum(1 for l in g.logs() if "Omega Mr. Fungi applied" in l), 1)

    def test_every_weapon_with_an_omega_works_the_same(self):
        g = game(offset=OMEGA_AT)
        ws = [k.split(":", 1)[1] for k in g.data["items"].keys() if k.startswith("omega:")]
        self.assertEqual(len(ws), 20)
        for i, w in enumerate(sorted(ws)):
            g.R.grant(("omega:" if i % 2 else "weapon:") + w)
        deliver(g, 3000)
        for i, w in enumerate(sorted(ws)):
            g.R.grant(("weapon:" if i % 2 else "omega:") + w)
        deliver(g, 3000)
        for w in ws:
            self.assertEqual(g.give_count("weapon:" + w), 1, w)
            self.assertEqual(flag(g, w), 1, w)
            self.assertEqual(tier(g, w), 2, w)
            self.assertTrue(g.state.inventory["weapon:" + w] and g.state.inventory["omega:" + w], w)

    def test_byte_that_is_not_a_flag_is_never_written(self):
        g = game(offset=0x20)                         # the simulator keeps a level (3) there
        g.R.grant("omega:drillhound")
        deliver(g)
        self.assertEqual(g.sim.mem[g.sim.inv_records[wid(g, "drillhound")] + 0x10 + 0x20], 3)
        self.assertEqual(g.state.omega["drillhound"].status, "pending")
        self.assertTrue(g.log_has("not a flag"))

    def test_runtime_off_writes_nothing(self):
        g = game(offset=OMEGA_AT, settings={"omega_runtime": False})
        g.R.grant("omega:enforcer")
        deliver(g)
        self.assertTrue(g.owns("weapon:enforcer"))                          # the prerequisite still comes
        self.assertEqual(flag(g, "enforcer"), 0)
        self.assertEqual(g.state.omega["enforcer"].status, "pending")
        self.assertTrue(g.note_has("omega_runtime = false"))

    def test_without_17_the_tier_is_still_kept(self):
        g = game(without=("17_rando_omega.lua",))
        self.assertIsNone(g.g.RANDO_OMEGA)
        g.R.grant("omega:enforcer")
        deliver(g)
        self.assertTrue(g.owns("weapon:enforcer"))
        self.assertEqual(tier(g, "enforcer"), 2)
        self.assertTrue(g.note_has("17_rando_omega.lua is not installed"))
        g.R.grant("weapon:enforcer")
        deliver(g)
        self.assertEqual(g.give_count("weapon:enforcer"), 1)
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.23"), [l for l in g.logs() if "KIT" in l])
        self.assertTrue(g.log_has("17_rando_omega not installed"))

    def test_kit_check_and_status(self):
        g = game(offset=OMEGA_AT)
        self.assertTrue(g.log_has("RANDO-KIT all 12 required scripts are 10.0.23"), [l for l in g.logs() if "KIT" in l])
        self.assertTrue(g.log_has("RANDO-OMEGA\tloaded"))
        g.R.grant("omega:enforcer")
        deliver(g)
        self.assertIn("Omega 1/1", g.R.status_text())


# ------------------------------------------------------------------- runtime: learning the flag's byte
class LearningTests(unittest.TestCase):
    def own(self, g, *ws):
        for w in ws:
            g.R.grant("weapon:" + w)
        deliver(g, 900)
        for w in ws:
            self.assertTrue(g.owns("weapon:" + w), w)

    def test_two_omega_purchases_teach_the_byte_then_pending_rewards_are_set(self):
        g = game()
        g.R.grant("omega:ricochet")
        deliver(g)
        self.assertTrue(g.owns("weapon:ricochet"))
        self.assertEqual(flag(g, "ricochet"), 0)                            # not learned: nothing written
        self.assertEqual(g.state.omega["ricochet"].status, "pending")
        self.assertTrue(g.note_has("set once the randomizer has found your game's Omega flag"))
        self.own(g, "enforcer", "mr_fungi")
        g.sim.enter_vendor(); g.step(120)
        g.sim.buy_omega(wid(g, "enforcer"), NAMES["enforcer"], True)      # with a Raritanium upgrade: 2 candidates
        g.step(120)
        self.assertIsNone(g.state.omega_cal.off)
        self.assertTrue(g.log_has("Omega purchase 1 of 2 (enforcer)"))
        g.sim.leave_vendor()
        self.assertEqual(flag(g, "ricochet"), 0)
        g.sim.enter_vendor(); g.step(120)
        g.sim.buy_omega(wid(g, "mr_fungi"), NAMES["mr_fungi"], False)
        g.step(120)
        g.sim.leave_vendor()
        self.assertEqual(g.state.omega_cal.off, OMEGA_AT)
        self.assertTrue(g.log_has("LEARNED: the Omega flag is the byte at +0x5B"))
        deliver(g, 900)
        self.assertEqual(flag(g, "ricochet"), 1)
        self.assertEqual(g.state.omega["ricochet"].status, "applied")

    def test_one_purchase_with_an_upgrade_never_teaches_a_wrong_byte(self):
        g = game()
        self.own(g, "enforcer", "mr_fungi")
        g.sim.OMEGA_AT = 0x170 + 0x20                                       # the real flag outside the bytes read
        g.sim.enter_vendor(); g.step(120)
        g.sim.mem[g.sim.inv_records[wid(g, "enforcer")] + 0x10 + 0x190] = 1
        g.sim.upgrade(wid(g, "enforcer"))                                   # only a mod byte changes in the span
        g.sim.emit("PurchaseWeaponEvent", g.lua.table_from({"WeaponName": NAMES["enforcer"]}))
        g.step(120)
        cal = g.state.omega_cal
        self.assertIsNone(cal.off)                                          # one purchase is never trusted
        g.sim.enter_vendor(); g.step(120)
        g.sim.emit("PurchaseWeaponEvent", g.lua.table_from({"WeaponName": NAMES["mr_fungi"]}))   # nothing changed
        g.step(120)
        self.assertIsNone(g.state.omega_cal.off)
        self.assertTrue(g.log_has("not an Omega purchase"))

    def test_a_byte_every_weapon_holds_as_1_is_never_a_candidate(self):
        g = game()
        self.own(g, "enforcer", "mr_fungi", "ricochet")
        for id_ in list(g.sim.inv_order.values()):                         # a field that is 1 in every record
            g.sim.mem[g.sim.inv_records[id_] + 0x10 + 0x60] = 1
        rec = g.sim.inv_records[wid(g, "enforcer")] + 0x10
        g.sim.mem[rec + 0x60] = 0                                           # (0 before the purchase, then 1)
        g.sim.enter_vendor(); g.step(120)
        g.sim.mem[rec + 0x60] = 1
        g.sim.emit("PurchaseWeaponEvent", g.lua.table_from({"WeaponName": NAMES["enforcer"]}))
        g.step(120)
        self.assertTrue(g.log_has("not an Omega purchase"))
        self.assertIsNone(g.state.omega_cal)

    def test_buying_a_new_weapon_teaches_nothing(self):
        g = game()
        self.own(g, "enforcer")
        g.sim.enter_vendor(); g.step(120)
        g.sim.vendor_buy(wid(g, "ricochet"), 5)
        g.sim.emit("PurchaseWeaponEvent", g.lua.table_from({"WeaponName": NAMES["ricochet"]}))
        g.step(120)
        self.assertIsNone(g.state.omega_cal)

    def test_learned_byte_survives_a_new_game(self):
        g = game()
        self.own(g, "enforcer", "mr_fungi")
        for w in ("enforcer", "mr_fungi"):
            g.sim.enter_vendor(); g.step(120)
            g.sim.buy_omega(wid(g, w), NAMES[w])
            g.step(120)
        self.assertEqual(g.state.omega_cal.off, OMEGA_AT)
        g.sim.new_game()
        g.step(300)
        self.assertEqual(g.state.run, 2)
        self.assertEqual(g.state.omega_cal.off, OMEGA_AT)
        self.assertEqual(len(list(g.state.omega.keys())), 0)


# --------------------------------------------------------------- save / load, New Game+, keeping it
class PersistenceTests(unittest.TestCase):
    def test_save_and_load_keep_the_tiers(self):
        g = game(offset=OMEGA_AT)
        g.R.grant("omega:burst_pistol")
        g.R.grant("weapon:enforcer")
        deliver(g)
        text = g.companion_export()
        g2 = Game(settings={"omega_flag_offset": OMEGA_AT})
        for id_ in list(g.sim.inv_order.values()):
            g2.sim.weapons_owned[id_] = True
            g2.sim.inv_add(id_)
        g2.sim.set_omega(wid(g2, "burst_pistol"), 1)                       # the game's save has the flag too
        g2.ready(saved=text)
        deliver(g2)
        self.assertEqual(g2.R.omega_tier("burst_pistol"), 2)
        self.assertEqual(g2.R.omega_tier("enforcer"), 1)
        self.assertEqual(g2.state.omega["burst_pistol"].status, "applied")
        self.assertTrue(g2.state.omega_prereq["burst_pistol"])
        g2.R.grant("weapon:burst_pistol")
        deliver(g2)
        self.assertEqual(g2.sim.omega_of(wid(g2, "burst_pistol")), 1)
        self.assertEqual(g2.give_count("weapon:burst_pistol"), 0)          # this session sent nothing

    def test_a_save_without_the_flag_gets_it_set_again(self):
        g = game(offset=OMEGA_AT)
        g.R.grant("omega:cold_snap")
        deliver(g)
        text = g.companion_export()
        g2 = Game(settings={"omega_flag_offset": OMEGA_AT})
        for id_ in list(g.sim.inv_order.values()):
            g2.sim.weapons_owned[id_] = True
            g2.sim.inv_add(id_)                                             # the game's save lost the flag
        g2.ready(saved=text)
        deliver(g2, 1200)
        self.assertEqual(g2.sim.omega_of(wid(g2, "cold_snap")), 1)
        self.assertTrue(g2.log_has("kept Omega Cold Snap"))

    def test_merge_keeps_the_furthest_omega_status(self):
        g = game(offset=OMEGA_AT)
        saved_before = g.companion_export()                                   # nothing yet
        g.R.grant("omega:enforcer")
        deliver(g)
        self.assertEqual(g.state.omega["enforcer"].status, "applied")
        g.companion_restore(saved_before)                                   # the companion connects late
        self.assertEqual(g.state.omega["enforcer"].status, "applied")
        self.assertTrue(g.state.inventory["omega:enforcer"])

    def test_loads_move_the_records_and_the_flag_is_found_again(self):
        g = game(offset=OMEGA_AT)
        g.R.grant("omega:enforcer")
        deliver(g)
        old = g.sim.inv_records[wid(g, "enforcer")]
        g.travel("Sargasso")
        deliver(g, 900)
        self.assertNotEqual(g.sim.inv_records[wid(g, "enforcer")], old)
        self.assertEqual(flag(g, "enforcer"), 1)
        self.assertTrue(g.log_has("inventory: "))

    def test_restore_inventory_sends_cannot_downgrade(self):
        g = game(offset=OMEGA_AT)
        g.sim.give_resets_omega = True                                      # the worst case (not seen in your game)
        g.R.grant("omega:enforcer")
        deliver(g)
        self.assertEqual(flag(g, "enforcer"), 1)
        g.real.restore_inventory("test")
        deliver(g, 1200)
        self.assertGreaterEqual(g.give_count("weapon:enforcer"), 2)       # sent again, the game cleared the flag ...
        self.assertEqual(flag(g, "enforcer"), 1)                            # ... and it was set again
        self.assertTrue(g.log_has("kept Omega Enforcer"))

    def test_new_game_plus_keeps_the_games_own_omegas(self):
        g = game(offset=OMEGA_AT)
        g.sim.give_resets_omega = True
        # Challenge Mode: the weapon carried over, already Omega in the game (bought in the first run)
        g.sim.weapons_owned[wid(g, "ricochet")] = True
        g.sim.inv_add(wid(g, "ricochet"))
        g.sim.set_omega(wid(g, "ricochet"), 1)
        g.travel("NefCity")
        deliver(g, 600)
        self.assertTrue(g.g.RANDO_OMEGA.game_omega["ricochet"])
        g.R.grant("weapon:ricochet")                                        # a normal reward for it
        deliver(g, 1200)
        self.assertEqual(flag(g, "ricochet"), 1)
        # and its Omega reward: the game already has it, nothing written
        g.R.grant("omega:ricochet")
        deliver(g)
        self.assertEqual(g.state.omega["ricochet"].status, "applied")
        self.assertEqual(g.state.omega["ricochet"].how, "the game already had it")


# -------------------------------------------------------------------------- a whole seed, end to end
class SeedTests(unittest.TestCase):
    def test_omega_seed_locations_pay_their_omega(self):
        g = Game(settings={"omega_weapons": True, "omega_flag_offset": OMEGA_AT, "seed": "omega-run"})
        self.assertFalse(g.load_errors)
        g.ready()
        lids = [lid for lid in sorted(g.seed.locations.keys())
                if str(g.seed.locations[lid].item or "").startswith("omega:")]
        self.assertEqual(len(lids), 20)
        for lid in lids[:5]:
            g.state.access[g.data.locations[lid].planet or "x"] = True
            g.R.collect(lid, "test")
        deliver(g, 2400)
        for lid in lids[:5]:
            w = g.seed.locations[lid].item.split(":", 1)[1]
            self.assertTrue(g.state.inventory["omega:" + w], w)
            self.assertEqual(g.R.omega_tier(w), 2)
            self.assertEqual(flag(g, w), 1, w)


class StartTests(unittest.TestCase):
    def test_an_omega_in_start_items_comes_with_its_weapon(self):
        g = Game(settings={"omega_weapons": True, "omega_flag_offset": OMEGA_AT, "seed": "omega-start",
                           "start_items": "omega:enforcer"})
        self.assertFalse(g.load_errors)
        g.ready()
        self.assertIn("omega:enforcer", list(g.seed.start["items"].values()))
        deliver(g, 1500)
        self.assertTrue(g.owns("weapon:enforcer"))
        self.assertEqual(g.give_count("weapon:enforcer"), 1)
        self.assertEqual(flag(g, "enforcer"), 1)
        starts = list(g.seed.start["items"].values())
        # the prerequisite unless the seed also starts with the Enforcer itself (then it was owned first)
        self.assertEqual(bool(g.state.omega_prereq["enforcer"]), "weapon:enforcer" not in starts)
        self.assertEqual(g.R.omega_tier("enforcer"), 2)
        self.assertTrue(g.note_has("Omega Enforcer"))                      # in the start text


# ---------------------------------------------------------------------------------- release safety
class ReleaseTests(unittest.TestCase):
    def test_17_ships_in_v060_with_omega_off_by_default(self):
        # v0.60 (the player's decision): 17 ships, but the player's settings keep omega_weapons = false because the
        # flag has not been written in the real game yet (rounds 27-44: "inventory not found")
        sys.path.insert(0, str(ROOT / "tools"))
        import build_public_release as b
        self.assertIn("17_rando_omega.lua", b.release_scripts())
        self.assertIn("17_rando_omega.lua", b.OPTIONAL)
        txt = (ROOT / "release" / "04_rando_settings.lua").read_text(encoding="utf-8")
        self.assertIn("omega_weapons = false,", txt)


if __name__ == "__main__":
    unittest.main()
