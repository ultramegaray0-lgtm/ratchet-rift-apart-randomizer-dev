"""Turns a research zip (companion/research/Research-Campaign.bat) into the mission registry
override scripts/07_rando_campaign_registry.lua (Randomizer 3.2).

Names the game answered "not a mission" for are dropped, names it answered for are kept.

    python tools/build_campaign_registry.py campaign_research_<date>.zip

Every MIS_* name the research found (missions the game reported, story overlay regions, mission
configs, script-node variables) is matched to the campaign visits by prefix. A visit's mission
list is replaced only by names actually found, in the order the game reported them; visits with
no match keep their current entry and stay marked as unverified.
"""
import io
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luajson import py  # noqa: E402
from lupa import lua54  # noqa: E402

OUT = os.path.join(ROOT, "mod", "RiftApartRandomizer", "scripts", "07_rando_campaign_registry.lua")
# visit -> name prefixes (from the dag codenames of the 1.x research and your logs)
PREFIXES = {
    "corson_intro": ["MIS_INTRO"], "nefcity_1": ["MIS_NEFCITY_01"], "sargasso_1": ["MIS_SARG_01"],
    "scarstu_1": ["MIS_ZURK_01"], "savali_1": ["MIS_SAV_01", "MIS_SVLI_01"], "blizar_1": ["MIS_BLIZAR_01", "MIS_BLIZAR"],
    "torren_1": ["MIS_MOL_01"], "cordelion_1": ["MIS_CORD_01", "MIS_CORD_BOSS"], "scarstu_2": ["MIS_ZURK_02"],
    "ardolis_1": ["MIS_ARD_01", "MIS_ARD"], "sargasso_2": ["MIS_SARG_02"], "savali_2": ["MIS_SAV_02", "MIS_SVLI_02"],
    "viceron_1": ["MIS_ZORD_01", "MIS_ZORD"], "finale": ["MIS_MEGA"],
}
NOT_STORY = ("_DEFAULT", "RYNO_PLANS", "ARENA_CHALLENGE", "MIS_HAX", "MIS_POCKET", "MIS_CLANK_DEFAULT", "POST_MISSION")


def collect(zip_path):
    z = zipfile.ZipFile(zip_path)
    names, order = set(), {}
    text_all = []
    for n in z.namelist():
        if n.endswith((".json", ".lua", ".log")):
            text_all.append(z.read(n).decode("utf-8", "replace"))
    blob = "\n".join(text_all)
    for m in re.finditer(r"\bMIS_[A-Z0-9_]+", blob.upper()):
        names.add(m.group(0))
    missing = set()
    if "randomizer_research.lua" in z.namelist():
        L = lua54.LuaRuntime()
        data = py(L.execute(z.read("randomizer_research.lua").decode("utf-8")))
        for name, m in (data.get("missions") or {}).items():
            order[name.upper()] = m.get("first_frame", 0)
            names.add(name.upper())
        # 3.2: what the game answered when asked (lab Ctrl+F12): which names are missions
        for name, m in (data.get("known") or {}).items():
            if not isinstance(m, dict):
                continue
            if m.get("missing"):
                missing.add(name.upper())
            elif m.get("state") is not None:
                names.add(name.upper())
                order.setdefault(name.upper(), 10**8)
    names = {n for n in names if not any(b in n for b in NOT_STORY) and n not in missing}
    return names, order


def match(names, order):
    out = {}
    taken = set()
    # longest prefixes first, so MIS_ZURK_02 is not swallowed by MIS_ZURK
    pairs = sorted(((p, seg) for seg, ps in PREFIXES.items() for p in ps), key=lambda x: -len(x[0]))
    for p, seg in pairs:
        hits = sorted((n for n in names if n.startswith(p) and n not in taken), key=lambda n: (order.get(n, 10**9), n))
        if hits and seg not in out:
            out[seg] = hits
            taken.update(hits)
    return out


def render(matched, source):
    lines = ["-- Randomizer 3.0 mission registry from your game (tools/build_campaign_registry.py).",
             f"-- source: {source}. Visits not listed keep the built-in entry (unverified).",
             "if RANDO_CAMPAIGN then",
             "  local found = {"]
    for seg in sorted(matched):
        lines.append(f'    {seg} = {{ {", ".join(json.dumps(n) for n in matched[seg])} }},')
    lines += ["  }",
              "  for id, missions in pairs(found) do",
              "    local seg = RANDO_CAMPAIGN.BY_ID[id]",
              "    if seg then seg.missions = missions; seg.src = \"game (research)\" end",
              "  end",
              "end", ""]
    return "\n".join(lines)


def main(argv=None):
    args = argv or sys.argv[1:]
    if not args:
        print(__doc__); return 2
    names, order = collect(args[0])
    matched = match(names, order)
    text = render(matched, os.path.basename(args[0]))
    out = args[1] if len(args) > 1 else OUT
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"{len(names)} story mission names found; {len(matched)} of {len(PREFIXES)} visits matched")
    for seg in PREFIXES:
        print(f"  {seg:13} {', '.join(matched.get(seg, ['(not found - stays unverified)']))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
