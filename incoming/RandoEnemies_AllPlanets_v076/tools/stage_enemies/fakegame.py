"""fakegame.py - a tiny SYNTHETIC game folder (toc, dag, one DSAR archive) written to the documented formats.

Used only by the self-test to run probe -> poc -> verify -> install -> uninstall end to end without the real game.
It proves the tool is consistent with the format documents (Overstrike / rivet / Ripped Apart); it does NOT prove the
real game's zones look like this - only the probe on your game files can show that.
"""
from __future__ import annotations

import os
import struct
from typing import Dict, List, Tuple

import rcra


def dat1(type_id: int, sections: List[Tuple[int, bytes]], strings: bytes = b"") -> bytes:
    n = len(sections)
    head = 16 + 12 * n
    pos = head + len(strings)
    table, body, offs = [], bytearray(), []
    for tag, data in sections:
        pos += (-pos) % 16
        offs.append(pos)
        pos += len(data)
    out = bytearray(struct.pack("<IIIHH", rcra.DAT1_MAGIC, type_id, pos, n, 0))
    for (tag, data), o in zip(sections, offs):
        out += struct.pack("<III", tag, o, len(data))
    out += strings
    for (tag, data), o in zip(sections, offs):
        out += bytes(o - len(out))
        out += data
    return bytes(out)


def lz4_literals(data: bytes) -> bytes:
    """A valid LZ4 block holding only literals (the format allows it)."""
    n = len(data)
    if n < 15:
        return bytes([n << 4]) + data
    out = bytearray([0xF0])
    r = n - 15
    while r >= 255:
        out.append(255)
        r -= 255
    out.append(r)
    return bytes(out) + data


def dsar(payload: bytes, chunk: int = 1000) -> bytes:
    chunks = [payload[i:i + chunk] for i in range(0, len(payload), chunk)]
    comp = [lz4_literals(c) for c in chunks]
    first = 32 + 32 * len(chunks)
    out = bytearray(struct.pack("<IHHIIQQ", rcra.DSAR_MAGIC, 3, 1, len(chunks), first, len(payload), 0))
    pos, real = first, 0
    for c, cc in zip(chunks, comp):
        out += struct.pack("<QQIIB7s", real, pos, len(c), len(cc), 3, b"\x55" * 7)
        pos += len(cc)
        real += len(c)
    for cc in comp:
        out += cc
    return bytes(out)


def build(root: str, zones: Dict[str, bytes]) -> Dict[str, int]:
    """zones: path -> raw zone bytes (DAT1 at 0). Writes root/toc, root/dag, root/d/fake.archive. Returns ids."""
    os.makedirs(os.path.join(root, "d"), exist_ok=True)
    items = sorted((rcra.crc64_path(p), p, raw) for p, raw in zones.items())
    payload, sizes, headers = bytearray(), bytearray(), bytearray()
    for k, (aid, p, raw) in enumerate(items):
        off = len(payload)
        payload += raw
        sizes += struct.pack("<IIIi", len(raw), 0, off, len(headers))
        headers += struct.pack("<I8I", 0x5A0E5A0E, len(raw), 0, 0, 0, 0, 0, 0, 0)
    with open(os.path.join(root, "d", "fake.archive"), "wb") as f:
        f.write(dsar(bytes(payload)))
    spans = [(0, len(items))] + [(len(items), 0)] * 255
    archives = b"d\\fake.archive".ljust(40, b"\0") + struct.pack("<QQIHI", 0, 0, 0, 0, 0)
    toc_dat = dat1(0x51B8E006, [
        (rcra.TOC_ASSET_IDS, struct.pack("<%dQ" % len(items), *[i[0] for i in items])),
        (rcra.TOC_SPANS, b"".join(struct.pack("<II", a, b) for a, b in spans)),
        (rcra.TOC_SIZES, bytes(sizes)),
        (rcra.TOC_ARCHIVES, archives),
        (rcra.TOC_HEADERS, bytes(headers)),
    ])
    with open(os.path.join(root, "toc"), "wb") as f:
        f.write(struct.pack("<II", rcra.TOC_MAGIC, len(toc_dat) + 8) + toc_dat)
    # dag: names as cstrings after the section table
    names = [i[1] for i in items]
    n = len(names)
    strings = bytearray()
    head = 16 + 12 * 5
    offs = []
    for nm in names:
        offs.append(head + len(strings))
        strings += nm.encode() + b"\0"
    dag_dat = dat1(0x2A077A51, [
        (rcra.DAG_ASSET_IDS, bytes(8 * n)),
        (rcra.DAG_NAMES, struct.pack("<%dI" % n, *offs)),
        (rcra.DAG_TYPES, bytes([1] * n)),
        (rcra.DAG_LINKS, struct.pack("<i", -1)),
        (rcra.DAG_HEADS, struct.pack("<%di" % n, *([0] * n))),
    ], bytes(strings))
    with open(os.path.join(root, "dag"), "wb") as f:
        f.write(struct.pack("<III", 0xB8EF3955, len(dag_dat) + 12, 0) + dag_dat)
    return {p: aid for aid, p, _ in items}


