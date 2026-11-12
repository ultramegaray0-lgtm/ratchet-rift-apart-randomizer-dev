"""Regression against Randomizer 8.4 (git commit V84_COMMIT, the kit delivered as 8.4): 8.5 changes
no generation code, so the same seed must give the IDENTICAL seed - every field, the hub plan with
its heroes and entries included - in every preset. Progress saved by 8.4 (and 8.3) carries over."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from luajson import py  # noqa: E402

V84_COMMIT = "350a34f"   # "8.4 RC: install manifest test, final test counts"
SCRIPTS = "mod/RiftApartRandomizer/scripts/"


def git_show(path):
    r = subprocess.run(["git", "-C", ROOT, "show", f"{V84_COMMIT}:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


@unittest.skipUnless(git_show(SCRIPTS + "02_rando_generator.lua") is not None, "the 8.4 commit is not in this repository")
class RegressionV84Tests(unittest.TestCase):
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

    def test_identical_seeds_in_every_preset(self):
        presets = ["hub", "hub_chaos", "balanced", "chaos", "full", "campaign", "everything"]
        n = 0
        for preset in presets:
            for i in range(25):
                seed = f"reg84-{preset}-{i}"
                a, err = self._gen_old(seed, self.old.table_from({}), preset)
                self.assertIsNotNone(a, err)
                b, err = self.new.generate(seed, {}, preset)
                self.assertIsNotNone(b, err)
                self.assertEqual(py(a), py(b), seed)
                n += 1
        self.assertEqual(n, 25 * len(presets))

    def test_only_version_tags_changed_in_the_generation_scripts(self):
        here = os.path.join(ROOT, SCRIPTS)
        for f in ("01_rando_data.lua", "02_rando_generator.lua", "03_rando_campaign.lua", "05_rando_bindings.lua"):
            old = git_show(SCRIPTS + f).decode("utf-8").replace('"8.4.0"', '"8.5.0"')
            with open(os.path.join(here, f), encoding="utf-8") as fh:
                self.assertEqual(old, fh.read(), f)


if __name__ == "__main__":
    unittest.main()
