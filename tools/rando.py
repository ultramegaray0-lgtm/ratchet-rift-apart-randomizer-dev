"""Randomizer 8.0 offline command line and spoiler generator (needs Python 3.9+ and `pip install lupa`).

It runs the same Lua generator the game runs (scripts/01_rando_data.lua, 02_rando_generator.lua, 03_rando_campaign.lua).

  python tools/rando.py generate --seed "my seed" [--preset balanced] [--set key=value ...] [--out DIR]
  python tools/rando.py random [--preset chaos]           # a random seed
  python tools/rando.py share "RA8|my seed|hub|..."      # generate from a share code
  python tools/rando.py presets                           # the presets and what each changes
  python tools/rando.py batch --count 1000 [--preset all] # mass validation
  python tools/rando.py settings                          # list every setting and its default

`generate` writes spoiler.txt, seed.json and settings.lua (paste into 04_rando_settings.lua).
"""
import argparse
import json
import os
import secrets
import sys
import time

from lupa import lua54

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.environ.get("RANDO_SCRIPTS", os.path.join(ROOT, "mod", "RiftApartRandomizer", "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from luajson import py  # noqa: E402

WORDS = ["lombax", "rivet", "clank", "kit", "zurkie", "nefarious", "ryno", "glitch", "rift", "bolt",
         "savali", "blizar", "torren", "ardolis", "viceron", "sargasso", "trudi", "speetle", "qwark", "pocket",
         "omni", "hover", "dimension", "phantom", "hurl", "warp", "gold", "raritanium", "spybot", "lorb"]


class Engine:
    def __init__(self, scripts=SCRIPTS):
        self.lua = lua54.LuaRuntime(unpack_returned_tuples=True)
        for f in ("01_rando_data.lua", "02_rando_generator.lua", "03_rando_campaign.lua", "07_rando_campaign_registry.lua"):
            path = os.path.join(scripts, f)
            if not os.path.exists(path) and f.startswith("07_"):
                continue                           # optional: written by build_campaign_registry.py
            with open(path, encoding="utf-8") as fh:
                self.lua.execute(fh.read())
        self.G = self.lua.globals().RANDO_GEN
        self._gen = self.lua.eval(
            "function(seed, user, preset) local s, err, errs = RANDO_GEN.generate(seed, user, preset);"
            " if not s then return nil, err end; return s, RANDO_GEN.audit(s) end")

    def table(self, d):
        return self.lua.table_from(d or {})

    def generate(self, seed, settings=None, preset="balanced"):
        s, audit = self._gen(seed, self.table(settings), preset)
        if s is None:
            return None, audit
        return s, list(py(audit) or [])

    def spoiler(self, seed_table):
        return self.G.spoiler(seed_table)

    def defaults(self):
        return py(self.G.DEFAULTS)

    def db(self):
        return py(self.lua.globals().RANDO_DATA)


def parse_sets(pairs, defaults):
    out = {}
    for kv in pairs or []:
        k, _, v = kv.partition("=")
        d = defaults.get(k)
        if isinstance(d, bool):
            out[k] = v.lower() in ("1", "true", "yes", "on")
        elif isinstance(d, int):
            out[k] = int(v)
        else:
            out[k] = v
    return out


def settings_lua(seed, preset, user):
    lines = ["-- paste into scripts/04_rando_settings.lua (replace the seed / preset / options there)",
             f'seed = "{seed}",', f'preset = "{preset}",']
    for k in sorted(user):
        v = user[k]
        lines.append(f"{k} = {json.dumps(v) if isinstance(v, str) else str(v).lower()},")
    return "\n".join(lines) + "\n"


def cmd_generate(args, eng, seed=None, preset=None, user=None):
    seed = seed or args.seed
    preset = preset or args.preset
    user = user if user is not None else parse_sets(args.set, eng.defaults())
    t = time.time()
    s, audit = eng.generate(seed, user, preset)
    if s is None:
        print("FAILED:", audit)
        return 1
    out = args.out or os.path.join("out", s.fingerprint)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "spoiler.txt"), "w", encoding="utf-8") as f:
        f.write(eng.spoiler(s))
    with open(os.path.join(out, "seed.json"), "w", encoding="utf-8") as f:
        json.dump(py(s), f, indent=1, sort_keys=True)
    with open(os.path.join(out, "settings.lua"), "w", encoding="utf-8") as f:
        f.write(settings_lua(seed, preset, user))
    with open(os.path.join(out, "00_rando_seed.lua"), "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Pre-generated Randomizer 8.0 seed (tools/rando.py). Put it in <game>\\scripts to play this\n"
                "-- exact seed; it replaces the seed in 04_rando_settings.lua. Delete it to go back.\n")
        f.write("RANDO_SEED = " + eng.G.serialize(s) + "\n")
    print(f"seed {seed!r} preset {preset} fingerprint {s.fingerprint} (attempt {s.attempt}, {time.time() - t:.3f}s)")
    print("share code:", s.share_code)
    print("audit:", "ok" if not audit else audit)
    print("written to", out)
    return 0 if not audit else 1


