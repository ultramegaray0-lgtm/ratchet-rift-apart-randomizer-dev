"""rando_give.dll: host unit test of its portable core, and a check that the shipped DLL is
exactly what its source builds to (except the link timestamp)."""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from harness import MOD, ROOT  # noqa: E402

SRC = MOD / "rando_give_source"


@unittest.skipUnless(shutil.which("cc") or shutil.which("gcc"), "no C compiler")
class NativeCoreTests(unittest.TestCase):
    def test_core(self):
        cc = shutil.which("cc") or shutil.which("gcc")
        with tempfile.TemporaryDirectory() as d:
            exe = os.path.join(d, "t")
            subprocess.run([cc, "-O1", "-Wall", "-Wextra", "-Werror", "-I", str(SRC),
                            str(ROOT / "tests" / "native" / "test_rando_give_core.c"), "-o", exe], check=True)
            r = subprocess.run([exe], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("all native core checks passed", r.stdout)


class MissionBytesFromYourGameTests(unittest.TestCase):
    """rando_give.dll v3 calls the mission system only when every byte matches: the expected
    bytes must be exactly what your game's code dump holds (round 14 research zip)."""

    def test_expected_bytes_come_from_the_dump(self):
        import json
        import re
        dump = json.load(open(ROOT / "tests" / "data" / "round14_game_code_dump.json", encoding="utf-8-sig"))
        src = (SRC / "rando_give_core.h").read_text()
        code = {}
        for a in dump["actions"].values():
            h = a["handlers"]["slot10"]
            code[int(h["rva"], 16)] = bytes.fromhex(h["bytes"])
        for rva, hexbytes in dump["targets"].items():
            if hexbytes:
                code.setdefault(int(rva, 16), bytes.fromhex(hexbytes))
        rvas = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"#define (RVA_\w+) 0x([0-9A-Fa-f]+)u", src)}
        arrays = {m.group(1): bytes(int(x, 16) for x in re.findall(r"0x([0-9a-f]{2})", m.group(2)))
                  for m in re.finditer(r"static const u8 (RG_EXPECTED_\w+)\[[^\]]+\] = \{(.*?)\};", src, re.S)}
        pairs = {"RG_EXPECTED_MAKE_HANDLER": "RVA_MAKE_HANDLER", "RG_EXPECTED_START_HANDLER": "RVA_START_HANDLER",
                 "RG_EXPECTED_COMPLETE_HANDLER": "RVA_COMPLETE_HANDLER", "RG_EXPECTED_MS_READY": "RVA_MS_READY",
                 "RG_EXPECTED_MS_STATE_BY_NAME": "RVA_MS_STATE_BY_NAME", "RG_EXPECTED_MS_MAKE_A": "RVA_MS_MAKE_A",
                 "RG_EXPECTED_MS_MAKE_B": "RVA_MS_MAKE_B", "RG_EXPECTED_MS_FIND": "RVA_MS_FIND",
                 "RG_EXPECTED_MS_STATE_BY_INDEX": "RVA_MS_STATE_BY_INDEX", "RG_EXPECTED_MS_SET_STATE": "RVA_MS_SET_STATE",
                 "RG_EXPECTED_HANDLER": "RVA_ADD_TO_INVENTORY_HANDLER",
                 "RG_EXPECTED_SET_ACTIVE_HANDLER": "RVA_SET_ACTIVE_HANDLER", "RG_EXPECTED_REPLAY_HANDLER": "RVA_REPLAY_HANDLER",
                 "RG_EXPECTED_MS2_LOOKUP": "RVA_MS2_LOOKUP", "RG_EXPECTED_MS2_STATE": "RVA_MS2_STATE",
                 "RG_EXPECTED_MS2_RESOLVE": "RVA_MS2_RESOLVE", "RG_EXPECTED_MS2_COMPONENT": "RVA_MS2_COMPONENT",
                 "RG_EXPECTED_VANITY_GIVE_HANDLER": "RVA_VANITY_GIVE_HANDLER", "RG_EXPECTED_RESOLVE_HANDLE": "RVA_RESOLVE_HANDLE",
                 "RG_EXPECTED_FIND_COMPONENT_A": "RVA_FIND_COMPONENT_A", "RG_EXPECTED_FIND_COMPONENT_B": "RVA_FIND_COMPONENT_B",
                 "RG_EXPECTED_VANITY_GIVE_BUNDLE": "RVA_VANITY_GIVE_BUNDLE",
                 "RG_EXPECTED_FIRE_OUTPUT": "RVA_FIRE_OUTPUT",
                 # v6 (8.0)
                 "RG_EXPECTED_MS2_STATE_WALK": "RVA_MS2_STATE", "RG_EXPECTED_LEVEL_SET": "RVA_LEVEL_SET_BIT",
                 "RG_EXPECTED_IS_LEVEL_UNLOCKED": "RVA_IS_LEVEL_UNLOCKED",
                 "RG_EXPECTED_UNLOCK_LEVEL_HANDLER": "RVA_UNLOCK_LEVEL_HANDLER",
                 "RG_EXPECTED_PLANETARY_TRAVEL_HANDLER": "RVA_PLANETARY_TRAVEL_HANDLER"}
        for arr, rva_name in pairs.items():
            want = arrays[arr]
            got = code[rvas[rva_name]][:len(want)]
            self.assertEqual(got, want, arr)
        # the handlers really reference the manager global and the alternate-path flag
        from capstone import CS_ARCH_X86, CS_MODE_64, Cs
        md = Cs(CS_ARCH_X86, CS_MODE_64)
        refs = set()
        for ins in md.disasm(arrays["RG_EXPECTED_START_HANDLER"], rvas["RVA_START_HANDLER"]):
            m = re.search(r"\[rip ([+-]) 0x([0-9a-f]+)\]", ins.op_str)
            if m:
                refs.add(ins.address + ins.size + (1 if m.group(1) == "+" else -1) * int(m.group(2), 16))
        self.assertIn(rvas["RVA_MS_MANAGER"], refs)
        self.assertIn(rvas["RVA_MS_ALT_FLAG"], refs)
        self.assertIn(rvas["RVA_MS2_MANAGER"], refs)        # system 2, the branch your game takes
        # v5: the armor handler references the hero handle global and the vanity manager type,
        # and calls exactly the four functions the helper calls
        refs, calls = set(), set()
        for ins in md.disasm(arrays["RG_EXPECTED_VANITY_GIVE_HANDLER"], rvas["RVA_VANITY_GIVE_HANDLER"]):
            m = re.search(r"\[rip ([+-]) 0x([0-9a-f]+)\]", ins.op_str)
            if m:
                refs.add(ins.address + ins.size + (1 if m.group(1) == "+" else -1) * int(m.group(2), 16))
            if ins.mnemonic == "call":
                calls.add(int(ins.op_str, 16))
        self.assertEqual(refs, {rvas["RVA_HERO_HANDLE"], rvas["RVA_VANITY_MANAGER_TYPE"]})
        self.assertEqual(calls, {rvas["RVA_RESOLVE_HANDLE"], rvas["RVA_FIND_COMPONENT_A"], rvas["RVA_FIND_COMPONENT_B"],
                                 rvas["RVA_VANITY_GIVE_BUNDLE"]})
        # v5: the handler is replaced whole, so the check covers all of it (it ends in the tail
        # jump to the output plug function, whose two plugs are the ones the helper fires)
        insns = list(md.disasm(arrays["RG_EXPECTED_VANITY_GIVE_HANDLER"], rvas["RVA_VANITY_GIVE_HANDLER"]))
        self.assertEqual(insns[-1].address + insns[-1].size, rvas["RVA_VANITY_GIVE_HANDLER"] + len(arrays["RG_EXPECTED_VANITY_GIVE_HANDLER"]))
        self.assertEqual((insns[-1].mnemonic, int(insns[-1].op_str, 16)), ("jmp", rvas["RVA_FIRE_OUTPUT"]))
        plugs = {int(i.op_str.split(", ")[1], 16) for i in insns if i.mnemonic == "mov" and i.op_str.startswith("edx, ")}
        self.assertEqual(plugs, {0xCD6C8C3D, 0x329EA4F1})
        self.assertIn("#define RG_PLUG_SUCCESS 0xCD6C8C3Du", src)
        self.assertIn("#define RG_PLUG_FAILURE 0x329EA4F1u", src)
        # the node fields it reads: the script context (+0x58) and the bundle (+0x60)
        self.assertTrue(any(i.op_str == "rdx, qword ptr [rbx + 0x60]" for i in insns))
        self.assertTrue(any(i.op_str == "rcx, qword ptr [rbx + 0x58]" for i in insns))
        # the vtable slot the game calls is this handler, in both dumps
        for dump_name in ("round14_game_code_dump.json", "round15_game_code_dump.json"):
            dd = json.load(open(ROOT / "tests" / "data" / dump_name, encoding="utf-8-sig"))
            self.assertEqual(int(dd["actions"]["VanityGiveBundleAction"]["handlers"]["slot10"]["rva"], 16), rvas["RVA_VANITY_GIVE_HANDLER"])
            t = {int(k, 16): bytes.fromhex(v) for k, v in dd["targets"].items() if v}
            self.assertEqual(t[rvas["RVA_FIRE_OUTPUT"]][:16], arrays["RG_EXPECTED_FIRE_OUTPUT"])
        # both dumps hold the same armor code (same exe in rounds 14 and 15)
        r15all = json.load(open(ROOT / "tests" / "data" / "round15_game_code_dump.json", encoding="utf-8-sig"))
        h15 = bytes.fromhex(r15all["actions"]["VanityGiveBundleAction"]["handlers"]["slot10"]["bytes"])
        self.assertEqual(h15[:len(arrays["RG_EXPECTED_VANITY_GIVE_HANDLER"])], arrays["RG_EXPECTED_VANITY_GIVE_HANDLER"])
        # v6: the 8.0 paths name exactly the globals and functions the helper uses, in both dumps
        def refs_calls(name):
            r, c = set(), []
            for ins in md.disasm(arrays[name], rvas[pairs_rva[name]]):
                m = re.search(r"\[rip ([+-]) 0x([0-9a-f]+)\]", ins.op_str)
                if m:
                    r.add(ins.address + ins.size + (1 if m.group(1) == "+" else -1) * int(m.group(2), 16))
                if ins.mnemonic == "call" and re.match(r"^0x[0-9a-f]+$", ins.op_str):
                    c.append(int(ins.op_str, 16))
            return r, c
        pairs_rva = pairs
        r, c = refs_calls("RG_EXPECTED_UNLOCK_LEVEL_HANDLER")
        self.assertEqual(r, {rvas["RVA_LEVELS_GLOBAL"]})
        self.assertEqual(c.count(rvas["RVA_LEVEL_SET_BIT"]), 2)
        r, c = refs_calls("RG_EXPECTED_PLANETARY_TRAVEL_HANDLER")
        self.assertEqual(r, {rvas["RVA_PLANETARY_TRAVEL_BYTE"]})
        r, c = refs_calls("RG_EXPECTED_MS2_STATE_WALK")
        self.assertEqual(c, [rvas["RVA_MS2_RESOLVE"], rvas["RVA_MS2_COMPONENT"], rvas["RVA_MS2_TABLE_FIND"], rvas["RVA_MS2_ENTRY_FIND"]])
        walk = list(md.disasm(arrays["RG_EXPECTED_MS2_STATE_WALK"], rvas["RVA_MS2_STATE"]))
        ops = [i.mnemonic + " " + i.op_str for i in walk]
        self.assertIn("call qword ptr [rax + 0x38]", ops)            # obj->vt[0x38]: the node id
        self.assertIn("lea rcx, [rsi + 0x1b0]", ops)                 # the manager's save table
        self.assertIn("mov rax, qword ptr [rax + 0x28]", ops)        # the entry's record
        self.assertEqual(ops[-1], "mov eax, dword ptr [rax + 0x30]") # the state
        r15code = {}
        for a in r15all["actions"].values():
            h = a["handlers"]["slot10"]
            r15code[int(h["rva"], 16)] = bytes.fromhex(h["bytes"])
        for rva, hexbytes in r15all["targets"].items():
            if hexbytes:
                r15code.setdefault(int(rva, 16), bytes.fromhex(hexbytes))
        for arr in ("RG_EXPECTED_MS2_STATE_WALK", "RG_EXPECTED_LEVEL_SET", "RG_EXPECTED_IS_LEVEL_UNLOCKED",
                    "RG_EXPECTED_UNLOCK_LEVEL_HANDLER", "RG_EXPECTED_PLANETARY_TRAVEL_HANDLER"):
            self.assertEqual(r15code[rvas[pairs[arr]]][:len(arrays[arr])], arrays[arr], arr + " (round 15)")
        # round 15: the system 1 manager is NULL in your game (Dump-GameCode -Extended)
        r15 = json.load(open(ROOT / "tests" / "data" / "round15_game_code_dump.json", encoding="utf-8-sig"))
        self.assertEqual(r15["mission_manager"]["manager"], "0x0")


