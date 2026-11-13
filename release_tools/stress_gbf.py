"""10,000 random-settings hub seeds forced to goldbolts_first: audit + independent hub verifier + every Gold Bolt an item."""
import os, random, sys, collections
repo = os.path.abspath(sys.argv[1]); os.chdir(repo)
sys.path[:0] = [os.path.join(repo, "tests"), os.path.join(repo, "tools")]
import rando
from luajson import py
from test_v100 import verify_hub_seed
from test_v05 import gold_bolt_problems
eng = rando.Engine(); d0 = eng.defaults(); rnd = random.Random("v05-stress")
total = ok = refused = 0; bad = []; warn = collections.Counter()
for c in range(int(sys.argv[2])):
    u = rando.random_settings(rnd, d0); u["hub"] = True; u["distribution"] = "goldbolts_first"
    p = rnd.choice(["balanced", "chaos", "full", "campaign", "everything"])
    for i in range(2):
        total += 1
        s, audit = eng.generate(f"v05s-{c}-{i}", u, p)
        if s is None:
            if "too few items for one per Gold Bolt" in str(audit): refused += 1
            else: bad.append((c, i, p, str(audit)[:200]))
            continue
        d = py(s)
        pr = list(audit) + verify_hub_seed(d) + gold_bolt_problems(d)
        if pr: bad.append((c, i, p, pr[:3]))
        else: ok += 1
        for w in d.get("warnings") or []:
            if "lowered" in w or "turned on" in w: warn[w.split(":")[0].split(" from")[0]] += 1
print(f"random-settings goldbolts_first hub seeds: {ok}/{total} valid, {refused} honestly refused (too few items for 25 Gold Bolts), bad {len(bad)}")
print("relaxations used:", dict(warn))
for b in bad[:10]: print("  BAD", b)
sys.exit(1 if bad else 0)
