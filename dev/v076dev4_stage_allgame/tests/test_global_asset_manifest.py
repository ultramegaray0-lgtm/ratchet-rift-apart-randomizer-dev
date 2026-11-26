#!/usr/bin/env python3
"""Offline tests for the generated cross-planet actor asset catalog."""
import json
import os
import random
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

    def test_runtime_spawner_script_parses_as_lua54(self):
        from lupa import LuaRuntime
        root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
        script = os.path.join(root, "mod", "RiftApartRandomizer", "scripts", "16_rando_spawners.lua")
        with open(script, encoding="utf-8") as fh:
            source = fh.read()
        lua = LuaRuntime()
        compile_lua = lua.eval("function(source) return load(source) end")
        compiled = compile_lua(source)
        self.assertIsNotNone(compiled, "16_rando_spawners.lua did not parse")

    def test_manifest_includes_factory_and_real_spawner_template_assets_only(self):
        scan = SimpleNamespace(
            actor_catalog={"1111111111111111": [
                {"kind": "enm_pirate_robot_melee", "asset": "actors/unused_placed_enemy.actor"}
            ]},
            zones={"2222222222222222": {
                "planet": "sargasso", "zone": "sargasso.zone",
                "template_nodes": [
                    {"uid": "3333333333333333", "kind": "enm_neo_nefarious_shooter",
                     "asset": "actors/nefarious.actor", "is_spawner_class": True},
                    {"uid": "4444444444444444", "kind": "enm_pirate_robot_melee",
                     "asset": "actors/not_a_spawner.actor", "is_spawner_class": False},
                ]
            }},
            template_catalog_all={
                "5555555555555555": {"kind": "enm_pirate_robot_melee", "asset": "actors/pirate.actor"}
            },
        )
        with tempfile.TemporaryDirectory() as out:
            rows = SA.write_global_enemy_asset_manifest(scan, Brain(), out)
            self.assertEqual({row["path"] for row in rows},
                             {"actors/pirate.actor", "actors/nefarious.actor"})

    def test_runtime_registry_uses_preload_and_one_spawn_per_frame(self):
        root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
        script = os.path.join(root, "mod", "RiftApartRandomizer", "scripts", "16_rando_spawners.lua")
        with open(script, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("V.GLOBAL_SPAWNS_PER_FRAME = 1", source)
        self.assertIn("V.GLOBAL_REQUESTS_PER_FRAME = 4", source)
        self.assertIn("V.GLOBAL_POLLS_PER_FRAME = 4", source)
        self.assertIn("rivet.template_actor, item.row.path, item.uid, false", source)
        self.assertIn("rivet.template_actor, item.row.path, item.uid, true", source)
        self.assertIn("rivet.on_frame(function()", source)
        self.assertIn("V.global_frame_ready = ready", source)
        self.assertNotIn("  V.global_templates_tick(frame)", source)

    def test_stage_monitor_handshake_disables_runtime_writes(self):
        root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
        runtime_path = os.path.join(root, "mod", "RiftApartRandomizer", "scripts", "16_rando_spawners.lua")
        stage_path = os.path.join(HERE, "..", "scripts", "18_rando_stage_enemies.lua")
        with open(runtime_path, encoding="utf-8") as fh:
            runtime = fh.read()
        with open(stage_path, encoding="utf-8") as fh:
            stage = fh.read()
        self.assertIn('V.STAGE_LUA = "1.1.0"', runtime)
        self.assertIn('function V.stage_manifest() return RANDO_STAGE_ENEMIES end', runtime)
        self.assertIn('function V.stage_mode() return type(V.stage_manifest()) == "table" end', runtime)
        self.assertIn("function V.stage_owns_rec(r)", runtime)
        self.assertIn('if manifest.profile ~= "v3" then return true end', runtime)
        self.assertIn('return V.stage_factory_keys[key] == true', runtime)
        self.assertIn('return V.stage_node_keys[key] == true', runtime)
        self.assertIn('if V.stage_owns_rec(r) then return note_why(r, ".stage owns this " .. tostring(r.kind) .. " Template variable") end', runtime)
        self.assertIn("if V.stage_tick then pcall(V.stage_tick, frame, ready, V.enabled()) end", runtime)
        self.assertIn("pcall(V.stage_on_spawn, e, r, a", runtime)
        self.assertIn("pcall(V.stage_on_death, h)", runtime)
        self.assertIn("function V.global_templates_tick(frame)\n  if not V.enabled() then return end", runtime)
        self.assertIn("if not V.enabled() then return end", runtime)
        self.assertNotIn("if not V.enabled() or V.stage_mode() then return end", runtime)
        self.assertIn('if not (SP and SP.V and SP.V.stage_mode) then', stage)
        self.assertIn('local expected_adapter = c.adapter or "factory"', stage)
        self.assertIn('r.kind == "template" and "node_template" or nil', stage)
        self.assertIn('if not c and V.stage_manifest().profile ~= "v3" and uid then', stage)
        self.assertIn('ST.STAGE_LUA = "1.1.0"', stage)
        self.assertIn('RANDO_FILES["18_rando_stage_enemies"] = "10.0.50"', stage)
        self.assertIn('RANDO_FILES["16_rando_spawners"] = "10.0.50"', runtime)

    def test_v3_profile_keeps_shared_factories_native_and_owns_only_manifest_keys(self):
        builder_path = os.path.join(HERE, "..", "tools", "stage_enemies", "stage_allgame.py")
        with open(builder_path, encoding="utf-8") as fh:
            builder = fh.read()
        self.assertIn('if opts.profile in ("safe", "v3") or (opts.profile == "max" and unseen):', builder)
        self.assertIn('profile = %s, label = %s, stage_lua = %s', builder)
        self.assertIn('if nd["key"] == 0:', builder)
        self.assertIn('nd["key"] == 0 else', builder)

    def test_v3_node_template_planner_only_changes_exact_single_owner_local_spawners(self):
        class FakeBrain:
            def regular(self, kind, asset=None):
                return True, "ground", "fixture"
            def pair(self, original, original_family, replacement, replacement_family):
                return (original != replacement, "proven", "fixture pair")
            def family(self, kind, asset=None):
                return "ground", "fixture"

        factories = [
            {"key": "FACTORY-A", "form": "local", "uid": "1111111111111111",
             "kind": "enm_pirate_robot_shooter", "asset": "actors/shooter.actor", "rec": 0, "problem": None},
            {"key": "FACTORY-B", "form": "local", "uid": "2222222222222222",
             "kind": "enm_pirate_robot_melee", "asset": "actors/melee.actor", "rec": 1, "problem": None},
        ]
        def node(key, var_index, uid, kind, rec, owners=1):
            return {"key": key, "action": 0, "class": "SPAWNER", "is_spawner_class": True,
                    "template_plug": 1, "template_plug_count": 1, "var_index": var_index,
                    "form": "local", "uid": uid, "kind": kind, "asset": "actors/%s.actor" % kind,
                    "rec": rec, "owners": owners, "co_owner_classes": [], "other_plugs": "", "problem": ""}
        rec = {"zone": "fixture.zone", "zone_id": "ABCDEF0123456789", "planet": "fixture",
               "factories": factories,
               "template_nodes": [
                   node("NODE-A", 2, "1111111111111111", "enm_pirate_robot_shooter", 0),
                   node("NODE-B", 3, "2222222222222222", "enm_pirate_robot_melee", 1),
                   node("NODE-SHARED", 4, "1111111111111111", "enm_pirate_robot_shooter", 0, owners=2),
                   dict(node("0000000000000000", 5, "1111111111111111", "enm_pirate_robot_shooter", 0),
                        problem="zero Script Action key: no stable runtime identity for the stage manifest"),
               ]}
        opts = SimpleNamespace(verdict_map={}, rate=1.0)
        changes, decisions = SA.plan_node_template_adapters(
            SimpleNamespace(), FakeBrain(), rec, opts, random.Random("v3-node-test"), [], {})
        self.assertEqual({c["key"] for c in changes}, {"NODE-A", "NODE-B"})
        self.assertTrue(all(c["adapter"] == "node_template" for c in changes))
        self.assertEqual(decisions["NODE-SHARED"][0], "refused")
        self.assertEqual(decisions["0000000000000000"][0], "refused")
        self.assertTrue(all(c["replacement_index"] in (0, 1) for c in changes))

    def test_v3_node_only_zone_keeps_one_anchor_and_replaces_the_other_node(self):
        class FakeBrain:
            def regular(self, kind, asset=None):
                return True, "ground", "fixture"
            def pair(self, original, original_family, replacement, replacement_family):
                return (original != replacement, "proven", "fixture pair")
            def family(self, kind, asset=None):
                return "ground", "fixture"

        def node(key, var_index, uid, kind, rec):
            return {"key": key, "action": 0, "class": "SPAWNER", "is_spawner_class": True,
                    "template_plug": 1, "template_plug_count": 1, "var_index": var_index,
                    "form": "local", "uid": uid, "kind": kind, "asset": "actors/%s.actor" % kind,
                    "rec": rec, "owners": 1, "co_owner_classes": [], "other_plugs": "", "problem": ""}
        rec = {"zone": "node_only.zone", "zone_id": "ABCDEF0123456789", "planet": "fixture",
               "factories": [], "template_nodes": [
                   node("NODE-A", 2, "1111111111111111", "enm_pirate_robot_shooter", 0),
                   node("NODE-B", 3, "2222222222222222", "enm_pirate_robot_melee", 1),
               ]}
        changes, decisions = SA.plan_node_template_adapters(
            SimpleNamespace(), FakeBrain(), rec, SimpleNamespace(verdict_map={}, rate=1.0),
            random.Random("v3-node-only"), [], {})
        self.assertEqual(len(changes), 1)
        self.assertEqual(sum(1 for value in decisions.values() if value[0] == "anchor"), 1)
        self.assertEqual(sum(1 for value in decisions.values() if value[0] == "changed"), 1)

    def test_v3_installer_bundles_one_synchronized_runtime_kit(self):
        root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
        runtime_dir = os.path.join(root, "mod", "RiftApartRandomizer", "scripts")
        self.assertEqual(SA.VERSION, "3.0.0-alpha.1")
        self.assertIn("runtime_scripts", SA.RUNTIME_BUNDLE_DIR)
        self.assertIn("runtime_scripts", str(SA.INSTALL_FILES))
        self.assertGreaterEqual(len(SA.RUNTIME_SCRIPT_NAMES), 18)
        for name in SA.RUNTIME_SCRIPT_NAMES:
            with open(os.path.join(runtime_dir, name), encoding="utf-8") as fh:
                source = fh.read()
            self.assertIn('RANDO_FILES["' + name[:-4] + '"] = "10.0.50"', source, name)

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
