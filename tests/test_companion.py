"""End-to-end test of companion/RandoCompanion.ps1 (the real script, run by PowerShell 7)
against a fake rivet_hook pipe bridge that runs the real randomizer scripts in the simulator.

The bridge protocol matches rivet_hook's bridge.cpp: a u32 little-endian length, then the
request text ("script.exec <chunk>"); the answer is a u32 length and JSON
{"ok": true, "result": {"value": "..."}} with the value cut at 4095 characters, or
{"ok": false, "error": "..."}. On Linux .NET's NamedPipeClientStream connects to the Unix
socket <tmp>/CoreFxPipe_<name>.

Skipped when pwsh is not installed (set PWSH=/path/to/pwsh)."""
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from harness import Game, MOD  # noqa: E402

PWSH = os.environ.get("PWSH") or shutil.which("pwsh") or "/home/claude/ext/pwsh/pwsh"
COMPANION = MOD / "companion" / "RandoCompanion.ps1"


class FakeBridge:
    def __init__(self, game):
        self.game = game
        self.lock = threading.Lock()
        self.name = "rivet_test_" + uuid.uuid4().hex[:8]
        self.path = os.path.join(tempfile.gettempdir(), "CoreFxPipe_" + self.name)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.path)
        self.sock.listen(4)
        self.requests = []
        self.canned = {}            # bridge command -> fn(request) -> result (research tests)
        self.stop = False
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def exec_lua(self, chunk):
        with self.lock:
            fn = self.game.lua.eval("function(src) local f, e = load(src); if not f then return false, e end;"
                                    " local ok, v = pcall(f); if not ok then return false, tostring(v) end;"
                                    " if v == nil then return true, 'ok' end; return true, tostring(v) end")
            ok, value = fn(chunk)
            return ok, (value or "")[:4095]

    def serve(self):
        while not self.stop:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                try:
                    n = struct.unpack("<I", self.recv(conn, 4))[0]
                    req = self.recv(conn, n).decode("utf-8")
                    self.requests.append(req)
                    if req.startswith("script.exec "):
                        ok, value = self.exec_lua(req[len("script.exec "):])
                        body = {"ok": True, "result": {"value": value}} if ok else {"ok": False, "error": value}
                    elif req.split(" ", 1)[0] in self.canned:
                        body = {"ok": True, "result": self.canned[req.split(" ", 1)[0]](req)}
                    elif req.startswith("mem.read "):
                        _, addr, length = req.split()
                        with self.lock:
                            hx = self.game.sim.mem_hex(int(addr, 16), int(length, 0))
                        body = {"ok": True, "result": {"address": addr, "length": int(length, 0), "bytes": hx}} if hx else \
                            {"ok": False, "error": "address is not readable"}
                    else:
                        body = {"ok": False, "error": "unknown command"}
                    data = json.dumps(body).encode("utf-8")
                    conn.sendall(struct.pack("<I", len(data)) + data)
                except Exception:
                    pass

    @staticmethod
    def recv(conn, n):
        buf = b""
        while len(buf) < n:
            part = conn.recv(n - len(buf))
            if not part:
                raise EOFError
            buf += part
        return buf

    def close(self):
        self.stop = True
        self.sock.close()
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass


def run_companion(bridge, save_dir, iterations, interval=50, extra=()):
    """runs the real companion while the simulated game keeps running frames"""
    stop = threading.Event()

    def frames():
        while not stop.is_set():
            with bridge.lock:
                bridge.game.step(2)
            stop.wait(0.005)
    t = threading.Thread(target=frames, daemon=True)
    t.start()
    try:
        return subprocess.run([PWSH, "-NoProfile", "-File", str(COMPANION), "-PipeName", bridge.name,
                               "-SaveDir", save_dir, "-IntervalMs", str(interval), "-Iterations", str(iterations), *extra],
                              capture_output=True, text=True, timeout=180)
    finally:
        stop.set()
        t.join()


