"""8.0 release validation: tens of thousands of seeds through the generator's own audit and the
independent verifiers written in Python from the documented rules (tests/test_generator.py verify,
tests/test_campaign.py verify_campaign / verify_fallback). Run from the project root:

    python tools/big_batch.py [--scale 1.0]

Every seed must pass ALL of:
  audit            the generator's own audit (02_rando_generator.lua G.audit)
  verify           items: one route per item, 25 Gold Bolts with grantable items, currency ranges and
                   budgets, prices, start rules, Coordinates never behind themselves, reachability
  verify_campaign  visit-by-visit replay (level-locked seeds in the game's own order, reordered
                   mission orders in their order): no visit ever waits for something unobtainable
  verify_fallback  the order that really runs until mission control is verified (the game's own)
  verify_hub       8.0 hub seeds: the two (or more) starting Coordinates, every planet's Coordinates
                   exactly once, and EVERY order a player could choose has something to do until
                   the finale (tests/test_hub.py, written independently of 03_rando_campaign.lua)
A refused seed counts only if the refusal is honest (fewer grantable items than Gold Bolts)."""
import argparse
import random
import sys
import time

sys.path.insert(0, 'tests'); sys.path.insert(0, 'tools')
import rando  # noqa: E402
from luajson import py  # noqa: E402
from test_generator import verify, honest_refusal  # noqa: E402
from test_campaign import verify_campaign, verify_fallback  # noqa: E402
from test_hub import verify_hub  # noqa: E402


def check(d):
    probs = list(verify(d))
    if d["settings"].get("hub"):
        if not d.get("hub"):
            probs.append("hub seed without a plan")
        else:
            probs += verify_hub(d["hub"], d["settings"])[0]
    if d["settings"]["travel_lock"] or d["settings"]["campaign_mode"] != "vanilla":
        probs += verify_campaign(d)
        probs += verify_fallback(d)
    return probs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.0)
    a = ap.parse_args(argv)
    n = lambda x: max(1, int(x * a.scale))  # noqa: E731
    eng = rando.Engine()
    d0 = eng.defaults()
    t = time.time()
    total = valid = refused = 0
    bad = []

    def run(label, seed, user, preset):
        nonlocal total, valid, refused
        total += 1
        s, audit = eng.generate(seed, user, preset)
        if s is None:
            if honest_refusal(eng, preset, user, audit, extra_start=3):
                refused += 1
            else:
                bad.append((label, seed, preset, user, audit))
            return
        if audit:
            bad.append((label, seed, preset, user, audit)); return
        p = check(py(s))
        if p:
            bad.append((label, seed, preset, user, p[:3])); return
        valid += 1

    hubs = ["hub", "hub_chaos"]
    for p in hubs:
        for i in range(n(3000)):
            run("hub", f"big8-{p}-{i}", {}, p)
    for name, user in (("hub-3-coords", {"hub_start_coordinates": 3}), ("hub-unlock-2", {"hub_unlocks": 2}),
                       ("hub-half", {"hub_finale": "half"}), ("hub-no-revisits", {"hub_revisits": False}),
                       ("hub-restored", {"restored_weapons": True}), ("hub-4-3", {"hub_start_coordinates": 4, "hub_unlocks": 3})):
        for i in range(n(500)):
            run(name, f"big8-{name}-{i}", user, "hub")
    print(f"8.0 hub: {valid}/{total} valid, bad {len(bad)} ({time.time() - t:.0f}s)", flush=True)
    presets7 = ["balanced", "chaos", "full", "campaign", "everything"]
    for p in presets7:
        for i in range(n(2000)):
            run("preset", f"big7-{p}-{i}", {}, p)
    print(f"7.0 presets: {valid}/{total} valid, bad {len(bad)} ({time.time() - t:.0f}s)", flush=True)
    for p in ["standard", "coordinates"]:
        for i in range(n(1000)):
            run("legacy", f"big7-{p}-{i}", {}, p)
    for name, user in (("restored", {"restored_weapons": True}), ("vanilla-shop", {"shop": "vanilla"}),
                       ("levels-restored", {"levels": True, "restored_weapons": True}),
                       ("start-items", {"start_items": "weapon:headhunter,glitch,armor:pirate_head", "levels": True})):
        for i in range(n(1000)):
            run(name, f"big7-{name}-{i}", user, "balanced")
    print(f"+ legacy presets and variants: {valid}/{total} valid, bad {len(bad)} ({time.time() - t:.0f}s)", flush=True)
    rnd = random.Random("big-random-7")
    for c in range(n(2000)):
        p = rnd.choice(presets7 + ["standard", "coordinates"] + hubs)
        u = rando.random_settings(rnd, d0)
        u["campaign_mode"], u["random_start"] = "vanilla", False
        for i in range(4):
            run("random", f"big7r-{c}-{i}", u, p)
    print(f"+ random settings: {valid}/{total} valid, {refused} honestly refused, bad {len(bad)} ({time.time() - t:.0f}s)", flush=True)
    for p in ["planet_shuffle", "mission_shuffle", "full_campaign", "campaign_chaos"]:
        for i in range(n(2000)):
            run("mission-order", f"big7c-{p}-{i}", {}, p)
        for i in range(n(500)):
            run("mission-order+levels", f"big7cl-{p}-{i}", {"levels": True}, p)
    print(f"+ experimental mission orders: {valid}/{total} valid, {refused} honestly refused, bad {len(bad)} ({time.time() - t:.0f}s)")
    print("TOTAL", total, "VALID", valid, "REFUSED (honest)", refused, "BAD", len(bad))
    for b in bad[:10]:
        print("  BAD", b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
