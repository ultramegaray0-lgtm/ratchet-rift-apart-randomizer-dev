#!/usr/bin/env python3
"""stage_allgame.py 2.2.0 - the ALL-PLANET .stage Enemy Randomizer builder (Rift Apart Randomizer v0.76-DEV4).

Standard library only (the free `lz4` package is used automatically when installed: about 100x faster reading).
Reads the game folder (toc, dag, archives) READ-ONLY. Only `install` / `uninstall` write to the game folder, and they back
up every file they replace first.

WHAT IT DOES
  1. scan    every zone asset the game's dag lists (all planets, revisits, mission variants). Decodes each zone's actor
             and script tables; lists every SunsetSpawnerFactory (class 2E910F8C), its Templates variable, its owners and
             its Locations (spawn points). Builds two game-wide tables:
               * every actor uid -> (zone, kind), so an EXTERNAL spawn point (an actor of another zone) is resolved to
                 what it really is (a StaticVolume, or an anim clue authored for one enemy kind);
               * every anim clue -> the enemy kinds the game itself spawns at it (learned, not typed in).
  2. plan    applies the rules below to every factory, picks a replacement per factory (seeded, deterministic, weighted
             to spread the kinds of each zone), keeps one native user of every replacement template ("anchor").
  3. build   writes ONE RandoEnemies.stage with every changed zone, 18_rando_stage_manifest.lua, a JSON manifest, an
             inventory of every spawner in the game with the decision and reason, and a coverage report per planet/zone.
  4. check   re-reads a built .stage against the game's own zones: only the planned bytes differ, every reference
             consistent, every change still passes the rules.
  5. --cross-planet (EXPERIMENTAL) permits a globally unique foreign enemy Template UID via idx=0xFFFF.
             The source UID must already be used by a native factory in exactly one scanned zone; no actor data
             is copied. This proves file-structure consistency, NOT that the engine accepts every foreign template.

THE PROVEN METHOD (unchanged from tool 1.1.0 / stage_multi 1.2.0, which the 2026-11-25 run confirmed on 4 spawners)
  A change rewrites ONE Zone Script Vars entry: u16 Zone Actors index at entry+4 and u64 uid at entry+16. Nothing else.

THE RULES (a factory is changed only when ALL hold; every refusal is recorded with its reason)
  R1 single owner      its Templates variable is used by no other script node (a co-owner, e.g. an `Out` plug that writes
                       the variable, could undo or misuse the change).
     profile max       (default) ALSO a shared variable whose every co-owner is a node class/plug seen on a shared
                       variable whose runtime change SPAWNED the replacement (16's V.write_var writes the variable itself,
                       so that is the same change). Tier "shared-seen". Co-owner class F512DB23 is never changed.
     profile safe      single owner only (written to NEW_DIR/safe by every build, as a fallback).
     profile all       every shared variable (UNVERIFIED). For ONE exploratory session: check its log with
                       stage_check_log.py --json, and the next build learns from it - a shared spawner that WORKED makes
                       its co-owner classes "seen" everywhere (max profile), one that kept its original at volume spawn
                       points marks its co-owner classes as failing.
  R2 local, consistent the variable is a local actor reference whose index is its uid's Zone Actors record (C1).
  R3 regular enemy     original and replacement are regular enemies (ground / swarmer / flyer / turret family, not a
                       boss, mount, vehicle, NPC, friendly, hazard, or a bot class the kit calls "unclear").
  R4 same zone         the replacement is a template actor of THIS zone that a native factory really spawns from, and
                       at least one native factory keeps it after the patch (the anchor). A zone can only reference its
                       own actors, so the replacement pool is the enemy kinds each zone already holds.
  R5 killable pair     a pair proven in game (V.COMPAT_BUILTIN, your rivet.logs, the .stage runs), or the kit's
                       KILLABLE rule: same faction AND same movement group. Cross-faction pairs are refused: the kit's
                       round 63 evidence shows them spawning and never dying. Pairs proven bad are refused.
  R6 spawn points      every Locations point can host the replacement: a volume (local or resolved external) always;
                       an anim clue only if the game itself spawns the replacement kind at that clue (or one of its clue
                       family, animclue_<w1>_<w2>); a group/empty variable never. An external point no zone of the game
                       holds is allowed as "external-unresolved" (2 of 2 such changes worked in game) unless
                       --strict-external.

usage
  python -I stage_allgame.py scan    --game GAME --out NEW_DIR                   (inventory + coverage report only)
  python -I stage_allgame.py build   --game GAME --out NEW_DIR [--seed S] [--planet NAME ...] [--profile max|safe|all]
  experimental cross-planet build: add --cross-planet (foreign actor refs; requires in-game validation)
  python -I stage_allgame.py check   --game GAME --build NEW_DIR                 (or NEW_DIR/safe)
  after a play session:  stage_check_log.py rivet.log --manifest NEW_DIR/stage_enemies_manifest.json --json v1.json
                         stage_allgame.py build --game GAME --out NEXT_DIR --verdicts v1.json   (failures stay native)
  python -I stage_allgame.py install --game GAME --build NEW_DIR                 (backs up, then copies 3 files)
  python -I stage_allgame.py uninstall --game GAME                               (puts the newest backup back)
  offline (no game folder; zones extracted before):  --zone-file "levels\\...\\x.zone=PATH.zone.orig" (repeatable)
GAME = the folder that holds RiftApart.exe, toc and dag.
"""
from __future__ import annotations

import argparse
import array
import bisect
import csv
import hashlib
import io
import json
import os
import random
import re
import shutil
import struct
import sys
import time
import zipfile
from collections import Counter, OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)        # python -I does not add the script folder

import rcra                          # noqa: E402  (tool 1.1.0's reader: toc, DSAR, dag, DAT1, .stage writer)
import knowledge as KN               # noqa: E402  (tool 1.1.0: 16_rando_spawners.lua + rivet.log knowledge)

try:                                 # optional, free: pip install lz4. Checked against the built-in decoder before use.
    import lz4.block as _lz4

    def _fast_lz4(src, out_size):
        return _lz4.decompress(src, uncompressed_size=out_size)
    _probe = b"rift apart randomizer " * 50
    if _fast_lz4(_lz4.compress(_probe, store_size=False), len(_probe)) == _probe:
        _slow_lz4 = rcra.lz4_block_decompress
        rcra.lz4_block_decompress = _fast_lz4
        LZ4 = "lz4 package"
    else:
        LZ4 = "built-in (lz4 package failed its check)"
except Exception:
    LZ4 = "built-in (pure Python; pip install lz4 makes the scan ~100x faster)"

VERSION = "2.2.0"
KIT = "v0.76-DEV4"
STAGE_LUA = "1.1.0"                   # the 16/18 handshake value (V.STAGE_LUA / ST.STAGE_LUA); unchanged
STAGE_MOD_PATH = "mods/RandoEnemies.stage"
MANIFEST_LUA = "18_rando_stage_manifest.lua"
STAGE_LUA_FILE = "18_rando_stage_enemies.lua"
HEADER = 36

SEC_ZONE_ACTORS, SEC_SCRIPT_VARS, SEC_SCRIPT_PLUGS = 0x70682CB8, 0xD86A7934, 0xBEAB52E7
SEC_SCRIPT_ACTIONS, SEC_ACTOR_ASSETS = 0x5E54ACCF, 0x78684035
FACTORY_CLASS = 0x2E910F8C
NODE_SPAWNER_CLASS = rcra.crc32_engine("SpawnerScriptAction")  # exact class name used by 16_rando_spawners.lua
VAR_SIZE, PLUG_SIZE, ACTION_SIZE, ACTOR_SIZE = 32, 12, 40, 32
PLUG_TEMPLATES = rcra.crc32_engine("Templates")
PLUG_TEMPLATE = rcra.crc32_engine("Template")
PLUG_LOCATIONS = rcra.crc32_engine("Locations")
PLUG_COUNT = 0x90D607B0               # the factory's float spawn count (stage_multi 1.2.0 decode)
assert PLUG_TEMPLATES == 3990217346 and PLUG_TEMPLATE == 1835115251 and PLUG_LOCATIONS == 0x951BD5B6

# ---- fallback knowledge (stage_multi 1.2.0; the kit's 16_rando_spawners.lua + your logs come first) ----------------
FAMILY_FALLBACK = {"enm_pirate_robot_shooter": "ground", "enm_pirate_robot_melee": "swarmer",
                   "enm_pirate_robot_shielded": "swarmer", "enm_pirate_bladeball": "swarmer",
                   "enm_indigenous_crab": "swarmer", "enm_indigenous_puffoid": "swarmer"}
# in-game .stage evidence (this tool's own method). Kind names in full.
STAGE_EVIDENCE = {
    ("enm_pirate_robot_shooter", "enm_pirate_robot_melee"): ".stage run 2026-11-25: FF06CCC2A9AC1EA2 WORKED (Ardolis)",
    ("enm_pirate_robot_shooter", "enm_pirate_bladeball"): ".stage run 2026-11-25: 9C3139C7FFED7137 WORKED, killed after 8 s (Ardolis)",
    ("enm_indigenous_puffoid", "enm_indigenous_crab"): ".stage run 2026-11-25: FA5FB32C7AAB4C4A and DAFCA25C58FD387F WORKED (Ardolis)",
    ("enm_pirate_robot_melee", "enm_pirate_robot_shielded"): "DEV3 runtime on Ardolis: FE80D89C2D6D5A2D SUCCESS",
    ("enm_pirate_bladeball", "enm_pirate_robot_melee"): "V.COMPAT_BUILTIN round38-40",
}
BAD_PAIRS = {("enm_pirate_bladeball", "enm_pirate_robot_shooter"): "V.COMPAT_BUILTIN: proven bad",
             ("enm_pirate_robot_melee", "enm_pirate_robot_shooter"): "V.COMPAT_BUILTIN: proven bad"}
# the changes confirmed in game (rivet.log 2026-11-25, stage_check_log WORKED). Kept in every build that holds the zone.
PINS = [
    ("AE530D22FE113E2B", "FF06CCC2A9AC1EA2", "92C793D47A4657B6", "shooter -> brawler, WORKED 2026-11-25"),
    ("AE530D22FE113E2B", "9C3139C7FFED7137", "C37DB04A5A1F0972", "shooter -> bladeball, WORKED 2026-11-25"),
    ("AE530D22FE113E2B", "FA5FB32C7AAB4C4A", "B69D08BA44EE560E", "puffoid -> crab, WORKED 2026-11-25"),
    ("AE530D22FE113E2B", "DAFCA25C58FD387F", "D7677BCD9AAF5963", "puffoid -> crab, WORKED 2026-11-25"),
]
# R1b - shared Templates variables. 16_rando_spawners.lua's V.write_var writes the live script VARIABLE (uid + handle),
# the storage every plug of that variable reads, so a runtime change of a shared variable is the same change a .stage
# makes. DEV3 runtime on Ardolis (ROOT_CAUSE outcomes.txt): these co-owner node class/plug pairs were on shared variables
# whose replacement SPAWNED. A shared variable is changed only when EVERY co-owner is one of them ("max" profile).
COOWNER_SEEN = {
    "1FDCA5D3/93BF4450": "F3D033F9CBFADB82 shooter -> brawler SUCCESS (DEV3 runtime, Ardolis)",
    "0AC0B46C/93BF4450": "F4A34D9C49E5642A puffoid -> crab SUCCESS (DEV3 runtime, Ardolis)",
    "31B870E3/F7EDFFC8": "F607A5D72DB3F350 puffoid -> crab SUCCESS (DEV3 runtime, Ardolis)",
    "A3DF6F8E/93BF4450": "FE80D89C2D6D5A2D brawler -> shielded SUCCESS (DEV3 runtime, Ardolis)",
    "DBCB7A59/320B57AF": "FE80D89C2D6D5A2D brawler -> shielded SUCCESS (DEV3 runtime, Ardolis)",
}
# co-owner classes on shared variables whose runtime change did NOT take, at spawn points that were not the reason
# (88259456BFA87EA8: StaticVolume x3, ORIGINAL; D26E32B81D7B7C85: external, ORIGINAL). Never changed, in any profile.
COOWNER_BAD_CLASSES = {"F512DB23": "88259456BFA87EA8 and D26E32B81D7B7C85 kept their original at runtime (DEV3)"}
# Runtime evidence is cumulative, but only an actual observation can change policy.
# A later WORKED or failure supersedes an earlier observation; NOT REACHED is absence of evidence
# and must never erase a prior result.
FAILURE_VERDICTS = frozenset(("ORIGINAL SPAWNED", "NO SPAWN"))


