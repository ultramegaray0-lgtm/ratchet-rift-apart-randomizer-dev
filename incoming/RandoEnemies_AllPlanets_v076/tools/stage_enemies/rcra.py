"""rcra.py - read-only access to Ratchet & Clank: Rift Apart (PC) asset files, and .stage writing.

Part of the Rift Apart Randomizer's .stage Enemy Randomizer (v0.76-DEV4). Python 3.9+, standard library only.

Nothing here writes to the game folder. Every structure is taken from the open-source modding tools' code, not guessed:

  CRC64 asset ids ........ Overstrike DAT1/CRC64.cs + DAT1/Utils.cs (Normalize); checked against ids the game's own
                           create_asset_id produced (rivet.log "[loader] ... resolved to asset id ...")
  CRC32 type / plug ids .. rivet docs/format/dat1.txt APPENDIX A; checked against Ripped Apart libra/lump_types.h and
                           the randomizer's V.crc ("Templates" = 3990217346, rivet.log)
  toc .................... Overstrike DAT1/TOC.cs (TOC_I29) + DAT1/Sections/TOC/*.cs; rivet docs/format/toc.txt
  DSAR archives .......... Overstrike DAT1/DSAR.cs; rivet docs/format/dsar.txt (LZ4 = type 3; GDeflate = textures only)
  dag .................... Ripped Apart libra/dependency_dag.c; rivet docs/format/dag.txt
  DAT1 ................... Overstrike DAT1/DAT1.cs; Ripped Apart libra/dat_container.c
  36-byte asset header ... Overstrike AssetHeadersSection_I29 (36 bytes); rivet toc.txt (schema + sizes[8]);
                           rivet_hook runtime_loader.cpp (a loose/.stage built asset = header, data at 0x24)
  .stage ................. Overstrike Installers/StageInstaller.cs + Detectors/StageModDetector.cs;
                           rivet_hook runtime_loader.cpp load_mod_asset_overstrike_stage_entry
"""
from __future__ import annotations

import bisect
import hashlib
import io
import json
import os
import struct
import zipfile
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

FORMAT_LIB_VERSION = "1.1.0"   # 1.1.0: unnamed zone sections labelled (zone.py decodes them)


class FormatError(Exception):
    """A file does not have the structure the modding tools document. Never guessed around."""


# --------------------------------------------------------------------------------------------------------------------
# hashes
# --------------------------------------------------------------------------------------------------------------------
def _crc32_table() -> List[int]:
    t = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
        t.append(c)
    return t


_CRC32 = _crc32_table()


def crc32_engine(text) -> int:
    """The engine's string hash: reflected CRC-32, start value 0xEDB88320, no final XOR (rivet dat1.txt App. A)."""
    data = text.encode("utf-8") if isinstance(text, str) else bytes(text)
    c = 0xEDB88320
    for b in data:
        c = (c >> 8) ^ _CRC32[(b ^ c) & 0xFF]
    return c


def _crc64_table() -> List[int]:
    poly = 0xC96C5795D7870F42  # ECMA-182, reflected (Overstrike's table[1] == 0xB32E4CBE03A75F6F)
    t = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ poly if c & 1 else c >> 1
        t.append(c)
    return t


_CRC64 = _crc64_table()


def normalize_path(path: str) -> str:
    """Overstrike Utils.Normalize: lower case, '/' separators, no repeated, leading or trailing '/'."""
    s = path.lower().replace("\\", "/")
    out = []
    prev_slash = False
    for ch in s:
        if ch == "/":
            if prev_slash:
                continue
            prev_slash = True
        else:
            prev_slash = False
        out.append(ch)
    r = "".join(out)
    if r.startswith("/"):
        r = r[1:]
    if r.endswith("/"):
        r = r[:-1]
    return r


def crc64_path(path: str) -> int:
    """An asset id from its path (Overstrike CRC64.Hash: start 0xC96C5795D7870F42, >> 2, top bit set)."""
    v = 0xC96C5795D7870F42
    for b in normalize_path(path).encode("utf-8"):
        v = (v >> 8) ^ _CRC64[(v ^ b) & 0xFF]
    return (v >> 2) | 0x8000000000000000


