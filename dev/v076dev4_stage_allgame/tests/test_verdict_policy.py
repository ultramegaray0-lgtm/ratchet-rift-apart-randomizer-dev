#!/usr/bin/env python3
"""Offline regression tests for V2.0.1 runtime-evidence precedence.

These tests do not need game files or a real .stage. Run:
  python -I -m unittest discover -s tests -p "test_verdict_policy.py"
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "stage_enemies"))
import stage_allgame as SA  # noqa: E402

ARDOLIS = "AE530D22FE113E2B"
OLD_UID = "92C793D47A4657B6"
NEW_UID = "D78BDDE784EF233E"


class VerdictPolicyTests(unittest.TestCase):
    def test_latest_no_spawn_suppresses_historical_pin(self):
        verdicts = {ARDOLIS: {"FF06CCC2A9AC1EA2": ("NO SPAWN", OLD_UID)}}
        self.assertNotIn("FF06CCC2A9AC1EA2",
                         {k for k, _, _ in SA.effective_pins(ARDOLIS, verdicts)})

    def test_latest_worked_replaces_historical_pin_uid(self):
        verdicts = {ARDOLIS: {"FF06CCC2A9AC1EA2": ("WORKED", NEW_UID)}}
        pins = {k: uid for k, uid, _ in SA.effective_pins(ARDOLIS, verdicts)}
        self.assertEqual(pins["FF06CCC2A9AC1EA2"], NEW_UID)

    def test_new_worked_spawner_becomes_dynamic_pin(self):
        verdicts = {ARDOLIS: {"B2B978B5BC3D8A4D": ("WORKED", NEW_UID)}}
        pins = {k: uid for k, uid, _ in SA.effective_pins(ARDOLIS, verdicts)}
        self.assertEqual(pins["B2B978B5BC3D8A4D"], NEW_UID)

    def test_later_failure_overrides_earlier_worked(self):
        old = ("WORKED", OLD_UID)
        latest = ("NO SPAWN", NEW_UID)
        self.assertEqual(SA.merge_verdict_entry(old, latest), latest)

    def test_later_worked_overrides_earlier_failure(self):
        old = ("NO SPAWN", OLD_UID)
        latest = ("WORKED", NEW_UID)
        self.assertEqual(SA.merge_verdict_entry(old, latest), latest)

    def test_not_reached_does_not_erase_worked(self):
        old = ("WORKED", OLD_UID)
        self.assertEqual(SA.merge_verdict_entry(old, ("NOT REACHED", None)), old)

    def test_not_reached_does_not_erase_failure(self):
        old = ("NO SPAWN", OLD_UID)
        self.assertEqual(SA.merge_verdict_entry(old, ("NOT REACHED", None)), old)

    def test_no_pins_disables_static_and_dynamic_pins(self):
        verdicts = {ARDOLIS: {
            "FF06CCC2A9AC1EA2": ("WORKED", NEW_UID),
            "B2B978B5BC3D8A4D": ("WORKED", OLD_UID),
        }}
        self.assertEqual(SA.effective_pins(ARDOLIS, verdicts, no_pins=True), [])

    def test_other_zone_pins_are_not_leaked(self):
        verdicts = {ARDOLIS: {"B2B978B5BC3D8A4D": ("WORKED", NEW_UID)}}
        self.assertEqual(SA.effective_pins("0000000000000000", verdicts), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