def merge_verdict_entry(previous, incoming):
    if previous is not None and incoming[0] == "NOT REACHED":
        return previous
    return incoming


def effective_pins(zone_id, verdict_map, no_pins=False):
    """Use old hard-coded confirmations only until a runtime verdict exists for that spawner.

    A current WORKED verdict pins the exact replacement UID from that run. A current failure
    suppresses stale historical pins. NOT REACHED leaves prior evidence intact.
    """
    if no_pins:
        return []
    runtime = verdict_map.get(zone_id, {})
    pins = {}
    for zid, key, uid, why in PINS:
        if zid != zone_id:
            continue
        observed = runtime.get(key)
        if observed and observed[0] in FAILURE_VERDICTS:
            continue
        if observed and observed[0] == "WORKED":
            continue
        pins[key] = (uid, why)
    for key, (verdict, uid) in runtime.items():
        if verdict == "WORKED" and uid:
            pins[key] = (uid, "WORKED in the latest supplied runtime evidence")
    return [(key, uid, why) for key, (uid, why) in sorted(pins.items())]


PROFILES = ("max", "safe", "all")
REGULAR_FAMILIES = set(KN.FAMILY_GROUP)          # ground, swarmer, turret, flyer
NOT_ENEMY_PREFIX = ("veh_", "npc_", "amb_", "crt_", "critter", "haz_", "prop_", "animclue")


class Refused(Exception):
    pass


class NoActors(Refused):
    """a zone without actor tables (lighting, geometry, sound ...): nothing to change, not an error"""


def short(path):
    return path.replace("\\", "/").split("/")[-1].replace(".actor", "")


def hex16(v):
    return "%016X" % v


def planet_of(zone_path):
    """the planet folder (levels\\i29\\instance\\<planet>\\...); else the first folder below levels\\i29; else the zone
    file's first name token (i29_nefcity_01_gp.zone -> nefcity). Only a label for the reports."""
    p = [x for x in zone_path.replace("/", "\\").lower().split("\\") if x]
    dirs, f = p[:-1], (p[-1] if p else "")
    if "instance" in dirs and dirs.index("instance") + 1 < len(dirs):
        return dirs[dirs.index("instance") + 1]
    rest = dirs[2:] if dirs[:2] == ["levels", "i29"] else dirs[1:] if dirs[:1] == ["levels"] else dirs
    if rest:
        return rest[0]
    tok = [t for t in re.split(r"[_.]", f) if t and t not in ("i29", "zone") and not t.isdigit()]
    return tok[0] if tok else "other"


def clue_family(kind):
    w = kind.split("_")
    return "_".join(w[:3]) if kind.startswith("animclue_") and len(w) >= 3 else None