@unittest.skipUnless(os.path.exists(PWSH), "PowerShell 7 (pwsh) is not installed")
class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_fresh_start_save_and_restore_after_restart(self):
        g = Game(test_mode=True)
        b = FakeBridge(g)
        try:
            out = run_companion(b, self.dir, 6)
            self.assertIn("starting fresh", out.stdout, out.stdout + out.stderr)
            self.assertIn("spoiler log written", out.stdout)
            self.assertTrue(g.R.restored)
            with b.lock:
                g.ready(fresh=False)
                g.fire("MissionStateChangedEvent", MissionName="MIS_INTRO", MissionState=4)
                g.fire("GainGoldBoltEvent", BoltName="NefCity 1")
                for i in range(150):
                    g.R.on_gold_bolt(f"Nowhere {i}")       # big state: several chunks
                bolts = g.R.bolts_collected()
            out = run_companion(b, self.dir, 3)
            self.assertIn("saved (version", out.stdout, out.stdout + out.stderr)
        finally:
            b.close()
        fp = g.g.RANDO_SEED.fingerprint
        save = os.path.join(self.dir, f"rando_{fp}.lua")
        with open(save, encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(text.startswith("return {"))
        self.assertGreater(len(text), 4095)

        # the game restarts: a new VM, the companion restores
        g2 = Game(test_mode=True)
        b2 = FakeBridge(g2)
        try:
            out = run_companion(b2, self.dir, 6)
            self.assertIn("restored progress", out.stdout, out.stdout + out.stderr)
        finally:
            b2.close()
        self.assertTrue(g2.R.restored)
        self.assertEqual(g2.R.bolts_collected(), bolts)
        self.assertTrue(g2.state.collected["planet:corson_v"])
        start_weapon = next(k for k in g2.seed.start["items"].values() if k.startswith("weapon:"))
        self.assertEqual(g2.item_status(start_weapon), "confirmed")
        spoilers = os.listdir(os.path.join(self.dir, "spoilers"))
        self.assertEqual(len(spoilers), 1)
        with open(os.path.join(self.dir, "spoilers", spoilers[0]), encoding="utf-8") as f:
            self.assertIn("PLAYTHROUGH", f.read())

    def test_damaged_save_is_not_loaded(self):
        g = Game()
        g.wait_seed()
        fp = g.g.RANDO_SEED.fingerprint
        with open(os.path.join(self.dir, f"rando_{fp}.lua"), "w") as f:
            f.write("garbage")
        b = FakeBridge(g)
        try:
            out = run_companion(b, self.dir, 3)
        finally:
            b.close()
        self.assertIn("is damaged and there is no usable .bak", out.stdout, out.stdout)
        self.assertFalse(g.R.restored)          # never overwrites it with a fresh state

    def test_damaged_save_falls_back_to_bak(self):
        g = Game().ready()
        g.fire("GainGoldBoltEvent", BoltName="NefCity 1")
        good = g.companion_export()
        fp = g.g.RANDO_SEED.fingerprint
        main = os.path.join(self.dir, f"rando_{fp}.lua")
        with open(main + ".bak", "w") as f:
            f.write(good)
        with open(main, "w") as f:
            f.write(good[: len(good) // 2])          # cut off mid-write
        g2 = Game()
        b = FakeBridge(g2)
        try:
            out = run_companion(b, self.dir, 6)
        finally:
            b.close()
        self.assertIn("using the previous save", out.stdout, out.stdout)
        self.assertEqual(g2.R.bolts_collected(), 1)

    def test_new_game_keeps_the_previous_run_file(self):
        g = Game(test_mode=True)
        b = FakeBridge(g)
        try:
            run_companion(b, self.dir, 4)
            with b.lock:
                g.ready(fresh=False)
                g.fire("GainGoldBoltEvent", BoltName="NefCity 1")
            run_companion(b, self.dir, 3)
            with b.lock:
                g.sim.new_game(); g.step(60)
            out = run_companion(b, self.dir, 3)
            self.assertIn("new game: run 2 of this seed starts; run 1 kept", out.stdout, out.stdout + out.stderr)
        finally:
            b.close()
        fp = g.g.RANDO_SEED.fingerprint
        with open(os.path.join(self.dir, f"rando_{fp}.run1.lua"), encoding="utf-8") as f:
            self.assertIn('["run"]=1', f.read())
        with open(os.path.join(self.dir, f"rando_{fp}.lua"), encoding="utf-8") as f:
            self.assertIn('["run"]=2', f.read())

    def test_random_seed_is_remembered(self):
        g = Game(settings={"seed": "random"})
        b = FakeBridge(g)
        try:
            out = run_companion(b, self.dir, 6)
        finally:
            b.close()
        self.assertIn("new random seed:", out.stdout, out.stdout + out.stderr)
        with open(os.path.join(self.dir, "random_seed.txt"), encoding="utf-8") as f:
            remembered = f.read().strip()
        self.assertEqual(g.seed.seed, remembered)
        g2 = Game(settings={"seed": "random"})
        b2 = FakeBridge(g2)
        try:
            out = run_companion(b2, self.dir, 6)
        finally:
            b2.close()
        self.assertIn("continuing random seed: " + remembered, out.stdout)
        self.assertEqual(g2.seed.fingerprint, g.seed.fingerprint)
        self.assertIn("restored progress", out.stdout)
        g3 = Game(settings={"seed": "random"})
        b3 = FakeBridge(g3)
        try:
            out = run_companion(b3, self.dir, 6, extra=("-NewRandomSeed",))
        finally:
            b3.close()
        self.assertNotEqual(g3.seed.seed, remembered)

    def test_old_scripts_are_reported(self):
        g = Game()
        g.lua.execute('function rando_bridge_status() return "a|b|1|1|10|1" end')
        b = FakeBridge(g)
        try:
            out = run_companion(b, self.dir, 2)
        finally:
            b.close()
        self.assertIn("randomizer 1.x scripts", out.stdout)

    def test_waits_for_the_game(self):
        g = Game()
        b = FakeBridge(g)
        b.close()                                # nothing listening
        out = run_companion(b, self.dir, 1)
        self.assertIn("waiting for the game", out.stdout, out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(os.path.exists(PWSH), "PowerShell 7 (pwsh) is not installed")
class ResearchToolTests(unittest.TestCase):
    """Dump-GameCode.ps1 against a fake exe image holding the real AddToInventoryAction handler
    bytes (from rando_give_core.h); tools/analyze_dump.py must find SendMessage and its globals."""

    def test_dump_and_analyze(self):
        import re as _re
        hdr = (MOD / "rando_give_source" / "rando_give_core.h").read_text()
        body = hdr[hdr.index("RG_EXPECTED_HANDLER[0xA3] = {"):]
        body = body[body.index("{") + 1:body.index("};")]
        handler = bytes(int(x, 16) for x in _re.findall(r"0x([0-9a-f]{2})", body))
        g = Game()
        base = 0x140000000
        sim = g.sim
        vt = base + 0x2FA4DE0
        sim.map(vt, 24 * 8)
        for i in range(24):
            sim.put_u64(vt + 8 * i, base + 0x86CB90 if i == 10 else base + 0x1000 + i * 0x10)
        sim.map(base + 0x86CB90, 0x600)
        for i, b in enumerate(handler):
            sim.mem[base + 0x86CB90 + i] = b
        for t in (0x1B7B850, 0x12AB160, 0x12BE970):
            sim.map(base + t, 0x200)
        sim.put_u64(sim.MB + 0x30, base)
        d = tempfile.mkdtemp()
        out_json = os.path.join(d, "dump.json")
        b = FakeBridge(g)
        try:
            r = subprocess.run([PWSH, "-NoProfile", "-File", str(MOD / "companion" / "research" / "Dump-GameCode.ps1"),
                                "-PipeName", b.name, "-Out", out_json], capture_output=True, text=True, timeout=180)
        finally:
            b.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("AddToInventoryAction : ok", r.stdout)
        sys.path.insert(0, str(MOD.parents[1] / "tools"))
        import analyze_dump
        with open(out_json, encoding="utf-8-sig") as f:
            dump = json.load(f)
        h = dump["actions"]["AddToInventoryAction"]["handlers"]["slot10"]
        self.assertEqual(h["rva"], "0x86CB90")
        res = analyze_dump.analyze(h["bytes"], 0x86CB90)
        self.assertIn(0x1B7B850, res["calls"])             # SendMessage
        self.assertIn(0x12AB160, res["calls"])             # GetPlayerActors
        self.assertIn(0x60315B8, res["globals"])           # the AddToInventoryHandle message id
        self.assertIn(0x7817619B, res["constants"])        # the Target plug hash
        self.assertIn("rbx+0x60", res["fields"])           # the item field
        shutil.rmtree(d, ignore_errors=True)



@unittest.skipUnless(os.path.exists(PWSH), "PowerShell 7 (pwsh) is not installed")
class CampaignResearchTests(unittest.TestCase):
    """Research-Campaign.ps1 end to end against the fake bridge (canned engine answers shaped
    like rivet_hook's), checking that it collects every part and writes one zip."""

    def test_research_zip(self):
        import zipfile
        g = Game()
        g.ready()
        g.lua.execute('SIM.install_missions({ { "MIS_INTRO", 4 }, { "MIS_SAV_01", 0 } })')
        g.fire("MissionStateChangedEvent", MissionName="MIS_INTRO", MissionState=2, PreviousState=0)
        b = FakeBridge(g)

        # like rivet_hook: "<command> <filter> <limit>", the filter a case-sensitive substring,
        # split at spaces (no quotes: 3.0 sent "" and got nothing back in round 14)
        def listing(items, key):
            def answer(r):
                parts = r.split(" ")
                flt = parts[1] if len(parts) > 1 else ""
                return {key: [x for x in items if flt in (x if isinstance(x, str) else x.get("name", x.get("type", "")))]}
            return answer
        b.canned["event.classes"] = listing(["MissionStateChangedEvent", "PerformWarpEvent", "CameraShakeEvent"], "classes")
        b.canned["event.info"] = lambda r: {"name": r.split()[1], "fields": [{"name": "MissionName", "type": "string"}]}
        b.canned["level.checkpoints"] = listing([{"name": "CHK_SAV_01_LANDING", "hash": "0x1", "region": 3, "area": "Savali"}], "checkpoints")
        b.canned["level.regions"] = listing([{"name": "MIS_SAV_01_overlay", "type": "overlay", "story": True, "loaded": False}], "regions")
        b.canned["config.list"] = listing([{"id": "1111111111111111", "type": "MissionConfig"}, {"id": "2222222222222222", "type": "HeroConfig"}], "configs")
        b.canned["config.get"] = lambda r: {"type": "MissionConfig", "fields": {"Name": "MIS_INTRO"}}
        b.canned["script.nodes"] = lambda r: [{"component": 5000, "actor": 5001, "uid": "x", "class": r.split()[1]}]
        b.canned["script.node"] = lambda r: {"component": int(r.split()[1]), "outputs": [], "vars": []}
        d = tempfile.mkdtemp()
        try:
            r = subprocess.run([PWSH, "-NoProfile", "-File", str(MOD / "companion" / "research" / "Research-Campaign.ps1"),
                                "-PipeName", b.name, "-OutDir", d, "-NoSaves", "-NoDag"], capture_output=True, text=True, timeout=300)
        finally:
            b.close()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        zips = [f for f in os.listdir(d) if f.endswith(".zip")]
        self.assertEqual(len(zips), 1, r.stdout)
        z = zipfile.ZipFile(os.path.join(d, zips[0]))
        names = set(z.namelist())
        for want in ("event_classes.json", "event_info.json", "checkpoints.json", "regions.json", "config_list.json",
                     "configs.json", "script_nodes.json", "randomizer_research.lua", "summary.json"):
            self.assertIn(want, names)
        info = json.loads(z.read("event_info.json").decode("utf-8-sig"))
        self.assertIn("MissionStateChangedEvent", info)
        self.assertNotIn("CameraShakeEvent", info)
        cfg = json.loads(z.read("configs.json").decode("utf-8-sig"))
        self.assertEqual(list(cfg), ["1111111111111111"])
        lua_text = z.read("randomizer_research.lua").decode("utf-8")
        self.assertIn("MIS_INTRO", lua_text)
        summary = json.loads(z.read("summary.json").decode("utf-8-sig"))
        self.assertIn("described", summary["steps"]["nodes"])
        self.assertEqual(summary["steps"]["level"], "1 checkpoints, 1 regions")
        cps = json.loads(z.read("checkpoints.json").decode("utf-8-sig"))
        self.assertEqual(len(cps), 1)                           # found under two filters, kept once
        self.assertNotIn('""', " ".join(b.requests))
        self.assertIn("known", lua_text)                        # what the game answered
        shutil.rmtree(d, ignore_errors=True)
