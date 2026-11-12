"""Writes scripts/06_rando_capabilities.lua from the lab's rivet.log (Randomizer 3.2).

    python tools/build_capabilities.py rivet.log [--out mod/RiftApartRandomizer/scripts/06_rando_capabilities.lua]

Only VERIFIED lines count - the game's mission state visibly changed (11_rando_campaign.lua):
  RANDO-LAB VERIFIED read (41 missions answered, system 2)
  RANDO-LAB VERIFIED native start (mission X went 1 -> 2)
  RANDO-LAB VERIFIED native complete (mission MIS_INTRO went 3 -> 4)
  RANDO-LAB VERIFIED travel CHK_... (fly)
mission_control needs start verified (your game's mission system has no make-available). new_game_init needs complete verified
on MIS_INTRO (lab Ctrl+F11 during a new game's intro) as well as mission_control. Nothing is
ever inferred from a missing line.
"""
import argparse
import datetime
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "mod", "RiftApartRandomizer", "scripts", "06_rando_capabilities.lua")
NATIVE = re.compile(r"RANDO-LAB VERIFIED native (make_available|start|complete|replay) \(mission (\S+) went (\S+) -> (\S+)\)")
TRAVEL = re.compile(r"RANDO-LAB VERIFIED travel (\S+)(?: \((fly|warp)\))?")
READ = re.compile(r"RANDO-LAB VERIFIED read \((.*)\)")


def parse(lines):
    kinds, evidence, travel, reads = set(), [], [], []
    intro = False
    for line in lines:
        m = NATIVE.search(line)
        if m:
            kind, mission, a, b = m.groups()
            kinds.add(kind)
            evidence.append(f"{kind}: {mission} {a} -> {b}")
            if kind == "complete" and mission == "MIS_INTRO":
                intro = True
        t = TRAVEL.search(line)
        if t:
            travel.append(f"{t.group(1)} ({t.group(2) or 'fly'})")
        r = READ.search(line)
        if r:
            reads.append(r.group(1))
    return kinds, evidence, travel, reads, intro


def render(kinds, evidence, travel, reads, source, intro=False):
    mc = "start" in kinds
    out = ["-- Randomizer 3.2 capabilities, written by tools/build_capabilities.py from a lab rivet.log.",
           f"-- source: {source}"]
    for r in reads:
        out.append(f"--   evidence: mission table read matches the game ({r})")
    for e in evidence:
        out.append(f"--   evidence: {e}")
    for t in travel:
        out.append(f"--   evidence: travel reached {t}")
    out.append("RANDO_CAPABILITIES = {")
    out.append(f'  source = "{source}",')
    out.append(f"  mission_read = {{ verified = {'true' if reads else 'false'} }},")
    out.append(f"  mission_control = {{ verified = {'true' if mc else 'false'}, backend = \"native\" }},")
    out.append(f"  travel = {{ verified = {'true' if travel else 'false'} }},")
    ngi = intro and mc
    out.append(f"  new_game_init = {{ verified = {'true' if ngi else 'false'} }},")
    out.append("}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    with open(a.log, encoding="utf-8", errors="replace") as f:
        kinds, evidence, travel, reads, intro = parse(f)
    source = f"{os.path.basename(a.log)} ({datetime.date.today().isoformat()})"
    text = render(kinds, evidence, travel, reads, source, intro)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
