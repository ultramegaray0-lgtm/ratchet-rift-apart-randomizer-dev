# Release tools (v0.5)

- `check_reqs.py <repo> <n> [key=value ...]`: independent check of the gameplay rules over 2n seeds
  (every Gold Bolt an item, Hoverboots/Map-O-Matic, randomized start, armor, one route per weapon,
  planet shuffle, early game). Uses the kit's 04_rando_settings.lua; `preset=` and settings can be overridden.
- `stress_gbf.py <repo> <n>`: 2n random-settings hub seeds with distribution = goldbolts_first.
- `validate_release.py <zip> <repo> <workdir>`: the 28 release checks (archive, checksums, contents,
  personal data, Windows details, simulated install on another drive, installed-copy tests, uninstall).

Run with the dev requirements (`pip install lupa`). They are not part of the player package.
