"""Combat audit of a rivet.log (dev 10.29+): for every level visit, the enemy replacements that spawned, by pair
(spawner adapter | original kind > replacement kind), and the deaths the randomizer tied to its own bots.

Dev 10.29 logs say how many deaths named one of the randomizer's bots ("deaths seen N (of our bots M)") but not
which ones. This tool shows, per level visit, which replacement pairs could account for the bots that never died:
a pair whose spawn count equals (replaced - deaths of ours) exactly is reported. That is arithmetic on the log, not
proof of which bot died; dev 10.30 logs each death of a replaced bot by handle ("DEATH ...").

    python tools/combat_audit.py tests/data/round40_rivet.log
"""
import re
import sys
from collections import Counter, OrderedDict

SPAWN = re.compile(r"\tSPAWN (\d+) \| (\S+) \| (.*?) \| (factory Templates|node Template group|node Template|no spawner) (\S+) \| "
                   r"original (\S+) \| selected (\S+) \| spawned (\S+) \((\w+)\) \| (.*)$")
DETAIL = re.compile(r"level detail: .*deaths seen (\d+) \(of our bots (\d+)\), bots gone (\d+)")
SUMMARY = re.compile(r"ENEMY SPAWNS on this level: (\d+), replaced (\d+)")
DEATH = re.compile(r"\tDEATH (\d+) ")
ADAPTER = {"factory Templates": "factory", "node Template": "template", "node Template group": "group"}


def kind(name):
    return name[:19].lower()


def audit(lines):
    visits, cur = [], None

    def new():
        return {"replaced": OrderedDict(), "handles": {}, "spawns": 0, "deaths": None, "ours": None, "gone": None,
                "missions": Counter(), "start": None, "end": None, "dead_handles": set()}

    for i, line in enumerate(lines):
        m = SPAWN.search(line)
        if m:
            if cur is None:
                cur = new(); cur["start"] = i + 1
            h, _, enc, ad, _key, orig, sel, spawned, fam, result = m.groups()
            cur["spawns"] += 1
            cur["missions"][enc.split(" @ ")[0]] += 1
            if result.startswith("SUCCESS"):
                pair = "%s|%s>%s/%s" % (ADAPTER.get(ad, ad), kind(orig), kind(spawned), fam)
                cur["replaced"].setdefault(pair, []).append(int(h))
                cur["handles"][int(h)] = pair
            continue
        m = DEATH.search(line)
        if m and cur is not None:
            cur["dead_handles"].add(int(m.group(1)))
            continue
        m = DETAIL.search(line)
        if m and cur is not None:
            cur["deaths"], cur["ours"], cur["gone"] = (int(x) for x in m.groups())
            continue
        if SUMMARY.search(line) and cur is not None:
            cur["end"] = i + 1
            visits.append(cur)
            cur = None
    return visits


def report(visits):
    out = []
    for n, v in enumerate(visits, 1):
        replaced = sum(len(x) for x in v["replaced"].values())
        mission = v["missions"].most_common(1)[0][0] if v["missions"] else "-"
        out.append("visit %d (log lines %s-%s, %s): %d enemy spawns, %d replaced, deaths seen %s, of our bots %s, gone %s"
                   % (n, v["start"], v["end"], mission, v["spawns"], replaced, v["deaths"], v["ours"], v["gone"]))
        for pair, hs in v["replaced"].items():
            dead = sum(1 for h in hs if h in v["dead_handles"])
            out.append("  %-62s spawned %2d%s" % (pair, len(hs), ("  died %d (by handle)" % dead) if v["dead_handles"] else ""))
        if replaced and v["ours"] is not None and not v["dead_handles"]:
            missing = replaced - v["ours"]
            fits = [p for p, hs in v["replaced"].items() if len(hs) == missing]
            out.append("  replaced bots with no death tied to them: %d%s" % (
                missing, ("; pair(s) with exactly that many spawns: " + ", ".join(fits)) if fits and missing else ""))
    return "\n".join(out)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "tests/data/round40_rivet.log"
    with open(path, encoding="utf-8", errors="replace") as f:
        print(report(audit(f.read().splitlines())))
