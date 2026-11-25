"""knowledge.py - what the randomizer already KNOWS about enemies, read from its own files and your rivet.logs.

Nothing here is typed in by hand: template uids come from 16_rando_spawners.lua's V.REG_BUILTIN and from the logs'
"learned template" / CHANGED lines; combat evidence from V.COMPAT_BUILTIN; actor asset paths from the logs' ASSET
lines; spawner keys and their original enemies from SPAWN lines. The rules (faction, kind key, movement group) are
ports of the Lua functions of the same names, so the tool and the game agree.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

# ---- ports of 16_rando_spawners.lua ---------------------------------------------------------------------------------
FAMILY_GROUP = {"ground": "walker", "swarmer": "walker", "turret": "turret", "flyer": "flyer"}   # V.FAMILY_GROUP
FACTION_ALIAS = {"indigenous": "wildlife", "native": "wildlife", "creature": "wildlife"}          # V.FACTION_ALIAS
SIZE_TOKENS = ["_small", "_medium", "_large", "_xl", "_ps4", "_v2", "_rcf", "_rcn"]               # V.SIZE_TOKENS
NAME_EXCLUDE = ["npc_", "boss", "ally", "friend", "civ_", "vendor", "dummy", "test_", "infobot", "sheep", "lemming"]


def short(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    n = re.split(r"[\\/]", str(name))[-1]
    n = re.sub(r"\.actor$", "", n)
    return re.sub(r"\.a$", "", n)


def base_name(name: str) -> str:
    n = (short(name) or "").lower()
    for t in SIZE_TOKENS:
        n = re.sub(re.escape(t) + "$", "", n)
        n = n.replace(t + "_", "_")
    for t in SIZE_TOKENS:
        n = re.sub(re.escape(t) + "$", "", n)
    return n


def faction(name: str) -> str:
    n = (short(name) or "").lower()
    m = re.match(r"^enm_([a-z0-9]+)_", n) or re.match(r"^([a-z0-9]+)_", n)
    if not m:
        return base_name(n)
    return FACTION_ALIAS.get(m.group(1), m.group(1))


def kind_key(name: str, family: Optional[str]) -> str:
    return (short(name) or "?").lower()[:19] + "/" + str(family or "?")


def pair_key(adapter: str, o_name: str, o_fam: str, r_name: str, r_fam: str) -> str:
    return "%s|%s>%s" % (adapter, kind_key(o_name, o_fam), kind_key(r_name, r_fam))


def excluded(name: str) -> bool:
    n = (short(name) or "").lower()
    return any(x in n for x in NAME_EXCLUDE)


# ---- the knowledge ----------------------------------------------------------------------------------------------------
@dataclass
class Template:
    uid: str
    name: str
    family: Optional[str] = None
    cls: Optional[str] = None
    role: Optional[str] = None
    sources: Set[str] = field(default_factory=set)


@dataclass
class Spawner:
    key: str
    adapter: str
    planet: str
    encounters: Set[str] = field(default_factory=set)
    originals: Dict[str, int] = field(default_factory=dict)   # original kind name -> spawns seen
    # template uids this spawner's variable was SEEN holding (tool 1.0.1): a SPAWN line followed directly by the
    # "learned template ... (spawn)" line of that same spawn (16_rando_spawners.lua logs both in one call, ledger first)
    uids: Set[str] = field(default_factory=set)


@dataclass
class Knowledge:
    templates: Dict[str, Template] = field(default_factory=dict)
    actor_paths: Dict[str, str] = field(default_factory=dict)        # enemy name -> .actor path
    actor_family: Dict[str, str] = field(default_factory=dict)
    actor_class: Dict[str, str] = field(default_factory=dict)
    compat: Dict[str, tuple] = field(default_factory=dict)           # pair key -> ("ok"|"bad", evidence)
    spawners: Dict[str, Spawner] = field(default_factory=dict)
    planets: Set[str] = field(default_factory=set)
    notes: List[str] = field(default_factory=list)

    def add_template(self, uid, name, family=None, cls=None, role=None, source="?"):
        uid = uid.upper()
        t = self.templates.get(uid)
        if t is None:
            t = self.templates[uid] = Template(uid, name, family, cls, role)
        elif short(t.name) != short(name):
            self.notes.append("uid %s named both %s and %s (kept %s)" % (uid, t.name, name, t.name))
        t.family = t.family or family
        t.cls = t.cls or cls
        t.role = t.role or role
        t.sources.add(source)

    def family_of(self, name: str) -> Optional[str]:
        return self.actor_family.get(short(name))

    def enemy_templates(self) -> Dict[str, Template]:
        """Templates of role 'enemy' (or a known enemy family) that are never excluded by name."""
        out = {}
        for uid, t in self.templates.items():
            fam = t.family or self.family_of(t.name)
            if t.role not in (None, "enemy"):
                continue
            if fam not in FAMILY_GROUP or excluded(t.name):
                continue
            out[uid] = t
        return out

    def pair_status(self, o: Template, r: Template, adapter="factory"):
        fo = o.family or self.family_of(o.name)
        fr = r.family or self.family_of(r.name)
        return self.compat.get(pair_key(adapter, o.name, fo, r.name, fr))

    # ---- tool 1.1.0: identity comes from the zone (its actor asset), knowledge only adds the family -----------------
    def kind_info(self, name: str):
        """(family, class, role, sources) of an enemy KIND by its short name, from every template the registry and the
        logs know plus the logs' ASSET lines - only when they all agree. (None, ...) when unknown or ambiguous."""
        n = (short(name) or "").lower()
        fams, clss, roles, srcs = set(), set(), set(), set()
        for t in self.templates.values():
            if (short(t.name) or "").lower() == n:
                if t.family:
                    fams.add(t.family)
                if t.cls:
                    clss.add(t.cls)
                if t.role:
                    roles.add(t.role)
                srcs |= t.sources
        for k, f in self.actor_family.items():
            if (short(k) or "").lower() == n and f:
                fams.add(f)
                srcs.add("ASSET line")
        for k, c in self.actor_class.items():
            if (short(k) or "").lower() == n and c:
                clss.add(c)
        fam = next(iter(fams)) if len(fams) == 1 else None
        cls = next(iter(clss)) if len(clss) == 1 else None
        role = next(iter(roles)) if len(roles) == 1 else None
        return fam, cls, role, sorted(srcs), sorted(fams)

    def pair_status_names(self, o_name: str, o_fam: str, r_name: str, r_fam: str, adapter="factory"):
        return self.compat.get(pair_key(adapter, o_name, o_fam, r_name, r_fam))


