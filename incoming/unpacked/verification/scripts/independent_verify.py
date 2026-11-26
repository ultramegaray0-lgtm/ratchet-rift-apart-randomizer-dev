"""independent_verify.py - checks a Phase A RandoEnemies.stage against the original zone WITHOUT the kit's rcra.py /
stage_enemies.py code (its own DAT1 parser, its own diff), so the tool is not grading itself.

usage: python -I independent_verify.py <zone.orig backup> <RandoEnemies.stage> <stage_enemies_manifest.json> <probe.json>
Exit 0 = every check passed.
"""
import hashlib
import json
import struct
import sys
import zipfile

orig_path, stage_path, manifest_path, probe_path = sys.argv[1:5]
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print("%-4s %-62s %s" % ("ok" if ok else "FAIL", name, detail))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def dat1(buf):
    magic, type_id, size, count, unk = struct.unpack_from("<4sIIHH", buf, 0)
    secs = [struct.unpack_from("<III", buf, 16 + 12 * k) for k in range(count)]
    return magic, type_id, size, unk, secs


def u64(buf, off):
    return struct.unpack_from("<Q", buf, off)[0]


NAMES = {0xD86A7934: "Zone Script Vars", 0x70682CB8: "Zone Actors", 0x06ABCAB2: "Zone Scene Objects",
         0x5E54ACCF: "Zone Script Actions", 0xBEAB52E7: "Zone Script Plugs", 0x30DADA09: "Zone Asset References"}

m = json.load(open(manifest_path, encoding="utf-8"))
c = m["changes"][0]
ORIG_UID, REP_UID = int(c["original_uid"], 16), int(c["replacement_uid"], 16)

# ---- 1. the backup is the real zone (as the probe read it from the game) --------------------------------------------
blob = open(orig_path, "rb").read()
oh, oraw = blob[:36], blob[36:]
probe = json.load(open(probe_path, encoding="utf-8"))
pz = next(z for z in probe["zones"] if z["zone_id"] == c["zone_id"])
check("backup = 36-byte header + zone", len(blob) == 36 + len(oraw), "%d = 36 + %d" % (len(blob), len(oraw)))
check("backup zone sha256 = probe's (read from your game)", sha(oraw) == pz["sha256"], pz["sha256"][:16])
check("backup header = probe's toc header", oh.hex() == pz["header"], oh.hex()[:24] + "...")
check("backup zone sha256 = manifest zone_sha256_original", sha(oraw) == c["zone_sha256_original"])

# ---- 2. the .stage ---------------------------------------------------------------------------------------------------
z = zipfile.ZipFile(stage_path)
check("zip integrity (CRC of every member)", z.testzip() is None)
names = z.namelist()
member = "0/" + c["zone_id"]
check("members = info.json + one span-0 zone by hex id", names == ["info.json", member], str(names))
info = json.loads(z.read("info.json"))
check("info.json game = RCRA", info.get("game") == "RCRA")
pblob = z.read(member)
ph, praw = pblob[:36], pblob[36:]
check("stage sha256 = manifest stage_sha256", sha(open(stage_path, "rb").read()) == m["stage_sha256"])
check("patched zone sha256 = manifest zone_sha256_patched", sha(praw) == c["zone_sha256_patched"])

# ---- 3. header, sizes, structure ------------------------------------------------------------------------------------
check("asset header identical to the game's", ph == oh)
schema = struct.unpack_from("<I", ph)[0]
sizes = struct.unpack_from("<8I", ph, 4)
check("header block sizes add up to the patched zone", sum(sizes) == len(praw), "%s = %d" % ([s for s in sizes if s], len(praw)))
check("patched zone size = original size", len(praw) == len(oraw), "%d bytes" % len(praw))
mo, mp = dat1(oraw), dat1(praw)
check("DAT1 magic / type / size / flags unchanged", mo[:4] == mp[:4] and mo[0] == b"1TAD",
      "type %08X, DAT1 size %d (header schema %08X)" % (mo[1], mo[2], schema))
check("DAT1 section table identical (%d sections)" % len(mo[4]), mo[4] == mp[4])
check("every section inside the zone", all(o + s <= len(praw) for _, o, s in mp[4]))
th_end = 16 + 12 * len(mo[4])
check("DAT1 header + section table bytes identical", oraw[:th_end] == praw[:th_end])