def hex64(v: int) -> str:
    return "%016X" % (v & 0xFFFFFFFFFFFFFFFF)


def uid_bytes(uid_hex: str) -> bytes:
    """A uid as the game stores it in memory (little-endian u64): the randomizer logs it as 16 hex digits."""
    v = int(uid_hex, 16)
    if not 0 <= v < (1 << 64):
        raise ValueError("not a 64-bit uid: " + uid_hex)
    return struct.pack("<Q", v)


# --------------------------------------------------------------------------------------------------------------------
# LZ4 block format (the DSAR chunk type 3 codec). Pure Python; checked against the lz4 package in the self-test.
# --------------------------------------------------------------------------------------------------------------------
def lz4_block_decompress(src: bytes, out_size: int) -> bytes:
    dst = bytearray()
    i, n = 0, len(src)
    while i < n:
        token = src[i]
        i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                if i >= n:
                    raise FormatError("LZ4: literal length runs past the block")
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        if i + lit > n:
            raise FormatError("LZ4: literals run past the block")
        dst += src[i:i + lit]
        i += lit
        if i >= n:
            break  # the last sequence has literals only
        if i + 2 > n:
            raise FormatError("LZ4: truncated match offset")
        off = src[i] | (src[i + 1] << 8)
        i += 2
        if off == 0 or off > len(dst):
            raise FormatError("LZ4: bad match offset %d at output %d" % (off, len(dst)))
        ml = token & 15
        if ml == 15:
            while True:
                if i >= n:
                    raise FormatError("LZ4: match length runs past the block")
                b = src[i]
                i += 1
                ml += b
                if b != 255:
                    break
        ml += 4
        start = len(dst) - off
        if ml <= off:
            dst += dst[start:start + ml]
        else:
            pat = bytes(dst[start:])
            q, r = divmod(ml, off)
            dst += pat * q + pat[:r]
        if len(dst) > out_size:
            raise FormatError("LZ4: output larger than the chunk's size")
    if len(dst) != out_size:
        raise FormatError("LZ4: decompressed %d bytes, the chunk says %d" % (len(dst), out_size))
    return bytes(dst)


# --------------------------------------------------------------------------------------------------------------------
# DAT1
# --------------------------------------------------------------------------------------------------------------------
DAT1_MAGIC = 0x44415431


@dataclass
class Dat1Section:
    tag: int
    offset: int  # relative to the DAT1 start
    size: int


@dataclass
class Dat1:
    data: bytes
    base: int  # where DAT1 starts in `data`
    type_id: int
    size: int
    sections: Dict[int, Dat1Section] = field(default_factory=dict)
    order: List[int] = field(default_factory=list)

    @staticmethod
    def parse(data: bytes, base: int = 0) -> "Dat1":
        if len(data) < base + 16:
            raise FormatError("DAT1: too short")
        magic, type_id, size, count, unknowns = struct.unpack_from("<IIIHH", data, base)
        if magic != DAT1_MAGIC:
            raise FormatError("DAT1: magic %08X at %d (expected 44415431)" % (magic, base))
        if base + 16 + 12 * count > len(data):
            raise FormatError("DAT1: section table runs past the data")
        d = Dat1(data=data, base=base, type_id=type_id, size=size)
        for k in range(count):
            tag, off, sz = struct.unpack_from("<III", data, base + 16 + 12 * k)
            if base + off + sz > len(data):
                raise FormatError("DAT1: section %08X (%d bytes at %d) runs past the data (%d)" % (tag, sz, off, len(data) - base))
            d.sections[tag] = Dat1Section(tag, off, sz)
            d.order.append(tag)
        return d

    def has(self, tag: int) -> bool:
        return tag in self.sections

    def section(self, tag: int) -> bytes:
        s = self.sections.get(tag)
        if s is None:
            raise FormatError("DAT1: no section %08X" % tag)
        a = self.base + s.offset
        return self.data[a:a + s.size]

    def abs_offset(self, tag: int) -> int:
        return self.base + self.sections[tag].offset

    def cstring(self, offset: int) -> str:
        a = self.base + offset
        e = self.data.find(b"\0", a)
        if e < 0:
            raise FormatError("DAT1: unterminated string at %d" % offset)
        return self.data[a:e].decode("utf-8", "replace")


