#!/usr/bin/env python3
"""Regression tests for V3 stage log attribution (factory, node Template, shared owners)."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "stage_enemies"))
import stage_check_log as CHECK  # noqa: E402


class StageCheckLogV3Tests(unittest.TestCase):
    def run_fixture(self, log_text, manifest=None, inventory_csv=None, template_inventory_csv=None):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "rivet.log")
            json_path = os.path.join(tmp, "verdicts.json")
            with open(log_path, "w", encoding="utf-8") as fh:
                fh.write(log_text)
            manifest_path = None
            if manifest is not None:
                manifest_path = os.path.join(tmp, "stage_enemies_manifest.json")
                with open(manifest_path, "w", encoding="utf-8") as fh:
                    json.dump(manifest, fh)
            inventory_path = None
            if inventory_csv is not None:
                inventory_path = os.path.join(tmp, "inventory.csv")
                with open(inventory_path, "w", encoding="utf-8") as fh:
                    fh.write(inventory_csv)
            template_inventory_path = None
            if template_inventory_csv is not None:
                template_inventory_path = os.path.join(tmp, "template_adapter_inventory.csv")
                with open(template_inventory_path, "w", encoding="utf-8") as fh:
                    fh.write(template_inventory_csv)
            args = SimpleNamespace(logs=[log_path], manifest=manifest_path, inventory=inventory_path,
                                   template_inventory=template_inventory_path, json=json_path, all=True)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = CHECK.run(args)
            with open(json_path, encoding="utf-8") as fh:
                data = json.load(fh)
            return result, output.getvalue(), data

    def test_manifest_expands_shared_node_owner_keys_and_reads_template_spawn(self):
        uid = "2222222222222222"
        manifest = {"changes": [{
            "key": "AAAAAAAAAAAAAAAA", "spawner_keys": ["AAAAAAAAAAAAAAAA", "BBBBBBBBBBBBBBBB"], "adapter": "node_template",
            "original": "enm_pirate_robot_shooter", "replacement": "enm_pirate_robot_melee",
            "replacement_uid": uid, "planet": "ardolis", "zone": "levels\\i29\\instance\\ardolis\\test.zone",
            "tier": "node-template/confirmed"
        }]}
        log = "\n".join([
            "[rivet] init",
            "[script] [rando]\tRANDO-STAGE\tSTAGE VARIABLE template BBBBBBBBBBBBBBBB: holds %s (enm_pirate_robot_melee) = the .stage value - the patched zone IS loaded" % uid,
            "[script] [rando]\tRANDO-ENEMIES\tSTAGE SPAWN 778 | MIS_TEST | template BBBBBBBBBBBBBBBB (the patched spawner) | variable %s | handle uid %s | spawned enm_pirate_robot_melee (swarmer) | change 1 enm_pirate_robot_shooter -> enm_pirate_robot_melee | REPLACEMENT SPAWNED (the .stage value was used)" % (uid, uid),
            "[script] [rando]\tRANDO-STAGE\tSTAGE DEATH 778: enm_pirate_robot_melee (spawner BBBBBBBBBBBBBBBB) died 3 s after it spawned",
        ])
        rc, output, data = self.run_fixture(log, manifest)
        self.assertEqual(rc, 0)
        verdicts = data["verdicts"]
        self.assertEqual(verdicts["BBBBBBBBBBBBBBBB"]["verdict"], "WORKED")
        self.assertEqual(verdicts["AAAAAAAAAAAAAAAA"]["verdict"], "NOT REACHED")
        self.assertEqual(verdicts["BBBBBBBBBBBBBBBB"]["adapter"], "node_template")
        self.assertIn("actor 778 pirate_robot_melee", output)

    def test_log_only_v3_stage_change_splits_shared_keys_and_reads_node_spawn(self):
        original_uid, replacement_uid = "1111111111111111", "2222222222222222"
        log = "\n".join([
            "[rivet] init",
            "[script] [rando]\tRANDO-STAGE\tSTAGE CHANGE 7: levels\\i29\\instance\\ardolis\\test.zone Zone Script Vars +128 (entry 1): %s #0 (enm_pirate_robot_shooter) -> %s #1 (enm_pirate_robot_melee) | node_template|fixture | adapter node_template | spawners AAAAAAAAAAAAAAAA,BBBBBBBBBBBBBBBB" % (original_uid, replacement_uid),
            "[script] [rando]\tRANDO-STAGE\tSTAGE VARIABLE template AAAAAAAAAAAAAAAA: holds %s (enm_pirate_robot_melee) = the .stage value - the patched zone IS loaded" % replacement_uid,
            "[script] [rando]\tRANDO-ENEMIES\tSPAWN 900 | ardolis | MIS_TEST | node Template AAAAAAAAAAAAAAAA | original enm_pirate_robot_shooter | selected enm_pirate_robot_melee | spawned enm_pirate_robot_melee (swarmer) | SUCCESS",
            "[script] [rando]\tRANDO-ENEMIES\tSTAGE SPAWN 900 | MIS_TEST | template AAAAAAAAAAAAAAAA (the patched spawner) | variable %s | handle uid %s | spawned enm_pirate_robot_melee (swarmer) | change 7 enm_pirate_robot_shooter -> enm_pirate_robot_melee | REPLACEMENT SPAWNED" % (replacement_uid, replacement_uid),
        ])
        rc, output, data = self.run_fixture(log)
        self.assertEqual(rc, 0)
        self.assertEqual(data["verdicts"]["AAAAAAAAAAAAAAAA"]["verdict"], "WORKED")
        self.assertEqual(data["verdicts"]["BBBBBBBBBBBBBBBB"]["verdict"], "NOT REACHED")
        self.assertEqual(data["verdicts"]["AAAAAAAAAAAAAAAA"]["adapter"], "node_template")
        self.assertIn("CHANGE 7  AAAAAAAAAAAAAAAA", output)

    def test_runtime_only_node_template_spawn_creates_exact_worked_evidence(self):
        key = "CCCCCCCCCCCCCCCC"
        original_uid, selected_uid = "1111111111111111", "F00D123456780000"
        log = "\n".join([
            "[rivet] init",
            "[script] [rando]\tRANDO-ENEMIES\tSPAWN 990 | ardolis | MIS_RUNTIME | node Template %s | original enm_pirate_robot_shooter | selected enm_pirate_robot_melee uid %s | spawned enm_pirate_robot_melee (swarmer) | SUCCESS" % (key, selected_uid),
        ])
        template_inventory = (
            "planet,zone,zone_id,node_key,class_id,is_SpawnerScriptAction\\n"
            "ardolis,levels\\\i29\\\instance\\\ardolis\\\test.zone,ABCDEF0123456789,%s,2E910F8C,True\\n" % key
        )
        rc, output, data = self.run_fixture(log, template_inventory_csv=template_inventory)
        self.assertEqual(rc, 0)
        verdict = data["verdicts"][key]
        self.assertEqual(verdict["verdict"], "WORKED")
        self.assertEqual(verdict["replacement_uid"], selected_uid)
        self.assertEqual(verdict["adapter"], "node_template")
        self.assertEqual(verdict["zone"], "levels\\\\i29\\\\instance\\\\ardolis\\\\test.zone")
        self.assertEqual(verdict["zone_id"], "ABCDEF0123456789")
        self.assertIn("runtime-observed", output)

    def test_legacy_factory_stage_logs_still_parse(self):
        original_uid, replacement_uid = "1111111111111111", "2222222222222222"
        log = "\n".join([
            "[rivet] init",
            "[script] [rando]\tRANDO-STAGE\tSTAGE CHANGE 1: levels\\i29\\instance\\ardolis\\test.zone Zone Script Vars +64 (entry 0): %s #0 (enm_pirate_robot_shooter) -> %s #1 (enm_pirate_robot_melee) | factory|fixture | spawners ABCDEF0123456789" % (original_uid, replacement_uid),
            "[script] [rando]\tRANDO-STAGE\tSTAGE VARIABLE factory ABCDEF0123456789: holds %s (enm_pirate_robot_melee) = the .stage value - the patched zone IS loaded" % replacement_uid,
            "[script] [rando]\tRANDO-ENEMIES\tSPAWN 901 | ardolis | MIS_TEST | factory Templates ABCDEF0123456789 | original enm_pirate_robot_shooter | selected enm_pirate_robot_melee | spawned enm_pirate_robot_melee (ground) | SUCCESS",
        ])
        rc, output, data = self.run_fixture(log)
        self.assertEqual(rc, 0)
        self.assertEqual(data["verdicts"]["ABCDEF0123456789"]["verdict"], "WORKED")
        self.assertEqual(data["verdicts"]["ABCDEF0123456789"]["adapter"], "factory")


if __name__ == "__main__":
    unittest.main()
