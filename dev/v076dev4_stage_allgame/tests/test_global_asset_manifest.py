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

    def test_native_resident_templates_clear_all_lifecycle_flags_checked_by_lua(self):
        root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
        patch_path = os.path.join(root, "tools", "global_registry", "patch_rivet_hook.py")
        runtime_path = os.path.join(root, "mod", "RiftApartRandomizer", "scripts", "16_rando_spawners.lua")
        with open(patch_path, encoding="utf-8") as fh:
            patch = fh.read()
        with open(runtime_path, encoding="utf-8") as fh:
            runtime = fh.read()
        clear = "actor->flags &= ~(ActorFlag::Activated | ActorFlag::StartedActive | ActorFlag::UpdateEnabled | (1u << 7) | (1u << 8));"
        self.assertEqual(patch.count(clear), 4, "both native creation/reuse code and both patch anchors clear unload flags")
        self.assertIn("local inactive_mask = 0x1 | 0x8 | 0x80 | 0x100 | 0x2000", runtime)
        self.assertIn("(actor_flags & 0x4) == 0 or (actor_flags & inactive_mask) ~= 0", runtime)

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

    def test_v3_next_build_and_log_check_keep_the_hybrid_profile(self):
        root = os.path.abspath(os.path.join(HERE, ".."))
        next_path = os.path.join(root, "BUILD_NEXT_VERDICT_GUIDED.bat")
        build_path = os.path.join(root, "BUILD_V3_0_MAX_COVERAGE.bat")
        check_path = os.path.join(root, "CHECK_MY_LOG.bat")
        with open(next_path, encoding="utf-8") as fh:
            next_build = fh.read()
        with open(build_path, encoding="utf-8") as fh:
            v3_build = fh.read()
        with open(check_path, encoding="utf-8") as fh:
            check_log = fh.read()
        self.assertIn("--profile v3 --rate 1.0 %VERD%", next_build)
        self.assertIn('echo %CD%\\%OUT%', v3_build)
        self.assertIn("LAST_INSTALLED.txt", v3_build)
        self.assertIn("stage_check_log.py", check_log)
        self.assertIn("--manifest", check_log)
        self.assertIn("LAST_INSTALLED.txt", check_log)

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
        self.assertIn('if a.profile == "v3" and (getattr(a, "cross_planet", False) or getattr(a, "force_all_enemies", False)):', builder)

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

    def test_zone_census_marks_only_all_spawner_template_co_owners_safe(self):
        def make_zone(second_class, second_plug):
            zone = SA.Zone.__new__(SA.Zone)
            first = {"r": 0, "key": 0xAAA, "cls": SA.NODE_SPAWNER_CLASS, "plugs": [0]}
            second = {"r": 1, "key": 0xBBB, "cls": second_class, "plugs": [1]}
            zone.nodes = [first, second]
            zone.plugs = [(SA.PLUG_TEMPLATE, 0, 0), (second_plug, 0, 0)]
            uid = int("1111111111111111", 16)
            zone.vars = [(5, 0, 0, 0, 0, uid, 0)]
            zone.owners = {0: [(first, 0, SA.PLUG_TEMPLATE), (second, 1, second_plug)]}
            zone.actors = [(0, 0, 0, 0, 0, 0, uid)]
            zone.asset_paths = ["actors/enm_pirate_robot_shooter.actor"]
            zone.rec_of = {uid: 0}
            zone.dup_uids = {}
            zone.dup_keys = set()
            return zone

        safe = make_zone(SA.NODE_SPAWNER_CLASS, SA.PLUG_TEMPLATE).template_nodes()
        self.assertEqual(len(safe), 2)
        self.assertTrue(all(n["shared_spawner_safe"] for n in safe))
        self.assertTrue(all(n["spawner_keys"] == ["0000000000000AAA", "0000000000000BBB"] for n in safe))

        generic_owner = make_zone(0xDEADBEEF, SA.PLUG_TEMPLATE).template_nodes()
        self.assertTrue(all(not n["shared_spawner_safe"] for n in generic_owner))
        other_plug = make_zone(SA.NODE_SPAWNER_CLASS, SA.PLUG_LOCATIONS).template_nodes()
        self.assertTrue(all(not n["shared_spawner_safe"] for n in other_plug))

    def test_v3_anchor_solver_keeps_shared_node_variable_as_one_indivisible_source(self):
        class FakeBrain:
            def regular(self, kind, asset=None):
                return True, "ground", "fixture"
            def pair(self, original, original_family, replacement, replacement_family):
                return (original != replacement, "proven", "fixture pair")
            def family(self, kind, asset=None):
                return "ground", "fixture"

        def node(key, vi, uid, kind, owners, keys, safe):
            return {"key": key, "action": 0, "class": "%08X" % SA.NODE_SPAWNER_CLASS,
                    "is_spawner_class": True, "template_plug": 1, "template_plug_count": 1,
                    "var_index": vi, "form": "local", "uid": uid, "kind": kind,
                    "asset": "actors/%s.actor" % kind, "rec": vi, "owners": owners,
                    "co_owner_classes": [], "co_owner_keys": keys, "spawner_keys": keys,
                    "shared_spawner_safe": safe, "other_plugs": "", "problem": ""}
        akeys = ["NODE-A1", "NODE-A2"]
        rec = {"zone": "anchor.zone", "zone_id": "ABCDEF0123456789", "planet": "fixture",
               "factories": [], "template_nodes": [
                   node("NODE-A1", 5, "1111111111111111", "enm_pirate_robot_shooter", 2, akeys, True),
                   node("NODE-A2", 5, "1111111111111111", "enm_pirate_robot_shooter", 2, akeys, True),
                   node("NODE-B", 6, "2222222222222222", "enm_pirate_robot_melee", 1, ["NODE-B"], True),
               ]}
        changes, decisions = SA.plan_node_template_adapters(
            SimpleNamespace(), FakeBrain(), rec, SimpleNamespace(verdict_map={}, rate=1.0),
            random.Random("v3-shared-anchor"), [], {})
        self.assertEqual(len(changes), 1)
        changed_keys = set(changes[0]["spawner_keys"])
        self.assertIn(changes[0]["var_index"], (5, 6))
        if changes[0]["var_index"] == 5:
            self.assertEqual(changed_keys, set(akeys))
            self.assertEqual(decisions["NODE-B"][0], "anchor")
        else:
            self.assertEqual(changed_keys, {"NODE-B"})
            self.assertEqual(decisions["NODE-A1"][0], "anchor")
            self.assertEqual(decisions["NODE-A2"][0], "anchor")

    def test_v3_shared_spawner_template_variable_is_changed_once_for_all_owners(self):
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
        def node(key):
            return {"key": key, "action": 0, "class": "%08X" % SA.NODE_SPAWNER_CLASS,
                    "is_spawner_class": True, "template_plug": 1, "template_plug_count": 1,
                    "var_index": 5, "form": "local", "uid": "1111111111111111",
                    "kind": "enm_pirate_robot_shooter", "asset": "actors/shooter.actor", "rec": 0,
                    "owners": 2, "co_owner_classes": [], "co_owner_keys": ["NODE-A", "NODE-B"],
                    "spawner_keys": ["NODE-A", "NODE-B"], "shared_spawner_safe": True,
                    "other_plugs": "", "problem": ""}
        rec = {"zone": "shared.zone", "zone_id": "ABCDEF0123456789", "planet": "fixture",
               "factories": factories, "template_nodes": [node("NODE-A"), node("NODE-B")]}
        changes, decisions = SA.plan_node_template_adapters(
            SimpleNamespace(), FakeBrain(), rec, SimpleNamespace(verdict_map={}, rate=1.0),
            random.Random("v3-shared-node"), [], {})
        self.assertEqual(len(changes), 1, "one shared Script Vars entry must be patched once")
        self.assertEqual(changes[0]["spawner_keys"], ["NODE-A", "NODE-B"])
        self.assertEqual(changes[0]["var_index"], 5)
        self.assertEqual(decisions["NODE-A"][0], "changed")
        self.assertEqual(decisions["NODE-B"][0], "changed")

    def test_v3_node_adapter_pins_exact_latest_worked_replacement(self):
        class FakeBrain:
            def regular(self, kind, asset=None):
                return True, "ground", "fixture"
            def pair(self, original, original_family, replacement, replacement_family):
                return (original != replacement, "kin", "unverified fixture pair")
            def family(self, kind, asset=None):
                return "ground", "fixture"

        factories = [
            {"key": "FACTORY-A", "form": "local", "uid": "1111111111111111",
             "kind": "enm_pirate_robot_shooter", "asset": "actors/shooter.actor", "rec": 0, "problem": None},
            {"key": "FACTORY-B", "form": "local", "uid": "2222222222222222",
             "kind": "enm_pirate_robot_melee", "asset": "actors/melee.actor", "rec": 1, "problem": None},
        ]
        node = {"key": "NODE-A", "action": 0, "class": "%08X" % SA.NODE_SPAWNER_CLASS,
                "is_spawner_class": True, "template_plug": 1, "template_plug_count": 1,
                "var_index": 5, "form": "local", "uid": "1111111111111111",
                "kind": "enm_pirate_robot_shooter", "asset": "actors/shooter.actor", "rec": 0,
                "owners": 1, "co_owner_classes": [], "co_owner_keys": [],
                "spawner_keys": ["NODE-A"], "shared_spawner_safe": True,
                "other_plugs": "", "problem": ""}
        rec = {"zone": "pin.zone", "zone_id": "ABCDEF0123456789", "planet": "fixture",
               "factories": factories, "template_nodes": [node]}
        opts = SimpleNamespace(verdict_map={"ABCDEF0123456789": {
            "NODE-A": ("WORKED", "2222222222222222")}}, rate=1.0)
        changes, decisions = SA.plan_node_template_adapters(
            SimpleNamespace(), FakeBrain(), rec, opts, random.Random("v3-node-worked-pin"), [], {})
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["replacement_uid"], "2222222222222222")
        self.assertEqual(changes[0]["pair_tier"], "confirmed")
        self.assertEqual(changes[0]["tier"], "node-template/confirmed")
        self.assertIn("WORKED", changes[0]["pair_evidence"])
        self.assertEqual(decisions["NODE-A"][0], "changed")

    def test_v3_shared_node_adapter_rejects_conflicting_worked_uids(self):
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
        nodes = []
        for key in ("NODE-A", "NODE-B"):
            nodes.append({"key": key, "action": 0, "class": "%08X" % SA.NODE_SPAWNER_CLASS,
                "is_spawner_class": True, "template_plug": 1, "template_plug_count": 1,
                "var_index": 5, "form": "local", "uid": "1111111111111111",
                "kind": "enm_pirate_robot_shooter", "asset": "actors/shooter.actor", "rec": 0,
                "owners": 2, "co_owner_classes": [], "co_owner_keys": ["NODE-A", "NODE-B"],
                "spawner_keys": ["NODE-A", "NODE-B"], "shared_spawner_safe": True,
                "other_plugs": "", "problem": ""})
        rec = {"zone": "conflict.zone", "zone_id": "ABCDEF0123456789", "planet": "fixture",
               "factories": factories, "template_nodes": nodes}
        opts = SimpleNamespace(verdict_map={"ABCDEF0123456789": {
            "NODE-A": ("WORKED", "2222222222222222"),
            "NODE-B": ("WORKED", "1111111111111111")}}, rate=1.0)
        changes, decisions = SA.plan_node_template_adapters(
            SimpleNamespace(), FakeBrain(), rec, opts, random.Random("v3-conflicting-pins"), [], {})
        self.assertEqual(changes, [])
        self.assertEqual(decisions["NODE-A"][0], "refused")
        self.assertEqual(decisions["NODE-B"][0], "refused")
        self.assertIn("conflicting confirmed", decisions["NODE-A"][1])

    def test_v3_shared_node_variable_with_unsafe_co_owner_stays_native(self):
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
        nodes = []
        for key in ("NODE-A", "NODE-B"):
            nodes.append({"key": key, "action": 0, "class": "%08X" % SA.NODE_SPAWNER_CLASS,
                "is_spawner_class": True, "template_plug": 1, "template_plug_count": 1,
                "var_index": 5, "form": "local", "uid": "1111111111111111",
                "kind": "enm_pirate_robot_shooter", "asset": "actors/shooter.actor", "rec": 0,
                "owners": 2, "co_owner_classes": ["DEADBEEF/12345678"], "co_owner_keys": ["NODE-A", "OTHER"],
                "spawner_keys": [key], "shared_spawner_safe": False, "other_plugs": "", "problem": ""})
        rec = {"zone": "unsafe.zone", "zone_id": "ABCDEF0123456789", "planet": "fixture",
               "factories": factories, "template_nodes": nodes}
        changes, decisions = SA.plan_node_template_adapters(
            SimpleNamespace(), FakeBrain(), rec, SimpleNamespace(verdict_map={}, rate=1.0),
            random.Random("v3-unsafe-shared"), [], {})
        self.assertEqual(changes, [])
        self.assertEqual(decisions["NODE-A"][0], "refused")
        self.assertEqual(decisions["NODE-B"][0], "refused")
        self.assertIn("non-spawner", decisions["NODE-A"][1])

    def test_v3_manifest_records_every_owner_of_a_shared_node_variable(self):
        change = {
            "zone": "shared.zone", "zone_id": "ABCDEF0123456789", "planet": "fixture",
            "entry_rel": 128, "var_index": 5,
            "original_uid": "1111111111111111", "original_index": 0,
            "original": "enm_pirate_robot_shooter", "original_family": "ground",
            "replacement_uid": "2222222222222222", "replacement_index": 1,
            "replacement": "enm_pirate_robot_melee", "replacement_family": "swarmer",
            "replacement_external": False, "replacement_source_planet": "fixture",
            "replacement_source_zone": "shared.zone", "original_refs": 1, "replacement_refs": 1,
            "tier": "node-template/proven", "adapter": "node_template", "pair": "fixture",
            "key": "NODE-A", "spawner_keys": ["NODE-A", "NODE-B"],
        }
        manifest = SA.manifest_lua({"changes": [change], "zones": [{"planet": "fixture"}],
            "label": "shared test", "stage_sha256": "abc", "seed": "test", "profile": "v3"})
        self.assertIn('spawner_keys = { "NODE-A", "NODE-B" }', manifest)

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
        self.assertEqual(SA.VERSION, "3.0.0-alpha.3")
        self.assertIn("runtime_scripts", SA.RUNTIME_BUNDLE_DIR)
        self.assertIn("runtime_scripts", str(SA.INSTALL_FILES))
        self.assertGreaterEqual(len(SA.RUNTIME_SCRIPT_NAMES), 18)
        with open(os.path.join(runtime_dir, "10_rando_runtime.lua"), encoding="utf-8") as fh:
            runtime_core = fh.read()
        self.assertIn('R.KIT_VERSION = "10.0.50"', runtime_core)
        with open(os.path.join(runtime_dir, "04_rando_settings.lua"), encoding="utf-8") as fh:
            settings = fh.read()
        self.assertIn('enemy_compat = "max"', settings)
        self.assertIn('enemy_mix_movement = true', settings)
        for name in SA.RUNTIME_SCRIPT_NAMES:
            with open(os.path.join(runtime_dir, name), encoding="utf-8") as fh:
                source = fh.read()
            self.assertIn('RANDO_FILES["' + name[:-4] + '"] = "10.0.50"', source, name)

    def test_v3_runtime_bundle_rejects_missing_or_mixed_scripts(self):
        with tempfile.TemporaryDirectory() as out:
            bundle = os.path.join(out, SA.RUNTIME_BUNDLE_DIR)
            os.makedirs(bundle)
            for name in SA.RUNTIME_SCRIPT_NAMES:
                stamp = 'RANDO_FILES["%s"] = "10.0.50"\\n' % name[:-4]
                if name == "10_rando_runtime.lua":
                    stamp += 'R.KIT_VERSION = "10.0.50"\\n'
                if name == "04_rando_settings.lua":
                    stamp += 'enemy_compat = "max"\\nenemy_mix_movement = true\\n'
                with open(os.path.join(bundle, name), "w", encoding="utf-8") as fh:
                    fh.write(stamp)
            with open(os.path.join(out, SA.STAGE_LUA_FILE), "w", encoding="utf-8") as fh:
                fh.write('RANDO_FILES["18_rando_stage_enemies"] = "10.0.50"\\nST.STAGE_LUA = "1.1.0"\\n')
            self.assertEqual(SA.runtime_bundle_problems(out), [])
            with open(os.path.join(bundle, "16_rando_spawners.lua"), "w", encoding="utf-8") as fh:
                fh.write('RANDO_FILES["16_rando_spawners"] = "10.0.39"\\n')
            self.assertTrue(any("10.0.39 != runtime core 10.0.50" in x
                                for x in SA.runtime_bundle_problems(out)))
            os.remove(os.path.join(bundle, "17_rando_omega.lua"))
            self.assertTrue(any("runtime bundle missing 17_rando_omega.lua" in x
                                for x in SA.runtime_bundle_problems(out)))

    def test_v3_build_requires_stage_monitor_and_generated_manifests(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(len(SA.v3_artifact_problems(out, "v3")), 3)
            with open(os.path.join(out, SA.STAGE_LUA_FILE), "w", encoding="utf-8") as fh:
                fh.write("-- stage monitor\\n")
            with open(os.path.join(out, SA.GLOBAL_ASSET_LUA), "w", encoding="utf-8") as fh:
                fh.write("RANDO_GLOBAL_ENEMY_ASSETS = {}\\n")
            with open(os.path.join(out, SA.MANIFEST_LUA), "w", encoding="utf-8") as fh:
                fh.write('RANDO_STAGE_ENEMIES = { profile = "v3" }\\n')
            self.assertEqual(SA.v3_artifact_problems(out, "v3"), [])
            self.assertEqual(SA.v3_artifact_problems(out, "max"), [])

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