# ======================================================================================================================
# zone decoding (stage_multi 1.2.0's decoder: its writer reproduces tool 1.1.0's patched zone byte for byte)
# ======================================================================================================================
class Zone:
    def __init__(self, header, raw, path="?", zid=0, span=0):
        self.header, self.raw, self.path, self.zid, self.span = header, raw, path, zid, span
        if len(raw) < 16:
            raise Refused("not a zone (too short)")
        magic, typ, size, cnt = struct.unpack_from("<IIIH", raw, 0)
        if magic != rcra.DAT1_MAGIC:
            raise Refused("no DAT1 magic at offset 0")
        self.secs = {}
        for k in range(cnt):
            t, o, s = struct.unpack_from("<III", raw, 16 + 12 * k)
            if t in self.secs:
                raise Refused("section %08X twice" % t)
            if o + s > len(raw):
                raise Refused("section %08X out of bounds" % t)
            self.secs[t] = (o, s)
        self.section_table = raw[16:16 + 12 * cnt]
        self.has_scripts = all(t in self.secs for t in (SEC_SCRIPT_VARS, SEC_SCRIPT_PLUGS, SEC_SCRIPT_ACTIONS))
        if SEC_ACTOR_ASSETS not in self.secs or SEC_ZONE_ACTORS not in self.secs:
            raise NoActors("no actor tables")
        for t, rs in ((SEC_ZONE_ACTORS, ACTOR_SIZE), (SEC_SCRIPT_VARS, VAR_SIZE), (SEC_SCRIPT_PLUGS, PLUG_SIZE),
                      (SEC_SCRIPT_ACTIONS, ACTION_SIZE)):
            if t in self.secs and self.secs[t][1] % rs:
                raise Refused("section %08X not a multiple of %d" % (t, rs))
        ao, asz = self.secs[SEC_ACTOR_ASSETS]
        if asz % 12:
            raise Refused("actor-asset table size %d not n*12" % asz)
        n = asz // 12
        self.asset_ids = [struct.unpack_from("<Q", raw, ao + 8 * i)[0] for i in range(n)]
        self.asset_paths = []
        for i in range(n):
            off = struct.unpack_from("<I", raw, ao + 8 * n + 4 * i)[0]
            end = raw.find(b"\0", off)
            if off >= len(raw) or end < 0:
                raise Refused("actor-asset path %d out of bounds" % i)
            self.asset_paths.append(raw[off:end].decode("latin1"))
        zo, zs = self.secs[SEC_ZONE_ACTORS]
        self.actors = [struct.unpack_from("<IIIIIIQ", raw, zo + ACTOR_SIZE * i) for i in range(zs // ACTOR_SIZE)]
        self.rec_of, self.dup_uids = {}, {}
        for i, a in enumerate(self.actors):
            if a[1] >= n:
                raise Refused("Zone Actors #%d: asset index %d out of range" % (i, a[1]))
            if a[6] in self.rec_of:
                self.dup_uids.setdefault(a[6], [self.rec_of[a[6]]]).append(i)
            else:
                self.rec_of[a[6]] = i
        self.vars, self.plugs, self.nodes, self.owners = [], [], [], {}
        self.var_base = 0
        if not self.has_scripts:
            return
        vo, vs = self.secs[SEC_SCRIPT_VARS]
        self.var_base = vo
        self.vars = [struct.unpack_from("<HHHHQQQ", raw, vo + VAR_SIZE * v) for v in range(vs // VAR_SIZE)]
        po, ps = self.secs[SEC_SCRIPT_PLUGS]
        self.plugs = [struct.unpack_from("<III", raw, po + PLUG_SIZE * p) for p in range(ps // PLUG_SIZE)]
        so, ss = self.secs[SEC_SCRIPT_ACTIONS]
        seen = [0] * len(self.plugs)
        for r in range(ss // ACTION_SIZE):
            o = so + ACTION_SIZE * r
            key = struct.unpack_from("<Q", raw, o)[0]
            a0, a1, b0, b1 = struct.unpack_from("<HHHH", raw, o + 18)
            cls = struct.unpack_from("<I", raw, o + 28)[0]
            plugs = []
            for f, c in ((a0, a1), (b0, b1)):
                if f == 0xFFFF:
                    continue
                for p in range(f, f + c):
                    if p >= len(self.plugs):
                        raise Refused("Script Actions #%d: plug %d out of range" % (r, p))
                    seen[p] += 1
                    plugs.append(p)
            self.nodes.append({"r": r, "key": key, "cls": cls, "plugs": plugs})
        if any(x != 1 for x in seen):
            raise Refused("Script Actions plug ranges do not partition Script Plugs exactly once")
        for nd in self.nodes:
            for p in nd["plugs"]:
                name, vi, kind = self.plugs[p]
                if vi >= len(self.vars):
                    raise Refused("plug %d -> Script Vars %d out of range" % (p, vi))
                self.owners.setdefault(vi, []).append((nd, p, name))
        keys = Counter(nd["key"] for nd in self.nodes)
        self.dup_keys = {k for k, c in keys.items() if c > 1}

    def kind_of_rec(self, rec):
        return short(self.asset_paths[self.actors[rec][1]])

    def asset_path_of_rec(self, rec):
        return self.asset_paths[self.actors[rec][1]]

    def var_form(self, vi):
        typ, aux, idx, aux2, name, uid, pad = self.vars[vi]
        if typ != 5:
            return "not-actor"
        if uid == 0:
            return "group" if aux != 0xFFFF else "empty"
        if idx == 0xFFFF:
            return "external"
        return "local"

    def c1(self):
        """every local type-5 reference: index == the Zone Actors record of its uid; external ones: uid not in zone"""
        bad, n = [], 0
        for vi, v in enumerate(self.vars):
            f = self.var_form(vi)
            if f == "local":
                n += 1
                if self.rec_of.get(v[5]) != v[2] or v[5] in self.dup_uids:
                    bad.append(vi)
            elif f == "external" and v[5] in self.rec_of:
                bad.append(vi)
        return n, bad

    def factories(self):
        """every SunsetSpawnerFactory node as a dict (never raises: problems become 'problem')"""
        out = []
        for nd in self.nodes:
            if nd["cls"] != FACTORY_CLASS:
                continue
            f = {"key": hex16(nd["key"]), "action": nd["r"], "problem": None, "sv": None, "owners": 0, "co_owner_classes": [],
                 "form": None, "uid": None, "rec": None, "kind": None, "count": None, "locs": []}
            out.append(f)
            if nd["key"] in self.dup_keys:
                f["problem"] = "the node key is on several Script Actions records"
            tpl = [(p, self.plugs[p][1]) for p in nd["plugs"] if self.plugs[p][0] == PLUG_TEMPLATES]
            if len(tpl) != 1:
                f["problem"] = f["problem"] or "%d Templates plugs" % len(tpl)
                continue
            f["plug"], vi = tpl[0]
            f["sv"] = vi
            own = self.owners.get(vi, [])
            f["owners"] = len(own)
            f["co_owner_classes"] = sorted({"%08X/%08X" % (o[0]["cls"], o[2]) for o in own if o[0] is not nd})
            f["form"] = self.var_form(vi)
            v = self.vars[vi]
            if f["form"] in ("local", "external"):
                f["uid"], f["rec"] = hex16(v[5]), v[2]
                if f["form"] == "local":
                    if self.rec_of.get(v[5]) != v[2] or v[5] in self.dup_uids:
                        f["problem"] = f["problem"] or "Templates reference inconsistent in the game's own zone"
                    elif v[2] < len(self.actors):
                        f["kind"] = self.kind_of_rec(v[2])
                        f["asset"] = self.asset_path_of_rec(v[2])
            for p in nd["plugs"]:
                nm, pv, _ = self.plugs[p]
                if nm == PLUG_LOCATIONS:
                    form = self.var_form(pv)
                    lv = self.vars[pv]
                    kind = self.kind_of_rec(lv[2]) if form == "local" and lv[2] < len(self.actors) else None
                    f["locs"].append({"form": form, "sv": pv, "uid": hex16(lv[5]), "kind": kind})
                elif nm == PLUG_COUNT:
                    cv = self.vars[pv]
                    if cv[0] == 2:
                        f["count"] = round(struct.unpack("<f", struct.pack("<I", cv[5] & 0xFFFFFFFF))[0], 3)
        return out

    def template_nodes(self):
        """Read-only census of nodes with a singular Template plug; never changes their variables."""
        out = []
        for nd in self.nodes:
            if nd["cls"] == FACTORY_CLASS:
                continue
            template_plugs = [(p, self.plugs[p][1]) for p in nd["plugs"] if self.plugs[p][0] == PLUG_TEMPLATE]
            if not template_plugs:
                continue
            # Preserve every candidate, including malformed/multi-plug nodes, for forensic classification.
            for plug, vi in template_plugs:
                v = self.vars[vi]
                form = self.var_form(vi)
                kind = None
                asset = None
                if form == "local" and v[2] < len(self.actors) and self.rec_of.get(v[5]) == v[2] and v[5] not in self.dup_uids:
                    kind = self.kind_of_rec(v[2])
                    asset = self.asset_path_of_rec(v[2])
                owners = self.owners.get(vi, [])
                other_plugs = []
                for p in nd["plugs"]:
                    nm, pvi, _ = self.plugs[p]
                    if p != plug:
                        other_plugs.append("%08X:sv%d" % (nm, pvi))
                out.append({
                    "key": hex16(nd["key"]), "action": nd["r"], "class": "%08X" % nd["cls"],
                    "is_spawner_class": nd["cls"] == NODE_SPAWNER_CLASS,
                    "template_plug": plug, "template_plug_count": len(template_plugs),
                    "var_index": vi, "form": form, "uid": hex16(v[5]), "kind": kind, "asset": asset,
                    "owners": len(owners),
                    "co_owner_classes": sorted({"%08X/%08X" % (o[0]["cls"], o[2]) for o in owners if o[0] is not nd}),
                    "other_plugs": ";".join(other_plugs),
                    "problem": ("multiple Template plugs" if len(template_plugs) != 1 else
                                "duplicate node key" if nd["key"] in self.dup_keys else
                                "local Template reference is inconsistent" if form == "local" and kind is None else "")
                })
        return out

    def node_template_spawners(self):
        """Count distinct nodes with a Template plug outside SunsetSpawnerFactory."""
        return sum(1 for nd in self.nodes if nd["cls"] != FACTORY_CLASS
                   and any(self.plugs[p][0] == PLUG_TEMPLATE for p in nd["plugs"]))


def apply_changes(raw, changes):
    out = bytearray(raw)
    for c in changes:
        a = c["entry_abs"]
        out[a + 4:a + 6] = struct.pack("<H", c["replacement_index"])
        out[a + 16:a + 24] = struct.pack("<Q", int(c["replacement_uid"], 16))
    return bytes(out)


def compare(z0, z1, changes):
    """the only allowed differences: {index, uid} of the planned entries; everything else identical"""
    problems = []
    if len(z0.raw) != len(z1.raw):
        problems.append("size differs")
    if z0.header != z1.header:
        problems.append("toc header differs")
    if z0.section_table != z1.section_table:
        problems.append("section table differs")
    allowed = set()
    for c in changes:
        a = c["entry_abs"]
        allowed |= set(range(a + 4, a + 6)) | set(range(a + 16, a + 24))
    lo = min((c["entry_abs"] for c in changes), default=0)
    hi = max((c["entry_abs"] + VAR_SIZE for c in changes), default=0)
    # fast path: everything outside [lo, hi) must be identical
    if z0.raw[:lo] != z1.raw[:lo] or z0.raw[hi:] != z1.raw[hi:]:
        problems.append("bytes differ outside the changed Script Vars entries")
    diff = [i for i in range(lo, hi) if z0.raw[i] != z1.raw[i]]
    stray = [i for i in diff if i not in allowed]
    if stray:
        problems.append("%d byte(s) outside the planned fields, first at %d" % (len(stray), stray[0]))
    n, bad = z1.c1()
    if bad:
        problems.append("C1: %d inconsistent actor reference(s): SV %s" % (len(bad), bad[:10]))
    for c in changes:
        v = z1.vars[c["var_index"]]
        if hex16(v[5]) != c["replacement_uid"] or v[2] != c["replacement_index"]:
            problems.append("SV #%d does not hold the replacement" % c["var_index"])
        if v[0] != 5 or v[1] != 0xFFFF or v[3] != 0xFFFF or v[6] != 0:
            problems.append("SV #%d: type/aux/padding changed" % c["var_index"])
        if v[4] != z0.vars[c["var_index"]][4]:
            problems.append("SV #%d: name hash changed" % c["var_index"])
    return problems, diff, n


# ======================================================================================================================
# sources: the game folder, or zone files extracted before (offline)
# ======================================================================================================================
class Source:
    def __init__(self, game=None, zone_files=(), planets=(), limit=0, log=print):
        self.game, self.toc, self.dag, self.log = game, None, None, log
        self.items = []               # (path, zid, span, loader)
        filt = [p.lower() for p in planets]
        if game:
            if not os.path.isfile(os.path.join(game, "toc")):
                raise Refused("no 'toc' in %s (pass the folder that holds RiftApart.exe, toc and dag)" % game)
            if not os.path.isfile(os.path.join(game, "dag")):
                raise Refused("no 'dag' in %s: the zone names come from it" % game)
            self.toc, self.dag = rcra.Toc(game), rcra.Dag(game)
            names = sorted({self.dag.names[i] for i in range(self.dag.count) if self.dag.type_name(i) == "zone"})
            self.dag_zone_count = len(names)
            rows = []
            self.missing = []
            for nm in names:
                if filt and not any(f in nm.lower() for f in filt):
                    continue
                zid = rcra.crc64_path(nm)
                e = self.toc.find(zid, 0) or self.toc.find(zid)
                if e is None:
                    self.missing.append(nm)
                    continue
                rows.append((e.archive, e.offset, nm, zid, e))
            rows.sort()                       # archive order: sequential reads hit the chunk cache
            for _, _, nm, zid, e in rows:
                self.items.append((nm, zid, e.span, (lambda e=e: (self.toc.header(e), self.toc.read(e)))))
        for spec in zone_files:
            if "=" not in spec:
                raise Refused("--zone-file needs ZONE_PATH=FILE (the zone's path inside the game, then the file)")
            nm, fp = spec.split("=", 1)
            if filt and not any(f in nm.lower() for f in filt):
                continue
            zid = rcra.crc64_path(nm)

            def load(fp=fp):
                blob = open(fp, "rb").read()
                if rcra.find_dat1(blob, 64) == HEADER:
                    return blob[:HEADER], blob[HEADER:]
                if rcra.find_dat1(blob, 64) == 0:
                    return None, blob
                raise Refused("%s: neither a 36-byte header + zone nor a bare zone" % fp)
            self.items.append((nm, zid, 0, load))
            self.dag_zone_count = getattr(self, "dag_zone_count", 0) + 1
            self.missing = getattr(self, "missing", [])
        if limit:
            self.items = self.items[:limit]

    def actor_asset(self, path):
        if not self.toc:
            return None
        e = self.toc.find(rcra.crc64_path(path), 0) or self.toc.find(rcra.crc64_path(path))
        if e is None:
            return None
        try:
            return self.toc.read(e)
        except rcra.FormatError:
            return None

    def close(self):
        if self.toc:
            self.toc.close()


# ======================================================================================================================
# knowledge: families, factions, pairs
# ======================================================================================================================
class Brain:
    def __init__(self, scripts_dir, logs, source=None, actor_family=True, log=print):
        self.k = KN.Knowledge()
        self.notes = []
        self.src, self.actor_family_on, self.log = source, actor_family, log
        if scripts_dir and os.path.isfile(os.path.join(scripts_dir, "16_rando_spawners.lua")):
            KN.load_scripts(self.k, scripts_dir)
        else:
            self.notes.append("16_rando_spawners.lua not found in %s: only the built-in fallback knowledge is used" % scripts_dir)
        for p in logs:
            try:
                KN.load_log(self.k, p)
            except OSError as e:
                self.notes.append("log %s: %s" % (p, e))
        self.notes += self.k.notes
        # class -> family, only where every source agrees
        cf = defaultdict(set)
        for t in self.k.templates.values():
            if t.cls and t.family:
                cf[t.cls].add(t.family)
        for nm, c in self.k.actor_class.items():
            f = self.k.actor_family.get(nm)
            if c and f:
                cf[c].add(f)
        self.class_family = {c: next(iter(f)) for c, f in cf.items() if len(f) == 1}
        self._fam = {}

    def family(self, kind, asset_path=None):
        """(family or None, source)"""
        if kind in self._fam:
            return self._fam[kind]
        fam, cls, role, srcs, fams = self.k.kind_info(kind)
        out = None
        if fam:
            out = (fam, "kit knowledge (%s)" % ", ".join(srcs[:2]))
        elif len(fams) > 1:
            out = (None, "kit knowledge disagrees: %s" % "/".join(fams))
        elif kind in FAMILY_FALLBACK:
            out = (FAMILY_FALLBACK[kind], "stage_multi 1.2.0 table")
        elif self.actor_family_on and asset_path and self.src:
            out = self._family_from_actor(asset_path)
        self._fam[kind] = out or (None, "unknown: no rivet.log has seen this kind yet")
        return self._fam[kind]

    def _family_from_actor(self, path):
        data = self.src.actor_asset(path)
        if not data:
            return None
        found = set()
        for c, f in self.class_family.items():
            if c.encode() in data:
                found.add((c, f))
                continue
            h = struct.pack("<I", rcra.crc32_engine(c))
            i = data.find(h)
            while i >= 0:
                if i % 4 == 0:
                    found.add((c, f))
                    break
                i = data.find(h, i + 1)
        fams = {f for _, f in found}
        if len(fams) == 1:
            return (fams.pop(), "actor file (bot class %s) - UNVERIFIED inference" % "/".join(sorted(c for c, _ in found)))
        if fams:
            return (None, "actor file names several bot classes %s" % sorted(c for c, _ in found))
        return None

    def role(self, kind):
        roles = {t.role for t in self.k.templates.values() if (KN.short(t.name) or "").lower() == kind.lower() and t.role}
        return roles

    def regular(self, kind, asset_path=None):
        """(ok, family, why)"""
        n = kind.lower()
        if n.startswith(NOT_ENEMY_PREFIX):
            return False, None, "not an enemy (%s)" % n.split("_")[0]
        if KN.excluded(n):
            return False, None, "excluded by the kit's name rules (boss / NPC / friendly / ...)"
        roles = self.role(kind)
        if roles and roles != {"enemy"}:
            return False, None, "kit role %s" % "/".join(sorted(roles))
        fam, src = self.family(kind, asset_path)
        if fam is None:
            return False, None, "family %s" % src
        if fam not in REGULAR_FAMILIES:
            return False, fam, "family %s (not a regular enemy: boss-tier, mount, unclear or friendly)" % fam
        return True, fam, src

    def pair(self, o, fo, r, fr):
        """(ok, tier, evidence)"""
        if o == r:
            return False, None, "same kind"
        st = self.k.pair_status_names(o, fo, r, fr)
        if (o, r) in BAD_PAIRS:
            return False, None, BAD_PAIRS[(o, r)]
        if st and st[0] == "bad":
            return False, None, "proven bad: " + st[1][:90]
        if (o, r) in STAGE_EVIDENCE:
            return True, "proven", STAGE_EVIDENCE[(o, r)]
        if st and st[0] == "ok":
            return True, "proven", "V.COMPAT_BUILTIN / your logs: " + st[1][:90]
        if KN.faction(o) != KN.faction(r):
            return False, None, "cross-faction %s -> %s (kit evidence: such replacements spawned and never died)" % (
                KN.faction(o), KN.faction(r))
        if KN.FAMILY_GROUP[fo] != KN.FAMILY_GROUP[fr]:
            return False, None, "movement group %s -> %s" % (KN.FAMILY_GROUP[fo], KN.FAMILY_GROUP[fr])
        return True, "kin", "same faction (%s), same movement group (%s): the kit's KILLABLE rule" % (
            KN.faction(o), KN.FAMILY_GROUP[fo])


# ======================================================================================================================
# scan
# ======================================================================================================================
class Scan:
    def __init__(self):
        self.zones = OrderedDict()       # zid hex -> record
        self.actor_ids = {}              # zid hex -> sorted array('Q') of actor uids
        self.template_catalog = {}       # globally unique enemy templates used by native factories
        self.template_catalog_all = {}   # includes non-unique UIDs, for resolving existing external templates
        self.actor_catalog = defaultdict(list)  # UID -> every scanned actor kind/home
        self.template_uid_homes = defaultdict(set)
        self.clue_uids = {}              # uid -> set of clue kinds (from every zone)
        self.ext_needed = set()
        self.resolved = {}               # uid -> (kind or None, zone, how)
        self.clue_hosts = defaultdict(set)
        self.clue_family_hosts = defaultdict(set)
        self.errors = []
        self.seconds = 0.0


def scan(source, log=print, keep_zone=None):
    """keep_zone(zid_hex) -> True keeps (header, raw) in memory for the build"""
    S = Scan()
    S.kept = {}
    t0 = time.time()
    n = len(source.items)
    for i, (path, zid, span, load) in enumerate(source.items):
        zh = hex16(zid)
        rec = {"zone": path, "zone_id": zh, "planet": planet_of(path), "span": span, "status": "ok", "factories": [],
               "node_template_spawners": 0, "template_nodes": [], "actors": 0}
        S.zones[zh] = rec
        try:
            header, raw = load()
            rec["size"] = len(raw)
            z = Zone(header, raw, path, zid, span)
        except NoActors:
            rec["status"] = "no actors"
            continue
        except (Refused, rcra.FormatError, OSError) as e:
            rec["status"] = "not decodable: %s" % e
            S.errors.append((path, str(e)))
            continue
        rec["actors"] = len(z.actors)
        rec["has_header"] = header is not None
        rec["sha256"] = hashlib.sha256(raw).hexdigest()
        if header is not None:
            schema, sizes = rcra.header_block_sizes(header)
            rec["header_ok"] = sum(sizes) == len(raw)
        S.actor_ids[zh] = array.array("Q", sorted(z.rec_of))
        for u, r in z.rec_of.items():
            k = z.kind_of_rec(r)
            S.actor_catalog[hex16(u)].append({"kind": k, "asset": z.asset_path_of_rec(r),
                                               "zone_id": zh, "zone": path, "planet": rec["planet"], "rec": r})
            if k.startswith("animclue_"):
                S.clue_uids.setdefault(u, set()).add(k)
        if not z.has_scripts:
            rec["status"] = "no scripts"
            continue
        rec["template_nodes"] = z.template_nodes()
        rec["node_template_spawners"] = z.node_template_spawners()
        n1, bad = z.c1()
        rec["c1_local_refs"], rec["c1_bad"] = n1, len(bad)
        facs = z.factories()
        rec["factories"] = facs
        for f in facs:
            if f["form"] == "local" and f["uid"] and f["kind"]:
                meta = {"uid": f["uid"], "kind": f["kind"], "asset": f.get("asset"),
                        "rec": f["rec"], "zone_id": zh, "zone": path, "planet": rec["planet"]}
                S.template_uid_homes[f["uid"]].add(zh)
                S.template_catalog_all.setdefault(f["uid"], meta)
                if not f["problem"]:
                    S.template_catalog.setdefault(f["uid"], meta)
            for l in f["locs"]:
                if l["form"] == "external":
                    S.ext_needed.add(int(l["uid"], 16))
                elif l["form"] == "local" and l["kind"] and l["kind"].startswith("animclue_") and f["kind"]:
                    S.clue_hosts[l["kind"]].add(f["kind"])
        if keep_zone and facs and keep_zone(zh):
            S.kept[zh] = load                         # re-read for the build (hundreds of zones do not stay in memory)
        if (i + 1) % 25 == 0 or i + 1 == n:
            log("  scanned %d/%d zones (%.0f s)" % (i + 1, n, time.time() - t0))
    # Foreign template UIDs are candidates only when globally unique and backed by a native factory.
    S.template_catalog = {u: v for u, v in S.template_catalog.items() if len(S.template_uid_homes[u]) == 1}
    # resolve external spawn points across the whole game
    home_of = defaultdict(list)
    need = S.ext_needed
    for zh, arr in S.actor_ids.items():
        for u in arr:
            if u in need:
                home_of[u].append(zh)
    for u in need:
        homes = home_of.get(u, [])
        if not homes:
            S.resolved[u] = (None, None, "unresolved")
            continue
        kinds = S.clue_uids.get(u)
        if kinds and len(kinds) > 1:
            S.resolved[u] = ("?", homes[0], "ambiguous")
        elif kinds:
            S.resolved[u] = (next(iter(kinds)), homes[0], "clue")
        else:
            S.resolved[u] = ("volume", homes[0], "volume" if len(homes) == 1 else "volume (uid in %d zones)" % len(homes))
    for zh, rec in S.zones.items():
        for f in rec["factories"]:
            for l in f["locs"]:
                if l["form"] == "external":
                    k, home, how = S.resolved.get(int(l["uid"], 16), (None, None, "unresolved"))
                    l["resolved"] = {"kind": k, "zone": S.zones[home]["zone"] if home else None, "how": how}
                    if how == "clue" and f["kind"]:
                        S.clue_hosts[k].add(f["kind"])
    for clue, kinds in S.clue_hosts.items():
        cf = clue_family(clue)
        if cf:
            S.clue_family_hosts[cf] |= kinds
    S.seconds = time.time() - t0
    return S


def _has(arr, u):
    i = bisect.bisect_left(arr, u)
    return i < len(arr) and arr[i] == u


# ======================================================================================================================
# plan
# ======================================================================================================================
def point_verdict(S, loc, rep, strict_external):
    """(ok, tier, text) for one spawn point and one replacement kind"""
    form = loc["form"]
    if form == "local":
        pk, where = loc["kind"], "local"
    elif form == "external":
        res = loc.get("resolved") or {"kind": None, "how": "unresolved"}
        if res["how"] == "unresolved":
            if strict_external:
                return False, None, "external spawn point %s is in no zone of the game (--strict-external)" % loc["uid"]
            return True, "external-unresolved", "external %s (in no scanned zone)" % loc["uid"]
        if res["how"] == "ambiguous":
            return False, None, "external spawn point %s is a different anim clue in different zones" % loc["uid"]
        pk, where = res["kind"], "external"
        if pk == "volume":
            return True, "external-volume", "external %s (%s, a non-clue actor of %s)" % (loc["uid"], res["how"], short(res["zone"] or "?"))
    else:
        return False, None, "spawn point SV #%d is a %s variable (undecoded)" % (loc["sv"], form)
    if pk and pk.startswith("animclue_"):
        if rep in S.clue_hosts.get(pk, ()):
            return True, "clue-native", "%s anim clue %s: the game spawns %s there" % (where, pk, rep)
        cf = clue_family(pk)
        if cf and rep in S.clue_family_hosts.get(cf, ()):
            return True, "clue-family", "%s anim clue %s: the game spawns %s at %s_* clues" % (where, pk, rep, cf)
        return False, None, "%s anim clue %s, never used for %s" % (where, pk, rep)
    return True, "volume", "%s %s" % (where, pk)


def spawn_points_ok(S, f, rep, strict_external):
    if not f["locs"]:
        return False, None, "no Locations plug: spawn point unknown"
    tiers, parts = [], []
    for l in f["locs"]:
        ok, tier, text = point_verdict(S, l, rep, strict_external)
        if not ok:
            return False, None, text
        tiers.append(tier)
        parts.append(text)
    order = ["external-unresolved", "clue-family", "external-volume", "clue-native", "volume"]
    worst = min(tiers, key=order.index)
    return True, worst, "; ".join(parts)


def plan_zone_force(S, brain, rec, opts, rng):
    """Aggressive experimental mode: replace every classifiable enemy factory.

    It deliberately relaxes faction/movement and spawn-clue rules, but still requires:
    - a unique source enemy template from a scanned zone;
    - a single, structurally valid Templates plug;
    - an identifiable original enemy kind;
    - a decodable local/external actor reference.

    Replacements use external UID references (idx=0xFFFF) to avoid consuming a local
    anchor. Known failed replacement UIDs are blacklisted, but the spawner is retried
    with a different candidate. Every forced change is clearly marked for in-game testing.
    """
    facs = rec["factories"]
    decisions = OrderedDict()
    changes = []
    global_pool = [v for v in S.template_catalog.values() if (v.get("kind") or "").startswith("enm_")]
    global_pool.sort(key=lambda x: (x["kind"], x["uid"]))
    usage = Counter()

    for f in facs:
        key = f["key"]
        if f.get("problem"):
            decisions[key] = ("refused", "force mode cannot safely identify one Templates variable: " + f["problem"])
            continue
        # A Templates variable shared by multiple owners cannot be safely
        # changed for one spawner: it would also change every co-owner.
        if f.get("owners", 0) != 1:
            decisions[key] = ("refused", "kept native: shared Templates variable (%d owners)" % f.get("owners", 0))
            continue
        if f.get("form") not in ("local", "external") or not f.get("uid") or f.get("sv") is None:
            decisions[key] = ("refused", "force mode requires a singular local/external enemy Template reference")
            continue

        original_uid = f["uid"]
        original_kind = f.get("kind")
        original_asset = f.get("asset")
        if f["form"] == "external":
            homes = S.actor_catalog.get(original_uid, [])
            kinds = {x["kind"] for x in homes}
            if len(kinds) == 1:
                original_kind = next(iter(kinds))
                original_asset = next((x.get("asset") for x in homes if x["kind"] == original_kind), None)
        if not original_kind or not original_kind.startswith("enm_"):
            decisions[key] = ("not enemy", "original template could not be classified as an enemy")
            continue

        ok_orig, original_family, original_reason = brain.regular(original_kind, original_asset)
        if not ok_orig:
            decisions[key] = ("refused", "kept native: boss-tier, non-regular, or unclassified (" + str(original_reason) + ")")
            continue

        verdict = (getattr(opts, "verdict_map", {}) or {}).get(rec["zone_id"], {}).get(key)
        avoid = {verdict[1]} if verdict and verdict[0] in ("NO SPAWN", "ORIGINAL SPAWNED") and verdict[1] else set()

        candidates = [x for x in global_pool if x["uid"] != original_uid and x["uid"] not in avoid
                      and x["zone_id"] != rec["zone_id"]]
        if not candidates:
            decisions[key] = ("refused", "no globally unique foreign enemy template is available")
            continue

        ranked = []
        rejected = Counter()
        for candidate in candidates:
            ok_rep, rep_family, _ = brain.regular(candidate["kind"], candidate.get("asset"))
            if not ok_rep:
                rejected["boss-tier/non-regular candidate"] += 1
                continue
            try:
                pair_ok, pair_tier, pair_evidence = brain.pair(original_kind, original_family,
                                                                candidate["kind"], rep_family)
            except Exception:
                pair_ok, pair_tier, pair_evidence = False, None, "compatibility check failed"
            if not pair_ok:
                rejected["incompatible/unproven pair"] += 1
                continue
            spawn_ok, spawn_tier, spawn_evidence = spawn_points_ok(S, f, candidate["kind"], False)
            if not spawn_ok:
                rejected["spawn-point evidence missing/incompatible"] += 1
                continue
            ranked.append((candidate, rep_family, pair_tier, pair_evidence, spawn_tier, spawn_evidence))
        if not ranked:
            why = ", ".join("%s: %d" % item for item in sorted(rejected.items())) or "no foreign candidate"
            decisions[key] = ("refused", "kept native: no candidate passed pair and spawn-point checks (" + why + ")")
            continue
        weights = [1.0 / (1.0 + usage[x[0]["kind"]]) for x in ranked]
        candidate, rep_family, pair_tier, pair_evidence, spawn_tier, spawn_evidence = rng.choices(
            ranked, weights=weights, k=1)[0]
        usage[candidate["kind"]] += 1

        # V2.2 only reaches this point after regular-enemy, pair, and spawn-point checks pass.
        tier = "FORCED-TEST"
        changes.append({
            "zone": rec["zone"], "zone_id": rec["zone_id"], "planet": rec["planet"], "key": key,
            "action": f["action"], "plug": f.get("plug"), "var_index": f["sv"],
            "original_uid": original_uid, "original_index": f["rec"], "original": original_kind,
            "original_family": original_family or "unknown",
            "replacement_uid": candidate["uid"], "replacement_index": 0xFFFF,
            "replacement_external": True, "replacement_source_zone": candidate["zone"],
            "replacement_source_zone_id": candidate["zone_id"], "replacement_source_planet": candidate["planet"],
            "replacement": candidate["kind"], "replacement_family": rep_family or "unknown",
            "pair_tier": pair_tier, "pair_evidence": "SAFE V2.2.0: " + pair_evidence,
            "spawn_tier": spawn_tier or "forced-unsafe",
            "spawn_points": spawn_evidence or "forced: spawn point was not validated",
            "count": f.get("count"), "tier": tier, "anchor": None,
            "pair": "safe-force|%s>%s" % (original_kind, candidate["kind"]),
        })
        decisions[key] = ("changed", "%s -> %s [FORCED, in-game test required]" %
                          (original_kind, candidate["kind"]))

    changes.sort(key=lambda c: c["var_index"])
    return changes, decisions, {}, []


def plan_zone(S, brain, rec, opts, rng):
    """returns (changes, decisions{key: (status, reason)}, anchors)"""
    if getattr(opts, "force_all_enemies", False):
        return plan_zone_force(S, brain, rec, opts, rng)
    facs = [f for f in rec["factories"]]
    dec = OrderedDict()
    # the replacement pool: local templates a native factory spawns from
    users = defaultdict(list)
    for f in facs:
        if f["form"] == "local" and f["kind"] and not f["problem"]:
            users[f["uid"]].append(f["key"])
    pool = {}
    for uid, keys in users.items():
        f0 = next(f for f in facs if f["uid"] == uid)
        ok, fam, why = brain.regular(f0["kind"], f0.get("asset"))
        if ok:
            pool[uid] = {"kind": f0["kind"], "family": fam, "rec": f0["rec"], "family_src": why,
                         "external": False, "source_zone": rec["zone"], "source_zone_id": rec["zone_id"],
                         "source_planet": rec["planet"]}
    if getattr(opts, "cross_planet", False):
        for uid, meta in S.template_catalog.items():
            if uid in pool or meta["zone_id"] == rec["zone_id"]:
                continue
            ok, fam, why = brain.regular(meta["kind"], meta.get("asset"))
            if ok:
                pool[uid] = {"kind": meta["kind"], "family": fam, "rec": 0xFFFF, "family_src": why,
                             "external": True, "source_zone": meta["zone"], "source_zone_id": meta["zone_id"],
                             "source_planet": meta["planet"]}
    # per factory: eligibility, then the replacement options
    options = {}
    for f in facs:
        k = f["key"]
        if f["problem"]:
            dec[k] = ("refused", "zone data: " + f["problem"])
            continue
        if f["form"] != "local":
            dec[k] = ("refused", "Templates variable is a %s reference" % f["form"])
            continue
        if not f["kind"]:
            dec[k] = ("refused", "template actor unknown")
            continue
        ok, fam, why = brain.regular(f["kind"], f.get("asset"))
        if not ok:
            dec[k] = ("not enemy" if why.startswith(("not an enemy", "excluded", "kit role", "family large", "family mount",
                                                      "family friendly", "family unclear")) else "refused", "original %s: %s" % (f["kind"], why))
            continue
        vd = (getattr(opts, "verdict_map", {}) or {}).get(rec["zone_id"], {}).get(k)
        if vd and vd[0] in ("ORIGINAL SPAWNED", "NO SPAWN"):
            dec[k] = ("refused", "in-game verdict %s (stage_check_log --json): left native" % vd[0])
            continue
        shared = f["owners"] != 1
        if shared:
            co = f["co_owner_classes"]
            seen_set = set(COOWNER_SEEN) | set(getattr(opts, "coowner_learned", {}))
            bad_cls = set(COOWNER_BAD_CLASSES) | (set(getattr(opts, "coowner_bad_learned", {})) - {c.split("/")[0] for c in seen_set})
            bad = [c for c in co if c.split("/")[0] in bad_cls]
            unseen = [c for c in co if c not in seen_set]
            if bad:
                dec[k] = ("refused", "R1 shared variable: co-owner %s is a node class whose spawners kept their original at runtime" % bad[0])
                continue
            if opts.profile == "safe" or (opts.profile == "max" and unseen):
                dec[k] = ("refused", "R1 shared variable: %d owners, co-owner class/plug %s %s" % (
                    f["owners"], ", ".join(co[:3]), "(profile safe)" if opts.profile == "safe" else "never seen in a runtime success"))
                continue
            shared = "seen" if not unseen else "unverified"
        opts_f, why_not = [], Counter()
        for uid, candidate in pool.items():
            rk, rfam, rrec, rwhy = candidate["kind"], candidate["family"], candidate["rec"], candidate["family_src"]
            if uid == f["uid"] or rk == f["kind"]:
                continue
            pok, ptier, pev = brain.pair(f["kind"], fam, rk, rfam)
            if not pok:
                why_not[pev.split(":")[0].split("(")[0].strip()[:60]] += 1
                continue
            sok, stier, stext = spawn_points_ok(S, f, rk, opts.strict_external)
            if not sok:
                why_not["spawn point: " + re.sub(r" for \S+$", " for the replacement", stext)[:140]] += 1
                continue
            opts_f.append({"uid": uid, "kind": rk, "family": rfam, "rec": rrec, "pair_tier": ptier, "pair_evidence": pev,
                           "spawn_tier": stier, "spawn_points": stext, "family_src": rwhy,
                           "external": candidate["external"], "source_zone": candidate["source_zone"],
                           "source_zone_id": candidate["source_zone_id"], "source_planet": candidate["source_planet"]})
        if not opts_f:
            if not pool or set(pool) <= {f["uid"]}:
                dec[k] = ("refused", "no other regular enemy template in this zone (pool: %s)" % (
                    ", ".join(sorted({v["kind"] for v in pool.values()})) or "empty"))
            else:
                dec[k] = ("refused", "no compatible replacement: " + "; ".join("%s x%d" % kv for kv in why_not.most_common(3)))
            continue
        options[k] = opts_f
        f["_fam"] = fam
        f["_shared"] = shared
    # pins (confirmed in game) come first and must pass the same rules
    changes, chosen = [], {}
    pins = effective_pins(rec["zone_id"], getattr(opts, "verdict_map", {}) or {}, opts.no_pins)
    pin_report = []
    for key, uid, why in pins:
        o = next((x for x in options.get(key, []) if x["uid"] == uid), None)
        if o is None:
            pin_report.append((key, uid, "PIN REFUSED: " + dec.get(key, ("?", "replacement not among the options"))[1]))
            continue
        chosen[key] = o
        pin_report.append((key, uid, "kept (%s)" % why))
    # anchors: every replacement template keeps one unchanged native user
    changeable = set(options) - set(chosen)
    fixed_users = {uid: [k for k in ks if k not in options and k not in chosen] for uid, ks in users.items()}
    anchors = {}
    want = Counter()
    sole = Counter()
    for k, os_ in options.items():
        for o in os_:
            want[o["uid"]] += 1
        if len(os_) == 1:
            sole[os_[0]["uid"]] += 1
    needed = {o["uid"] for o in chosen.values()}
    for uid, candidate in pool.items():
        if candidate["external"]:
            continue
        if fixed_users.get(uid):
            anchors[uid] = fixed_users[uid][0]
            continue
        if uid not in needed and want[uid] < 2 and not sole[uid]:
            continue
        cands = [k for k in users[uid] if k in changeable]
        if not cands:
            continue
        a = min(cands, key=lambda k: (len(options[k]), k))
        anchors[uid] = a
        changeable.discard(a)
        dec[a] = ("anchor", "kept native: the last unchanged user of %s %s (a replacement elsewhere in this zone)" % (pool[uid]["kind"], uid))
    # pinned replacements need their anchor
    for key in list(chosen):
        if not chosen[key].get("external") and chosen[key]["uid"] not in anchors:
            pin_report.append((key, chosen[key]["uid"], "PIN DROPPED: no unchanged native user of its replacement"))
            del chosen[key]
    # assignment: seeded order, weighted choice (proven pairs 3x, kinds already used here count against)
    used = Counter(o["kind"] for o in chosen.values())
    order = sorted(changeable)
    rng.shuffle(order)
    for k in order:
        os_ = [o for o in options[k] if o.get("external") or o["uid"] in anchors]
        if not os_:
            dec[k] = ("refused", "every compatible replacement template lost its last native user (anchor)")
            continue
        if opts.rate < 1.0 and rng.random() >= opts.rate:
            dec[k] = ("kept", "--rate %.2f left this one native" % opts.rate)
            continue
        w = [(3.0 if o["pair_tier"] == "proven" else 1.0) / (1 + used[o["kind"]]) for o in os_]
        o = rng.choices(os_, weights=w, k=1)[0]
        chosen[k] = o
        used[o["kind"]] += 1
    # every chosen replacement must still have an unchanged user (anchor safety net)
    for k, o in list(chosen.items()):
        if not o.get("external") and anchors.get(o["uid"]) in chosen:
            del chosen[k]
            dec[k] = ("refused", "anchor conflict")
    fac_by_key = {f["key"]: f for f in facs}
    for k, o in chosen.items():
        f = fac_by_key[k]
        tier = ("shared-seen/" + o["spawn_tier"]) if f.get("_shared") == "seen" else "UNVERIFIED-shared" if f.get("_shared") else (
            "confirmed" if any(p[0] == k and p[1] == o["uid"] for p in pins) else
            ("proven" if o["pair_tier"] == "proven" else "kin") + "/" + o["spawn_tier"])
        changes.append({
            "zone": rec["zone"], "zone_id": rec["zone_id"], "planet": rec["planet"], "key": k, "action": f["action"],
            "plug": f["plug"], "var_index": f["sv"], "original_uid": f["uid"], "original_index": f["rec"],
            "original": f["kind"], "original_family": f["_fam"], "replacement_uid": o["uid"], "replacement_index": o["rec"],
            "replacement_external": bool(o.get("external")), "replacement_source_zone": o.get("source_zone"),
            "replacement_source_zone_id": o.get("source_zone_id"), "replacement_source_planet": o.get("source_planet"),
            "replacement": o["kind"], "replacement_family": o["family"], "pair_tier": o["pair_tier"],
            "pair_evidence": o["pair_evidence"], "spawn_tier": o["spawn_tier"], "spawn_points": o["spawn_points"],
            "count": f["count"], "tier": tier, "anchor": anchors.get(o["uid"]),
            "pair": "factory|%s/%s>%s/%s" % (f["kind"][:19], f["_fam"], o["kind"][:19], o["family"]),
        })
        dec[k] = ("changed", "%s -> %s [%s]" % (f["kind"], o["kind"], tier))
    for f in facs:
        dec.setdefault(f["key"], ("refused", "?"))
    changes.sort(key=lambda c: c["var_index"])
    return changes, dec, anchors, pin_report


# ======================================================================================================================
# outputs
# ======================================================================================================================
def lua_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def manifest_lua(m):
    L = ["-- generated by stage_allgame.py %s (%s). DATA, not a script to edit." % (VERSION, KIT),
         "-- It tells 18_rando_stage_enemies.lua which spawners the installed %s changed on disk." % STAGE_MOD_PATH,
         "-- Remove it together with mods/RandoEnemies.stage to turn the .stage Enemy Randomizer off.",
         "-- %d change(s) in %d zone(s) on %d planet(s)." % (len(m["changes"]), len(m["zones"]), len({z["planet"] for z in m["zones"]})),
         "RANDO_STAGE_ENEMIES = {",
         "  format = 1, tool = %s, kit = %s, label = %s, stage_lua = %s," % (lua_str(VERSION), lua_str(KIT), lua_str(m["label"]), lua_str(STAGE_LUA)),
         "  stage_file = %s, stage_sha256 = %s, seed = %s, zones_changed = %d," % (
             lua_str(STAGE_MOD_PATH), lua_str(m["stage_sha256"]), lua_str(m["seed"]), len(m["zones"])),
         "  changes = {"]
    for c in m["changes"]:
        L.append("    { zone = %s, zone_id = %s, planet = %s, section = %s, offset = %d, var_index = %d," % (
            lua_str(c["zone"]), lua_str(c["zone_id"]), lua_str(c["planet"]), lua_str("Zone Script Vars"), c["entry_rel"], c["var_index"]))
        L.append("      original_uid = %s, original_index = %d, original = %s, original_family = %s," % (
            lua_str(c["original_uid"]), c["original_index"], lua_str(c["original"]), lua_str(c["original_family"])))
        L.append("      replacement_uid = %s, replacement_index = %d, replacement = %s, replacement_family = %s," % (
            lua_str(c["replacement_uid"]), c["replacement_index"], lua_str(c["replacement"]), lua_str(c["replacement_family"])))
        L.append("      replacement_external = %s, replacement_source_planet = %s, replacement_source_zone = %s," % (
            "true" if c.get("replacement_external") else "false", lua_str(c.get("replacement_source_planet") or ""),
            lua_str(c.get("replacement_source_zone") or "")))
        L.append("      original_refs = %d, replacement_refs = %d, tier = %s," % (c["original_refs"], c["replacement_refs"], lua_str(c["tier"])))
        L.append("      pair = %s, spawner_keys = { %s } }," % (lua_str(c["pair"]), lua_str(c["key"])))
    L += ["  },", "}", ""]
    return "\n".join(L)


def write_inventory(S, decisions, out):
    rows = []
    for zh, rec in S.zones.items():
        for f in rec["factories"]:
            st, why = decisions.get(zh, {}).get(f["key"], ("not planned", rec["status"]))
            rows.append([rec["planet"], rec["zone"], zh, f["key"], f["kind"] or "-", f["count"], f["owners"],
                         "; ".join((l["kind"] or (l.get("resolved") or {}).get("kind") or l["form"]) for l in f["locs"]) or "-",
                         st, why])
    with open(os.path.join(out, "inventory.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["planet", "zone", "zone_id", "spawner", "original", "count", "owners", "spawn points", "decision", "reason"])
        w.writerows(rows)
    return rows


def write_template_inventory(S, out):
    """Separate forensic inventory for node Template adapters; this is diagnostic only, not a patch plan."""
    rows = []
    for zh, rec in S.zones.items():
        for n in rec.get("template_nodes", []):
            rows.append([rec["planet"], rec["zone"], zh, n["key"], n["class"], n["is_spawner_class"],
                         n["template_plug_count"], n["var_index"], n["form"], n["uid"], n["kind"] or "-",
                         n["asset"] or "-", n["owners"], ";".join(n["co_owner_classes"]),
                         n["other_plugs"], n["problem"] or rec["status"]])
    path = os.path.join(out, "template_adapter_inventory.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["planet", "zone", "zone_id", "node_key", "class_id", "is_SpawnerScriptAction",
                    "Template_plug_count", "var_index", "reference_form", "template_uid", "kind", "asset",
                    "owners", "co_owner_classes", "other_plugs", "problem"])
        w.writerows(rows)
    return rows


def coverage_report(S, rows, changes, pins, opts, source, brain, stage_info):
    L = []
    enemy_rows = [r for r in rows if r[8] != "not enemy"]
    changed = [r for r in rows if r[8] == "changed"]
    by_planet = defaultdict(lambda: Counter())
    for r in rows:
        by_planet[r[0]]["factories"] += 1
        if r[8] != "not enemy":
            by_planet[r[0]]["enemy"] += 1
        if r[8] == "changed":
            by_planet[r[0]]["changed"] += 1
    zones_dec = [z for z in S.zones.values() if z["status"] in ("ok", "no scripts", "no actors")]
    zones_fac = [z for z in S.zones.values() if z["factories"]]
    zones_chg = sorted({c["zone_id"] for c in changes})
    rep_kinds = Counter(c["replacement"] for c in changes)
    tiers = Counter(c["tier"].split("/")[0] for c in changes)
    stiers = Counter(c["spawn_tier"] for c in changes)
    L += ["# .stage Enemy Randomizer - all-planet build (stage_allgame %s, %s)" % (VERSION, KIT), "",
          "Seed `%s`. Source: %s. Reader: %s. Scan time %.0f s." % (
              opts.seed, ("game folder" if source.game else "zone files given on the command line"), LZ4, S.seconds), "",
          "## Totals", "",
          "| | |", "|---|---|",
          "| zone assets in the game's dag | %d |" % source.dag_zone_count,
          "| zones scanned / decoded | %d / %d |" % (len(S.zones), len(zones_dec)),
          "| zones not in the toc | %d |" % len(source.missing),
          "| zone status | %s |" % ", ".join("%s %d" % (k.split(":")[0], n) for k, n in Counter(z["status"].split(":")[0] for z in S.zones.values()).most_common()),
          "| zones that hold spawner factories | %d |" % len(zones_fac),
          "| spawner factories (all kinds) | %d |" % len(rows),
          "| of them enemy spawners | %d |" % len(enemy_rows),
          "| **changed** | **%d (%.0f%% of enemy spawners)** |" % (len(changed), 100.0 * len(changed) / max(1, len(enemy_rows))),
          "| zones changed | %d |" % len(zones_chg),
          "| planets with changes | %d |" % len({c["planet"] for c in changes}),
          "| replacement enemy kinds used | %d |" % len(rep_kinds),
          "| other spawner nodes (`Template` adapter, not handled) | %d |" % sum(z["node_template_spawners"] for z in S.zones.values()),
          "| exact `SpawnerScriptAction` class candidates | %d |" % sum(1 for z in S.zones.values() for n in z.get("template_nodes", []) if n["is_spawner_class"]),
          "| .stage size | %s |" % stage_info, ""]
    L += ["Change tiers: " + ", ".join("%s %d" % kv for kv in tiers.most_common()) + ".",
          "Spawn-point tiers: " + ", ".join("%s %d" % kv for kv in stiers.most_common()) + ".", "",
          "- **confirmed**: the exact replacement UID was observed spawning in supplied runtime verdict evidence (or in the bundled historical evidence); the latest observed result takes precedence.",
          "- **proven**: the pair has in-game evidence (built-in table, your logs, the .stage runs). NOT yet seen at this spawner.",
          "- **kin**: same faction and movement group, the kit's KILLABLE rule. Unverified in game.",
          "- spawn points: `volume` local volume; `clue-native` an anim clue the game itself uses for the replacement; "
          "`external-volume` another zone's non-clue actor; `clue-family` a clue of the same family; `external-unresolved` "
          "an actor no zone holds (2 of 2 worked in game).", ""]
    if pins:
        L += ["## The confirmed changes", ""] + ["- %s -> %s: %s" % p for p in pins] + [""]
    L += ["## By planet", "", "| planet | factories | enemy spawners | changed | % |", "|---|---:|---:|---:|---:|"]
    for p, c in sorted(by_planet.items(), key=lambda kv: -kv[1]["changed"]):
        L.append("| %s | %d | %d | %d | %.0f%% |" % (p, c["factories"], c["enemy"], c["changed"], 100.0 * c["changed"] / max(1, c["enemy"])))
    L += ["", "## By zone (zones with enemy spawners)", "", "| planet | zone | enemy spawners | changed | swaps |", "|---|---|---:|---:|---|"]
    by_zone = defaultdict(list)
    for c in changes:
        by_zone[c["zone_id"]].append(c)
    for z in zones_fac:
        ens = [r for r in rows if r[2] == z["zone_id"] and r[8] != "not enemy"]
        if not ens:
            continue
        sw = Counter("%s->%s" % (c["original"].replace("enm_", ""), c["replacement"].replace("enm_", "")) for c in by_zone[z["zone_id"]])
        L.append("| %s | %s | %d | %d | %s |" % (z["planet"], z["zone"].replace("\\", "/").split("/")[-1], len(ens),
                                                 len(by_zone[z["zone_id"]]), ", ".join("%s x%d" % kv for kv in sw.most_common(6)) or "-"))
    L += ["", "## Replacement kinds", ""] + ["- %s: %d spawner(s)" % kv for kv in rep_kinds.most_common()]
    L += ["", "## Why enemy spawners were not changed", "", "| reason | spawners |", "|---|---:|"]
    why = Counter()
    for r in enemy_rows:
        if r[8] != "changed":
            why[re.sub(r"[0-9A-F]{16}", "<uid>", re.sub(r"SV #\d+", "SV", r[9]))[:150]] += 1
    for w, n in why.most_common(40):
        L.append("| %s | %d |" % (w.replace("|", "/"), n))
    if S.errors or source.missing:
        L += ["", "## Zones that could not be read", ""]
        L += ["- %s: %s" % e for e in S.errors[:200]]
        L += ["- %s: in the dag but not in the toc" % m for m in source.missing[:200]]
    L += ["", "## Knowledge used", ""] + ["- " + n for n in brain.notes[:12]]
    L += ["- learned anim-clue hosts: %d clues, %d clue families" % (len(S.clue_hosts), len(S.clue_family_hosts)),
          "- external spawn points: %d, resolved %d, unresolved %d, ambiguous %d" % (
              len(S.resolved), sum(1 for v in S.resolved.values() if v[2] not in ("unresolved", "ambiguous")),
              sum(1 for v in S.resolved.values() if v[2] == "unresolved"), sum(1 for v in S.resolved.values() if v[2] == "ambiguous"))]
    fams = Counter(v[1].split(" (")[0] for v in brain._fam.values())
    L += ["- enemy-kind family sources: " + ", ".join("%s %d" % kv for kv in fams.most_common())]
    return "\n".join(L) + "\n"


class StageWriter:
    """A .stage written one zone at a time (hundreds of zones never sit in memory together). Same layout as
    rcra.write_stage (tool 1.1.0): info.json first, then "<span>/<ASSET ID>" members = 36-byte header + zone, deflate,
    fixed timestamp, members in (span, asset id) order, so the same input gives byte-identical output."""

    def __init__(self, path, description):
        self.path, self.tmp = path, path + ".tmp"
        self.z = zipfile.ZipFile(self.tmp, "w", compression=zipfile.ZIP_DEFLATED)
        info = {"name": "Rift Apart Randomizer - all-planet Enemy .stage (%s, stage_allgame %s)" % (KIT, VERSION),
                "author": "Rift Apart Randomizer", "game": rcra.STAGE_GAME_ID, "description": description}
        self._add("info.json", json.dumps(info, indent=2, sort_keys=True).encode("utf-8"))
        self.last = None

    def _add(self, name, data):
        zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        self.z.writestr(zi, data)

    def add(self, span, zid, header, raw):
        if span % 8 != 0:
            raise Refused("only span 0 (built, no language) assets are written, not span %d" % span)
        if len(header) != HEADER:
            raise Refused("asset %s: header is %d bytes, 36 needed" % (hex16(zid), len(header)))
        if self.last is not None and (span, zid) <= self.last:
            raise Refused("members out of order")
        self.last = (span, zid)
        self._add("%d/%s" % (span, hex16(zid)), header + raw)

    def close(self):
        self.z.close()
        os.replace(self.tmp, self.path)


# ======================================================================================================================
# commands
# ======================================================================================================================
def default_scripts(game):
    for d in ([os.path.join(game, "scripts")] if game else []) + [os.path.join(HERE, "..", "..", "scripts")]:
        if os.path.isfile(os.path.join(d, "16_rando_spawners.lua")):
            return os.path.abspath(d)
    return None


def run_plan(a, build):
    if os.path.basename(os.path.normpath(a.out)).upper() == "AUTO":          # BUILD_ALL_PLANETS.bat: builds\AUTO
        base = os.path.dirname(os.path.normpath(a.out)) or "."
        a.out = os.path.join(base, ("build-" if build else "scan-") + time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, "LAST_BUILD.txt" if build else "LAST_SCAN.txt"), "w") as fh:
            fh.write(os.path.abspath(a.out))
    if os.path.exists(a.out) and os.listdir(a.out):
        raise Refused("%s exists and is not empty: never overwrite a build" % a.out)
    logs = list(a.log or [])
    if a.game and os.path.isfile(os.path.join(a.game, "rivet.log")) and not a.no_game_log:
        logs.append(os.path.join(a.game, "rivet.log"))
    src = Source(a.game, a.zone_file or [], a.planet or [], a.limit)
    if not src.items:
        raise Refused("no zone to scan")
    print("stage_allgame %s: %d zone(s) to scan (%s)" % (VERSION, len(src.items), LZ4))
    brain = Brain(a.scripts or default_scripts(a.game), logs, src, not a.no_actor_family)
    a.verdict_map = {}
    ev_dir = os.path.join(HERE, "evidence")
    bundled = sorted(os.path.join(ev_dir, f) for f in os.listdir(ev_dir) if f.endswith(".json")) if os.path.isdir(ev_dir) else []
    if bundled and not a.no_evidence:
        print("bundled in-game evidence: %s" % ", ".join(os.path.basename(f) for f in bundled))
    for vf in (bundled if not a.no_evidence else []) + list(a.verdicts or []):
        vj = json.load(open(vf))
        for key, v in vj.get("verdicts", {}).items():
            zid = hex16(rcra.crc64_path(v["zone"])) if v.get("zone") not in (None, "?") else None
            if zid:
                bucket = a.verdict_map.setdefault(zid, {})
                incoming = (v["verdict"], v.get("replacement_uid"))
                bucket[key.upper()] = merge_verdict_entry(bucket.get(key.upper()), incoming)
    if a.verdict_map:
        print("verdicts: %s" % ", ".join("%s %d" % kv for kv in Counter(v[0] for z in a.verdict_map.values() for v in z.values()).items()))
    S = scan(src, keep_zone=lambda zh: build)
    # learn co-owner classes from in-game verdicts of SHARED-variable spawners (e.g. a --profile all session)
    a.coowner_learned, a.coowner_bad_learned = {}, {}
    for zh, vm in a.verdict_map.items():
        rec = S.zones.get(zh)
        if not rec:
            continue
        for f in rec["factories"]:
            vd = vm.get(f["key"])
            if not vd or f["owners"] < 2:
                continue
            if vd[0] == "WORKED":
                for c in f["co_owner_classes"]:
                    a.coowner_learned[c] = "%s WORKED in your game (%s)" % (f["key"], rec["planet"])
            elif vd[0] == "ORIGINAL SPAWNED" and all(l["form"] == "local" and not (l["kind"] or "").startswith("animclue_")
                                                      for l in f["locs"]):
                for c in f["co_owner_classes"]:
                    a.coowner_bad_learned[c.split("/")[0]] = "%s kept its original at volume spawn points (%s)" % (f["key"], rec["planet"])
    if a.coowner_learned or a.coowner_bad_learned:
        print("learned from your verdicts: %d co-owner class/plug pair(s) seen working, %d class(es) seen failing" % (
            len(a.coowner_learned), len(a.coowner_bad_learned)))
    print("scan done: %d zones, %d with factories, %d factories, %d errors" % (
        len(S.zones), sum(1 for z in S.zones.values() if z["factories"]), sum(len(z["factories"]) for z in S.zones.values()), len(S.errors)))
    profiles = [(a.profile, a.out)]
    if build and not a.no_safe and a.profile != "safe":
        profiles.append(("safe", os.path.join(a.out, "safe")))
    rc = 0
    for prof, out in profiles:
        a.profile = prof
        print("\n==== profile %s -> %s" % (prof, out))
        rc = emit(a, S, src, brain, build, out) or rc
    src.close()
    return rc


def emit(a, S, src, brain, build, out):
    import copy
    changes, decisions, pins = [], {}, []
    zrecs, planned = {}, []
    for zh, rec0 in S.zones.items():
        if not rec0["factories"]:
            continue
        rec = copy.deepcopy(rec0)
        zrecs[zh] = rec
        rng = random.Random("%s|%s" % (a.seed, zh))
        ch, dec, anchors, pin_report = plan_zone(S, brain, rec, a, rng)
        decisions[zh] = dec
        pins += pin_report
        if ch:
            planned.append((rec["span"], int(zh, 16), zh, ch))
    os.makedirs(out, exist_ok=True)
    members = []
    stage = os.path.join(out, "RandoEnemies.stage")
    writer = StageWriter(stage, "All-planet enemy swap, profile %s, seed %s (stage_allgame %s)" % (a.profile, a.seed, VERSION)) \
        if build and planned else None
    for span, zid, zh, ch in sorted(planned):
        rec = zrecs[zh]
        if not build:
            changes += ch
            continue
        header, raw = S.kept[zh]()
        why = None
        if hashlib.sha256(raw).hexdigest() != rec["sha256"]:
            why = "the zone read differently the second time (file changed during the build?)"
        elif header is None:
            why = "zone has no 36-byte toc header: cannot be written to a .stage"
        if why:
            for c in ch:
                decisions[zh][c["key"]] = ("refused", why)
            continue
        z0 = Zone(header, raw, rec["zone"])
        n0, bad0 = z0.c1()
        if bad0:
            for c in ch:
                decisions[zh][c["key"]] = ("refused", "the game's own zone fails C1: the zone is left alone")
            continue
        for c in ch:
            c["entry_abs"] = z0.var_base + VAR_SIZE * c["var_index"]
            c["entry_rel"] = c["entry_abs"] - z0.secs[SEC_SCRIPT_VARS][0]
        new = apply_changes(raw, ch)
        z1 = Zone(header, new, rec["zone"])
        problems, diff, n1 = compare(z0, z1, ch)
        chk = {c["key"] for c in ch}
        users_after = {hex16(z1.vars[f["sv"]][5]) for f in z1.factories() if f["form"] == "local" and f["key"] not in chk}
        for c in ch:
            if not c.get("replacement_external") and c["replacement_uid"] not in users_after:
                problems.append("%s: replacement %s has no unchanged native user after the patch" % (c["key"], c["replacement_uid"]))
        if problems:
            for c in ch:
                decisions[zh][c["key"]] = ("refused", "zone validation failed: " + "; ".join(problems)[:200])
            print("ZONE REFUSED %s: %s" % (rec["zone"], "; ".join(problems)))
            continue

        def refs(zz, uid):
            return sum(1 for v in zz.vars if v[0] == 5 and hex16(v[5]) == uid)
        for c in ch:
            c["original_refs"] = refs(z1, c["original_uid"]) + 1          # 18 prints original_refs - 1 as "expected"
            c["replacement_refs"] = refs(z1, c["replacement_uid"]) - 1
            c["changed_bytes"] = len([i for i in diff if c["entry_abs"] <= i < c["entry_abs"] + VAR_SIZE])
        rec["sha256_patched"] = hashlib.sha256(new).hexdigest()
        rec["changes"] = len(ch)
        writer.add(span, zid, header, new)
        members.append((span, zid))
        changes += ch
    stage_info = "-"
    if writer:
        writer.close()
        if not members:
            os.remove(stage)
    if build and changes:
        ssha = hashlib.sha256(open(stage, "rb").read()).hexdigest()
        stage_info = "%.1f MB on disk, %d zone members" % (os.path.getsize(stage) / 1e6, len(members))
        zones = [{"zone": zrecs[hex16(zid)]["zone"], "zone_id": hex16(zid), "planet": zrecs[hex16(zid)]["planet"],
                  "span": span, "sha256_original": zrecs[hex16(zid)]["sha256"], "sha256_patched": zrecs[hex16(zid)]["sha256_patched"],
                  "changes": zrecs[hex16(zid)]["changes"]} for span, zid in members]
        m = {"format": 1, "tool": VERSION, "kit": KIT, "stage_lua": STAGE_LUA, "seed": a.seed, "profile": a.profile,
             "label": ("V2.1.0 FORCE ALL ENEMIES - EXPERIMENTAL; classifiable enemy factories use global foreign templates" if getattr(a, "force_all_enemies", False) else "all-planet build, profile %s (uid + index, spawn-point rule, KILLABLE pairs)" % a.profile), "stage_sha256": ssha,
             "settings": {"profile": a.profile, "strict_external": a.strict_external, "rate": a.rate,
                          "planets": a.planet or "all", "actor_family": not a.no_actor_family,
                          "cross_planet": bool(getattr(a, "cross_planet", False) or getattr(a, "force_all_enemies", False)),
                          "force_all_enemies": bool(getattr(a, "force_all_enemies", False))},
             "zones": zones, "changes": changes, "pins": [{"key": k, "replacement": u, "result": w} for k, u, w in pins]}
        with open(os.path.join(out, "stage_enemies_manifest.json"), "w") as fh:
            json.dump(m, fh, indent=1)
        with open(os.path.join(out, MANIFEST_LUA), "w", encoding="utf-8") as fh:
            fh.write(manifest_lua(m))
        with open(os.path.join(out, "changes.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["planet", "zone", "spawner", "original", "replacement", "count", "tier", "pair evidence",
                        "spawn points", "replacement external", "replacement source planet", "replacement source zone"])
            for c in changes:
                w.writerow([c["planet"], c["zone"], c["key"], c["original"], c["replacement"], c["count"], c["tier"],
                            c["pair_evidence"], c["spawn_points"], bool(c.get("replacement_external")),
                            c.get("replacement_source_planet") or "", c.get("replacement_source_zone") or ""])
    rows = write_inventory(S, decisions, out)
    template_rows = write_template_inventory(S, out)
    print("  Template-adapter census: %d plug records; %d exact SpawnerScriptAction nodes (diagnostic only)" % (len(template_rows), sum(1 for z in S.zones.values() for n in z.get("template_nodes", []) if n["is_spawner_class"])))
    lua18 = next((x for x in (os.path.join(HERE, "..", "..", "scripts", STAGE_LUA_FILE), os.path.join(HERE, STAGE_LUA_FILE))
                  if os.path.isfile(x)), "")
    if build and changes and lua18:
        shutil.copy2(lua18, os.path.join(out, STAGE_LUA_FILE))
    rep = coverage_report(S, rows, changes, pins, a, src, brain, stage_info)
    with open(os.path.join(out, "COVERAGE_REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write(rep)
    inv = {"tool": VERSION, "profile": a.profile, "zones": list(S.zones.values()),
           "clue_hosts": {k: sorted(v) for k, v in S.clue_hosts.items()},
           "external": {hex16(u): {"kind": v[0], "zone": S.zones[v[1]]["zone"] if v[1] else None, "how": v[2]} for u, v in S.resolved.items()}}
    with open(os.path.join(out, "inventory.json"), "w") as fh:
        json.dump(inv, fh, indent=0, default=list)
    print(rep.split("## By planet")[0])
    for k, u, w in pins:
        print("PIN %s -> %s: %s" % (k, u, w))
    if build and not changes:
        raise Refused("no spawner passed every rule: nothing to build (see COVERAGE_REPORT.md)")
    if build:
        if check_build(out, src_args=a, verbose=False):
            raise Refused("the new build fails its own check")
        print("written: %s" % ", ".join(sorted(os.listdir(out))))
    return 0


def cmd_scan(a):
    return run_plan(a, build=False)


def cmd_build(a):
    return run_plan(a, build=True)


def check_build(out, src_args, verbose=True):
    """re-reads the .stage, compares every member with the game's own zone and the manifest"""
    m = json.load(open(os.path.join(out, "stage_enemies_manifest.json")))
    stage = os.path.join(out, "RandoEnemies.stage")
    zf = zipfile.ZipFile(stage)
    problems = []
    if zf.testzip():
        problems.append(".stage: a corrupt member")
    info = json.loads(zf.read("info.json").decode("utf-8"))
    names = {n for n in zf.namelist() if n != "info.json" and not n.endswith("/")}
    if hashlib.sha256(open(stage, "rb").read()).hexdigest() != m["stage_sha256"]:
        problems.append("stage sha256 differs from the manifest")
    if info.get("game") != "RCRA":
        problems.append("info.json game is not RCRA")
    lua = open(os.path.join(out, MANIFEST_LUA), encoding="utf-8").read()
    if lua.count("spawner_keys") != len(m["changes"]):
        problems.append("the Lua manifest has %d changes, the JSON %d" % (lua.count("spawner_keys"), len(m["changes"])))
    seen = set()
    for c in m["changes"]:
        k = (c["zone_id"], c["var_index"])
        if k in seen:
            problems.append("two changes on %s SV #%d" % k)
        seen.add(k)
    keys = Counter((c["zone_id"], c["key"]) for c in m["changes"])
    problems += ["spawner %s changed twice" % k[1] for k, n in keys.items() if n > 1]
    src = Source(getattr(src_args, "game", None), getattr(src_args, "zone_file", None) or [], [], 0)
    orig = {hex16(zid): load for _, zid, _, load in src.items}
    external_source_cache = {}
    by_zone = defaultdict(list)
    for c in m["changes"]:
        by_zone[c["zone_id"]].append(c)
    if len(names) != len(m["zones"]):
        problems.append("%d members in the .stage, %d zones in the manifest" % (len(names), len(m["zones"])))
    total = 0
    for zrec in m["zones"]:
        zh = zrec["zone_id"]
        name = "%d/%s" % (zrec["span"], zh)
        if name not in names:
            problems.append("member %s missing" % name)
            continue
        blob = zf.read(name)
        if zh not in orig:
            problems.append("%s: the original zone is not available to compare" % zrec["zone"])
            continue
        h0, r0 = orig[zh]()
        if hashlib.sha256(r0).hexdigest() != zrec["sha256_original"]:
            problems.append("%s: the game's zone changed since the build (game update?): rebuild" % zrec["zone"])
            continue
        z0 = Zone(h0, r0, zrec["zone"])
        if blob[:HEADER] != h0:
            problems.append("%s: header differs from the game's" % zrec["zone"])
        z1 = Zone(blob[:HEADER], blob[HEADER:], zrec["zone"])
        if hashlib.sha256(z1.raw).hexdigest() != zrec["sha256_patched"]:
            problems.append("%s: patched sha256 differs from the manifest" % zrec["zone"])
        ch = by_zone[zh]
        pr, diff, n1 = compare(z0, z1, ch)
        problems += ["%s: %s" % (zrec["zone"], p) for p in pr]
        facs = {f["key"]: f for f in z0.factories()}
        changed_keys = {c["key"] for c in ch}
        after_users = {hex16(z1.vars[f["sv"]][5]) for k, f in facs.items() if f["form"] == "local" and k not in changed_keys}
        for c in ch:
            f = facs.get(c["key"])
            if not f or f["sv"] != c["var_index"]:
                problems.append("%s %s: not the factory that owns SV #%d" % (zrec["zone"], c["key"], c["var_index"]))
                continue
            if f["owners"] != 1 and not c["tier"].startswith(("UNVERIFIED", "shared-seen", "FORCED-UNVERIFIED")):
                problems.append("%s %s: shared Templates variable" % (zrec["zone"], c["key"]))
            if f["uid"] != c["original_uid"]:
                problems.append("%s %s: original kind does not match the zone" % (zrec["zone"], c["key"]))
            elif c.get("replacement_external"):
                if c["replacement_index"] != 0xFFFF or c["replacement_uid"] in z0.rec_of:
                    problems.append("%s %s: malformed external replacement reference" % (zrec["zone"], c["key"]))
                else:
                    src_id = c.get("replacement_source_zone_id")
                    if not src_id or src_id not in orig:
                        problems.append("%s %s: external source zone is absent from this game scan" % (zrec["zone"], c["key"]))
                    else:
                        if src_id not in external_source_cache:
                            sh, sr = orig[src_id]()
                            external_source_cache[src_id] = Zone(sh, sr, c.get("replacement_source_zone") or src_id)
                        source_zone = external_source_cache[src_id]
                        source_rec = source_zone.rec_of.get(int(c["replacement_uid"], 16))
                        if source_rec is None or source_zone.kind_of_rec(source_rec) != c["replacement"]:
                            problems.append("%s %s: foreign template UID/kind is not present in its recorded source zone" %
                                             (zrec["zone"], c["key"]))
            elif z0.kind_of_rec(c["replacement_index"]) != c["replacement"]:
                problems.append("%s %s: replacement kind does not match the zone" % (zrec["zone"], c["key"]))
            if not c.get("replacement_external") and c["replacement_uid"] not in after_users:
                problems.append("%s %s: replacement has no unchanged native user" % (zrec["zone"], c["key"]))
            if not c["tier"].startswith(("FORCED-UNVERIFIED", "FORCED-TEST")):
                if not any(l["form"] in ("local", "external") for l in f["locs"]) or any(l["form"] not in ("local", "external") for l in f["locs"]):
                    problems.append("%s %s: spawn points not decodable" % (zrec["zone"], c["key"]))
                for l in f["locs"]:
                    if l["form"] == "local" and l["kind"].startswith("animclue_") and c["spawn_tier"] not in ("clue-native", "clue-family", "external-unresolved", "external-volume"):
                        problems.append("%s %s: anim clue spawn point not covered by the tier" % (zrec["zone"], c["key"]))
        total += len(ch)
    src.close()
    zf.close()
    print("CHECK %s: %d change(s) in %d zone member(s) re-read and compared with the game's zones: %s" % (
        stage, total, len(names), "PASS" if not problems else "FAIL"))
    for p in problems[:50]:
        print("  " + p)
    return 0 if not problems else 1


def cmd_check(a):
    return check_build(a.build, a)


# ---- install / uninstall (the only commands that write to the game folder) ------------------------------------------
INSTALL_FILES = [("RandoEnemies.stage", "mods/RandoEnemies.stage"), (MANIFEST_LUA, "scripts/" + MANIFEST_LUA),
                 (STAGE_LUA_FILE, "scripts/" + STAGE_LUA_FILE)]


def cmd_install(a):
    game = a.game
    if not os.path.isfile(os.path.join(game, "RiftApart.exe")):
        raise Refused("no RiftApart.exe in %s" % game)
    toml = os.path.join(game, "rivet.toml")
    if not os.path.isfile(toml) or "RandoEnemies.stage" not in open(toml, encoding="utf-8", errors="replace").read():
        raise Refused("rivet.toml does not list mods/RandoEnemies.stage under [assets] paths: install the .stage once with "
                      "stage_enemies.py install (tool 1.1.0) or add it by hand")
    if check_build(a.build, a):
        raise Refused("the build does not pass its check against this game folder: nothing installed")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir = os.path.join(game, "rando_stage_backup", stamp)
    os.makedirs(bdir, exist_ok=False)
    for src_name, dst_rel in INSTALL_FILES:
        src_p = os.path.join(a.build, src_name)
        if not os.path.isfile(src_p):
            if src_name == STAGE_LUA_FILE:
                continue
            raise Refused("%s missing from the build" % src_name)
        dst = os.path.join(game, *dst_rel.split("/"))
        if os.path.isfile(dst):
            os.makedirs(os.path.join(bdir, os.path.dirname(dst_rel)), exist_ok=True)
            shutil.copy2(dst, os.path.join(bdir, *dst_rel.split("/")))
    for src_name, dst_rel in INSTALL_FILES:
        src_p = os.path.join(a.build, src_name)
        if os.path.isfile(src_p):
            shutil.copy2(src_p, os.path.join(game, *dst_rel.split("/")))
            print("installed %s" % dst_rel)
    print("backup of the files it replaced: %s" % bdir)
    return 0


def cmd_uninstall(a):
    root = os.path.join(a.game, "rando_stage_backup")
    if not os.path.isdir(root) or not os.listdir(root):
        raise Refused("no backup in %s" % root)
    last = os.path.join(root, sorted(os.listdir(root))[-1])
    for _, dst_rel in INSTALL_FILES:
        b = os.path.join(last, *dst_rel.split("/"))
        dst = os.path.join(a.game, *dst_rel.split("/"))
        if os.path.isfile(b):
            shutil.copy2(b, dst)
            print("restored %s" % dst_rel)
    print("restored from %s (the backup folder is kept)" % last)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, out=True):
        p.add_argument("--game")
        p.add_argument("--zone-file", action="append", help='offline: "levels\\...\\x.zone=FILE" (repeatable)')
        if out:
            p.add_argument("--out", required=True)
            p.add_argument("--seed", default="allgame-1")
            p.add_argument("--planet", action="append", help="only zones whose path contains this (repeatable)")
            p.add_argument("--limit", type=int, default=0, help="scan only the first N zones (testing)")
            p.add_argument("--scripts", help="folder with 16_rando_spawners.lua (default: GAME/scripts, then the kit's)")
            p.add_argument("--log", action="append", help="extra rivet.log files for the knowledge (repeatable)")
            p.add_argument("--no-game-log", action="store_true", help="do not read GAME/rivet.log")
            p.add_argument("--profile", choices=PROFILES, default="max",
                           help="max (default): single-owner spawners + shared ones whose co-owners were all seen in a runtime "
                                "success; safe: single-owner only; all: every shared variable too (UNVERIFIED)")
            p.add_argument("--no-safe", action="store_true", help="build: do not also write the safe/ fallback build")
            p.add_argument("--strict-external", action="store_true", help="refuse external spawn points no zone holds")
            p.add_argument("--no-actor-family", action="store_true", help="never infer a family from the actor file")
            p.add_argument("--cross-planet", action="store_true",
                           help="EXPERIMENTAL: use globally unique enemy template UIDs from other zones via external actor refs")
            p.add_argument("--force-all-enemies", action="store_true",
                           help="EXPERIMENTAL MAXIMUM: force every classifiable enemy SunsetSpawnerFactory to a globally unique foreign enemy template; bypasses faction/spawn-clue/shared-owner safety rules and requires in-game testing")
            p.add_argument("--no-pins", action="store_true", help="do not force the 4 changes confirmed in game")
            p.add_argument("--verdicts", action="append", help="stage_check_log.py --json file(s): WORKED kept as confirmed, "
                                                                "ORIGINAL SPAWNED / NO SPAWN left native (repeatable)")
            p.add_argument("--no-evidence", action="store_true", help="do not read the bundled evidence/*.json verdicts")
            p.add_argument("--rate", type=float, default=1.0, help="share of eligible spawners to change (default 1.0 = all)")
    for name in ("scan", "build"):
        common(sub.add_parser(name))
    c = sub.add_parser("check")
    common(c, out=False)
    c.add_argument("--build", required=True)
    i = sub.add_parser("install")
    i.add_argument("--game", required=True)
    i.add_argument("--build", required=True)
    i.add_argument("--zone-file", action="append")
    u = sub.add_parser("uninstall")
    u.add_argument("--game", required=True)
    a = ap.parse_args(argv)
    if a.cmd in ("scan", "build", "check") and not (a.game or a.zone_file):
        ap.error("--game or --zone-file is needed")
    try:
        return {"scan": cmd_scan, "build": cmd_build, "check": cmd_check, "install": cmd_install,
                "uninstall": cmd_uninstall}[a.cmd](a) or 0
    except (Refused, rcra.FormatError) as e:
        print("REFUSED:", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())