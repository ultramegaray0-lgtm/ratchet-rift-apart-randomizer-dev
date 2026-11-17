"""Regression against Randomizer 5.0: the 5.0 generator and data are taken from git (the commit
tagged in V5_COMMIT) and run side by side with 6.0 on the same seeds. What 6.0 must keep: the
same reward locations, one item per Gold Bolt, the fixed start, the 27 armor items and sources,
filler everywhere else, and the same rando_give.dll. What 6.0 changes on purpose (weapons) is
checked in test_generator.py and test_registry.py."""
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from luajson import py  # noqa: E402

V5_COMMIT = "2866d4a"   # "5.0: Blackhole Storm = wpn_warprifle; shuffled weapon shop ..."
SCRIPTS = "mod/RiftApartRandomizer/scripts/"


def git_show(path):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{V5_COMMIT}:{path}"], capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout


def v5_available():
    return git_show(SCRIPTS + "02_rando_generator.lua") is not None


@unittest.skipUnless(v5_available(), "the 5.0 commit is not in this repository (git history needed)")
class RegressionV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from lupa import lua54
        import rando
        cls.v6 = rando.Engine()
        L = lua54.LuaRuntime(unpack_returned_tuples=True)
        for f in ("01_rando_data.lua", "03_rando_campaign.lua", "02_rando_generator.lua"):
            L.execute(git_show(SCRIPTS + f).decode("utf-8"))
        cls.v5 = L
        cls._gen5 = L.eval("function(seed, user) local s, err = RANDO_GEN.generate(seed, user, 'standard'); return s, err end")

    def gen5(self, seed, user=None):
        s, err = self._gen5(seed, self.v5.table_from(user or {}))
        self.assertIsNotNone(s, err)
        return py(s)

    def gen6(self, seed, user=None):
        s, err = self.v6.generate(seed, user or {}, "standard")
        self.assertIsNotNone(s, err)
        return py(s)

    def test_versions(self):
        self.assertEqual(self.v5.globals().RANDO_GEN.VERSION, "5.0.0")
        self.assertEqual(self.v6.lua.globals().RANDO_GEN.VERSION, "8.0.0")      # the current generator

    def test_same_reward_locations_and_rules(self):
        # 5.0's defaults put ARSENAL_RESTORED in the pool; compare like with like
        user = {"include_arsenal_restored": True}
        for i in range(60):
            a, b = self.gen5(f"reg-{i}", user), self.gen6(f"reg-{i}", user)
            self.assertEqual(sorted(a["locations"]), sorted(b["locations"]), i)
            self.assertEqual(sorted(a["gold_bolts"]), sorted(b["gold_bolts"]), i)
            for s in (a, b):
                self.assertEqual(s["start"]["items"][:2], ["hoverboots", "map_o_matic"])
                bolts = [s["locations"][g].get("item") for g in s["gold_bolts"]]
                self.assertEqual(len(set(bolts)), 25)
                self.assertFalse(any(str(x).startswith("filler:") or x is None for x in bolts))
                armor = sorted(l["item"] for l in s["locations"].values() if str(l.get("item")).startswith("armor:"))
                self.assertEqual(len(armor), 27)
                srcs = [k for k in s["locations"] if k.startswith("source:")]
                self.assertEqual(len(srcs), 27)
                empty = [k for k, l in s["locations"].items() if not l.get("item")]
                self.assertEqual(empty, [])
            # armor is the same set of items in both
            self.assertEqual(sorted(l["item"] for l in a["locations"].values() if str(l.get("item")).startswith("armor:")),
                             sorted(l["item"] for l in b["locations"].values() if str(l.get("item")).startswith("armor:")))

    def test_6_never_does_what_5_could(self):
        """5.0 put no vendor weapon anywhere but the shop; 6.0 may, but then not in the shop too"""
        for i in range(60):
            b = self.gen6(f"reg-b-{i}")
            sold = set(b["shop"]["slots"].values())
            placed = {l.get("item") for l in b["locations"].values()} | set(b["start"]["items"])
            self.assertFalse(sold & placed, i)

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