def find_dat1(data: bytes, limit: int = 0x200) -> int:
    """Where the DAT1 magic is within the first `limit` bytes (-1: none)."""
    return data.find(struct.pack("<I", DAT1_MAGIC), 0, min(limit, len(data)))


# DAT1 section ids. Names and values from Ripped Apart libra/lump_types.h and rivet docs/dat1_hashes_known.txt; the
# self-test recomputes every value from its name with crc32_engine.
SECTION_NAMES = {
    0x06ABCAB2: "Zone Scene Objects",
    0xCB8D34F9: "Zone Impostors Atlas",
    0xDC311FC3: "Zone Impostors",
    0x30DADA09: "Zone Asset References",
    0x5E54ACCF: "Zone Script Actions",
    0xBEAB52E7: "Zone Script Plugs",
    0xD86A7934: "Zone Script Vars",
    0xEF8637D5: "Zone Script Strings",
    0x2300D240: "Zone Script Priuses",
    0x657512BB: "Zone Decal Geometry",
    0x6987F172: "Zone Model Insts",
    0x70682CB8: "Zone Actors",
    0x50EDC53D: "Zone Actor Priuses",
    0x91DE11D9: "Zone Decal Assets",
    0xBCF43558: "Zone Decals",
    0xC6A5905E: "Zone Model Names",
    0xDC625B3D: "Zone Actor Names",
    0xE4158AC3: "Zone Material Overrides",
    0x0CF58A6E: "Zone Actor Groups",
    0xBDAB2B0D: "Zone Volumes",
    0x97FF6EB5: "Zone Lights",
    0xB6A0B72A: "Zone Atmosphere Name",
    0x027795C5: "Zone EnvProbe Assets",
    0x557013E9: "Zone EnvProbe List",
    0x17AFFFCE: "Zone Override Tris",
    0x927C4EC3: "Zone Visual Effect Insts",
    0x3D5E2FEF: "Zone Visual Effect Names",
    0x2236C47A: "Level Link Names",
    0x2BA33702: "Level Zone Names",
    0x396F9418: "Level Regions Built",
    0x4130D903: "Level Region Names",
    0x4E023760: "Level Zones Built",
    0x7CA7267D: "Level Built",
    0x3AB204B9: "Actor Asset Refs",
    0x32FAC8E0: "Actor Built",
    0x364A6C7C: "Actor Object Built",
    0x135832C8: "Actor Prius Built",
    0x2F4056CE: "Conduit Asset Refs",
    0xCEB30E68: "Conduit Built",
}
SEC = {v: k for k, v in SECTION_NAMES.items()}
# stage tool 1.1.0: sections whose role is decoded and CHECKED on every zone (zone.py) but whose name string is not
# known (no crc32 match), so they are not in SECTION_NAMES (the self-test recomputes every name there)
ZONE_ACTOR_ASSET_TABLE = 0x78684035   # n * u64 actor asset id, n * u32 path offset; CRC64(path) == id on every entry
UNNAMED_SECTIONS = {ZONE_ACTOR_ASSET_TABLE: "actor-asset table (78684035)"}


def section_name(tag: int) -> str:
    return SECTION_NAMES.get(tag) or UNNAMED_SECTIONS.get(tag) or "%08X" % tag


# --------------------------------------------------------------------------------------------------------------------
# DSAR archives
# --------------------------------------------------------------------------------------------------------------------
DSAR_MAGIC = 0x52415344


class UnsupportedCompression(FormatError):
    pass