REG_LINE = re.compile(r'\["([0-9A-Fa-f]{16})"\]\s*=\s*"([^"|]+)\|([^"|]*)\|([^"|]*)\|([^"|]*)"')
COMPAT_LINE = re.compile(r'\["((?:factory|template|group)\|[^"]+)"\]\s*=\s*\{\s*"(ok|bad)"\s*,\s*"((?:[^"\\]|\\.)*)"', re.S)


def load_scripts(k: Knowledge, scripts_dir: str) -> None:
    path = os.path.join(scripts_dir, "16_rando_spawners.lua")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()
    a = src.find("V.REG_BUILTIN = {")
    b = src.find("\n}", a)
    if a < 0 or b < 0:
        raise ValueError("V.REG_BUILTIN not found in " + path)
    n = 0
    for m in REG_LINE.finditer(src[a:b]):
        k.add_template(m.group(1), m.group(2), m.group(3) or None, m.group(4) or None, m.group(5) or None, "REG_BUILTIN")
        n += 1
    a = src.find("V.COMPAT_BUILTIN = {")
    b = src.find("\n}", a)
    if a < 0 or b < 0:
        raise ValueError("V.COMPAT_BUILTIN not found in " + path)
    c = 0
    for m in COMPAT_LINE.finditer(src[a:b]):
        k.compat[m.group(1)] = (m.group(2), m.group(3))
        c += 1
    k.notes.append("%s: %d built-in template uids, %d built-in combat pairs" % (os.path.basename(path), n, c))


ASSET_RE = re.compile(r"RANDO-ENEMIES\tASSET (\S+) \(([a-z]+), (\w+)\): (\S+)")
LEARNED_RE = re.compile(r"learned template \d+ \(uid ([0-9A-F]{16})\): (\S+) = ([a-z?]+)/(\w+), role (\w+)")
CHANGED_RE = re.compile(r"CHANGED.*? (factory Templates|node Template|node Template group) ([0-9A-F]{16}) .*?: (\S+) -> (\S+) "
                        r"\[template \d+ uid ([0-9A-F]{16})")
SPAWN_RE = re.compile(r"SPAWN \d+ \| (\S+) \| (.*?) \| (factory Templates|node Template group|node Template|no spawner) (\S+) \| "
                      r"original (\S+) \| selected (\S+) \| spawned (\S+) \((\w+)\)")
ADAPTER = {"factory Templates": "factory", "node Template": "template", "node Template group": "group"}


def load_log(k: Knowledge, path: str) -> None:
    na = nl = nc = ns = nu = 0
    prev_spawn = None      # (key, spawned name) when the previous RANDO-ENEMIES line was a first-spawn SPAWN line
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "RANDO-ENEMIES" not in line:
                continue
            last, prev_spawn = prev_spawn, None
            m = ASSET_RE.search(line)
            if m:
                name, fam, cls, p = m.groups()
                k.actor_paths[name] = p.replace("\\", "/")
                k.actor_family[name] = fam
                k.actor_class[name] = cls
                na += 1
                continue
            m = LEARNED_RE.search(line)
            if m:
                uid, name, fam, cls, role = m.groups()
                k.add_template(uid, name, None if fam == "?" else fam, cls, role, os.path.basename(path))
                nl += 1
                # which spawner's variable held this uid: only when this line is the learn of the spawn logged on the
                # line before (same spawned kind, learned from a spawn, that spawn waiting for its first spawn to learn)
                if last and line.rstrip().endswith("(spawn)") and short(last[1]) == short(name):
                    k.spawners[last[0]].uids.add(uid.upper())
                    nu += 1
                continue
            m = CHANGED_RE.search(line)
            if m:
                _, _, _, rep, uid = m.groups()
                k.add_template(uid, rep, None, None, None, os.path.basename(path))
                nc += 1
                continue
            m = SPAWN_RE.search(line)
            if m:
                planet, enc, adapter, key, orig, _sel, spawned, fam = m.groups()
                if adapter == "no spawner" or key == "-":
                    continue
                s = k.spawners.get(key)
                if s is None:
                    s = k.spawners[key] = Spawner(key, ADAPTER[adapter], planet)
                s.encounters.add(enc)
                s.originals[orig] = s.originals.get(orig, 0) + 1
                k.planets.add(planet)
                ns += 1
                if "learned from its first spawn" in line:
                    prev_spawn = (key, spawned)
    k.notes.append("%s: %d ASSET, %d learned, %d CHANGED, %d SPAWN lines, %d spawn(s) tied to the template uid its variable held" % (
        os.path.basename(path), na, nl, nc, ns, nu))