def cmd_batch(args, eng):
    presets = (["hub", "hub_chaos", "balanced", "chaos", "full", "campaign", "everything", "standard", "coordinates", "planet_shuffle",
                "mission_shuffle", "full_campaign", "campaign_chaos"]
               if args.preset == "all" else [args.preset])
    import random
    rnd = random.Random(args.salt)
    defaults = eng.defaults()
    combos = [(p, {}) for p in presets]
    if args.random_settings:
        for _ in range(args.random_settings):
            combos.append((rnd.choice(presets), random_settings(rnd, defaults)))
    total = ok = refused = 0
    fails = []
    t = time.time()
    per = max(1, args.count // len(combos))
    for preset, user in combos:
        for i in range(per):
            seed = f"batch-{args.salt}-{i}"
            s, audit = eng.generate(seed, user, preset)
            total += 1
            if s is None and str(audit).startswith("too few items for one per Gold Bolt"):
                refused += 1                       # an honest refusal: these settings cannot fill 25 Gold Bolts
            elif s is None or audit:
                fails.append((preset, user, seed, audit))
            else:
                ok += 1
    dt = time.time() - t
    print(f"{total} seeds over {len(combos)} setting combinations: {ok} valid, {refused} refused "
          f"(settings with too few items for 25 Gold Bolts), {len(fails)} failed ({dt:.1f}s)")
    for f in fails[:10]:
        print("  FAIL", f)
    return 0 if not fails else 1


def random_settings(rnd, defaults):
    choice = {"start_coordinates": ["start_only", "first_two", "random_extra"],
              "weapon_logic": ["none", "light", "standard"], "accessibility": ["full", "beatable"],
              "campaign_mode": ["vanilla", "planet_shuffle", "mission_shuffle", "full", "chaos"],
              "shop": ["shuffle", "vanilla"], "shop_prices": ["vanilla", "weapon", "percent", "random"],
              "hub_finale": ["all", "half"]}
    # some values outside the ranges on purpose: the generator must keep the default and say so
    ranges = {"start_weapons": (0, 6), "start_gadgets": (0, 3), "shop_price_percent": (0, 520),
              "shop_price_max_percent": (0, 520), "bolts_min": (50, 60000), "bolts_max": (50, 110000),
              "raritanium_min": (0, 3000), "raritanium_max": (0, 5200), "bolts_budget": (0, 600000),
              "raritanium_budget": (0, 20000), "bolts_percent": (0, 100), "start_bolts": (0, 120000),
              "start_raritanium": (0, 6000), "hub_start_coordinates": (1, 5), "hub_unlocks": (0, 4)}
    user = {}
    for k, d in defaults.items():
        if k in ("exclude", "start_items"):
            continue
        if isinstance(d, bool):
            # weapons off leaves too few items for 25 Gold Bolts: keep such settings rare
            user[k] = rnd.random() < (0.9 if k in ("weapons", "include_arsenal_restored", "gadgets", "armor", "bolts", "raritanium") else 0.5)
        elif k in choice:
            user[k] = rnd.choice(choice[k])
        elif k in ranges:
            user[k] = rnd.randint(*ranges[k])
    if rnd.random() < 0.3:
        user["exclude"] = rnd.choice(["weapon:ryno_8", "weapon:ryno_8,omniglove", "access:savali", "weapon:mr_zurkon"])
    if rnd.random() < 0.3:
        user["start_items"] = rnd.choice(["weapon:enforcer", "glitch,armor:pirate_head", "weapon:headhunter,box_breaker",
                                          "access:ardolis", "weapon:shatterbomb", "nonsense"])
    return user


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate"); g.add_argument("--seed", required=True); g.add_argument("--preset", default="balanced")
    g.add_argument("--set", action="append"); g.add_argument("--out")
    r = sub.add_parser("random"); r.add_argument("--preset", default="balanced"); r.add_argument("--set", action="append"); r.add_argument("--out")
    s = sub.add_parser("share"); s.add_argument("code"); s.add_argument("--out")
    b = sub.add_parser("batch"); b.add_argument("--count", type=int, default=1000); b.add_argument("--preset", default="all")
    b.add_argument("--random-settings", type=int, default=0); b.add_argument("--salt", default="v2")
    sub.add_parser("settings")
    sub.add_parser("presets")
    args = ap.parse_args(argv)
    eng = Engine()
    if args.cmd == "generate":
        return cmd_generate(args, eng)
    if args.cmd == "random":
        seed = "-".join(secrets.choice(WORDS) for _ in range(3)) + "-" + str(secrets.randbelow(1000))
        args.seed = seed
        return cmd_generate(args, eng)
    if args.cmd == "share":
        seed, preset, user = eng.G.parse_share_code(args.code)
        if seed is None:
            print(preset); return 1
        args.set = None; args.preset = preset
        return cmd_generate(args, eng, seed=seed, preset=preset, user=py(user) or {})
    if args.cmd == "batch":
        return cmd_batch(args, eng)
    if args.cmd == "presets":
        presets = py(eng.lua.globals().RANDO_GEN.PRESETS)
        names = py(eng.lua.globals().RANDO_GEN.PRESET_NAMES)
        for k in ("balanced", "chaos", "full", "campaign", "everything"):
            print(f"{k:12} {names[k]:22} {', '.join(f'{a}={b}' for a, b in sorted((presets[k] or {}).items())) or '(the defaults)'}")
        return 0
    if args.cmd == "settings":
        for k, v in sorted(eng.defaults().items()):
            print(f"{k} = {v!r}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
