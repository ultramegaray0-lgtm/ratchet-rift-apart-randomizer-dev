"""Build mod/RiftApartRandomizer/dev_scripts/dev(debug).lua: every developer tool of the kit in one file (v0.62-DEV5).

    python tools/build_dev_debug.py          -> writes dev(debug).lua
    python tools/build_dev_debug.py --check  -> exit 1 if dev(debug).lua is not what the sources give

dev(debug).lua = tools/dev_debug_core.lua (its header, the section switches and the WARP / UNSTUCK section) followed by
every single dev(*).lua file, each inside DBG.section("<name>", function() ... end). The single files keep working on
their own; each starts with a guard that makes it stand down when dev(debug).lua has already run that section.
Their own RANDO_FILES stamps are left out (the kit check then names one developer file: dev(debug)).
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEV = ROOT / "mod" / "RiftApartRandomizer" / "dev_scripts"
CORE = ROOT / "tools" / "dev_debug_core.lua"
OUT = DEV / "dev(debug).lua"
# section -> its files, in the order the scripts folder would load them (name order)
SECTIONS = [
    ("keys", ["dev(keys).lua"]),
    ("testtravel", ["dev(testtravel).lua"]),
    ("testmode", ["dev(testmode).lua"]),
    ("omega_probe", ["dev(omega_inventory_probe).lua"]),
    ("probe", ["dev(item_ids).lua", "dev(probe).lua", "dev(vtables).lua"]),
    ("spawnprobe", ["dev(spawnprobe).lua"]),
    ("spawnproof", ["dev(spawnproof).lua"]),
]
STAMP = re.compile(r'^RANDO_FILES = RANDO_FILES or \{\}; RANDO_FILES\["dev\([^"]+\)"\] = "[^"]+".*$', re.M)


def build():
    parts = [CORE.read_text(encoding="utf-8").rstrip("\n") + "\n"]
    for name, files in SECTIONS:
        parts.append(f"\n-- ==== section: {name} ({', '.join(files)}) " + "=" * max(4, 100 - len(name) - sum(len(f) + 2 for f in files)) + "\n")
        parts.append(f'DBG.section("{name}", function()\n')
        for f in files:
            src = (DEV / f).read_text(encoding="utf-8")
            src = STAMP.sub(lambda m: "-- (" + f + "'s own kit stamp: dev(debug).lua carries one for all)", src)
            parts.append(f"-- ---- {f} ----\n")
            if len(files) > 1:
                parts.append("do\n" + src.rstrip("\n") + "\nend\n")
            else:
                parts.append(src.rstrip("\n") + "\n")
        parts.append("end)\n")
    parts.append('\nDBG.log("dev(debug).lua loaded - sections on:", (function() local t = {} for k, v in pairs(DBG.ran) do if v then t[#t + 1] = k end end table.sort(t) return table.concat(t, ", ") end)())\n')
    return "".join(parts)


def main():
    text = build()
    if "--check" in sys.argv:
        old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if old != text:
            print("dev(debug).lua is out of date: run python tools/build_dev_debug.py")
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({text.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
