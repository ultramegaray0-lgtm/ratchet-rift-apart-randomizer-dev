"""build_mirror.py - a read-only stand-in for the user's game folder holding ONE real zone.

The zone bytes and its 36-byte toc header come from the POC backup (<id>.zone.orig = header + zone, written by
stage_enemies.py poc from the real toc). Before anything is written this script checks them against what the probe
read from the real game (probe.json: zone sha256, header hex, size). The toc / dag / DSAR container is written with the
kit's own fakegame.py helpers, so stage_enemies.py's unmodified readers open it exactly as they open the real game.

usage: python -I build_mirror.py <tools/stage_enemies dir> <zone.orig> <probe.json> <out game dir>
"""
import hashlib
import json
import os
import struct
import sys

tools, orig_path, probe_path, out = sys.argv[1:5]
sys.path.insert(0, tools)
import fakegame  # noqa: E402
import rcra  # noqa: E402

ZONE_PATH = "levels\\i29\\instance\\ardolis\\ardolis_main\\ard_firstvisit_gp.zone"
blob = open(orig_path, "rb").read()
header, raw = blob[:36], blob[36:]
zid = rcra.crc64_path(ZONE_PATH)

with open(probe_path, "r", encoding="utf-8") as f:
    probe = json.load(f)
z = next(z for z in probe["zones"] if z["zone_id"] == rcra.hex64(zid))
checks = [
    ("zone id = crc64(path)", z["zone_id"] == "AE530D22FE113E2B"),
    ("zone sha256 = probe (real game)", hashlib.sha256(raw).hexdigest() == z["sha256"]),
    ("zone size = probe", len(raw) == z["size"]),
    ("36-byte header = probe's toc header", header.hex() == z["header"]),
    ("header block sizes add up to the zone", sum(struct.unpack_from("<8I", header, 4)) == len(raw)),
]
for name, ok in checks:
    print("%-40s %s" % (name, "ok" if ok else "FAILED"))
if not all(ok for _, ok in checks):
    sys.exit("the backup does not match the probe of the real game - refusing to build the mirror")

# fakegame.build writes a synthetic header; write the real one instead (same layout as fakegame.build)
os.makedirs(os.path.join(out, "d"), exist_ok=True)
with open(os.path.join(out, "d", "fake.archive"), "wb") as f:
    f.write(fakegame.dsar(raw, chunk=0x10000))
spans = [(0, 1)] + [(1, 0)] * 255
archives = b"d\\fake.archive".ljust(40, b"\0") + struct.pack("<QQIHI", 0, 0, 0, 0, 0)
toc_dat = fakegame.dat1(0x51B8E006, [
    (rcra.TOC_ASSET_IDS, struct.pack("<Q", zid)),
    (rcra.TOC_SPANS, b"".join(struct.pack("<II", a, b) for a, b in spans)),
    (rcra.TOC_SIZES, struct.pack("<IIIi", len(raw), 0, 0, 0)),
    (rcra.TOC_ARCHIVES, archives),
    (rcra.TOC_HEADERS, header),
])
with open(os.path.join(out, "toc"), "wb") as f:
    f.write(struct.pack("<II", rcra.TOC_MAGIC, len(toc_dat) + 8) + toc_dat)
head = 16 + 12 * 5
dag_dat = fakegame.dat1(0x2A077A51, [
    (rcra.DAG_ASSET_IDS, bytes(8)),
    (rcra.DAG_NAMES, struct.pack("<I", head)),
    (rcra.DAG_TYPES, bytes([1])),
    (rcra.DAG_LINKS, struct.pack("<i", -1)),
    (rcra.DAG_HEADS, struct.pack("<i", 0)),
], ZONE_PATH.encode() + b"\0")
with open(os.path.join(out, "dag"), "wb") as f:
    f.write(struct.pack("<III", 0xB8EF3955, len(dag_dat) + 12, 0) + dag_dat)

# read it back through the tool's own reader
toc = rcra.Toc(out)
e = toc.find(zid, 0)
back_h, back = toc.header(e), toc.read(e)
toc.close()
print("%-40s %s" % ("read back through rcra.Toc", "ok" if (back_h == header and back == raw) else "FAILED"))
print("mirror game folder:", out)
