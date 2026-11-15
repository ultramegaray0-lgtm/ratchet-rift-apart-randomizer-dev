"""Final release validation for the public package (Phase 6 / 8).

python3 -I validate_release.py <zip> <repo> <workroot-on-other-filesystem>
Prints one PASS/FAIL line per check and writes validation.json next to the zip.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile

ZIP, REPO, WORK = (os.path.abspath(p) for p in sys.argv[1:4])
KIT = os.path.join(REPO, "mod", "RiftApartRandomizer")
results = []


def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def tree(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root).replace(os.sep, "/")] = sha(p)
    return out


if os.path.exists(WORK):
    shutil.rmtree(WORK)
user_home = os.path.join(WORK, "Users", "Jane Q. Player (fresh)")
downloads = os.path.join(user_home, "Downloads", "Mods & Stuff")
os.makedirs(downloads)

# ---- 1. the archive itself
z = zipfile.ZipFile(ZIP)
names = z.namelist()
check("zip CRC test", z.testzip() is None)
top = {n.split("/")[0] for n in names}
check("single top-level folder", len(top) == 1, ", ".join(sorted(top)))
bad_chars = re.compile(r'[<>:"\\|?*\x00-\x1f]')
reserved = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}
probs = []
for n in names:
    if n.startswith("/") or re.match(r"^[A-Za-z]:", n) or ".." in n.split("/"):
        probs.append("unsafe path " + n)
    for part in [p for p in n.split("/") if p]:
        if bad_chars.search(part) or part.endswith((" ", ".")) or part.split(".")[0].lower() in reserved:
            probs.append("not a valid Windows name: " + n)
check("entry names valid and safe on Windows", not probs, "; ".join(probs[:5]))
steam = r"C:\Program Files (x86)\Steam\steamapps\common\Ratchet & Clank - Rift Apart" + "\\"
longest = max(len(steam + n.split("/", 2)[2].replace("/", "\\")) for n in names if n.startswith(next(iter(top)) + "/GAME_FOLDER/") and n.count("/") >= 2 and not n.endswith("/"))
check("installed paths fit MAX_PATH (260) in the default Steam folder", longest < 260, f"longest {longest} chars")
lower = {}
dup = [n for n in names if lower.setdefault(n.lower(), n) != n]
check("no names that differ only by case", not dup, ", ".join(dup))

# ---- 2. extract (Python) and with the system unzip into a second folder; both must agree
z.extractall(downloads)
pkg = os.path.join(downloads, next(iter(top)))
alt = os.path.join(WORK, "second extract (unzip)")
os.makedirs(alt)
r = subprocess.run(["unzip", "-q", ZIP, "-d", alt], capture_output=True, text=True)
check("extracts with unzip as well", r.returncode == 0, r.stderr.strip())
check("both extractions identical", tree(pkg) == tree(os.path.join(alt, next(iter(top)))))

# ---- 3. checksums
listed = {}
for line in open(os.path.join(pkg, "SHA256SUMS.txt"), encoding="utf-8"):
    if line.startswith("#") or not line.strip():
        continue
    h, p = line.rstrip("\n").split("  ", 1)
    listed[p] = h
actual = tree(pkg)
mism = [p for p, h in listed.items() if actual.get(p) != h]
unlisted = sorted(set(actual) - set(listed) - {"SHA256SUMS.txt"})
check("SHA256SUMS.txt matches every file", not mism, ", ".join(mism))
check("every file is in SHA256SUMS.txt", not unlisted, ", ".join(unlisted))

# ---- 4. contents: required present, nothing unwanted
required = ["README.md", "INSTALLATION.md", "TROUBLESHOOTING.md", "CREDITS_AND_LICENSES.md", "LICENSE.txt",
            "VERSION.txt", "SHA256SUMS.txt", "GAME_FOLDER/rivet.toml", "GAME_FOLDER/rando_give.dll",
            "GAME_FOLDER/rando_companion/Start-Companion.bat", "GAME_FOLDER/rando_companion/RandoCompanion.ps1"]
# every script of the kit except developer files (dev(name).lua)
kit_scripts = sorted(f for f in os.listdir(os.path.join(KIT, "scripts")) if f.endswith(".lua") and not re.match(r"dev\(.+\)\.lua$", f))
required += ["GAME_FOLDER/scripts/" + s for s in kit_scripts]
missing = [p for p in required if p not in actual]
check("all required files present", not missing, ", ".join(missing))
check("13 scripts", len([p for p in actual if p.startswith("GAME_FOLDER/scripts/")]) == 13)
check("exactly the files listed above, nothing more", sorted(actual) == sorted(required), ", ".join(sorted(set(actual) ^ set(required))))
unwanted = [p for p in actual if re.search(r"(^|/)(\.git|__pycache__|extras|research|source|tests?)(/|$)|\.(log|pyc|bak|tmp|sav|save|zip|exe|c|h|def|sh|py)$|_dev|dev\(|DEVELOPMENT_LOG|TEST_RESULTS|BATCH_|07_rando_testmode|08_rando_probe|06_rando_vtables|06_rando_item_ids|16_rando_testtravel|Install-Arsenal|randomizer_saves|spoiler", p, re.I)]
check("no development, debug, log, save or test files", not unwanted, ", ".join(unwanted))

# ---- 5. packaged files == the final build in the repo
pairs = {"GAME_FOLDER/rivet.toml": "rivet.toml", "GAME_FOLDER/rando_give.dll": "rando_give.dll"}
pairs.update({f"GAME_FOLDER/scripts/{s}": f"scripts/{s}" for s in kit_scripts})
pairs.update({f"GAME_FOLDER/rando_companion/{c}": f"companion/{c}" for c in ["Start-Companion.bat", "RandoCompanion.ps1"]})
diff = [p for p, k in pairs.items() if actual[p] != sha(os.path.join(KIT, k))]
check("packaged files byte-identical to the final build (repo)", not diff, ", ".join(diff))
tags = {s: re.search(r'RANDO_FILES\["[^"]+"\]\s*=\s*"([^"]+)"', open(os.path.join(pkg, "GAME_FOLDER", "scripts", s)).read()) for s in kit_scripts}
vers = {s: (m.group(1) if m else None) for s, m in tags.items()}
check("all 13 scripts carry the same kit tag", len(set(vers.values())) == 1 and None not in vers.values(), str(set(vers.values())))
check("rando_give.dll is the verified v6 binary", actual["GAME_FOLDER/rando_give.dll"] == "efb927232f67b7740aec473afa3866dd50636e1c29d0b2822717116a40092c12")

# ---- 6. no personal data or machine-specific paths
pat = re.compile(r"ultramega|@gmail|/home/|/mnt/|/root/|[A-Za-z]:\\Users\\(?!USER|USERNAME|<)|Users/[A-Za-z]|\bv2\.618\b|\bv3\.618\b|Rift\.Apart\.v|AppData\\Roaming|claude\.ai/", re.I)
hits = []
for p in actual:
    if p.endswith(".dll"):
        continue
    for i, line in enumerate(open(os.path.join(pkg, p), encoding="utf-8", errors="replace"), 1):
        if pat.search(line):
            hits.append(f"{p}:{i}: {line.strip()[:80]}")
check("no personal names, user folders, absolute dev paths or local folder names", not hits, " | ".join(hits[:6]))
dll = open(os.path.join(pkg, "GAME_FOLDER", "rando_give.dll"), "rb").read()
check("rando_give.dll holds no absolute build path or user name", not re.search(rb"(/home/|/root/|[A-Z]:\\\\|Users\\\\|ultramega)", dll))
fixed_paths = []
for p in [q for q in actual if q.startswith("GAME_FOLDER/") and not q.endswith(".dll")]:
    txt = open(os.path.join(pkg, p), encoding="utf-8").read()
    for m in re.finditer(r'["\'][A-Za-z]:[\\/][^"\']*["\']', txt):
        fixed_paths.append(f"{p}: {m.group(0)}")
check("no hard-coded drive-letter paths in anything that runs", not fixed_paths, "; ".join(fixed_paths[:5]))

# ---- 7. Windows text-file details
crlf_bat = all(b"\n" not in open(os.path.join(pkg, p), "rb").read().replace(b"\r\n", b"") for p in actual if p.endswith(".bat"))
check(".bat files use CRLF line endings", crlf_bat)
nonascii = [p for p in actual if p.endswith((".ps1", ".bat", ".lua", ".toml")) and any(c > 127 for c in open(os.path.join(pkg, p), "rb").read())]
check("scripts are pure ASCII (safe for Windows PowerShell 5.1 without a BOM)", not nonascii, ", ".join(nonascii))
bat = open(os.path.join(pkg, "GAME_FOLDER", "rando_companion", "Start-Companion.bat")).read()
check("Start-Companion.bat finds its script relative to itself, quoted", '"%~dp0RandoCompanion.ps1"' in bat)

# ---- 8. simulated clean install: a game folder on another filesystem, with spaces, & and ()
game = os.path.join(WORK, "Other Drive (E)", "SteamLibrary", "steamapps", "common", "Ratchet & Clank - Rift Apart")
os.makedirs(os.path.join(game, "mods"))
for f, data in {"RiftApart.exe": b"MZ fake game exe", "toc": b"fake toc", "hid.dll": b"rivet_hook proxy (stand-in)",
                "rivet_hook.dll": b"rivet_hook (stand-in)",
                "rivet.toml": b"[scripts]\nenabled = false\n"}.items():
    open(os.path.join(game, f), "wb").write(data)
before = tree(game)
backup_toml = os.path.join(user_home, "rivet.toml.mine")
shutil.copyfile(os.path.join(game, "rivet.toml"), backup_toml)
src = os.path.join(pkg, "GAME_FOLDER")
for d, _, fs in os.walk(src):
    for f in fs:
        rel = os.path.relpath(os.path.join(d, f), src)
        os.makedirs(os.path.dirname(os.path.join(game, rel)), exist_ok=True)
        shutil.copyfile(os.path.join(d, f), os.path.join(game, rel))
after = tree(game)
untouched = [p for p in before if p != "rivet.toml" and before[p] != after.get(p)]
check("install changes no game file (only adds files; rivet.toml replaced as documented)", not untouched, ", ".join(untouched))
cfg = tomllib.loads(open(os.path.join(game, "rivet.toml"), encoding="utf-8").read())
need = (cfg["scripts"]["enabled"] is True and cfg["scripts"]["path"] == "scripts" and cfg["overlay"]["enabled"] is True
        and cfg["bridge"]["enabled"] is True and cfg["renderdoc"]["enabled"] is True and cfg["renderdoc"]["dll_path"] == "rando_give.dll")
check("installed rivet.toml parses (TOML) and has every required setting", need)
check("rivet.toml's dll_path and scripts path are relative and resolve in the game folder",
      os.path.isfile(os.path.join(game, cfg["renderdoc"]["dll_path"])) and os.path.isdir(os.path.join(game, cfg["scripts"]["path"])))
check("rando_companion sits next to RiftApart.exe (where the companion looks for rivet.toml and mods)",
      os.path.isfile(os.path.join(os.path.dirname(os.path.join(game, "rando_companion", "x")), "..", "RiftApart.exe")))

# ---- 9. run the INSTALLED scripts: simulator suites + seed generation, fresh HOME, cwd elsewhere
# the release's scripts are the INSTALLED copy; tests that also load developer tooling (dev(name).lua,
# never shipped) take it from the repo
env = {"PATH": "/usr/bin:/bin", "HOME": user_home, "RANDO_MOD_DIR": game,
       "RANDO_SCRIPTS": os.path.join(game, "scripts"), "RANDO_DEV_SCRIPTS": os.path.join(KIT, "scripts"),
       "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
mods = ["tests.test_v055", "tests.test_v100", "tests.test_v054", "tests.test_v90", "tests.test_runtime", "tests.test_levels",
        "tests.test_generator", "tests.test_campaign", "tests.test_v85", "tests.test_registry"]
r = subprocess.run([sys.executable, "-m", "unittest", "-q"] + mods, cwd=REPO, env=env, capture_output=True, text=True, timeout=3000)
tail = r.stderr.strip().splitlines()
summary = " / ".join(l for l in tail[-3:] if l.strip())
failed_ids = re.findall(r"^(?:FAIL|ERROR): (\w+) \(tests\.(\w+)\.", r.stderr, re.M)
ran = re.search(r"Ran (\d+) tests", r.stderr)
check("simulator suites pass against the installed copy (" + ", ".join(m.split(".")[1] for m in mods) + ")",
      not failed_ids and ran is not None and r.returncode == 0,
      f"{ran.group(1) if ran else '?'} ran" + (f"; FAILURES: {failed_ids[:8]}" if failed_ids else ""))
open(os.path.join(WORK, "installed_suites.txt"), "w").write(r.stderr)
r2 = subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_reqs.py"), REPO, "500"], cwd=user_home, env=env,
                    capture_output=True, text=True, timeout=3000)
check("gameplay rules hold on 1,000 seeds generated from the installed scripts", r2.returncode == 0,
      " / ".join(r2.stdout.strip().splitlines()[:2]))
open(os.path.join(WORK, "installed_reqs.txt"), "w").write(r2.stdout + r2.stderr)

# ---- 10. simulate play artifacts, then the documented uninstall
os.makedirs(os.path.join(game, "rando_companion", "randomizer_saves", "spoilers"))
open(os.path.join(game, "rando_companion", "randomizer_saves", "rando_abc.lua"), "w").write("return {}")
open(os.path.join(game, "rivet.log"), "w").write("log")
for s in kit_scripts:
    os.remove(os.path.join(game, "scripts", s))
if not os.listdir(os.path.join(game, "scripts")):
    os.rmdir(os.path.join(game, "scripts"))
os.remove(os.path.join(game, "rando_give.dll"))
shutil.rmtree(os.path.join(game, "rando_companion"))
shutil.copyfile(backup_toml, os.path.join(game, "rivet.toml"))
os.remove(os.path.join(game, "rivet.log"))           # rivet_hook's own log (documented in step 4 of uninstall)
check("documented uninstall returns the game folder to exactly its pre-install state", tree(game) == before,
      str(sorted(set(tree(game)) ^ set(before))))

json.dump(results, open(os.path.join(os.path.dirname(ZIP), "validation.json"), "w"), indent=1)
failed = [x for x in results if not x["ok"]]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
