"""9.0 test helpers: an ordinary game (no hub) whose missions and checkpoints exist in the simulator.

Replaces the 8.0-8.5 hub helpers (hub_game / to_hub) for the tests that only used them to get a
running game with travel: the new game plays the prologue and the game's own travel takes the hero
to Nefarious City, as in 9.0."""
from harness import Game


def all_missions(g):
    names = set()
    for seg in g.g.RANDO_CAMPAIGN.SEGMENTS.values():
        for m in seg.missions.values():
            names.add(m)
    return sorted(names)


def level_game(seed="v90-level", settings=None, dll_version=6, missions=None, travel=True, **kw):
    """preset campaign (locked levels: the checkpoint catalog runs), simulated travel that lands"""
    st = {"seed": seed, "preset": "campaign"}
    st.update(settings or {})

    def before(game):
        game.sim.auto_travel = travel

    g = Game(settings=st, dll_version=dll_version, before_scripts=before, **kw)
    assert not g.load_errors, g.load_errors
    states = {n: 0 for n in all_missions(g)}
    states["MIS_INTRO"] = 2
    states.update(missions or {})
    g.sim.install_missions(g.lua.table_from([g.lua.table_from([n, s]) for n, s in states.items() if s is not None]))
    return g


def started(g, planet="NefCity"):
    """New Game, the parade, then the game's own travel (no planet menu) to `planet`"""
    g.companion_restore()
    g.sim.new_game()
    g.step(60)
    g.sim.parade_control()
    g.sim.parade_wrench()
    g.step(120)
    g.sim.set_mission("MIS_INTRO", 4)
    g.travel(planet)
    g.step(400)
    return g
