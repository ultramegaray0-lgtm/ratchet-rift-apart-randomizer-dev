#!/usr/bin/env python3
"""Reconcile an existing all-planet .stage with the newest runtime verdicts.

This is a surgical patcher: it does not invent new zone edits. It restores only manifest
entries whose latest observed result is NO SPAWN or ORIGINAL SPAWNED, retains WORKED and
NOT REACHED entries, and rebuilds the stage + Lua manifest. Every target byte is checked
against the expected replacement value before it is changed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import zipfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import stage_allgame as SA  # noqa: E402

FAILURES = {"NO SPAWN", "ORIGINAL SPAWNED"}
STAMP = (2026, 1, 1, 0, 0, 0)


def norm_zone(s):
    return str(s or "").replace("/", "\\").lower()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_member(zf, name, data):
    zi = zipfile.ZipInfo(name, date_time=STAMP)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    zf.writestr(zi, data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--runtime-script", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    m = json.load(open(a.manifest, encoding="utf-8"))
    vj = json.load(open(a.verdicts, encoding="utf-8"))
    verdicts = vj.get("verdicts", {})
    if not m.get("changes") or not m.get("zones"):
        raise SystemExit("ERROR: source manifest has no changes/zones")
    original_stage = open(a.stage, "rb").read()
    if sha(original_stage) != m.get("stage_sha256"):
        raise SystemExit("ERROR: source .stage SHA256 does not match its manifest")

    by_key = {}
    for key, v in verdicts.items():
        pair = (norm_zone(v.get("zone")), key.upper())
        by_key[pair] = v

    source_zip = zipfile.ZipFile(a.stage, "r")
    bad_member = source_zip.testzip()
    if bad_member:
        raise SystemExit("ERROR: source .stage has a corrupt member: " + bad_member)
    info = json.loads(source_zip.read("info.json").decode("utf-8"))
    stage_members = {name: source_zip.read(name) for name in source_zip.namelist()
                     if name != "info.json" and not name.endswith("/")}

    zones_by_id = {z["zone_id"]: z for z in m["zones"]}
    changes_by_zone = defaultdict(list)
    failure_count = Counter()
    verdict_count = Counter()
    for c in m["changes"]:
        pair = (norm_zone(c["zone"]), c["key"].upper())
        v = by_key.get(pair)
        if v is None:
            raise SystemExit("ERROR: no latest verdict for manifest spawner %s in %s" % pair)
        verdict = v.get("verdict")
        if verdict not in ("WORKED", "NOT REACHED", "NO SPAWN", "ORIGINAL SPAWNED"):
            raise SystemExit("ERROR: unknown verdict %r for %s" % (verdict, c["key"]))
        if verdict == "WORKED" and v.get("replacement_uid", "").upper() != c["replacement_uid"].upper():
            raise SystemExit("ERROR: WORKED replacement UID mismatch for %s: log=%s manifest=%s" %
                             (c["key"], v.get("replacement_uid"), c["replacement_uid"]))
        c["_runtime_verdict"] = verdict
        verdict_count[verdict] += 1
        if verdict in FAILURES:
            failure_count[verdict] += 1
        changes_by_zone[c["zone_id"]].append(c)

    if sum(verdict_count.values()) != len(m["changes"]):
        raise SystemExit("ERROR: verdict coverage does not match the manifest")

    # Validate and patch each stage member. All offsets are relative to the zone payload,
    # after its 36-byte TOC header.
    patched_members = {}
    retained_changes = []
    new_zone_records = []
    for zone_id, zrec in zones_by_id.items():
        member_name = "%d/%s" % (zrec["span"], zone_id)
        blob = stage_members.get(member_name)
        if blob is None:
            raise SystemExit("ERROR: missing stage member " + member_name)
        if len(blob) < SA.HEADER:
            raise SystemExit("ERROR: short stage member " + member_name)
        header, raw = blob[:SA.HEADER], bytearray(blob[SA.HEADER:])
        zone_changes = changes_by_zone.get(zone_id, [])
        for c in zone_changes:
            off = int(c["entry_abs"])
            if off < 0 or off + SA.VAR_SIZE > len(raw):
                raise SystemExit("ERROR: offset out of range for " + c["key"])
            current_index = int.from_bytes(raw[off + 4:off + 6], "little")
            current_uid = int.from_bytes(raw[off + 16:off + 24], "little")
            expected_index = int(c["replacement_index"])
            expected_uid = int(c["replacement_uid"], 16)
            if current_index != expected_index or current_uid != expected_uid:
                raise SystemExit("ERROR: source stage does not contain manifest replacement for %s" % c["key"])
            if c["_runtime_verdict"] in FAILURES:
                raw[off + 4:off + 6] = int(c["original_index"]).to_bytes(2, "little")
                raw[off + 16:off + 24] = int(c["original_uid"], 16).to_bytes(8, "little")
            else:
                retained_changes.append(c)

        # Re-parse the result and verify every retained change and every reverted change.
        raw_bytes = bytes(raw)
        z = SA.Zone(header, raw_bytes, zrec["zone"])
        for c in zone_changes:
            off = int(c["entry_abs"])
            idx = int.from_bytes(raw_bytes[off + 4:off + 6], "little")
            uid = int.from_bytes(raw_bytes[off + 16:off + 24], "little")
            if c["_runtime_verdict"] in FAILURES:
                if idx != int(c["original_index"]) or uid != int(c["original_uid"], 16):
                    raise SystemExit("ERROR: failed spawner was not restored: " + c["key"])
            else:
                if idx != int(c["replacement_index"]) or uid != int(c["replacement_uid"], 16):
                    raise SystemExit("ERROR: retained spawner changed unexpectedly: " + c["key"])

        for c in zone_changes:
            if c["_runtime_verdict"] in FAILURES:
                continue
            def refs(uid):
                return sum(1 for var in z.vars if var[0] == 5 and SA.hex16(var[5]) == uid)
            c["original_refs"] = refs(c["original_uid"]) + 1
            c["replacement_refs"] = refs(c["replacement_uid"]) - 1
            if c["_runtime_verdict"] == "WORKED":
                c["tier"] = "confirmed"
                c["pair_evidence"] = "RUNTIME WORKED 2026-11-26 01:53:24; " + c.get("pair_evidence", "")
            c.pop("_runtime_verdict", None)

        if any(c["zone_id"] == zone_id for c in retained_changes):
            patched_members[member_name] = header + raw_bytes
            zrec["sha256_patched"] = sha(raw_bytes)
            zrec["changes"] = sum(1 for c in retained_changes if c["zone_id"] == zone_id)
            new_zone_records.append(zrec)

    if len(retained_changes) != verdict_count["WORKED"] + verdict_count["NOT REACHED"]:
        raise SystemExit("ERROR: retained change count mismatch")
    if verdict_count["WORKED"] != 5 or verdict_count["NO SPAWN"] != 31 or verdict_count["NOT REACHED"] != 134:
        raise SystemExit("ERROR: latest evidence totals differ from expected 5/31/134; refusing stale patch")

    # The latest WORKED observations become exact-UID pins. Historical pins survive only
    # when the latest evidence did not observe a failure for that spawner.
    old_pins = {p["key"]: p for p in m.get("pins", [])}
    new_pins = []
    for c in retained_changes:
        pair = (norm_zone(c["zone"]), c["key"].upper())
        v = by_key[pair]
        if v["verdict"] == "WORKED":
            new_pins.append({"key": c["key"], "replacement": c["replacement_uid"],
                             "result": "WORKED in 2026-11-26 01:53:24 runtime verdict"})
        elif c["key"] in old_pins:
            new_pins.append(old_pins[c["key"]])
    m["pins"] = sorted(new_pins, key=lambda x: x["key"])
    m["changes"] = retained_changes
    m["zones"] = sorted(new_zone_records, key=lambda z: (z["span"], int(z["zone_id"], 16)))
    m["tool"] = "2.0.1"
    m["label"] = "V2.0.1 evidence-reconciled build: latest runtime failures restored; WORKED pinned; NOT REACHED retained"
    m.setdefault("settings", {})["evidence_file"] = os.path.basename(a.verdicts)
    m["settings"]["reconciled_from_stage_sha256"] = sha(original_stage)

    info["name"] = "Rift Apart Randomizer - Enemy .stage V2.0.1 Evidence Guided"
    info["description"] = ("Evidence-guided reconciliation of the 2026-11-26 runtime test: "
                           "5 WORKED retained, 31 failed changes restored to native, 134 NOT REACHED retained.")
    os.makedirs(a.out, exist_ok=True)
    stage_path = os.path.join(a.out, "RandoEnemies.stage")
    with zipfile.ZipFile(stage_path, "w", compression=zipfile.ZIP_DEFLATED) as outzip:
        write_member(outzip, "info.json", json.dumps(info, indent=2, sort_keys=True).encode("utf-8"))
        for name in sorted(patched_members, key=lambda n: (int(n.split("/", 1)[0]), int(n.split("/", 1)[1], 16))):
            write_member(outzip, name, patched_members[name])
    m["stage_sha256"] = sha(open(stage_path, "rb").read())
    with open(os.path.join(a.out, "stage_enemies_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=1)
    with open(os.path.join(a.out, "18_rando_stage_manifest.lua"), "w", encoding="utf-8") as fh:
        fh.write(SA.manifest_lua(m))
    with open(a.runtime_script, "rb") as src, open(os.path.join(a.out, SA.STAGE_LUA_FILE), "wb") as dst:
        dst.write(src.read())

    with open(os.path.join(a.out, "changes.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["planet", "zone", "spawner", "original", "replacement", "count", "tier", "pair evidence",
                    "spawn points", "replacement external", "replacement source planet", "replacement source zone"])
        for c in retained_changes:
            w.writerow([c["planet"], c["zone"], c["key"], c["original"], c["replacement"], c.get("count"), c["tier"],
                        c.get("pair_evidence"), c.get("spawn_points"), bool(c.get("replacement_external")),
                        c.get("replacement_source_planet") or "", c.get("replacement_source_zone") or ""])

    by_planet = defaultdict(Counter)
    for c in retained_changes:
        by_planet[c["planet"]]["changes"] += 1
        by_planet[c["planet"]][by_key[(norm_zone(c["zone"]), c["key"].upper())]["verdict"]] += 1
    lines = [
        "# V2.0.1 Evidence Reconciliation",
        "",
        "Source: uploaded all-planet build-20261125-223722 plus runtime verdicts 2026-11-26 01:53:24.",
        "",
        "| Result | Count |",
        "|---|---:|",
        "| WORKED (exact UID pinned) | %d |" % verdict_count["WORKED"],
        "| NO SPAWN (restored to original) | %d |" % verdict_count["NO SPAWN"],
        "| ORIGINAL SPAWNED (restored to original) | %d |" % verdict_count["ORIGINAL SPAWNED"],
        "| NOT REACHED (kept as unverified) | %d |" % verdict_count["NOT REACHED"],
        "| **Changes retained in V2.0.1** | **%d** |" % len(retained_changes),
        "",
        "The 31 failed entries are restored by rewriting only their original Script Vars index and UID. "
        "All other bytes in those zone members are preserved. This is a reconciliation of the uploaded build, "
        "not a fresh full-game rescan or an in-game validation of the 134 unvisited changes.",
        "",
        "## By planet",
        "",
        "| Planet | WORKED | NOT REACHED | Retained |",
        "|---|---:|---:|---:|",
    ]
    for planet, c in sorted(by_planet.items()):
        lines.append("| %s | %d | %d | %d |" %
                     (planet, c["WORKED"], c["NOT REACHED"], c["changes"]))
    lines += ["", "## Install", "",
              "Copy RandoEnemies.stage to mods/ and both 18_rando_stage_*.lua files to scripts/. "
              "Back up the currently installed files first. Keep the randomizer enabled while testing.",
              ""]
    with open(os.path.join(a.out, "V2.0.1_EVIDENCE_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    # Final archive and manifest consistency checks.
    with zipfile.ZipFile(stage_path, "r") as zf:
        if zf.testzip():
            raise SystemExit("ERROR: generated stage ZIP failed CRC validation")
        expected = {"%d/%s" % (z["span"], z["zone_id"]) for z in m["zones"]}
        actual = {n for n in zf.namelist() if n != "info.json" and not n.endswith("/")}
        if expected != actual:
            raise SystemExit("ERROR: generated stage member list differs from manifest")
    print("V2.0.1 reconciliation PASS")
    print("source changes: %d" % sum(verdict_count.values()))
    print("retained: %d (WORKED %d + NOT REACHED %d)" %
          (len(retained_changes), verdict_count["WORKED"], verdict_count["NOT REACHED"]))
    print("restored: %d (NO SPAWN %d + ORIGINAL SPAWNED %d)" %
          (failure_count["NO SPAWN"] + failure_count["ORIGINAL SPAWNED"],
           failure_count["NO SPAWN"], failure_count["ORIGINAL SPAWNED"]))
    print("stage: %s (%d bytes)" % (stage_path, os.path.getsize(stage_path)))
    print("sha256: %s" % m["stage_sha256"])
    print("zones: %d" % len(m["zones"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
