"""Builds the public player package from the repo (deterministic: same inputs, same zip bytes).

    python tools/build_public_release.py [--out DIR]

v0.60: Takes ONLY these from mod/RiftApartRandomizer: the 12 required scripts, the player's optional ones
(15_rando_hub, 16_rando_spawners + enemy.lua = the Enemy Randomizer, 17_rando_omega = Omega weapons), rivet.toml,
rando_give.dll (v7) and the companion's player files (Start-Companion, Install-ArsenalRestored). The settings file
is release/04_rando_settings.lua (the player's defaults), never the kit's developer one. Player docs come from
release/. NEVER in a package: boss.lua and chaos.lua (the Boss and Chaos Randomizers stay in this private repo),
dev(name).lua developer files, companion/research/, source code, dev docs and test results. The build stops if a
required script is missing, an unknown or excluded script would go in, a script carries another version tag, a
player-facing file mentions an excluded randomizer, or the DLL is not the verified binary.
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import zipfile

VERSION = "0.60"
BUILD = "10.0.25"                # the kit in this repo (VERSION is set when a public release is made)
NAME = f"Ratchet_Rift_Apart_Randomizer_v{VERSION}_Player_Release"
ZIP_NAME = NAME + ".zip"
DATE = (2026, 11, 19, 0, 0, 0)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "mod", "RiftApartRandomizer")
REL = os.path.join(ROOT, "release")

DEV_FILE = re.compile(r"^dev\(.+\)\.lua$")
REQUIRED = ["01_rando_data.lua", "02_rando_generator.lua", "03_rando_campaign.lua", "04_rando_settings.lua",
            "05_rando_bindings.lua", "06_rando_capabilities.lua", "09_rando_real.lua", "10_rando_runtime.lua",
            "11_rando_campaign.lua", "12_rando_shop.lua", "13_rando_armor.lua", "14_rando_travel.lua"]
OPTIONAL = ["15_rando_hub.lua",          # planet shuffle and the trip back to the hub; players may delete it
            "16_rando_spawners.lua", "enemy.lua",   # the Enemy Randomizer (v0.60)
            "17_rando_omega.lua"]        # Omega weapons (v0.60; omega_weapons = false by default, see KNOWN_ISSUES)
# PRIVATE DEV ONLY - never in a player package (v0.60 release rules): the Boss Randomizer and the Chaos Randomizer
EXCLUDED = ["boss.lua", "chaos.lua"]
PUBLIC_SETTINGS = os.path.join(REL, "04_rando_settings.lua")
COMPANION = ["Start-Companion.bat", "RandoCompanion.ps1", "Install-ArsenalRestored.bat", "Install-ArsenalRestored.ps1"]
DOCS = ["README.md", "INSTALLATION.md", "TROUBLESHOOTING.md", "KNOWN_ISSUES.md", "CREDITS_AND_LICENSES.md", "LICENSE.txt"]
# rando_give.dll v7: the Enemy Randomizer needs it (the SceneManager); it ran in your game from round32 on and is
# rebuilt byte-identical from rando_give_source/ with clang/lld 18.1.3
DLL_SHA256 = "8055703e7dd7f48e16aa5a081d6795c15d515a52802bd0d70aafe88b54640744"
RELEASE_DLL = os.path.join(KIT, "rando_give.dll")
# words no player-facing file (settings, docs, companion, launchers) may contain
# (the "chaos" PRESET - 1 starting weapon, wide prices - is a v0.55 player option, not the Chaos Randomizer)
EXCLUDED_WORDS = re.compile(r"boss[ _]?randomizer|chaos[ _]?randomizer|chaos_|chaos\.lua|key_bosses|key_chaos|BACKSPACE|"
                            r"boss\.lua|DEV DEFAULT|dev kit", re.I)


def release_scripts():
    """every .lua in scripts/ that is not a developer file, in name order"""
    names = sorted(f for f in os.listdir(os.path.join(KIT, "scripts")) if f.endswith(".lua"))
    return [n for n in names if not DEV_FILE.match(n) and n not in EXCLUDED]


def script_source(s):
    """the player's settings file comes from release/, every other script from the kit"""
    return PUBLIC_SETTINGS if s == "04_rando_settings.lua" else os.path.join(KIT, "scripts", s)


