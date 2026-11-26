#!/usr/bin/env python3
"""stage_check_log.py 3.0.0-alpha.3 - read rivet.log(s) and say, per .stage change, what the game really did.

  python -I stage_check_log.py rivet.log [more.log ...] [--manifest BUILD/stage_enemies_manifest.json]
                                [--json verdicts.json] [--all] [--save-dir verdicts]

With --manifest (a stage_allgame 2.0.0 build) every change of the build is listed, so changes you never reached count
as NOT REACHED per planet. Without it the changes come from the log's own "STAGE CHANGE n: ... | spawners KEY" lines
(18_rando_stage_enemies.lua writes one per changed spawner: at the start for small builds, when the spawner is first
listed for big ones). Several logs (several play sessions) are read in order and their evidence adds up.

Per changed spawner, per level visit:
  LISTED      "STAGE VARIABLE factory|template KEY: holds <uid> ... IS loaded" - the patched zone is in memory and the spawner exists
  SPAWNS      every "RANDO-ENEMIES SPAWN <handle> ... factory Templates KEY / node Template KEY ... spawned <kind>" and "STAGE SPAWN" lines (one per actor; duplicate records are collapsed)
  ACTIVE      DialogStartedEvent lines whose SenderHandle is one of those actors (combat barks)
  DEATH/GONE  "STAGE DEATH <h>" / "STAGE GONE <h>"
Verdicts:
  WORKED            the replacement kind spawned from the changed spawner
  ORIGINAL SPAWNED  the changed spawner still made the original kind
  NO SPAWN          listed (zone loaded, spawner present) but it never spawned while the level was loaded (its encounter
                    may not have started: play the area through)
  NOT REACHED       never listed (the area was not played, or the Enemy Randomizer was off: it must be ON to list)
--json writes the verdicts; `stage_allgame.py build --verdicts verdicts.json` then keeps WORKED changes as "confirmed"
and leaves ORIGINAL SPAWNED / NO SPAWN spawners native.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict

VERSION = "3.0.0-alpha.3"
RANK = {"WORKED": 0, "ORIGINAL SPAWNED": 1, "NO SPAWN": 2, "NOT REACHED": 3}


def short(n):
    return n.replace("enm_", "")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--manifest")
    ap.add_argument("--inventory", help="factory inventory.csv from the installed build (maps runtime spawner keys to zone paths)")
    ap.add_argument("--template-inventory", help="template_adapter_inventory.csv from the installed build (maps node Template keys to zone paths)")
    ap.add_argument("--json")
    ap.add_argument("--all", action="store_true", help="print every change, not only the reached ones")
    ap.add_argument("--save-dir", help="keep a copy of the log(s), this report and verdicts-<time>.json in this folder")
    a = ap.parse_args(argv)
    if a.save_dir:
        import io
        import shutil
        import time
        stamp = time.strftime("%Y%m%d-%H%M%S")
        os.makedirs(a.save_dir, exist_ok=True)
        kept = []
        for i, p in enumerate(a.logs):
            dst = os.path.join(a.save_dir, "rivet-%s%s.log" % (stamp, "-%d" % i if len(a.logs) > 1 else ""))
            shutil.copy2(p, dst)
            kept.append(dst)
        a.logs = kept
        a.json = a.json or os.path.join(a.save_dir, "verdicts-%s.json" % stamp)
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            rc = run(a)
        finally:
            sys.stdout = old
        txt = buf.getvalue()
        with open(os.path.join(a.save_dir, "check-%s.txt" % stamp), "w", encoding="utf-8") as fh:
            fh.write(txt)
        print(txt + "saved in %s: check-%s.txt, verdicts-%s.json, the log copy" % (a.save_dir, stamp, stamp))
        return rc
    return run(a)


def run(a):
    changes = OrderedDict()                       # key -> {n, original, replacement, planet, zone, zone_id, tier}
    inventory_by_key = defaultdict(dict)
    def read_inventory(path, key_col, adapter, require_spawner=False):
        if not path:
            return
        if not os.path.isfile(path):
            print("inventory not found (runtime-only evidence will not be zone-pinned): %s" % path)
            return
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            for row in csv.DictReader(fh):
                key = (row.get(key_col) or "").strip().upper()
                if not re.fullmatch(r"[0-9A-F]{16}", key):
                    continue
                if require_spawner and (row.get("is_SpawnerScriptAction") or "").strip().lower() not in ("true", "1", "yes"):
                    continue
                inventory_by_key[key][adapter] = {
                    "planet": row.get("planet") or "?", "zone": row.get("zone") or "?",
                    "zone_id": row.get("zone_id") or None}
    read_inventory(getattr(a, "inventory", None), "spawner", "factory")
    read_inventory(getattr(a, "template_inventory", None), "node_key", "node_template", True)
    if a.manifest:
        with open(a.manifest, encoding="utf-8") as fh:
            m = json.load(fh)
        for i, c in enumerate(m["changes"], 1):
            entry = {"n": i, "original": c["original"], "replacement": c["replacement"],
                     "replacement_uid": c["replacement_uid"], "planet": c.get("planet", "?"),
                     "zone": c.get("zone", "?"), "zone_id": c.get("zone_id"),
                     "tier": c.get("tier", "?"), "adapter": c.get("adapter", "factory")}
            for key in (c.get("spawner_keys") or [c["key"]]):
                changes[key.upper()] = dict(entry)
    lines = []
    for p in a.logs:
        with open(p, encoding="utf-8", errors="replace") as fh:
            lines += fh.read().splitlines()
    re_change_v3 = re.compile(r"STAGE CHANGE (\d+): (\S+) .*?-> ([0-9A-F]{16})(?: #\d+)? \(([^)]+)\) \| .*?\| adapter (factory|node_template) \| spawners (.*)$")
    re_change_legacy = re.compile(r"STAGE CHANGE (\d+): (\S+) .*?-> ([0-9A-F]{16})(?: #\d+)? \(([^)]+)\) \| .*\| spawners (.*)$")
    re_change_o = re.compile(r"STAGE CHANGE \d+: .*?\(([^)]+)\) -> [0-9A-F]{16}")
    re_var = re.compile(r"STAGE VARIABLE (factory|template) ([0-9A-F]{16}): holds ([0-9A-F]{16})")
    re_spawn = re.compile(r"RANDO-ENEMIES\tSPAWN (\d+) \| (\S+) \| (.*?) \| (factory Templates|node Template) ([0-9A-F]{16}) \| original (\S+) \| selected (\S+) uid ([0-9A-F]{16}|-) \| spawned (\S+)")
    re_spawn_legacy = re.compile(r"RANDO-ENEMIES\tSPAWN (\d+) \| (\S+) \| (.*?) \| (factory Templates|node Template) ([0-9A-F]{16}) \| original (\S+) \| selected \S+ \| spawned (\S+)")
    re_stage_spawn = re.compile(r"STAGE SPAWN (\d+) \| ([^|]+) \| (factory|template) ([0-9A-F]{16})(?: \(the patched spawner\))? \| variable ([0-9A-F]{16}) \| handle uid (\S+) \| spawned (\S+) \(([^)]*)\) \| change (\d+) .*? \| (.+)$")
    spawns_seen = set()
    for l in lines:
        m_ = re_change_v3.search(l) or re_change_legacy.search(l)
        if m_ and not a.manifest:
            adapter = m_.group(5) if re_change_v3.search(l) else "factory"
            keys_group = m_.group(6) if re_change_v3.search(l) else m_.group(5)
            for k in keys_group.split(","):
                k = k.strip().upper()
                if re.fullmatch(r"[0-9A-F]{16}", k) and k not in changes:
                    zone = m_.group(2)
                    pl = zone.replace("/", "\\").lower().split("\\")
                    planet = pl[pl.index("instance") + 1] if "instance" in pl and pl.index("instance") + 1 < len(pl) else "?"
                    meta = inventory_by_key.get(k, {}).get(adapter, {})
                    changes[k] = {"n": int(m_.group(1)), "original": re_change_o.search(l).group(1), "replacement": m_.group(4),
                                  "replacement_uid": m_.group(3), "planet": meta.get("planet", planet),
                                  "zone": meta.get("zone", zone), "zone_id": meta.get("zone_id"),
                                  "tier": "?", "adapter": adapter}
    rep_kinds = {v["replacement"] for v in changes.values()}
    visit = 0
    vis = defaultdict(lambda: defaultdict(lambda: {"listed": None, "spawns": [], "dead": set(), "gone": set()}))
    native = defaultdict(lambda: defaultdict(int))
    bark = defaultdict(list)
    where = {}
    re_dlg = re.compile(r"SenderHandle=(\d+) SoundEventId=\d+ SoundEventName=(\S+)")
    re_sd = re.compile(r"STAGE (DEATH|GONE) (\d+)")
    owner = {}
    def add_spawn(key, adapter, handle, kind, encounter):
        key = key.upper()
        expected = changes.get(key, {}).get("adapter", "factory")
        if key not in changes or adapter != expected:
            return
        identity = (key, visit, handle)
        if identity in spawns_seen:
            return
        spawns_seen.add(identity)
        vis[key][visit]["spawns"].append((handle, kind, encounter))
        owner[handle] = (key, visit)
    for l in lines:
        if "[rivet] init" in l:
            visit += 1
            where[visit] = "game start"
            continue
        if "RANDO-DISCOVER\tPlanetChangedEvent" in l or ("CheckpointTriggeredEvent" in l and "Loaded=true" in l):
            visit += 1
            where[visit] = l.split("\t")[-1].strip()
            continue
        m_ = re_var.search(l)
        if m_ and m_.group(2) in changes:
            vis[m_.group(2)][visit]["listed"] = m_.group(3)
            continue
        m_ = re_stage_spawn.search(l)
        if m_:
            h, adapter, key, kind = int(m_.group(1)), m_.group(3), m_.group(4), m_.group(7)
            add_spawn(key, "factory" if adapter == "factory" else "node_template", h, kind, m_.group(2).strip())
            continue
        m_ = re_spawn.search(l)
        if m_:
            h, key = int(m_.group(1)), m_.group(5)
            adapter = "factory" if m_.group(4) == "factory Templates" else "node_template"
            original, selected, selected_uid, kind = m_.group(6), m_.group(7), m_.group(8), m_.group(9)
            if key not in changes and selected != "-" and re.fullmatch(r"[0-9A-F]{16}", selected_uid):
                meta = inventory_by_key.get(key, {}).get(adapter, {})
                changes[key] = {"n": 0, "original": original, "replacement": selected,
                                "replacement_uid": selected_uid, "planet": meta.get("planet", m_.group(2)),
                                "zone": meta.get("zone", "runtime:" + m_.group(3)),
                                "zone_id": meta.get("zone_id"), "tier": "runtime-observed",
                                "adapter": adapter, "runtime_only": True}
                rep_kinds.add(selected)
            if key in changes:
                add_spawn(key, adapter, h, kind, m_.group(3))
            elif any(kind.startswith(r[:19]) for r in rep_kinds) and "STAGE" not in l:
                native[key][kind] += 1
            continue
        m_ = re_spawn_legacy.search(l)
        if m_:
            h, key, kind = int(m_.group(1)), m_.group(5), m_.group(7)
            adapter = "factory" if m_.group(4) == "factory Templates" else "node_template"
            if key in changes:
                add_spawn(key, adapter, h, kind, m_.group(3))
            elif any(kind.startswith(r[:19]) for r in rep_kinds) and "STAGE" not in l:
                native[key][kind] += 1
            continue
        m_ = re_dlg.search(l)
        if m_:
            bark[int(m_.group(1))].append(m_.group(2))
            continue
        m_ = re_sd.search(l)
        if m_ and int(m_.group(2)) in owner:
            key, v_i = owner[int(m_.group(2))]
            vis[key][v_i]["dead" if m_.group(1) == "DEATH" else "gone"].add(int(m_.group(2)))
    if not changes:
        print("no changed spawner known: pass --manifest, or the log contains no STAGE CHANGE / runtime replacement SPAWN record")
        return 1
    verdicts = OrderedDict()
    detail = {}
    for key, c in changes.items():
        out = []
        total = Counter()
        if key in vis:
            for v_i, v in sorted(vis[key].items()):
                sp = v["spawns"]
                kinds = Counter(k for _, k, _ in sp)
                if not sp:
                    verdict = "NO SPAWN" if v["listed"] else "listed earlier, no spawn on this visit"
                elif any(k.startswith(c["replacement"][:19]) for k in kinds):
                    verdict = "WORKED"
                elif any(k.startswith(c["original"][:19]) for k in kinds):
                    verdict = "ORIGINAL SPAWNED"
                else:
                    verdict = "something else spawned"
                total[verdict] += 1
                out.append("  visit %d (%s): %s | listed %s | spawns %d %s" % (
                    v_i, where.get(v_i, "start"), verdict, v["listed"] or "-", len(sp), dict(kinds) if kinds else ""))
                for h, kind, enc in sp:
                    b = bark.get(h, [])
                    fate = "died" if h in v["dead"] else "gone" if h in v["gone"] else "no death seen"
                    out.append("      actor %d %s @ %s | %s | barks %d%s" % (h, short(kind), enc, fate, len(b),
                                                                         (": " + ", ".join(b[:4])) if b else ""))
        verdict = ("WORKED" if total["WORKED"] else "ORIGINAL SPAWNED" if total["ORIGINAL SPAWNED"] else
                   "NO SPAWN" if total["NO SPAWN"] else "NOT REACHED")
        verdicts[key] = verdict
        detail[key] = out
    print("stage_check_log %s: %s | %d change(s)%s" % (VERSION, ", ".join(a.logs), len(changes),
                                                         " from the manifest" if a.manifest else " named in the log"))
    for key, c in changes.items():
        if verdicts[key] == "NOT REACHED" and not a.all:
            continue
        print("\nCHANGE %d  %s  %s  %s -> %s  [%s]" % (c["n"], key, c["planet"], c["original"], c["replacement"], c["tier"]))
        for x in detail[key]:
            print(x)
        print("  => %s" % verdicts[key])
    # summary
    by_planet = defaultdict(Counter)
    by_tier = defaultdict(Counter)
    for key, c in changes.items():
        by_planet[c["planet"]][verdicts[key]] += 1
        by_tier[c["tier"].split("/")[0]][verdicts[key]] += 1
    cols = ["WORKED", "ORIGINAL SPAWNED", "NO SPAWN", "NOT REACHED"]
    print("\nSUMMARY BY PLANET\n  %-22s %s" % ("planet", " ".join("%17s" % c for c in cols)))
    for p, cnt in sorted(by_planet.items()):
        print("  %-22s %s" % (p, " ".join("%17d" % cnt[c] for c in cols)))
    print("\nSUMMARY BY TIER\n  %-22s %s" % ("tier", " ".join("%17s" % c for c in cols)))
    for t, cnt in sorted(by_tier.items()):
        print("  %-22s %s" % (t, " ".join("%17d" % cnt[c] for c in cols)))
    tot = Counter(verdicts.values())
    print("\nTOTAL: %s" % ", ".join("%s %d" % (c, tot[c]) for c in cols))
    if native:
        print("\nNot changed by the .stage (their own zone data already uses a replacement kind; 18's STAGE SUMMARY may count them):")
        for key, kinds in sorted(native.items())[:40]:
            print("  %s %s" % (key, dict(kinds)))
    if a.json:
        payload = {"tool": "stage_check_log " + VERSION, "logs": a.logs,
                   "verdicts": {k: {"verdict": v, "replacement_uid": changes[k]["replacement_uid"], "original": changes[k]["original"],
                                    "replacement": changes[k]["replacement"], "planet": changes[k]["planet"], "zone": changes[k]["zone"],
                                    "zone_id": changes[k].get("zone_id"), "adapter": changes[k].get("adapter", "factory")}
                                for k, v in verdicts.items()}}
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        print("written: %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())