class Archive:
    """One archive file of the toc. DSAR (chunked, LZ4 for everything but textures) or plain."""

    def __init__(self, path: str):
        self.path = path
        self.f = open(path, "rb")
        head = self.f.read(32)
        self.dsar = len(head) >= 4 and struct.unpack_from("<I", head, 0)[0] == DSAR_MAGIC
        self.chunks: List[Tuple[int, int, int, int, int]] = []  # real_off, comp_off, real_size, comp_size, type
        self._starts: List[int] = []
        self._cache: Dict[int, bytes] = {}
        self._cache_order: List[int] = []
        if self.dsar:
            if len(head) < 32:
                raise FormatError("DSAR: header too short: " + path)
            _, vmaj, vmin, count, first = struct.unpack_from("<IHHII", head, 0)
            self.f.seek(32)
            table = self.f.read(first - 32)
            if len(table) != first - 32 or (first - 32) % 32 != 0:
                raise FormatError("DSAR: chunk table size %d is not a multiple of 32: %s" % (first - 32, path))
            for k in range((first - 32) // 32):
                ro, co, rs, cs, ty = struct.unpack_from("<QQIIB", table, 32 * k)
                self.chunks.append((ro, co, rs, cs, ty))
            self.chunks.sort()
            self._starts = [c[0] for c in self.chunks]
            if count and count != len(self.chunks):
                raise FormatError("DSAR: header says %d chunks, the table has %d: %s" % (count, len(self.chunks), path))

    def close(self):
        try:
            self.f.close()
        except Exception:
            pass

    def _chunk(self, k: int) -> bytes:
        if k in self._cache:
            return self._cache[k]
        ro, co, rs, cs, ty = self.chunks[k]
        if ty == 0xFE:
            out = bytes(rs)
        else:
            self.f.seek(co)
            comp = self.f.read(cs)
            if len(comp) != cs:
                raise FormatError("DSAR: chunk %d truncated in %s" % (k, self.path))
            if ty == 3:
                out = lz4_block_decompress(comp, rs)
            elif ty == 0:
                out = comp[:rs]
            elif ty == 2:
                raise UnsupportedCompression("GDeflate chunk (textures only, never needed for zones)")
            else:
                raise UnsupportedCompression("DSAR compression type %d" % ty)
        self._cache[k] = out
        self._cache_order.append(k)
        if len(self._cache_order) > 48:
            self._cache.pop(self._cache_order.pop(0), None)
        return out

    def read(self, offset: int, size: int) -> bytes:
        if not self.dsar:
            self.f.seek(offset)
            b = self.f.read(size)
            if len(b) != size:
                raise FormatError("archive %s: %d bytes at %d not available" % (self.path, size, offset))
            return b
        out = bytearray()
        end = offset + size
        k = bisect.bisect_right(self._starts, offset) - 1
        if k < 0:
            raise FormatError("DSAR: offset %d before the first chunk" % offset)
        pos = offset
        while pos < end:
            if k >= len(self.chunks):
                raise FormatError("DSAR: %d bytes at %d run past the last chunk of %s" % (size, offset, self.path))
            ro, co, rs, cs, ty = self.chunks[k]
            if not (ro <= pos < ro + rs):
                raise FormatError("DSAR: no chunk holds offset %d in %s" % (pos, self.path))
            data = self._chunk(k)
            a = pos - ro
            b = min(end, ro + rs) - ro
            out += data[a:b]
            pos = ro + b
            k += 1
        return bytes(out)


# --------------------------------------------------------------------------------------------------------------------
# toc
# --------------------------------------------------------------------------------------------------------------------
TOC_MAGIC = 0x34E89035
TOC_ASSET_IDS = 0x506D7B8A
TOC_SPANS = 0xEDE8ADA9
TOC_SIZES = 0x65BCF461
TOC_ARCHIVES = 0x398ABFF0
TOC_HEADERS = 0x654BDED9
ASSET_HEADER_SIZE = 36


@dataclass
class TocEntry:
    index: int
    span: int
    asset_id: int
    size: int
    archive: int
    offset: int
    header_offset: int


class Toc:
    def __init__(self, game_dir: str):
        self.game_dir = game_dir
        self.path = os.path.join(game_dir, "toc")
        with open(self.path, "rb") as f:
            raw = f.read()
        magic, _ = struct.unpack_from("<II", raw, 0)
        if magic != TOC_MAGIC:
            raise FormatError("toc: magic %08X (expected 34E89035, the uncompressed Rift Apart toc): %s" % (magic, self.path))
        self.dat = Dat1.parse(raw, 8)
        ids = self.dat.section(TOC_ASSET_IDS)
        self.ids = list(struct.unpack_from("<%dQ" % (len(ids) // 8), ids, 0))
        sp = self.dat.section(TOC_SPANS)
        self.spans = [struct.unpack_from("<II", sp, 8 * k) for k in range(len(sp) // 8)]
        sz = self.dat.section(TOC_SIZES)
        if len(sz) != 16 * len(self.ids):
            raise FormatError("toc: %d asset metadata bytes for %d assets (16 each expected)" % (len(sz), len(self.ids)))
        self._sizes = sz
        ar = self.dat.section(TOC_ARCHIVES)
        if len(ar) % 66:
            raise FormatError("toc: archive table is not 66-byte entries (%d bytes)" % len(ar))
        self.archive_names = []
        for k in range(len(ar) // 66):
            nm = ar[66 * k:66 * k + 40]
            self.archive_names.append(nm[:nm.find(b"\0") if b"\0" in nm else 40].decode("ascii", "replace"))
        self.headers = self.dat.section(TOC_HEADERS) if self.dat.has(TOC_HEADERS) else b""
        self._archives: Dict[int, Archive] = {}

    def span_of(self, index: int) -> int:
        for s, (start, count) in enumerate(self.spans):
            if start <= index < start + count:
                return s
        return -1

    def find(self, asset_id: int, span: Optional[int] = None) -> Optional[TocEntry]:
        spans = [span] if span is not None else range(len(self.spans))
        for s in spans:
            start, count = self.spans[s]
            i = bisect.bisect_left(self.ids, asset_id, start, start + count)
            if i < start + count and self.ids[i] == asset_id:
                return self.entry(i, s)
        return None

    def entry(self, index: int, span: Optional[int] = None) -> TocEntry:
        size, archive, offset, header = struct.unpack_from("<IIIi", self._sizes, 16 * index)
        return TocEntry(index, self.span_of(index) if span is None else span, self.ids[index], size, archive, offset, header)

    def archive(self, k: int) -> Archive:
        if k not in self._archives:
            name = self.archive_names[k].replace("\\", os.sep).replace("/", os.sep)
            self._archives[k] = Archive(os.path.join(os.path.dirname(self.path), name))
        return self._archives[k]

    def header(self, e: TocEntry) -> Optional[bytes]:
        if e.header_offset < 0:
            return None
        h = self.headers[e.header_offset:e.header_offset + ASSET_HEADER_SIZE]
        if len(h) != ASSET_HEADER_SIZE:
            raise FormatError("toc: asset header at %d is cut short" % e.header_offset)
        return h

    def read(self, e: TocEntry) -> bytes:
        return self.archive(e.archive).read(e.offset, e.size)

    def close(self):
        for a in self._archives.values():
            a.close()
        self._archives = {}


def header_block_sizes(header: bytes) -> Tuple[int, List[int]]:
    """rivet toc.txt: u32 schema, u32 sizes[8] (a zone: 0 content, 1 physics, ...)."""
    v = struct.unpack_from("<I8I", header, 0)
    return v[0], list(v[1:])


# --------------------------------------------------------------------------------------------------------------------
# dag (asset names, types, dependencies)
# --------------------------------------------------------------------------------------------------------------------
DAG_ASSET_IDS = 0x933C0D32
DAG_NAMES = 0xD101A6CC
DAG_TYPES = 0x7A0266BC
DAG_LINKS = 0xBC91D1CC
DAG_HEADS = 0xF958372E
ASSET_TYPES = ["level", "zone", "actor", "conduit", "config", "cinematic", "model", "animclip", "animset", "material",
               "materialgraph", "texture", "atmosphere", "effect", "soundbank", "localization", "type16", "type17",
               "zonelighting", "levellighting", "nodegraph", "type21", "wwiselookup"]


class Dag:
    def __init__(self, game_dir: str):
        self.path = os.path.join(game_dir, "dag")
        with open(self.path, "rb") as f:
            raw = f.read()
        base = find_dat1(raw, 64)
        if base < 0:
            raise FormatError("dag: no DAT1 within the first 64 bytes (a compressed dag is not supported): " + self.path)
        self.dat = Dat1.parse(raw, base)
        names = self.dat.section(DAG_NAMES)
        types = self.dat.section(DAG_TYPES)
        self.count = len(types)
        if len(names) != 4 * self.count:
            raise FormatError("dag: %d names for %d types" % (len(names) // 4, self.count))
        self.names = [self.dat.cstring(o) for o in struct.unpack_from("<%dI" % self.count, names, 0)]
        self.types = list(types)
        heads = self.dat.section(DAG_HEADS)
        self._heads = struct.unpack_from("<%di" % self.count, heads, 0) if len(heads) == 4 * self.count else None
        links = self.dat.section(DAG_LINKS)
        self._links = struct.unpack_from("<%di" % (len(links) // 4), links, 0)
        self.ids = [crc64_path(n) for n in self.names]  # dag.txt App. C: the stored ids are not initialized
        self.by_id = {}
        for k, i in enumerate(self.ids):
            self.by_id.setdefault(i, k)

    def type_name(self, k: int) -> str:
        t = self.types[k]
        return ASSET_TYPES[t] if t < len(ASSET_TYPES) else "type%d" % t

    def deps(self, k: int) -> List[int]:
        if self._heads is None:
            return []
        h = self._heads[k]
        out = []
        while 0 <= h < len(self._links):
            v = self._links[h]
            if v < 0:
                break
            out.append(v)
            h += 1
        return out


# --------------------------------------------------------------------------------------------------------------------
# STG (Overstrike Modding Tool's extracted-asset wrapper) - accepted as an input for people who extracted by hand
# --------------------------------------------------------------------------------------------------------------------
STG_MAGIC = 0x475453


def read_stg(blob: bytes) -> Tuple[Optional[bytes], bytes]:
    """Returns (header or None, raw). A file without the STG magic is taken as raw bytes."""
    if len(blob) >= 16 and (struct.unpack_from("<I", blob, 0)[0] & 0xFFFFFF) == STG_MAGIC:
        if blob[3] != 0:
            raise FormatError("STG: unknown version %d" % blob[3])
        flags, hs, ts = struct.unpack_from("<III", blob, 4)
        p = 16
        header = blob[p:p + hs]
        p += hs
        p += (-p) % 16
        p += ts
        p += (-p) % 16
        return (header if (flags & 1) and hs else None), blob[p:]
    return None, blob


# --------------------------------------------------------------------------------------------------------------------
# .stage writing
# --------------------------------------------------------------------------------------------------------------------
STAGE_GAME_ID = "RCRA"  # Overstrike Games/GameRCRA.cs


@dataclass
class StageEntry:
    span: int
    asset_id: int
    header: bytes
    raw: bytes
    path: str = ""

    def payload(self) -> bytes:
        return self.header + self.raw

    def zip_name(self) -> str:
        # the hex form needs no path hashing on either loader (rivet_hook stoull / Overstrike regex ^[0-9A-F]{16}$)
        return "%d/%s" % (self.span, hex64(self.asset_id))


def write_stage(path: str, name: str, author: str, description: str, entries: Iterable[StageEntry]) -> Dict:
    """A .stage both rivet_hook ([assets] paths) and Overstrike (format v1: span 0 = 36-byte header + data) load.

    The zip is written with a fixed timestamp and order so the same input gives byte-identical output."""
    entries = sorted(entries, key=lambda e: (e.span, e.asset_id))
    info = {"name": name, "author": author, "game": STAGE_GAME_ID, "description": description}
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        def add(n, data):
            zi = zipfile.ZipInfo(n, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
        add("info.json", json.dumps(info, indent=2, sort_keys=True).encode("utf-8"))
        for e in entries:
            if e.span % 8 != 0:
                raise FormatError("only span 0 (built, no language) assets are written here, not span %d" % e.span)
            if len(e.header) != ASSET_HEADER_SIZE:
                raise FormatError("asset %s: header is %d bytes, 36 needed" % (hex64(e.asset_id), len(e.header)))
            add(e.zip_name(), e.payload())
    os.replace(tmp, path)
    return info


def read_stage(path: str) -> Tuple[Dict, Dict[str, bytes]]:
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise FormatError(".stage: corrupt member " + bad)
        info = json.loads(z.read("info.json").decode("utf-8"))
        files = {n: z.read(n) for n in z.namelist() if n != "info.json" and not n.endswith("/")}
    return info, files


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
