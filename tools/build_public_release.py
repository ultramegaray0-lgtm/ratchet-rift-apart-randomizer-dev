"""Builds the public NexusMods package from the repo (deterministic: same inputs, same zip bytes).

    python tools/build_public_release.py [--out DIR]

Takes ONLY these from mod/RiftApartRandomizer: the 14 kit scripts, rivet.toml, rando_give.dll,
the companion's 4 player files and the DLL source. Docs come from release/. Everything else
(extras/, companion/research/, dev docs, test results) stays out on purpose.
"""
import argparse
import hashlib
import os
import shutil
import sys
import zipfile

VERSION = "0.54"
BUILD = "10.0.5"
NAME = f"Ratchet_Rift_Apart_Randomizer_v{VERSION}"
ZIP_NAME = f"Ratchet_Rift_Apart_Randomizer_Public_Release_v{VERSION}.zip"
DATE = (2026, 11, 13, 0, 0, 0)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "mod", "RiftApartRandomizer")
REL = os.path.join(ROOT, "release")

SCRIPTS = ["01_rando_data.lua", "02_rando_generator.lua", "03_rando_campaign.lua", "04_rando_settings.lua",
           "05_rando_bindings.lua", "06_rando_capabilities.lua", "09_rando_real.lua", "10_rando_runtime.lua",
           "11_rando_campaign.lua", "12_rando_shop.lua", "13_rando_armor.lua", "14_rando_travel.lua",
           "15_rando_hub.lua", "16_rando_testtravel.lua"]
COMPANION = ["Start-Companion.bat", "RandoCompanion.ps1", "Install-ArsenalRestored.bat", "Install-ArsenalRestored.ps1"]
DLL_SRC = ["rando_give.c", "rando_give_core.h", "kernel32.def", "ntdll.def", "build.sh"]
DOCS = ["README.md", "INSTALLATION.md", "TROUBLESHOOTING.md", "COMPATIBILITY.md", "CHANGELOG.md",
        "CREDITS_AND_LICENSES.md", "LICENSE.txt"]
DLL_SHA256 = "efb927232f67b7740aec473afa3866dd50636e1c29d0b2822717116a40092c12"


def plan():
    """(source path, path inside the package) for every file."""
    p = []
    for d in DOCS:
        p.append((os.path.join(REL, d), d))
    p.append((os.path.join(REL, "docs", "PLAYER_GUIDE.md"), "docs/PLAYER_GUIDE.md"))
    p.append((os.path.join(KIT, "rivet.toml"), "GAME_FOLDER/rivet.toml"))
    p.append((os.path.join(KIT, "rando_give.dll"), "GAME_FOLDER/rando_give.dll"))
    for s in SCRIPTS:
        p.append((os.path.join(KIT, "scripts", s), "GAME_FOLDER/scripts/" + s))
    for c in COMPANION:
        p.append((os.path.join(KIT, "companion", c), "GAME_FOLDER/rando_companion/" + c))
    for f in DLL_SRC:
        p.append((os.path.join(KIT, "rando_give_source", f), "source/rando_give/" + f))
    p.append((os.path.join(REL, "source_rando_give_README.md"), "source/rando_give/README.md"))
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
    # guards: the kit must be one consistent version, and the DLL the verified one
    have = sorted(f for f in os.listdir(os.path.join(KIT, "scripts")) if f.endswith(".lua"))
    if have != sorted(SCRIPTS):
        sys.exit(f"scripts folder differs from the kit list: {sorted(set(have) ^ set(SCRIPTS))}")
    for s in SCRIPTS:
        txt = open(os.path.join(KIT, "scripts", s), encoding="ascii").read()
        if f'= "{BUILD}"' not in txt:
            sys.exit(f"{s} is not tagged {BUILD}")
    if sha256(os.path.join(KIT, "rando_give.dll")) != DLL_SHA256:
        sys.exit("rando_give.dll is not the verified v6 binary")

    stage = os.path.join(a.out, NAME)
    if os.path.exists(stage):
        shutil.rmtree(stage)
    files = plan()
    for src, rel in files:
        dst = os.path.join(stage, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    with open(os.path.join(stage, "VERSION.txt"), "w", newline="\r\n") as f:
        f.write(f"Ratchet Rift Apart Randomizer - Public Release v{VERSION} (beta)\n"
                f"Randomizer build: {BUILD} (all 14 scripts are tagged {BUILD})\n"
                f"Game: Ratchet & Clank: Rift Apart, Steam v3.630.1.0\n"
                f"Needs: rivet_hook 2.0.1 (not included)\n"
                f"rando_give.dll: v6, SHA-256 {DLL_SHA256}\n")
    rels = sorted([r for _, r in files] + ["VERSION.txt"])
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
    print(f"{zpath}\n  {len(rels)} files, {os.path.getsize(zpath)} bytes, sha256 {sha256(zpath)}")


if __name__ == "__main__":
    main()
