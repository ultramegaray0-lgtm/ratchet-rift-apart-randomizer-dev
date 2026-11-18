"""Every bot actor the real game spawned in the logs of tests/data (rounds with dev(spawnprobe) or the Enemy
Randomizer's own lines), with its bot class, family and role (16_rando_spawners.lua SP.FAMILY_CLASSES), the planets,
the spawner kind (factory / node), and the in-game replacement evidence (VERIFY lines).

    python tools/enemy_census.py            -> a table (the source of docs/ENEMY_RANDOMIZER_COVERAGE.md's evidence)

Only what a log shows is listed; nothing is guessed.
"""
import collections
import glob
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPAWNERS = ROOT / "mod" / "RiftApartRandomizer" / "scripts" / "16_rando_spawners.lua"


def family_table():
    fam = []
    for m in re.finditer(r'\{ "(\w+)", "(\w+)", "(\w+)" \}', SPAWNERS.read_text(encoding="utf-8")):
        fam.append(m.groups())
    return fam


def classify(classes, fam):
    cs = set(classes.split(","))
    for c, f, r in fam:
        if c in cs or c + "Prius" in cs:
            return c, f, r
    return None, None, None


def census():
    fam = family_table()
    seen = collections.OrderedDict()

    def entry(key, cls, f, role):
        return seen.setdefault(key, {"class": cls, "family": f, "role": role, "planets": set(), "spawner": set(),
                                     "rounds": set(), "replaced_as_original": 0, "spawned_as_replacement": 0})

    for path in sorted(glob.glob(str(ROOT / "tests" / "data" / "round*_rivet.log"))):
        rnd = int(re.search(r"round(\d+)", path).group(1))
        planet, last = "?", None
        for line in open(path, encoding="utf-8", errors="replace"):
            m = re.search(r"PlanetChangedEvent\tNewPlanetName=(\w+)", line)
            if m:
                planet = m.group(1)
            m = re.search(r"spawn \d+: index \d+ location \S+ .*?spawned handle \d+ .*? asset [0-9A-F]+ (\S+?)\.actor classes (\S+)", line)
            if m:
                cls, f, role = classify(m.group(2), fam)
                last = None
                if cls:
                    e = entry(m.group(1), cls, f, role)
                    e["planets"].add(planet); e["rounds"].add(rnd); e["spawner"].add("node")
                    last = e
                continue
            if last is not None and re.search(r"spawn \d+: SpawnFactory handle", line):
                last["spawner"].discard("node"); last["spawner"].add("factory")
                continue
            m = re.search(r"learned template \d+ \(uid \w+\): (\S+) = (\w+)/(\w+), role (\w+)", line)
            if m:
                e = entry(m.group(1), m.group(3), m.group(2), m.group(4))
                e["planets"].add(planet); e["rounds"].add(rnd)
            m = re.search(r"VERIFY \S+ \S+(?: \S+)? \S+: requested (\S+), spawned (\S+): REPLACEMENT SPAWNED", line)
            if m:
                entry(m.group(2), None, None, None)["spawned_as_replacement"] += 1
            m = re.search(r"CHANGED factory Templates (\w+) .*: (\S+) -> (\S+)$", line)
            if m:
                pass
    return seen


if __name__ == "__main__":
    for k, e in census().items():
        print("%-34s %-28s %-10s %-10s %-34s %-14s rounds %s, replacement spawned %d" % (
            k, e["class"], e["family"], e["role"], ",".join(sorted(e["planets"])), ",".join(sorted(e["spawner"])) or "-",
            ",".join(str(r) for r in sorted(e["rounds"])), e["spawned_as_replacement"]))