# ----------------------------------------------------------------------------------------------------------------------
# stage tool 1.1.0: a SYNTHETIC zone with the real table layouts (zone.py): actor-asset table, Zone Actor Names,
# Zone Actors, Script Vars, Script Plugs, Script Actions (+ Zone Asset References for the probe's actor ids)
# ----------------------------------------------------------------------------------------------------------------------
def zone(assets: List[str], actors: List[Tuple[int, int, str]], vars_: List[dict], actions: List[Tuple[int, int, List[Tuple]]],
         refs: List[str] = (), extra: List[Tuple[int, bytes]] = ()) -> bytes:
    """assets: actor asset paths. actors: (uid, asset index, actor name). vars_: {type, aux, index, aux2, name, value}
    (missing keys: type 5, FFFF, FFFF, FFFF, 0, 0). actions: (key, class, [(plug name str|int, var index, kind), ...]),
    each action's plugs in its "a" range. The DAT1 string region holds the asset paths and actor names."""
    tags = [0x30DADA09, 0xDC625B3D, rcra.ZONE_ACTOR_ASSET_TABLE, 0x70682CB8, 0xD86A7934, 0xBEAB52E7, 0x5E54ACCF] + [t for t, _ in extra]
    head = 16 + 12 * len(tags)
    strings = bytearray()
    off = {}
    for s_ in list(assets) + [a[2] for a in actors]:
        if s_ not in off:
            off[s_] = head + len(strings)
            strings += s_.encode() + b"\0"
    aa = struct.pack("<%dQ" % len(assets), *[rcra.crc64_path(p) for p in assets]) + struct.pack("<%dI" % len(assets), *[off[p] for p in assets])
    names = [a[2] for a in actors]
    an = struct.pack("<%dI" % len(names), *[off[n] for n in names])
    za = b"".join(struct.pack("<IIIIIIQ", i, ai, 0x7C0 + 0x140 * i, 0xFFFFFFFF, 0, 0xC, uid) for i, (uid, ai, _) in enumerate(actors))
    sv = b"".join(struct.pack("<HHHHQQQ", v.get("type", 5), v.get("aux", 0xFFFF), v.get("index", 0xFFFF), v.get("aux2", 0xFFFF),
                              v.get("name", 0), v.get("value", 0), v.get("tail", 0)) for v in vars_)
    pl, sa = bytearray(), bytearray()
    n = 0
    for key, cls, plugs in actions:
        first = n if plugs else 0xFFFF
        for nm, vi, kind in plugs:
            h = rcra.crc32_engine(nm) if isinstance(nm, str) else nm
            pl += struct.pack("<III", h, vi, kind)
            n += 1
        sa += struct.pack("<QQHHHHHHIII", key, key, 1, 0xFFFF, 0, first, len(plugs), 0, cls, 0, 0)
    ar = b"".join(struct.pack("<Q", rcra.crc64_path(p)) for p in refs)
    secs = [(0x30DADA09, ar), (0xDC625B3D, an), (rcra.ZONE_ACTOR_ASSET_TABLE, aa), (0x70682CB8, za), (0xD86A7934, sv),
            (0xBEAB52E7, bytes(pl)), (0x5E54ACCF, bytes(sa))] + list(extra)
    return dat1(0x1F390AA0, secs, bytes(strings))


def spawner_zone(templates: List[Tuple[str, str, str]], spawners: List[Tuple[int, str]], shared: List[Tuple[int, int, str]] = (),
                 refs: List[str] = ()) -> bytes:
    """templates: (uid hex, .actor path, actor name). spawners: (factory key, template uid hex): one Templates variable
    each, its only plug. shared: (key, another key, template uid hex): ONE variable with a Templates plug on `key` and
    a second plug on the other node (a shared variable, never patched)."""
    assets = sorted({p for _, p, _ in templates})
    actors = [(int(u, 16), assets.index(p), n) for u, p, n in templates]
    rec = {int(u, 16): i for i, (u, _, _) in enumerate(templates)}
    vars_, actions = [], []
    kind = 0x93BF4450
    for key, u in spawners:
        uid = int(u, 16)
        vars_.append({"value": uid, "index": rec.get(uid, 0xFFFF), "name": 0xA61BE7D5F39117FF})
        actions.append((key, 0x2E910F8C, [("Templates", len(vars_) - 1, kind), ("Locations", len(vars_), kind)]))
        vars_.append({"type": 4, "aux": 0, "index": 0, "aux2": 0, "name": 1, "value": 7})
    for key, other, u in shared:
        uid = int(u, 16)
        vars_.append({"value": uid, "index": rec.get(uid, 0xFFFF), "name": 0xA61BE7D5F39117FF})
        actions.append((key, 0x2E910F8C, [("Templates", len(vars_) - 1, kind)]))
        actions.append((other, 0x0AC0B46C, [("Template", len(vars_) - 1, kind)]))
    vars_.append({})                                   # an empty type-5 entry
    vars_.append({"aux": 3})                           # a group-form type-5 entry
    vars_.append({"value": 0x8123456789ABCDEF})        # an external reference (not an actor of this zone)
    return zone(assets, actors, vars_, actions, refs)
