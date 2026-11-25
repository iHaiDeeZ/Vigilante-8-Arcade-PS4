#!/usr/bin/env python3
"""Disassemble a range of the 360 image (codegen/image.bin: the loaded layout, base 0x82000000) with capstone
(pip install capstone). VMX128 instructions, which capstone doesn't know, show as .long.

usage: ppcdis.py image.bin start [end|+len]      (hex addresses, e.g. 82134308 821347F0)
"""
import struct
import sys

import capstone

d = open(sys.argv[1], "rb").read()
BASE = 0x82000000
start = int(sys.argv[2], 16)
if len(sys.argv) > 3:
    e = sys.argv[3]
    end = start + int(e[1:], 16) if e.startswith("+") else int(e, 16)
else:
    end = start + 0x100
md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
for a in range(start, end, 4):
    word = d[a - BASE:a - BASE + 4]
    ins = list(md.disasm(word, a))
    if ins:
        i = ins[0]
        extra = ""
        # annotate lis immediates and type-3 PM4 headers
        if i.mnemonic == "lis":
            imm = struct.unpack(">I", word)[0] & 0xFFFF
            extra = f"   ; = 0x{imm:04X}0000"
        print(f"{a:08X}  {struct.unpack('>I', word)[0]:08X}  {i.mnemonic:8s} {i.op_str}{extra}")
    else:
        print(f"{a:08X}  {struct.unpack('>I', word)[0]:08X}  .long (vmx128?)")