@unittest.skipUnless(shutil.which("clang") and shutil.which("lld-link") and shutil.which("llvm-dlltool"),
                     "clang / lld-link / llvm-dlltool not installed")
class ShippedDllTests(unittest.TestCase):
    def test_shipped_dll_is_built_from_the_shipped_source(self):
        with tempfile.TemporaryDirectory() as d:
            work = os.path.join(d, "src")
            shutil.copytree(SRC, work)
            subprocess.run(["sh", "build.sh"], cwd=work, check=True, capture_output=True)
            built = open(os.path.join(work, "out", "rando_give.dll"), "rb").read()
        import hashlib
        # dev 10.24: the source is v7 (it also publishes the SceneManager) and its build IS the kit's
        # rando_give.dll: v7 ran in your game in round32 (SceneManager found 1x, direct delivery ready, armor give
        # verified, mission helper ready). The verified v6 binary (rounds 17-31, sha256 efb92723...) is kept in
        # rando_give_source/release_v6 for a public package (tools/build_public_release.py checks that hash).
        dev = (MOD / "rando_give.dll").read_bytes()
        self.assertEqual(built, dev)            # build.sh pins the link time: byte for byte
        self.assertEqual(hashlib.sha256(dev).hexdigest(),
                         "8055703e7dd7f48e16aa5a081d6795c15d515a52802bd0d70aafe88b54640744")
        shipped = (SRC / "release_v6" / "rando_give.dll").read_bytes()
        self.assertEqual(hashlib.sha256(shipped).hexdigest(),
                         "efb927232f67b7740aec473afa3866dd50636e1c29d0b2822717116a40092c12")


if __name__ == "__main__":
    unittest.main()
