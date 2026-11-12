"""Reads game_code_dump.json (companion/research/Dump-GameCode.ps1) and disassembles each
action handler: calls, RIP-relative globals, node-field offsets and 32-bit constants. This is
what is needed to give a new reward kind a byte-verified path in rando_give.dll.

    pip install capstone
    python tools/analyze_dump.py game_code_dump.json [--action VanityGiveBundleAction]
"""
import argparse
import json
import re
import sys

from capstone import CS_ARCH_X86, CS_MODE_64, Cs


def analyze(code_hex, rva, max_insn=200):
    code = bytes.fromhex(code_hex)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = False
    out = {"calls": [], "globals": [], "fields": set(), "constants": set(), "listing": []}
    for n, ins in enumerate(md.disasm(code, rva)):
        if n >= max_insn:
            break
        text = f"{ins.mnemonic} {ins.op_str}".strip()
        out["listing"].append(f"{ins.address:08X}  {text}")
        if ins.mnemonic == "call" and re.match(r"^0x[0-9a-f]+$", ins.op_str):
            out["calls"].append(int(ins.op_str, 16))
        m = re.search(r"\[rip ([+-]) 0x([0-9a-f]+)\]", ins.op_str)
        if m:
            disp = int(m.group(2), 16) * (1 if m.group(1) == "+" else -1)
            out["globals"].append(ins.address + ins.size + disp)
        for reg, off in re.findall(r"\[(rcx|rbx|rdi|rsi|r14|r15) \+ 0x([0-9a-f]+)\]", ins.op_str):
            out["fields"].add(f"{reg}+0x{off}")
        for c in re.findall(r"0x([0-9a-f]{6,8})\b", ins.op_str):
            if "rip" not in ins.op_str and ins.mnemonic in ("mov", "cmp", "lea") and len(c) >= 7:
                out["constants"].add(int(c, 16))
        if ins.mnemonic in ("ret", "int3") and n > 3:
            break
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--action")
    ap.add_argument("--listing", action="store_true")
    a = ap.parse_args(argv)
    with open(a.dump, encoding="utf-8-sig") as f:
        d = json.load(f)
    print("exe base", d["exe_base"])
    for name, act in d["actions"].items():
        if a.action and name != a.action:
            continue
        print(f"\n== {name} (vtable RVA {act['vtable_rva']})")
        for slot, h in act["handlers"].items():
            if not h.get("bytes"):
                continue
            r = analyze(h["bytes"], int(h["rva"], 16))
            print(f"  {slot} at RVA {h['rva']}: calls {[hex(c) for c in r['calls']]}")
            print(f"      globals {[hex(g) for g in r['globals']]}  fields {sorted(r['fields'])}  constants {[hex(c) for c in sorted(r['constants'])]}")
            if a.listing:
                for line in r["listing"]:
                    print("        " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
