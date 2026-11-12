"""Regression against Randomizer 8.3 (git commit V83_COMMIT, the kit round 20 ran): 8.4 is a
stabilization release, so the same seed must give the SAME seed - fingerprint, every location's
item, Gold Bolts, the shop, currency, start items and the hub plan - in every preset. The only
intended difference is the hero (and entry checkpoint) of four hub destinations, which the plan
copies from the registry and which never enters the fingerprint. Progress saved by 8.3 therefore
carries over."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from luajson import py  # noqa: E402

V83_COMMIT = "c08e8fe"   # "8.3: story starts on arrival (any order), stuck-story restart, keyboard keys"
SCRIPTS = "mod/RiftApartRandomizer/scripts/"
CHANGED = {"nefcity_1": ("rivet", "ratchet"), "sargasso_2": ("ratchet", "rivet"),
           "ardolis_1": ("rivet", "ratchet"), "viceron_1": ("ratchet", "rivet")}
ENTRY = {"cordelion_1": "CHK_CORD_A_START", "ardolis_1": "CHK_ARD_START", "viceron_1": "CHK_ZORDOOM_START"}


def git_show(path):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{V83_COMMIT}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


@unittest.skipUnless(git_show(SCRIPTS + "02_rando_generator.lua") is not None, "the 8.3 commit is not in this repository")
class RegressionV83Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from lupa import lua54
        import rando
        cls.new = rando.Engine()
        L = lua54.LuaRuntime(unpack_returned_tuples=True)
        for f in ("01_rando_data.lua", "03_rando_campaign.lua", "02_rando_generator.lua"):
            L.execute(git_show(SCRIPTS + f).decode("utf-8"))
        cls.old = L
        cls._gen_old = L.eval("function(seed, user, preset) local s, err = RANDO_GEN.generate(seed, user, preset); return s, err end")

    def gen_old(self, seed, preset):
        s, err = self._gen_old(seed, self.old.table_from({}), preset)
        self.assertIsNotNone(s, err)
        return py(s)

    def gen_new(self, seed, preset):
        s, err = self.new.generate(seed, {}, preset)
        self.assertIsNotNone(s, err)
        return py(s)

    def test_same_seeds_in_every_preset(self):
        presets = ["hub", "hub_chaos", "balanced", "chaos", "full", "campaign", "everything"]
        n = 0
        for preset in presets:
            for i in range(25):
                seed = f"reg83-{preset}-{i}"
                a, b = self.gen_old(seed, preset), self.gen_new(seed, preset)
                for key in ("fingerprint", "locations", "gold_bolts", "shop", "start", "settings"):
                    self.assertEqual(a.get(key), b.get(key), f"{seed}: {key}")
                if a.get("hub"):
                    ha, hb = a["hub"], b["hub"]
                    self.assertEqual(ha["start"], hb["start"], seed)
                    da = {d["id"]: d for d in ha["destinations"]}
                    db = {d["id"]: d for d in hb["destinations"]}
                    self.assertEqual(list(da), list(db), seed)
                    for did in da:
                        x, y = dict(da[did]), dict(db[did])
                        if did in CHANGED:
                            self.assertEqual((x.pop("hero"), y.pop("hero")), CHANGED[did], seed)
                        if did in ENTRY:
                            self.assertEqual(y.pop("entry", None), ENTRY[did], seed)
                            x.pop("entry", None)
                        self.assertEqual(x, y, f"{seed}: {did}")
                n += 1
        self.assertEqual(n, 25 * len(presets))


if __name__ == "__main__":
    unittest.main()
