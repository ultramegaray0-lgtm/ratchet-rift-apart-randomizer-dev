"""Independent check of the release's gameplay requirements (Phase 2) over many seeds.

Run from the repo root:  python3 -I /home/claude/scripts/check_reqs.py <repo> [count]
Uses the shipped Lua generator through tools/rando.py, with the kit's own 04_rando_settings.lua.
"""
import collections
import os
import re
import sys

repo = os.path.abspath(sys.argv[1])
N = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
sys.path[:0] = [os.path.join(repo, "tests"), os.path.join(repo, "tools")]
os.chdir(repo)
import rando  # noqa: E402
from luajson import py  # noqa: E402
from test_v90 import USER_SETTINGS  # noqa: E402

eng = rando.Engine()
G = eng.G
bolt_worthy = eng.lua.eval("function(k) return RANDO_GEN.bolt_worthy(k) end")
OVERRIDE = dict(a.split("=", 1) for a in sys.argv[3:])
db = eng.db()
preset, user = USER_SETTINGS()
user = dict(user, **OVERRIDE)
preset = user.pop('preset', preset)
fails = collections.Counter()
stats = collections.Counter()
starts = set()
routes = set()
first_coords = set()
gb_item = gb_cur = 0
total = 0

for ar in (False, True):
    for i in range(N):
        total += 1
        s, audit = eng.generate(f"pubrel-{ar}-{i}", dict(user, restored_weapons=ar), preset)
        if s is None or audit:
            fails["generator refused or audit failed"] += 1
            continue
        d = py(s)
        st = d["start"]["items"]
        # Hoverboots + Map-O-Matic always from the start
        if "hoverboots" not in st or "map_o_matic" not in st:
            fails["start lacks Hoverboots/Map-O-Matic"] += 1
        starts.add(tuple(sorted(x for x in st if x.startswith(("weapon:", "box_", "omni", "glitch")))))
        # one item per location (structure) and armor in the pool
        armor = 0
        where = collections.defaultdict(list)
        for lid, loc in d["locations"].items():
            it = loc.get("item")
            if isinstance(it, (list, dict)):
                fails["a location holds more than one item"] += 1
                continue
            if it is None:
                continue
            if it.startswith("armor:"):
                armor += 1
            if not it.startswith("filler:"):
                where[it].append(lid)
            if lid.startswith("goldbolt:"):
                if it.startswith("filler:"):
                    gb_cur += 1
                else:
                    gb_item += 1
        gbs = [lid for lid in d["locations"] if lid.startswith("goldbolt:")]
        if len(gbs) != 25:
            fails[f"{len(gbs)} Gold Bolt locations, not 25"] += 1
        for lid in gbs:
            it = d["locations"][lid].get("item")
            if not it or it.startswith("filler:") or not bolt_worthy(it):
                fails["a Gold Bolt does not hold exactly one grantable item"] += 1
        rnd_start = [x for x in st if x not in ("hoverboots", "map_o_matic") and not x.startswith("access:")]
        if not rnd_start:
            fails["starting kit has no randomized item"] += 1
        stats["random start items"] += len(rnd_start)
        sph1 = set(d["spheres"][0]) if d.get("spheres") else set()
        ew = sum(1 for l in sph1 if (d["locations"].get(l) or {}).get("item", "").startswith("weapon:"))
        ec = sum(1 for l in sph1 if (d["locations"].get(l) or {}).get("item", "").startswith("access:"))
        stats["early weapons"] += ew
        stats["early coords"] += ec
        if ew < 2: stats["seeds with <2 early weapons"] += 1
        if ew == 0: stats["seeds with 0 early weapons"] += 1
        if ec == 0: stats["seeds with no early Coordinates"] += 1
        if armor == 0 and d["settings"]["armor"]:
            fails["no armor in the reward pool"] += 1
        stats["armor rewards"] += armor
        for it, lids in where.items():
            if len(lids) > 1:
                fails[f"item placed twice: {it}"] += 1
        # a weapon sold in the shop is never also obtainable another way
        sold = set(d["shop"].get("slots", {}).values())
        for w in sold:
            if w in where:
                fails["weapon sold AND placed as a reward"] += 1
            if w in st:
                fails["weapon sold AND in the start"] += 1
        for w in st:
            if w.startswith("weapon:") and w in where:
                fails["start weapon also a reward"] += 1
        # planet shuffle on by default: hub plan exists, Coordinates are items, routes differ
        if not d["settings"]["hub"] or not d.get("hub"):
            fails["hub / planet shuffle not active"] += 1
        else:
            routes.add(tuple(d["hub"]["route"]))
        coords = [it for it in where if it.startswith("access:")]
        if not coords:
            fails["no Coordinates in the pool"] += 1
        stats["coordinates rewards"] += len(coords)

# No Gold Bolt prices: nothing in the shipped scripts touches the Gold Bolt reward costs
scripts = os.path.join(repo, "mod", "RiftApartRandomizer", "scripts")
cost_hits = []
for f in sorted(os.listdir(scripts)):
    txt = open(os.path.join(scripts, f), encoding="utf-8").read()
    for m in re.finditer(r"GoldBoltRewardCost|GoldBoltSystemConfig|Rewards\[\]|gold_?bolt_?(price|cost)", txt, re.I):
        cost_hits.append((f, m.group(0)))

print(f"seeds checked: {total} (kit settings: preset={preset}, {user}; half with ARSENAL_RESTORED)")
print(f"failures: {sum(fails.values())}")
for k, v in fails.most_common():
    print(f"  {v:6d}  {k}")
print(f"distinct starting kits: {len(starts)}")
print(f"distinct hub routes (planet orders): {len(routes)}")
print(f"Gold Bolts holding an item: {gb_item}, holding currency: {gb_cur} "
      f"({100.0 * gb_cur / max(1, gb_item + gb_cur):.1f}% currency)")
print(f"avg armor rewards per seed: {stats['armor rewards'] / total:.1f}; "
      f"avg Coordinates rewards: {stats['coordinates rewards'] / total:.1f}")
print(f"settings used: distribution={d['settings']['distribution']}, hub={d['settings']['hub']}, early_weapons={d['settings']['early_weapons']}")
print(f"random start items per seed: {stats['random start items'] / total:.2f}")
print(f"weapons reachable with the start alone (sphere 1): avg {stats['early weapons'] / total:.2f}; "
      f"seeds with <2: {stats['seeds with <2 early weapons']}, with 0: {stats['seeds with 0 early weapons']}")
print(f"Coordinates in sphere 1: avg {stats['early coords'] / total:.2f}; seeds with none: {stats['seeds with no early Coordinates']}")
print(f"Gold Bolt price/cost references in scripts: {cost_hits or 'none'}")
sys.exit(1 if fails else 0)
