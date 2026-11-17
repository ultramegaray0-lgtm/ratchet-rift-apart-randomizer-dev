"""Regression against Randomizer 6.0: the 6.0 generator and data are taken from git (V6_COMMIT) and
run side by side with 7.0's balanced preset (the 6.0 defaults plus 7.0's currency and prices). What
7.0 must keep: the same reward locations, one grantable item per Gold Bolt, Hoverboots and the
Map-O-Matic at the start, the 27 armor items and sources, the shop's 15 slots selling the weapon
pool, every location giving something, and the same rando_give.dll. What 7.0 changes on purpose
(currency amounts, prices, levels) is checked in test_generator.py and test_levels.py."""
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from luajson import py  # noqa: E402

V6_COMMIT = "292fffe"   # "Randomizer 6.0: unified weapon registry, shop slot map, no phantom rewards"
SCRIPTS = "mod/RiftApartRandomizer/scripts/"


def git_show(path):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{V6_COMMIT}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


@unittest.skipUnless(git_show(SCRIPTS + "02_rando_generator.lua") is not None, "the 6.0 commit is not in this repository")
class RegressionV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from lupa import lua54
        import rando
        cls.v7 = rando.Engine()
        L = lua54.LuaRuntime(unpack_returned_tuples=True)
        for f in ("01_rando_data.lua", "03_rando_campaign.lua", "02_rando_generator.lua"):
            L.execute(git_show(SCRIPTS + f).decode("utf-8"))
        cls.v6 = L
        cls._gen6 = L.eval("function(seed, user) local s, err = RANDO_GEN.generate(seed, user, 'standard'); return s, err end")

    def gen6(self, seed, user=None):
        s, err = self._gen6(seed, self.v6.table_from(user or {}))
        self.assertIsNotNone(s, err)
        return py(s)

    def gen7(self, seed, user=None, preset="balanced"):
        s, err = self.v7.generate(seed, user or {}, preset)
        self.assertIsNotNone(s, err)
        self.assertEqual(err, [])
        return py(s)

    def test_versions(self):
        self.assertEqual(self.v6.globals().RANDO_GEN.VERSION, "6.0.0")
        self.assertEqual(self.v7.lua.globals().RANDO_GEN.VERSION, "8.0.0")

    def test_same_locations_and_rules(self):
        for i in range(80):
            a, b = self.gen6(f"reg6-{i}"), self.gen7(f"reg6-{i}")
            self.assertEqual(sorted(a["locations"]), sorted(b["locations"]), i)
            self.assertEqual(sorted(a["gold_bolts"]), sorted(b["gold_bolts"]), i)
            self.assertEqual(sorted(a["shop"]["slots"]), sorted(b["shop"]["slots"]))
            for s in (a, b):
                self.assertEqual(s["start"]["items"][:2], ["hoverboots", "map_o_matic"])
                bolts = [s["locations"][g].get("item") for g in s["gold_bolts"]]
                self.assertEqual(len(set(bolts)), 25)
                self.assertFalse(any(str(x).startswith("filler:") or x is None for x in bolts))
                self.assertEqual(len([1 for l in s["locations"].values() if str(l.get("item")).startswith("armor:")]), 27)
                self.assertEqual([k for k, l in s["locations"].items() if not l.get("item")], [])
                # the shop sells 15 weapons of the pool, and none of them anywhere else
                sold = set(s["shop"]["slots"].values())
                self.assertEqual(len(sold), 15)
                elsewhere = {l.get("item") for l in s["locations"].values()} | set(s["start"]["items"])
                self.assertFalse(sold & elsewhere)

    def test_6_settings_still_work(self):
        """a 6.0 settings file keeps working: filler settings are converted, nothing is refused"""
        b = self.gen7("reg6-old", {"filler": "mixed", "filler_bolts": 5000, "filler_raritanium": 5,
                                   "include_arsenal_restored": False, "planet_locks": True}, "standard")
        self.assertTrue(b["settings"]["planet_locks"])
        self.assertFalse(b["settings"]["travel_lock"])                 # 6.0's planet_locks = rewards wait
        self.assertTrue(all(int(l["item"].split(":")[2]) in (5000, 5)
                            for l in b["locations"].values() if str(l.get("item")).startswith("filler:")))

    def test_same_helper_dll(self):
        """8.0 replaced rando_give.dll (v6: new request kinds). Everything the earlier helper did
        is kept: every expected byte array, RVA, mailbox offset, kind and result code of the old
        source is in the new source, unchanged."""
        old = git_show("mod/RiftApartRandomizer/rando_give_source/rando_give_core.h").decode("utf-8")
        new = open(os.path.join(ROOT, "mod", "RiftApartRandomizer", "rando_give_source", "rando_give_core.h"), encoding="utf-8").read()

        def arrays(src):
            return {m.group(1): m.group(2).split() for m in re.finditer(r"static const u8 (RG_\w+)\[[^\]]+\] = \{(.*?)\};", src, re.S)}

        def defines(src):
            return dict(re.findall(r"#define ((?:RVA|MB|RG|MS|MS2|CFG|HOOK)_\w+) (\S+)", src))

        def enums(src):
            return dict(re.findall(r"\t(RG_(?:STATUS|RESULT|KIND|ARMOR)_\w+) = (\d+)", src))
        na, nd, ne = arrays(new), defines(new), enums(new)
        for name, body in arrays(old).items():
            self.assertEqual(na.get(name), body, name)
        for name, value in defines(old).items():
            if name != "RG_VERSION":
                self.assertEqual(nd.get(name), value, name)
        for name, value in enums(old).items():
            self.assertEqual(ne.get(name), value, name)
        self.assertIn("#define RG_VERSION 7u", new)


if __name__ == "__main__":
    unittest.main()
