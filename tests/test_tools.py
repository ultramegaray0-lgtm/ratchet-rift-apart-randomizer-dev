"""tools/summarize_log.py on the real round-13 rivet.log and on a simulated kit-1.4 session."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.dirname(__file__))
import summarize_log  # noqa: E402
from harness import Game  # noqa: E402


class SummarizeLogTests(unittest.TestCase):
    def test_round13_log(self):
        with open(os.path.join(ROOT, "tests", "data", "round13_rivet.log"), encoding="utf-8") as f:
            s = summarize_log.summarize(f)
        self.assertEqual(s["rivet"], "2.0.0")
        self.assertEqual(s["confirmed"], ["weapon:predator_launcher", "weapon:headhunter", "weapon:warmonger", "weapon:schrodinger"])
        self.assertEqual(s["sent"]["weapon:executor"], 4)
        self.assertEqual(len(s["delivery_off"]), 1)
        self.assertIn("Mr. Zurkon (restored) for 6", s["bought"])
        self.assertEqual(s["errors"], [])

    def test_simulated_session(self):
        g = Game().ready()
        g.R.grant("weapon:headhunter"); g.step(60)
        g.step(600)                                                  # the shop is shuffled
        g.fire("GainGoldBoltEvent", BoltName="NefCity 1")
        g.sim.new_game(); g.step(60)
        g.fire("MissionStateChangedEvent", MissionName="MIS_MEGA_FINALE", MissionState=4)
        s = summarize_log.summarize(["[script] " + l for l in g.logs()])
        self.assertEqual(s["kit"], "10.0.18")
        self.assertTrue(s["prices"])                                 # 7.0: the vendor's prices were found
        self.assertIn("test-seed-2", s["seed"])
        self.assertIn("weapon:headhunter", s["confirmed"])
        self.assertEqual(s["delivery_off"], [])
        self.assertEqual(len(s["gold_bolts"]), 1)
        self.assertEqual(len(s["new_games"]), 1)
        self.assertTrue(s["vendor"])
        self.assertTrue(s["finale"])


if __name__ == "__main__":
    unittest.main()


class CliTests(unittest.TestCase):
    def test_generate_twice_in_separate_processes(self):
        import subprocess, tempfile
        outs = []
        for _ in range(2):
            d = tempfile.mkdtemp()
            subprocess.run([sys.executable, os.path.join(ROOT, "tools", "rando.py"), "generate", "--seed", "proc-check",
                            "--preset", "chaos", "--set", "start_weapons=3", "--out", d], check=True, capture_output=True)
            with open(os.path.join(d, "seed.json"), encoding="utf-8") as f:
                outs.append(f.read())
            with open(os.path.join(d, "spoiler.txt"), encoding="utf-8") as f:
                text = f.read()
                self.assertIn("GOLD BOLTS", text)
                self.assertIn("SHOP (Ms. Zurkon's 15 weapon slots", text)
        self.assertEqual(outs[0], outs[1])

    def test_batch_command(self):
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "rando.py"), "batch", "--count", "200"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertRegex(r.stdout, r"(\d+) seeds over \d+ setting combinations: \1 valid, 0 refused")
        self.assertIn(", 0 failed", r.stdout)
