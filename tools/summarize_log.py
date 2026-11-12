"""Summarize a rivet.log from a randomizer session: versions, errors, deliveries, rewards.

    python tools/summarize_log.py path/to/rivet.log
"""
import re
import sys
from collections import OrderedDict


def summarize(lines):
    out = OrderedDict(kit=None, rivet=None, seed=None, helper=None, errors=[], subscribed=None,
                      sent=OrderedDict(), confirmed=[], silent=[], delivery_off=[], received=[],
                      bought=[], planets=[], test_mode=False, restored=None,
                      gold_bolts=[], new_games=[], vendor=[], finale=False, travel=[], prices=[], arsenal=None,
                      hub=[], hub_research=[], hub_done=[])
    for line in lines:
        line = line.rstrip("\n")
        if m := re.search(r"\[rivet\] version (\S+?)(\[|$)", line):
            out["rivet"] = m.group(1)
        if m := re.search(r"Randomizer (\d+\.\d+\.\d+) loaded", line):
            out["kit"] = m.group(1)
        if "RANDO-SEED\tready" in line or "RANDO-SEED ready" in line:
            parts = line.split("\t")
            out["seed"] = " ".join(parts[2:4])
        if "loaded seed" in line:
            parts = line.split("\t")
            out["seed"] = " ".join(p for p in parts[2:4])
            if m := re.search(r"kit (\S+)", line):
                out["kit"] = m.group(1)
        if "direct delivery: helper at" in line:
            out["helper"] = line.split("helper at", 1)[1].strip()
        if "events subscribed" in line:
            out["subscribed"] = line.split("events subscribed", 1)[1].strip()
        if "TEST MODE on" in line:
            out["test_mode"] = True
        if "RANDO-SAVE restored:" in line:
            out["restored"] = line.split("restored:", 1)[1].strip()
        if "RANDO-ERROR" in line or "[sim]" in line or re.search(r"\berror\b", line, re.I) and "[script]" in line and "RANDO-NOTIFY" not in line:
            out["errors"].append(line)
        f = line.split("\t")
        if "RANDO-REAL" in line and len(f) > 3:
            if f[2] == "sent":
                out["sent"].setdefault(f[3], 0)
                out["sent"][f[3]] += 1
            elif f[2] == "confirmed":
                out["confirmed"].append(f[3])
            elif "no reaction" in f[2] or "no answer" in f[2]:
                out["silent"].append(line.split("RANDO-REAL", 1)[1].strip())
            elif "direct delivery off" in f[2] or "direct delivery paused" in f[2]:
                out["delivery_off"].append(" ".join(f[2:]).strip())
        if len(f) >= 2 and f[0].endswith("[rando]") and f[1].startswith("received "):
            out["received"].append(f[1][9:])
        if len(f) >= 2 and f[0].endswith("[rando]") and f[1].startswith("bought "):
            out["bought"].append(f[1][7:])
        if "RANDO-PLANET" in line:
            out["planets"].append(" ".join(f[3:]).strip())
        # 4.0
        if "RANDO-BOLT" in line and "->" in line:
            out["gold_bolts"].append(" ".join(f[2:]).strip())
        if len(f) >= 2 and f[0].endswith("[rando]") and f[1].startswith("NEW GAME"):
            out["new_games"].append(f[1])
        if "RANDO-VENDOR" in line or "RANDO-SHOP" in line:
            out["vendor"].append(" ".join(f[1:]).strip())
        if "campaign complete" in line and "RANDO-NOTIFY" not in line:
            out["finale"] = True
        # 7.0
        if "RANDO-TRAVEL" in line and "loaded" not in line:
            out["travel"].append(" ".join(f[2:]).strip())
        if "RANDO-SHOP" in line and ("Price at" in line or "prices left" in line):
            out["prices"].append(" ".join(f[2:]).strip())
        if "RANDO-SEED ARSENAL_RESTORED" in line:
            out["arsenal"] = line.split("ARSENAL_RESTORED", 1)[1].strip()
        # 8.0 hub
        if "RANDO-HUB" in line and "loaded" not in line:
            text = " ".join(x for x in f[2:] if x).strip()
            (out["hub_research"] if text.startswith("research:") else out["hub"]).append(text)
        if len(f) >= 2 and f[0].endswith("[rando]") and f[1].startswith("HUB: "):
            out["hub_done"].append(f[1][5:])
    return out


def main(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        s = summarize(fh)
    print(f"rivet_hook {s['rivet']} | kit {s['kit'] or '< 1.4'} | seed {s['seed']} | test mode {'on' if s['test_mode'] else 'off'}")
    print(f"helper: {s['helper']} | events: {s['subscribed']}")
    print(f"restored: {s['restored']}")
    print(f"planets: {', '.join(dict.fromkeys(s['planets']))}")
    print(f"received {len(s['received'])}: {', '.join(s['received'])}")
    print(f"bought: {', '.join(s['bought'])}")
    print(f"sent: {dict(s['sent'])}")
    print(f"confirmed: {', '.join(s['confirmed'])}")
    unconfirmed = [k for k in s["sent"] if k not in s["confirmed"]]
    print(f"sent but never confirmed: {', '.join(unconfirmed) or '-'}")
    for x in s["silent"]:
        print("  silent:", x)
    for x in s["delivery_off"]:
        print("  DELIVERY OFF/PAUSED:", x)
    print(f"Gold Bolts: {len(s['gold_bolts'])}")
    for x in s["gold_bolts"]:
        print("  ", x)
    for x in s["new_games"]:
        print("  ", x)
    print(f"vendor: {s['vendor'][0] if s['vendor'] else '-'}")
    print(f"prices: {s['prices'][0] if s['prices'] else '-'}")
    print(f"ARSENAL_RESTORED (auto): {s['arsenal'] or '-'}")
    print(f"levels: {len(s['travel'])} line(s)")
    for x in s["travel"][:30]:
        print("  ", x)
    print(f"hub: {len(s['hub'])} line(s), {len(s['hub_done'])} milestone(s), {len(s['hub_research'])} research line(s)")
    for x in s["hub_done"]:
        print("   HUB", x)
    for x in s["hub"][:60]:
        print("  ", x)
    print(f"campaign complete: {'yes' if s['finale'] else 'no'}")
    print(f"errors: {len(s['errors'])}")
    for e in s["errors"][:20]:
        print("  ", e)


if __name__ == "__main__":
    main(sys.argv[1])
