"""Builds the public NexusMods package from the repo (deterministic: same inputs, same zip bytes).

    python tools/build_public_release.py [--out DIR]

Takes ONLY these from mod/RiftApartRandomizer: every script in scripts/ EXCEPT developer files
(dev(name).lua), rivet.toml, rando_give.dll and the companion's 2 player files. Player docs come
from release/. Developer files, companion/research/, source code, dev docs and test results never
go in (the DLL's source is published in the GitHub repository instead). The build stops if a required script is missing, a script carries another version
tag, or the DLL is not the verified binary.
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import zipfile

VERSION = "0.55"
BUILD = "10.0.15"                # dev 10.20: the kit in this repo (VERSION is set when a public release is made)
NAME = f"Ratchet_Rift_Apart_Randomizer_v{VERSION}_Player_Release"
ZIP_NAME = NAME + ".zip"
DATE = (2026, 11, 15, 0, 0, 0)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "mod", "RiftApartRandomizer")
REL = os.path.join(ROOT, "release")

DEV_FILE = re.compile(r"^dev\(.+\)\.lua$")
REQUIRED = ["01_rando_data.lua", "02_rando_generator.lua", "03_rando_campaign.lua", "04_rando_settings.lua",
            "05_rando_bindings.lua", "06_rando_capabilities.lua", "09_rando_real.lua", "10_rando_runtime.lua",
            "11_rando_campaign.lua", "12_rando_shop.lua", "13_rando_armor.lua", "14_rando_travel.lua"]
OPTIONAL = ["15_rando_hub.lua",          # shipped; players may delete it (no planet shuffle then)
            "16_rando_spawners.lua", "enemy.lua", "boss.lua"]   # dev 10.12: Enemy / Boss Randomizer, off by default
# dev 10.13: in the kit for development, NEVER in a player package until it has been played (no guards by design)
# dev 10.15: 17_rando_omega.lua writes one byte of the game's weapon state (the Omega flag) at an offset it learns
# in the game; held back until that has been seen working in your game (docs/OMEGA.md)
HELD_BACK = ["chaos.lua", "17_rando_omega.lua"]
COMPANION = ["Start-Companion.bat", "RandoCompanion.ps1"]
DOCS = ["README.md", "INSTALLATION.md", "TROUBLESHOOTING.md", "CREDITS_AND_LICENSES.md", "LICENSE.txt"]
DLL_SHA256 = "efb927232f67b7740aec473afa3866dd50636e1c29d0b2822717116a40092c12"


def release_scripts():
    """every .lua in scripts/ that is not a developer file, in name order"""
    names = sorted(f for f in os.listdir(os.path.join(KIT, "scripts")) if f.endswith(".lua"))
    return [n for n in names if not DEV_FILE.match(n) and n not in HELD_BACK]


def plan(scripts):
    """(source path, path inside the package) for every file."""
    p = [(os.path.join(REL, d), d) for d in DOCS]
    p.append((os.path.join(KIT, "rivet.toml"), "GAME_FOLDER/rivet.toml"))
    p.append((os.path.join(KIT, "rando_give.dll"), "GAME_FOLDER/rando_give.dll"))
    for s in scripts:
        p.append((os.path.join(KIT, "scripts", s), "GAME_FOLDER/scripts/" + s))
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
    for s in scripts:
        txt = open(os.path.join(KIT, "scripts", s), encoding="ascii").read()
        if f'= "{BUILD}"' not in txt:
            sys.exit(f"{s} is not tagged {BUILD}")
        if "DEVELOPER TOOL" in txt:
            sys.exit(f"{s} says it is a developer tool but is not named dev(name).lua")
    if sha256(os.path.join(KIT, "rando_give.dll")) != DLL_SHA256:
        sys.exit("rando_give.dll is not the verified v6 binary")

    stage = os.path.join(a.out, NAME)
    if os.path.exists(stage):
        shutil.rmtree(stage)
    files = plan(scripts)
    for src, rel in files:
        dst = os.path.join(stage, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    with open(os.path.join(stage, "VERSION.txt"), "w", newline="\r\n") as f:
        f.write(f"Ratchet & Clank: Rift Apart Randomizer v{VERSION}\n"
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