# ---- 4. exactly one 8-byte change, and where it is -------------------------------------------------------------------
diff = [i for i in range(len(oraw)) if oraw[i] != praw[i]] if oraw != praw else []
lo, hi = (min(diff), max(diff)) if diff else (-1, -1)
check("bytes that differ: all inside one aligned 8-byte slot", bool(diff) and hi - lo < 8 and c["abs"] <= lo and hi < c["abs"] + 8,
      "%d byte(s) at %d..%d" % (len(diff), lo, hi))
check("everything outside that slot is byte-identical",
      oraw[:c["abs"]] == praw[:c["abs"]] and oraw[c["abs"] + 8:] == praw[c["abs"] + 8:])
sec = [(t, o, s) for t, o, s in mo[4] if o <= c["abs"] < o + s]
t, so, ss = sec[0]
check("the slot is in Zone Script Vars at the manifest offset", t == 0xD86A7934 and c["abs"] - so == c["rel"],
      "%s +%d" % (NAMES.get(t, "%08X" % t), c["abs"] - so))
check("old value = original uid, new value = replacement uid",
      u64(oraw, c["abs"]) == ORIG_UID and u64(praw, c["abs"]) == REP_UID,
      "%016X -> %016X" % (u64(oraw, c["abs"]), u64(praw, c["abs"])))

# ---- 5. the slot is the same kind of variable entry the replacement already sits in -------------------------------
sv = oraw[so:so + ss]
psv = praw[so:so + ss]


def entry(b, rel):          # Script Vars template-reference entries: 32 bytes = [u16 type, u16, u16, u16][u64][u64 uid][u64 0]
    e = rel - 16
    return struct.unpack_from("<HHHHQQQ", b, e)


known = {}
for h in pz["hits"]:
    if h["kind"] == "template" and h["section"] == "Zone Script Vars":
        known[h["rel"]] = h["id"]
types = {entry(sv, r)[0] for r in known}
check("all %d template refs in Script Vars sit in type-%s 32-byte entries" % (len(known), sorted(types)),
      len(types) == 1 and all(r % 32 == 16 for r in known) and all(entry(sv, r)[6] == 0 for r in known))
eo, ep = entry(sv, c["rel"]), entry(psv, c["rel"])
check("patched entry keeps its type/flags/name and zero tail", eo[:5] == ep[:5] and eo[6] == ep[6] == 0,
      "type %d, word %04X, name %016X" % (eo[0], eo[2], eo[4]))
rep_rel = [r for r, i in known.items() if int(i, 16) == REP_UID]
er = entry(sv, rep_rel[0]) if rep_rel else None
check("replacement's own existing variable is the same entry type", bool(er) and er[0] == eo[0],
      "replacement already referenced at Script Vars +%s" % rep_rel)

# ---- 6. reference counts by section, before and after ---------------------------------------------------------------
def count(buf, val):
    needle = struct.pack("<Q", val)
    out = {}
    for t, o, s in mo[4]:
        part = buf[o:o + s]
        n, i = 0, part.find(needle)
        while i >= 0:
            if i % 4 == 0:
                n += 1
            i = part.find(needle, i + 1)
        if n:
            out[NAMES.get(t, "%08X" % t)] = n
    return out


co, cp = count(oraw, ORIG_UID), count(praw, ORIG_UID)
ro, rp = count(oraw, REP_UID), count(praw, REP_UID)
print("     original uid %016X: before %s | after %s" % (ORIG_UID, co, cp))
print("     replacement uid %016X: before %s | after %s" % (REP_UID, ro, rp))
check("original: Script Vars 1 -> 0, its template actor still placed",
      co.get("Zone Script Vars") == 1 and "Zone Script Vars" not in cp and cp.get("Zone Actors") == co.get("Zone Actors") == 1)
check("replacement: Script Vars +1, template actor placed (Zone Actors)",
      rp.get("Zone Script Vars", 0) == ro.get("Zone Script Vars", 0) + 1 and rp.get("Zone Actors") == 1)

# ---- 7. no other zone in the probe references either uid -----------------------------------------------------------
other = sorted({(z_["zone"], h["id"]) for z_ in probe["zones"] if z_["zone_id"] != c["zone_id"] for h in z_["hits"]
                if h["id"] in (c["original_uid"], c["replacement_uid"])})
check("neither uid appears in any of the other %d probed zones" % (len(probe["zones"]) - 1), not other, str(other[:3]))

print("")
print("INDEPENDENT VERIFY: %s (%d checks, %d failed)" % ("PASS" if all(results) else "FAIL", len(results), results.count(False)))
sys.exit(0 if all(results) else 1)
