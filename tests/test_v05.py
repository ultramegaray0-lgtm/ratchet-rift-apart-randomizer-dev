"""Public Release v0.5: every Gold Bolt gives exactly one item.

The kit's 04_rando_settings.lua now sets distribution = "goldbolts_first". For hub seeds, the
goldbolts_first fill also keeps 10.0's early game (early_weapons weapons and one Coordinates where
the start alone reaches, Gold Bolts there first). Everything else must be exactly 10.0:
  - spread seeds are identical to 10.0 (commit bd0017a), field for field;
  - non-hub (pre-10.0) goldbolts_first seeds are identical to 10.0, field for field
(compared with the version string set back to 10.0.0, since it feeds every seed's fingerprint).
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "tools")]
import rando  # noqa: E402
from luajson import py  # noqa: E402
from harness import MOD  # noqa: E402
from test_v90 import USER_SETTINGS  # noqa: E402
from test_v100 import verify_hub_seed  # noqa: E402

ENG = rando.Engine(str(MOD / "scripts"))
BOLT_WORTHY = ENG.lua.eval("function(k) return RANDO_GEN.bolt_worthy(k) end")
BASE_COMMIT = "bd0017a"


def old_engine():
    """The 10.0 generator (scripts 01-03 from bd0017a), or None without git history."""
    tmp = tempfile.mkdtemp(prefix="rando10_")
    try:
        for f in ("01_rando_data.lua", "02_rando_generator.lua", "03_rando_campaign.lua"):
            src = subprocess.run(["git", "show", f"{BASE_COMMIT}:mod/RiftApartRandomizer/scripts/{f}"], cwd=ROOT,
                                 capture_output=True, check=True).stdout
            (pathlib.Path(tmp) / f).write_bytes(src)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return rando.Engine(tmp)


def gold_bolt_problems(d):
    probs = []
    gbs = [lid for lid in d["locations"] if lid.startswith("goldbolt:")]
    if len(gbs) != 25:
        probs.append("%d Gold Bolts" % len(gbs))
    for lid in gbs:
        it = d["locations"][lid].get("item")
        if not it or it.startswith("filler:") or not BOLT_WORTHY(it):
            probs.append("%s holds %s" % (lid, it))
    return probs


def early(d):
    first = set(d["spheres"][0])
    items = [(d["locations"].get(lid) or {}).get("item") or "" for lid in first]
    return sum(i.startswith("weapon:") for i in items), sum(i.startswith("access:") for i in items)


class KitSettingsTests(unittest.TestCase):
    def test_kit_sets_goldbolts_first(self):
        preset, user = USER_SETTINGS()
        self.assertEqual(user.get("distribution"), "goldbolts_first")
        self.assertEqual(preset, "balanced")

    def test_every_gold_bolt_is_an_item_with_the_kit_settings(self):
        preset, user = USER_SETTINGS()
        for ar in (False, True):
            for i in range(150):
                s, audit = ENG.generate(f"v05-kit-{ar}-{i}", dict(user, restored_weapons=ar), preset)
                self.assertIsNotNone(s, audit)
                self.assertEqual(audit, [])
                d = py(s)
                self.assertTrue(d["settings"]["hub"])
                self.assertEqual(gold_bolt_problems(d), [])
                self.assertEqual(verify_hub_seed(d), [])
                w, c = early(d)
                self.assertGreaterEqual(w, 2, "early weapons")
                self.assertGreaterEqual(c, 1, "early Coordinates")
                self.assertIn("hoverboots", d["start"]["items"])
                self.assertIn("map_o_matic", d["start"]["items"])

    def test_every_preset(self):
        for p in ("balanced", "chaos", "full", "campaign", "everything"):
            for ar in (False, True):
                for i in range(40):
                    s, audit = ENG.generate(f"v05-{p}-{ar}-{i}", {"distribution": "goldbolts_first", "restored_weapons": ar}, p)
                    self.assertIsNotNone(s, (p, audit))
                    self.assertEqual(audit, [], p)
                    d = py(s)
                    self.assertEqual(gold_bolt_problems(d), [], p)
                    self.assertEqual(verify_hub_seed(d), [], p)
                    w, c = early(d)
                    self.assertGreaterEqual(w, min(2, d["settings"]["early_weapons"]), p)
                    self.assertGreaterEqual(c, 1, p)

    def test_tight_settings_lower_early_weapons_instead_of_failing(self):
        # big_batch hub-random 756: armor off + early_weapons 6 + weapon logic left no Gold Bolt the
        # start reaches for the progression; v0.5 lowers early_weapons (with a note) and the seed works
        u = {"distribution": "goldbolts_first", "armor": False, "hub": True, "early_weapons": 6,
             "include_arsenal_restored": True, "start_weapons": 5, "start_gadgets": 0, "shop_weapons": 16,
             "start_coordinates": "start_only", "weapon_logic": "standard", "campaign_mode": "full"}
        s, audit = ENG.generate("big10r-756-0", u, "campaign")
        self.assertIsNotNone(s, audit)
        self.assertEqual(audit, [])
        d = py(s)
        self.assertEqual(gold_bolt_problems(d), [])
        self.assertEqual(verify_hub_seed(d), [])
        self.assertTrue(any(w.startswith("early_weapons lowered") for w in d["warnings"]), d["warnings"])

    def test_early_weapons_zero_places_none_on_purpose(self):
        s, audit = ENG.generate("v05-ew0", {"distribution": "goldbolts_first", "early_weapons": 0}, "balanced")
        self.assertEqual(audit, [])
        self.assertEqual(gold_bolt_problems(py(s)), [])


class UnchangedFrom10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = old_engine()
        # v0.5 is generator 10.0.1 (v0.51: 10.0.2), and the version is part of every seed's fingerprint
        # (and so of its random stream). To prove the LOGIC is unchanged, this copy runs as 10.0.0.
        cls.new = rando.Engine(str(MOD / "scripts"))
        cls.new.lua.execute('RANDO_GEN.VERSION = "10.0.0"')

    # v0.51 (10.0.2) moved the hub to Nefarious City: the hub plan's planet, checkpoints and each
    # destination's kind and menu label changed on purpose (tests/test_v051.py checks exactly that).
    # Everything else of a hub seed - placements, route, start, shop, spoiler data - must not.
    HUB_FIELDS_V051 = ("planet", "checkpoints")
    DEST_FIELDS_V051 = ("kind", "label")

    @classmethod
    def mask(cls, d):
        if isinstance(d, dict) and isinstance(d.get("hub"), dict):
            for k in cls.HUB_FIELDS_V051:
                d["hub"].pop(k, None)
            for dest in d["hub"].get("destinations") or []:
                for k in cls.DEST_FIELDS_V051:
                    dest.pop(k, None)
        return d

    def same(self, user, preset, n, tag):
        if self.old is None:
            self.skipTest("the 10.0 commit is not in this repository (git history needed)")
        for i in range(n):
            a, aa = self.new.generate(f"v05-same-{tag}-{i}", user, preset)
            b, ba = self.old.generate(f"v05-same-{tag}-{i}", user, preset)
            self.assertEqual(self.mask(py(a)) if a is not None else aa, self.mask(py(b)) if b is not None else ba, f"{tag} {i}")

    def test_spread_hub_seeds_identical(self):
        for p in ("balanced", "chaos", "everything"):
            self.same({"distribution": "spread"}, p, 15, "spread-" + p)

    def test_non_hub_goldbolts_first_seeds_identical(self):
        for p in ("balanced", "chaos", "full", "campaign", "everything"):
            self.same({"hub": False, "distribution": "goldbolts_first", "shop_weapons": 15}, p, 15, "pre10-" + p)

    def test_hub_false_with_kit_settings_identical(self):
        preset, user = USER_SETTINGS()
        self.same(dict(user, hub=False), preset, 20, "kit-nohub")


if __name__ == "__main__":
    unittest.main()
