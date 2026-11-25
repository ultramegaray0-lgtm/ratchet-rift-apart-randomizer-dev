#!/usr/bin/env python3
"""test_stage_allgame.py - end-to-end checks of stage_allgame.py 2.0.0 against the REAL Ardolis zone.

The real zone is game data and is never committed: pass it (and, optionally, the Phase B .stage and its JSON manifest
to prove the writer is byte-identical to stage_multi 1.2.0's). Without the zone every test is skipped.

usage: python -I test_stage_allgame.py --zone AE530D22FE113E2B.zone.orig [--phaseb-stage X.stage --phaseb-manifest X.json]
       [--scripts DIR_WITH_16_LUA] [--log rivet.log ...]
It builds a SYNTHETIC game folder (fakegame.py: toc, dag, one DSAR archive) holding:
  1. the real ard_firstvisit_gp.zone;
  2. a synthetic Ardolis zone holding actors with the uids of four of the real zone's EXTERNAL spawn points
     (a StaticVolume, a crab anim clue, a shooter anim clue, a volume), so cross-zone resolution is tested;
  3. a copy of the real zone under another planet's path (a second changed member, duplicate uids across zones).
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fakegame          # noqa: E402
import rcra              # noqa: E402
import stage_allgame as SA   # noqa: E402

ARD = "levels\\i29\\instance\\ardolis\\ardolis_main\\ard_firstvisit_gp.zone"
ARD_GLOBAL = "levels\\i29\\instance\\ardolis\\ardolis_main\\ardolis_main_globalgp_test.zone"
COPY = "levels\\i29\\instance\\testplanet\\testplanet_main\\copy_gp.zone"
VOLUME = "system\\volumes\\staticvolume.actor"
CLUE_CRAB = "characters\\animclue\\animclue_toxic_crab_unburrow_alert_intro.actor"
CLUE_SHOOTER = "characters\\animclue\\animclue_pirate_shooter_group_stand_conversation_idle_02.actor"

results = []


def ok(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("%s  %s%s" % ("PASS" if cond else "FAIL", name, ("  - " + detail) if detail and not cond else ""))


def run(args):
    p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "stage_allgame.py")] + args, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone")
    ap.add_argument("--phaseb-stage")
    ap.add_argument("--phaseb-manifest")
    ap.add_argument("--scripts")
    ap.add_argument("--log", action="append", default=[])
    a = ap.parse_args()
    if not a.zone or not os.path.isfile(a.zone):
        print("SKIP: no real zone given (--zone AE530D22FE113E2B.zone.orig); game data is never committed")
        return 0
    blob = open(a.zone, "rb").read()
    header, raw = blob[:36], blob[36:]
    ok("real zone is the game's (sha256 d40540ed...)",
       hashlib.sha256(raw).hexdigest() == "d40540edad455dee68a274540cd53589b3142ce458bac16bde82a0d6f185e016")

    # ---- the zone decoder and writer equal stage_multi 1.2.0's -----------------------------------------------------
    z = SA.Zone(header, raw, ARD)
    n, bad = z.c1()
    ok("decoder: C1 holds on the real zone (%d local refs)" % n, not bad and n == 302)
    facs = z.factories()
    ok("decoder: 43 factories in ard_firstvisit_gp", len(facs) == 43, str(len(facs)))
    if a.phaseb_stage and a.phaseb_manifest:
        m = json.load(open(a.phaseb_manifest))
        with zipfile.ZipFile(a.phaseb_stage) as zf:
            member = zf.read("0/AE530D22FE113E2B")
        mine = SA.apply_changes(raw, m["changes"])
        ok("writer: the Phase B changes give the Phase B zone byte for byte", header + mine == member)

    tmp = tempfile.mkdtemp(prefix="allgame_test_")
    try:
        # ---- synthetic game folder --------------------------------------------------------------------------------
        glob = fakegame.zone([VOLUME, CLUE_CRAB, CLUE_SHOOTER],
                             [(0xD14E8A72C2F15EA3, 0, "vol_a"), (0xD2FA1CDDCF5FD1F3, 1, "clue_crab"),
                              (0xBAD8BDEDF0A2F250, 2, "clue_shooter"), (0xAEC3CE1D9F8A8D8E, 0, "vol_b")], [], [])
        game = os.path.join(tmp, "game")
        noact = fakegame.dat1(0x1F390AA0, [(0x12345678, b"lighting only")])
        fakegame.build(game, {ARD: raw, ARD_GLOBAL: glob, COPY: raw,
                              "levels\\i29\\instance\\ardolis\\ardolis_main\\ard_lighting.zone": noact})
        open(os.path.join(game, "RiftApart.exe"), "wb").write(b"MZ")
        os.makedirs(os.path.join(game, "mods"))
        os.makedirs(os.path.join(game, "scripts"))
        open(os.path.join(game, "rivet.toml"), "w").write('[assets]\npaths = ["mods/RandoEnemies.stage"]\n')
        open(os.path.join(game, "mods", "RandoEnemies.stage"), "wb").write(b"OLD STAGE")
        common = ["--no-evidence"]
        if a.scripts:
            common += ["--scripts", a.scripts]
        for l in a.log:
            common += ["--log", l]

        out = os.path.join(tmp, "build")
        rc, txt = run(["build", "--game", game, "--out", out] + common)
        ok("build: exit 0", rc == 0, txt[-1500:])
        if rc:
            return 1
        ok("build: the main build and safe/ both pass their check", txt.count(": PASS") == 2, txt[-800:])
        m = json.load(open(os.path.join(out, "stage_enemies_manifest.json")))
        ms = json.load(open(os.path.join(out, "safe", "stage_enemies_manifest.json")))
        ch = {c["key"]: c for c in m["changes"] if c["zone_id"] == "AE530D22FE113E2B"}
        ok("scan: 3 zones, 2 changed members (Ardolis + the copy)", len(m["zones"]) == 2, str([z["zone"] for z in m["zones"]]))
        planets = {z["planet"] for z in m["zones"]}
        ok("planet names from the zone path", planets == {"ardolis", "testplanet"}, str(planets))
        for key in ("FF06CCC2A9AC1EA2", "9C3139C7FFED7137", "FA5FB32C7AAB4C4A", "DAFCA25C58FD387F"):
            ok("pin %s kept in max and safe" % key, ch.get(key, {}).get("tier") == "confirmed"
               and any(c["key"] == key and c["tier"] == "confirmed" for c in ms["changes"]))
        ok("cross-zone: D1FD84D3 (external -> a StaticVolume of another zone) is external-volume",
           ch.get("D1FD84D3A21C0F9A", {}).get("spawn_tier") == "external-volume", str(ch.get("D1FD84D3A21C0F9A")))
        ok("cross-zone: DAFCA25C (external -> a crab anim clue) is clue-native",
           ch.get("DAFCA25C58FD387F", {}).get("spawn_tier") == "clue-native", str(ch.get("DAFCA25C58FD387F", {}).get("spawn_tier")))
        inv = open(os.path.join(out, "inventory.csv"), encoding="utf-8").read()
        line = [l for l in inv.splitlines() if "F93E9AE445CCEF41" in l and "ard_firstvisit" in l]
        ok("cross-zone: F93E9AE4 (external -> a SHOOTER anim clue) is refused for a brawler",
           "F93E9AE445CCEF41" not in ch and line and "never used for" in line[0], str(line))
        ok("shared-seen tier only in max: F3D033F9/F4A34D9C/F607A5D7/FE80D89C",
           all(ch.get(k, {}).get("tier", "").startswith("shared-seen") for k in
               ("F3D033F9CBFADB82", "F4A34D9C49E5642A", "F607A5D72DB3F350", "FE80D89C2D6D5A2D"))
           and not any(c["tier"].startswith("shared") for c in ms["changes"]))
        ok("F512DB23 co-owner never changed (88259456, D26E32B8)",
           not any(c["key"] in ("88259456BFA87EA8", "D26E32B81D7B7C85") for c in m["changes"]))
        anim = [c for c in m["changes"] if c["spawn_tier"] not in ("volume", "external-volume", "external-unresolved",
                                                                    "clue-native", "clue-family")]
        ok("every change has a known spawn tier", not anim)
        ok("no cross-faction change", all(c["original"].split("_")[1] == c["replacement"].split("_")[1] for c in m["changes"]))
        ok("no change to a pair proven bad (-> shooter)", not any(c["replacement"] == "enm_pirate_robot_shooter" for c in m["changes"]))
        ok("CECB812E81FB7301 (shooter clue) never changed", not any(c["key"] == "CECB812E81FB7301" for c in m["changes"]))
        # every zone member: only the planned bytes differ
        info, files = rcra.read_stage(os.path.join(out, "RandoEnemies.stage"))
        allowed_ok = True
        for zrec in m["zones"]:
            data = files["0/" + zrec["zone_id"]][36:]
            zc = [c for c in m["changes"] if c["zone_id"] == zrec["zone_id"]]
            allowed = set()
            for c in zc:
                allowed |= set(range(c["entry_abs"] + 4, c["entry_abs"] + 6)) | set(range(c["entry_abs"] + 16, c["entry_abs"] + 24))
            diff = {i for i in range(len(raw)) if raw[i] != data[i]}
            allowed_ok = allowed_ok and diff <= allowed and len(data) == len(raw)
        ok("every member differs from the game's zone only in {index, uid} of its changes", allowed_ok)
        # Lua manifest parses and agrees
        try:
            import lupa
            L = lupa.LuaRuntime()
            L.execute(open(os.path.join(out, SA.MANIFEST_LUA), encoding="utf-8").read())
            t = L.globals().RANDO_STAGE_ENEMIES
            n_lua = len(list(t.changes.values()))
            ok("Lua manifest parses (Lua %s) with %d changes" % (L.eval("_VERSION"), n_lua), n_lua == len(m["changes"])
               and t.changes[1].zone is not None and t.changes[1].spawner_keys[1] is not None)
        except ImportError:
            print("SKIP  Lua manifest parse (pip install lupa)")
        rep = open(os.path.join(out, "COVERAGE_REPORT.md"), encoding="utf-8").read()
        ok("a zone without actors is 'no actors', not an error", "no actors 1" in rep and "could not be read" not in rep,
           rep[rep.find("zone status"):][:120])
        ok("the build carries the scale 18_rando_stage_enemies.lua", os.path.isfile(os.path.join(out, SA.STAGE_LUA_FILE))
           and 'ST.SCALE = "2.0.0"' in open(os.path.join(out, SA.STAGE_LUA_FILE), encoding="utf-8").read())
        # bundled in-game evidence: F93E9AE4 was NO SPAWN on 2026-11-25
        outv = os.path.join(tmp, "build_ev")
        rcv, txtv = run(["build", "--game", game, "--out", outv] + [x for x in common if x != "--no-evidence"])
        invv = open(os.path.join(outv, "inventory.csv"), encoding="utf-8").read() if rcv == 0 else ""
        lv = [l for l in invv.splitlines() if "F93E9AE445CCEF41" in l and "ard_firstvisit" in l]
        ok("bundled evidence: F93E9AE4 (NO SPAWN in your run) left native with the verdict as reason",
           rcv == 0 and "bundled in-game evidence" in txtv and lv and "in-game verdict NO SPAWN" in lv[0], str(lv)[:300])
        # learning: a shared spawner that WORKED makes its co-owner class "seen" (B0683892: co-owner 651365AF/B57CF5E2)
        vf = os.path.join(tmp, "v_learn.json")
        json.dump({"verdicts": {"B0683892A1C1273C": {"verdict": "WORKED", "replacement_uid": "92C793D47A4657B6", "zone": ARD}}},
                  open(vf, "w"))
        outl = os.path.join(tmp, "build_learn")
        rcl, txtl = run(["build", "--game", game, "--out", outl, "--verdicts", vf, "--no-safe"] + common)
        ml = json.load(open(os.path.join(outl, "stage_enemies_manifest.json"))) if rcl == 0 else {"changes": []}
        cl = [c for c in ml["changes"] if c["key"] == "B0683892A1C1273C" and c["zone_id"] == "AE530D22FE113E2B"]
        ok("learning: B0683892 (shared, co-owner 651365AF/B57CF5E2) WORKED -> kept, class learned",
           rcl == 0 and "1 co-owner class/plug pair(s) seen working" in txtl and cl and cl[0]["replacement"] == "enm_pirate_robot_melee",
           txtl[-300:])
        # determinism / seed
        out2 = os.path.join(tmp, "build2")
        run(["build", "--game", game, "--out", out2] + common)
        same = open(os.path.join(out, "RandoEnemies.stage"), "rb").read() == open(os.path.join(out2, "RandoEnemies.stage"), "rb").read()
        ok("deterministic: same seed, same .stage bytes", same)
        rc3, _ = run(["build", "--game", game, "--out", out2] + common)
        ok("never overwrites a build folder", rc3 == 2)
        # planet filter
        out4 = os.path.join(tmp, "build4")
        rc4, txt4 = run(["build", "--game", game, "--out", out4, "--planet", "testplanet"] + common)
        m4 = json.load(open(os.path.join(out4, "stage_enemies_manifest.json"))) if rc4 == 0 else {"zones": []}
        ok("--planet testplanet builds only that planet", rc4 == 0 and [z["planet"] for z in m4["zones"]] == ["testplanet"], txt4[-400:])
        # tamper: check must fail
        bad = os.path.join(tmp, "bad")
        shutil.copytree(out, bad)
        sp = os.path.join(bad, "RandoEnemies.stage")
        info, files = rcra.read_stage(sp)
        k = "0/AE530D22FE113E2B"
        d = bytearray(files[k])
        d[36 + 1000] ^= 0xFF
        files[k] = bytes(d)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("info.json", json.dumps(info))
            for n_, b in files.items():
                zf.writestr(n_, b)
        open(sp, "wb").write(buf.getvalue())
        mm = json.load(open(os.path.join(bad, "stage_enemies_manifest.json")))
        mm["stage_sha256"] = hashlib.sha256(buf.getvalue()).hexdigest()
        json.dump(mm, open(os.path.join(bad, "stage_enemies_manifest.json"), "w"))
        rc5, txt5 = run(["check", "--game", game, "--build", bad])
        ok("check FAILS on a stray byte", rc5 == 1 and "FAIL" in txt5, txt5[-400:])
        # install / uninstall (fake game folder only)
        shutil.copy(os.path.join(HERE, "..", "..", "scripts", SA.STAGE_LUA_FILE), out) if os.path.isfile(
            os.path.join(HERE, "..", "..", "scripts", SA.STAGE_LUA_FILE)) else None
        rc6, txt6 = run(["install", "--game", game, "--build", out])
        inst = open(os.path.join(game, "mods", "RandoEnemies.stage"), "rb").read()
        ok("install: copies the build, backs up the old file", rc6 == 0 and inst == open(os.path.join(out, "RandoEnemies.stage"), "rb").read()
           and os.path.isdir(os.path.join(game, "rando_stage_backup")), txt6[-400:])
        rc7, txt7 = run(["uninstall", "--game", game])
        ok("uninstall: the old file is back", rc7 == 0 and open(os.path.join(game, "mods", "RandoEnemies.stage"), "rb").read() == b"OLD STAGE", txt7[-300:])
        # scan-only
        out8 = os.path.join(tmp, "scan")
        rc8, _ = run(["scan", "--game", game, "--out", out8] + common)
        ok("scan: writes inventory and report, no .stage", rc8 == 0 and os.path.isfile(os.path.join(out8, "inventory.csv"))
           and not os.path.exists(os.path.join(out8, "RandoEnemies.stage")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    failed = [n for n, c in results if not c]
    print("\n%d checks, %d failed" % (len(results), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())