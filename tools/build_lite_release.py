"""Builds the LITE package for NexusMods from the repo (deterministic: same inputs, same zip bytes).

    python tools/build_lite_release.py [--out DIR]

v0.75 Lite: the try-it-first package. Lua scripts only - NO rando_give.dll, NO companion (no .bat / .ps1), no other
executable or binary. It takes the 12 required scripts and 15_rando_hub.lua (the trip back to Nefarious City) from
mod/RiftApartRandomizer/scripts, the settings file release_lite/04_rando_settings.lua (lite = true), the rivet.toml of
release_lite/ (no DLL loaded, no bridge) and the Lite docs. Everything that needs the DLL stays out: 16_rando_spawners +
enemy.lua (the Enemy Randomizer: the SceneManager), 17_rando_omega.lua (Omega and weapon XP: the SceneManager), and
never boss.lua, chaos.lua or a dev(name).lua file. The build stops if any of that would go in, a script carries another
version tag, the settings file is not the Lite one, rivet.toml would load a DLL, or a player-facing file mentions an
excluded randomizer.
"""
import argparse
import os
import pathlib
import re
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_public_release as P  # noqa: E402

VERSION = P.VERSION
BUILD = P.BUILD
NAME = f"Ratchet_Rift_Apart_Randomizer_v{VERSION}_Lite_NexusMods"
ZIP_NAME = NAME + ".zip"
DATE = P.DATE

ROOT = P.ROOT
KIT = P.KIT
LITE = os.path.join(ROOT, "release_lite")
REL = P.REL

SCRIPTS = P.REQUIRED + ["15_rando_hub.lua"]
NOT_IN_LITE = ["16_rando_spawners.lua", "enemy.lua", "17_rando_omega.lua"] + P.EXCLUDED
LITE_SETTINGS = os.path.join(LITE, "04_rando_settings.lua")
LITE_TOML = os.path.join(LITE, "rivet.toml")
DOCS = [("README.md", LITE), ("INSTALLATION.md", LITE), ("CREDITS_AND_LICENSES.md", REL), ("LICENSE.txt", REL)]
BINARY = re.compile(r"\.(dll|exe|bat|cmd|ps1|psm1|vbs|js|msi|scr|com)$", re.I)


def script_source(s):
    return LITE_SETTINGS if s == "04_rando_settings.lua" else os.path.join(KIT, "scripts", s)


def plan():
    p = [(os.path.join(d, n), n) for n, d in DOCS]
    p.append((LITE_TOML, "GAME_FOLDER/rivet.toml"))
    for s in SCRIPTS:
        p.append((script_source(s), "GAME_FOLDER/scripts/" + s))
    return p


def check():
    """every rule of the Lite package; returns a list of problems"""
    bad = []
    for s in SCRIPTS:
        src = script_source(s)
        if not os.path.exists(src):
            bad.append(f"{s} is missing")
            continue
        txt = pathlib.Path(src).read_text(encoding="ascii")
        if f'= "{BUILD}"' not in txt:
            bad.append(f"{s} is not tagged {BUILD}")
        if "DEVELOPER TOOL" in txt:
            bad.append(f"{s} says it is a developer tool")
    if [s for s in SCRIPTS if s in NOT_IN_LITE or P.DEV_FILE.match(s)]:
        bad.append("a script that needs the DLL, an excluded randomizer or a developer file would go in")
    st = pathlib.Path(LITE_SETTINGS).read_text(encoding="ascii")
    for want in ("lite = true", "bank_rewards = false", "shop_runtime = false", "armor = false", "omega_weapons = false",
                 "weapon_xp = false", "restored_weapons = false"):
        if want not in st:
            bad.append(f"the Lite settings file lacks {want!r}")
    if re.search(r'^\s*seed\s*=\s*"random"', st, re.M):
        bad.append("the Lite settings file must have a fixed seed (no companion)")
    toml = pathlib.Path(LITE_TOML).read_text(encoding="ascii")
    if "dll_path" in toml or re.search(r"^\s*\[renderdoc\][^\[]*enabled\s*=\s*true", toml, re.M | re.S):
        bad.append("the Lite rivet.toml would load a DLL")
    if re.search(r"^\s*\[bridge\][^\[]*enabled\s*=\s*true", toml, re.M | re.S):
        bad.append("the Lite rivet.toml opens the companion's bridge")
    for src, rel in plan():
        if BINARY.search(rel):
            bad.append(f"{rel} is a binary or a script that runs outside the game")
    facing = [os.path.join(d, n) for n, d in DOCS] + [LITE_SETTINGS, LITE_TOML]
    for f in facing:
        for i, line in enumerate(pathlib.Path(f).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if P.EXCLUDED_WORDS.search(line):
                bad.append(f"{os.path.basename(f)}:{i} mentions an excluded / developer feature: {line.strip()[:80]}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    a = ap.parse_args(argv)
    problems = check()
    if problems:
        sys.exit("Lite package refused:\n  " + "\n  ".join(problems))
    stage = os.path.join(a.out, NAME)
    if os.path.exists(stage):
        shutil.rmtree(stage)
    files = plan()
    for src, rel in files:
        dst = os.path.join(stage, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    with open(os.path.join(stage, "VERSION.txt"), "w", newline="\r\n") as f:
        f.write(f"Ratchet & Clank: Rift Apart Randomizer v{VERSION} LITE (beta, kit {BUILD})\n"
                f"Lua scripts only: no DLL, no companion\n"
                f"Game: Ratchet & Clank: Rift Apart, Steam v3.630.1.0\n"
                f"Needs: rivet_hook 2.0.1 (not included)\n")
    rels = sorted([r for _, r in files] + ["VERSION.txt"])
    if any(BINARY.search(r) or P.DEV_FILE.match(r.rsplit("/", 1)[-1]) for r in rels):
        sys.exit("a binary or developer file got into the Lite package")
    with open(os.path.join(stage, "SHA256SUMS.txt"), "w", newline="\n") as f:
        f.write(f"# SHA-256 of every file in {NAME} (paths relative to this folder)\n")
        f.write("# Check one on Windows:  certutil -hashfile <file> SHA256   (or PowerShell: Get-FileHash <file>)\n")
        for r in rels:
            f.write(f"{P.sha256(os.path.join(stage, *r.split('/')))}  {r}\n")
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
    print(f"{zpath}\n  {len(rels)} files ({len(SCRIPTS)} scripts), {os.path.getsize(zpath)} bytes, sha256 {P.sha256(zpath)}")


if __name__ == "__main__":
    main()