def plan(scripts):
    """(source path, path inside the package) for every file."""
    p = [(os.path.join(REL, d), d) for d in DOCS]
    p.append((os.path.join(KIT, "rivet.toml"), "GAME_FOLDER/rivet.toml"))
    p.append((RELEASE_DLL, "GAME_FOLDER/rando_give.dll"))
    for s in scripts:
        p.append((script_source(s), "GAME_FOLDER/scripts/" + s))
    for c in COMPANION:
        p.append((os.path.join(KIT, "companion", c), "GAME_FOLDER/rando_companion/" + c))
    return p


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    a = ap.parse_args(argv)
    scripts = release_scripts()
    missing = [s for s in REQUIRED if s not in scripts]
    if missing:
        sys.exit(f"required scripts missing: {missing}")
    unknown = [s for s in scripts if s not in REQUIRED + OPTIONAL]
    if unknown:
        sys.exit(f"scripts that are neither required, optional nor dev(name).lua: {unknown}")
    if [s for s in scripts if s in EXCLUDED]:
        sys.exit("an excluded randomizer would go into the package")
    for s in scripts:
        txt = open(script_source(s), encoding="ascii").read()
        if f'= "{BUILD}"' not in txt:
            sys.exit(f"{s} is not tagged {BUILD}")
        if "DEVELOPER TOOL" in txt:
            sys.exit(f"{s} says it is a developer tool but is not named dev(name).lua")
    if sha256(RELEASE_DLL) != DLL_SHA256:
        sys.exit("rando_give.dll is not the verified v7 binary")
    facing = [os.path.join(REL, d) for d in DOCS] + [PUBLIC_SETTINGS] + [os.path.join(KIT, "companion", c) for c in COMPANION]
    for f in facing:
        for i, line in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
            if EXCLUDED_WORDS.search(line):
                sys.exit(f"{os.path.basename(f)}:{i} mentions an excluded / developer feature: {line.strip()[:80]}")

    stage = os.path.join(a.out, NAME)
    if os.path.exists(stage):
        shutil.rmtree(stage)
    files = plan(scripts)
    for src, rel in files:
        dst = os.path.join(stage, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    with open(os.path.join(stage, "VERSION.txt"), "w", newline="\r\n") as f:
        f.write(f"Ratchet & Clank: Rift Apart Randomizer v{VERSION} (beta, kit {BUILD})\n"
                f"Game: Ratchet & Clank: Rift Apart, Steam v3.630.1.0\n"
                f"Needs: rivet_hook 2.0.1 (not included)\n")
    rels = sorted([r for _, r in files] + ["VERSION.txt"])
    if any(DEV_FILE.match(r.rsplit("/", 1)[-1]) for r in rels):
        sys.exit("a developer file got into the package")
    with open(os.path.join(stage, "SHA256SUMS.txt"), "w", newline="\n") as f:
        f.write(f"# SHA-256 of every file in {NAME} (paths relative to this folder)\n")
        f.write("# Check one on Windows:  certutil -hashfile <file> SHA256   (or PowerShell: Get-FileHash <file>)\n")
        for r in rels:
            f.write(f"{sha256(os.path.join(stage, *r.split('/')))}  {r}\n")
    rels.append("SHA256SUMS.txt")

    zpath = os.path.join(a.out, ZIP_NAME)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        dirs = sorted({"/".join(r.split("/")[:i]) for r in rels for i in range(1, r.count("/") + 1)})
        for d in [""] + dirs:
            zi = zipfile.ZipInfo(NAME + "/" + (d + "/" if d else ""), DATE)
            zi.external_attr = (0o40755 << 16) | 0x10
            z.writestr(zi, b"")
        for r in sorted(rels):
            zi = zipfile.ZipInfo(NAME + "/" + r, DATE)
            zi.external_attr = 0o100644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            with open(os.path.join(stage, *r.split("/")), "rb") as fh:
                z.writestr(zi, fh.read(), compresslevel=9)
    print(f"{zpath}\n  {len(rels)} files ({len(scripts)} scripts), {os.path.getsize(zpath)} bytes, sha256 {sha256(zpath)}")


if __name__ == "__main__":
    main()
