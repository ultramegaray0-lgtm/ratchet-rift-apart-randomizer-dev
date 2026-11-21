"""Round45 follow-up: event-prioritized factory discovery and read-only Omega diagnostics."""
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Game  # noqa: E402


class SpawnFactoryEventQueueTests(unittest.TestCase):
    def test_spawn_event_queues_each_factory_once_and_counts_spawns(self):
        game = Game(settings={"enemy_randomizer": True, "enemy_compat": "all"})
        game.lua.execute("""
        local V = RANDO_SPAWNERS.V
        V.new_level("round45 test")
        V.enabled = function() return true end
        V.on_spawn_seen({ SpawnedHandle = 501, SpawnFactory = 9001, SpawnLocation = 0 })
        V.on_spawn_seen({ SpawnedHandle = 502, SpawnFactory = 9001, SpawnLocation = 0 })
        function round45_queue_result()
          return #V.lvl.fac_queue, V.lvl.fac_queue[1], V.lvl.fac_spawns[9001]
        end
        """)
        count, fac, spawns = game.lua.eval("round45_queue_result")()
        self.assertEqual((count, fac, spawns), (1, 9001, 2))

    def test_event_discovered_factory_is_processed_before_full_scan(self):
        game = Game(settings={"enemy_randomizer": True})
        game.lua.execute("""
        local V = RANDO_SPAWNERS.V
        local order = {}
        V.drain_pending = function() return true end
        V.factory_rec = function(fac)
          order[#order + 1] = "factory:" .. tostring(fac)
          return { kind = "factory", var = { idx = 1, gen = 1 } }
        end
        V.read_one_orig = function(sc, r)
          order[#order + 1] = "read"
          r.orig = { uid = "0", actors = 0, single = false, group = false }
        end
        V.plan_rec = function(sc, r) order[#order + 1] = "plan" end
        V.scan = function(sc) order[#order + 1] = "full-scan"; V.lvl.scans = 1 end
        V.lvl = { fac_queue = { 9001 }, fac_queued = { [9001] = true }, scan_due = true,
                  queue = {}, deferred = {}, scans = 0, dirty = false, arm_running = false,
                  arms = {}, order = {}, pending = {} }
        local co = coroutine.create(function() V.pump({}) end)
        while coroutine.status(co) ~= "dead" do
          local ok, err = coroutine.resume(co)
          assert(ok, tostring(err))
        end
        function round45_order() return table.concat(order, ",") end
        """)
        order = game.lua.eval("round45_order")()
        self.assertEqual(order, "factory:9001,read,plan,full-scan")

    def test_omega_component_fallback_only_enumerates_and_reads(self):
        path = ROOT / "mod" / "RiftApartRandomizer" / "scripts" / "17_rando_omega.lua"
        source = path.read_text(encoding="utf-8")
        start = source.index("function O.component_diagnostic(hero)")
        end = source.index("\nfunction O.component()", start)
        diagnostic = source[start:end]
        self.assertIn("pcall(rivet.components, hero)", diagnostic)
        self.assertIn("pcall(rivet.component, hero, class)", diagnostic)
        self.assertIn("pcall(rivet.read", diagnostic)
        self.assertNotIn("rivet.write", diagnostic)
        self.assertNotIn("rivet.set_field", diagnostic)


if __name__ == "__main__":
    unittest.main()
