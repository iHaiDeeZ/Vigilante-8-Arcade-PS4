"""Find direct calls (bl) to given addresses in the 360 image's code.

usage: find_calls.py image.bin 0x82140FD0 ...
"""
import struct
import sys

d = open(sys.argv[1], "rb").read()
BASE = 0x82000000
targets = {int(x, 16) for x in sys.argv[2:]}
CODE = [(0x90000, 0x90000 + 0x29EF64), (0x32F000, 0x390000)]
for lo, hi in CODE:
    for off in range(lo, hi, 4):
        ins = struct.unpack_from(">I", d, off)[0]
        if ins >> 26 != 18:
            continue
        li = ins & 0x03FFFFFC
        if li & 0x02000000:
            li -= 0x04000000
        aa = (ins >> 1) & 1
        lk = ins & 1
        tgt = li if aa else BASE + off + li
        tgt &= 0xFFFFFFFF
        if tgt in targets:
            print(f"{BASE + off:08X}  {'bl' if lk else 'b '} {tgt:08X}")
