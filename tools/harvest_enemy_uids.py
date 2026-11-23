"""Every enemy template uid the real game's logs (tests/data/round*_rivet.log) named in a "learned template" line,
that the built-in registry of 16_rando_spawners.lua (V.REG_BUILTIN) does not hold yet.

    python tools/harvest_enemy_uids.py          -> Lua lines for V.REG_BUILTIN (stdout)
    python tools/harvest_enemy_uids.py --check  -> exit 1 if a harvestable uid is missing from V.REG_BUILTIN

A template uid is level data (the same in every game; round45 learned BA312C9E31A934D2 on two loads with two different
actor handles), so a uid the game named once classifies that spawner before its first spawn on every later save.
Only uids with ONE kind in every log (no MIXED line) and an enemy / boss role are taken; friendlies, mounts and story
bosses are never written (they stay "kind not known" -> never changed, which is what they should be anyway).
"""
import collections
import glob
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPAWNERS = ROOT / "mod" / "RiftApartRandomizer" / "scripts" / "16_rando_spawners.lua"
LEARNED = re.compile(r"learned template \d+ \(uid ([0-9A-F]{16})\): (\S+) = (\w+)/(\w+), role (\w+)")
MIXED = re.compile(r"template \d+ \(([0-9A-F]{16})\) spawned \S+ and \S+: MIXED")
NEVER_FAMILIES = {"friendly", "mount", "story_boss", "hazard"}


def harvest():
    seen, mixed = collections.defaultdict(set), set()
    for path in sorted(glob.glob(str(ROOT / "tests" / "data" / "round*_rivet.log"))):
        for line in open(path, encoding="utf-8", errors="replace"):
            m = LEARNED.search(line)
            if m:
                seen[m.group(1)].add(m.groups()[1:])
            m = MIXED.search(line)
            if m:
                mixed.add(m.group(1))
    out = {}
    for uid, obs in seen.items():
        if uid in mixed:
            continue
        kinds = {(n, f, c) for n, f, c, _ in obs}
        if len(kinds) != 1:
            continue
        name, fam, cls = next(iter(kinds))
        roles = {r for *_, r in obs}
        if fam in NEVER_FAMILIES:
            continue
        role = "boss" if "boss" in roles else ("enemy" if "enemy" in roles else None)
        if role is None and fam == "unclear":
            role = "enemy"                      # "all" mode: the unclear bot classes are regular enemies
        if role is None:
            continue
        out[uid] = (name, fam, cls, role)
    return out


def builtin():
    src = SPAWNERS.read_text(encoding="utf-8")
    blk = src[src.index("V.REG_BUILTIN = {"):]
    blk = blk[:blk.index("\n}\n")]
    return set(re.findall(r'\["([0-9A-F]{16})"\]', blk))


def main():
    have = builtin()
    missing = {u: v for u, v in sorted(harvest().items()) if u not in have}
    if "--check" in sys.argv:
        for u in missing:
            print("missing", u, missing[u])
        return 1 if missing else 0
    for u, (n, f, c, r) in missing.items():
        print(f'  ["{u}"] = "{n}|{f}|{c}|{r}",')
    return 0


if __name__ == "__main__":
    sys.exit(main())
