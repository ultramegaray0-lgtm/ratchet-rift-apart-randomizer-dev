# Randomizer 8.2: test travel, and the round 18 checkpoint catalog fix

8.2 is 8.1 plus two things. Your seed carries over: same generator (8.0.0), same fingerprint
(`kit-bolt-kit-198` → `4d170014c0c6` with ARSENAL_RESTORED), same saved progress. None of 8.2 has
run in your game yet.

## New: test travel (docs/TEST_TRAVEL.md)

F7 picks any planet, F8 its landing point, Ctrl+F7 warps there, Ctrl+F8 flies there with the
ship. While `test_travel = true`, nothing sends you back: not the hub, not locked levels, not
the planet menu. It opens no Coordinates. It's a runtime option, so the seed doesn't change.

## Fixed: the checkpoint catalog never finished (round 18)

| In the log | Cause | 8.2 |
|---|---|---|
| 11 × `14_rando_travel.lua:115 / 140 / 141 / 197: ran past the 8 ms frame budget`, and no `checkpoint catalog:` line | every checkpoint name was compared with every planet's every code; every sort comparison scored both names again; 128 names a frame, sharing the 8 ms with the shop and armor | codes are a table lookup per name token; areas and scores are worked out once per name; a slice stops after 1.5 ms; the best landing point is a linear pick, not a sort |

A test checks that every checkpoint name in your logs (rounds 13-18) gets the same planet as in
8.1. Another fills the catalog with 2,100 extra names and checks that it completes.

## Seen in round 18, not changed in 8.2

- **Shop:** `only 0 vendor weapon(s) in the array at +0x48`. ARSENAL_RESTORED's .stage replaces
  `configs\vendor\ven_weapon_vendor.config` (round 18 line 260), so the vendor's list isn't where
  the shop script looks. After 5 tries the shop gave you the seed's extra shop weapons directly,
  as designed.
- **Armor:** `13_rando_armor.lua:117` and `:256` ran past the frame budget, once each.
- **Pixelizer** was sent 4 times with no answer from the game.
- **This save has the whole story done** (every destination mission reads `complete`). On this
  save, hub destinations finish as soon as you arrive. Test travel is the way to try the travel
  here.

## Files

- `scripts/16_rando_testtravel.lua` (new)
- `scripts/14_rando_travel.lua` (catalog; no send-back during test travel)
- `scripts/15_rando_hub.lua` (`H.check_levels`; no send-back, keeper or startup guard during test travel)
- `scripts/10_rando_runtime.lua` (settings `test_travel`, `key_test_travel`, `key_test_point`; F9 status; KIT 8.2.0)
- `scripts/04_rando_settings.lua` (test travel on, keys F7 / F8)
- `tests/test_v82.py` (15 tests), `tests/data/round18_rivet.log`
