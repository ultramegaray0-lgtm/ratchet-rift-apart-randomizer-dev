#!/usr/bin/env python3
"""Offline tests for the generated cross-planet actor asset catalog."""
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "stage_enemies"))
import stage_allgame as SA  # noqa: E402


class Brain:
    def regular(self, kind, asset=None):
        if kind.endswith("_boss"):
            return False, None, "boss"
        return True, "ground", "known regular enemy"


class GlobalAssetManifestTests(unittest.TestCase):
    def test_manifest_deduplicates_paths_and_excludes_non_enemies(self):
        scan = SimpleNamespace(actor_catalog={}, zones={}, template_catalog_all={
            "1111111111111111": {"kind": "enm_pirate_robot_melee", "asset": r"characters\pirate\melee.actor", "planet": "ardolis"},
            "2222222222222222": {"kind": "enm_pirate_robot_melee", "asset": "characters/pirate/melee.actor", "planet": "sargasso"},
            "3333333333333333": {"kind": "enm_story_boss", "asset": "characters/boss.actor", "planet": "cordelion"},
        })
        with tempfile.TemporaryDirectory() as out:
            rows = SA.write_global_enemy_asset_manifest(scan, Brain(), out)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["path"], "characters/pirate/melee.actor")
            with open(os.path.join(out, SA.GLOBAL_ASSET_LUA), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn('path = "characters/pirate/melee.actor"', text)
            self.assertNotIn("characters/boss.actor", text)

    def test_manifest_excludes_ambiguous_path_metadata(self):
        scan = SimpleNamespace(actor_catalog={}, zones={}, template_catalog_all={
            "1111111111111111": {"kind": "enm_pirate_robot_melee", "asset": "shared/enemy.actor"},
            "2222222222222222": {"kind": "enm_neo_nefarious_shooter", "asset": "shared/enemy.actor"},
        })
        with tempfile.TemporaryDirectory() as out:
            rows = SA.write_global_enemy_asset_manifest(scan, Brain(), out)
            self.assertEqual(rows, [])
            with open(os.path.join(out, SA.GLOBAL_ASSET_LUA), encoding="utf-8") as fh:
                self.assertIn("RANDO_GLOBAL_ENEMY_ASSETS = {", fh.read())


if __name__ == "__main__":
    unittest.main()
