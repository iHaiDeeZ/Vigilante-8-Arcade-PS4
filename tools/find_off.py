"""Find loads/stores with given displacements (e.g. device fields) in the 360 image's code.

usage: find_off.py image.bin 0x33c0 0x33c4 ...
"""
import struct
import sys

d = open(sys.argv[1], "rb").read()
BASE = 0x82000000
want = {int(x, 16) for x in sys.argv[2:]}
CODE = [(0x90000, 0x90000 + 0x29EF64), (0x32F000, 0x390000)]
NAMES = {32: "lwz", 33: "lwzu", 34: "lbz", 35: "lbzu", 36: "stw", 37: "stwu", 38: "stb", 39: "stbu", 40: "lhz",
         42: "lha", 44: "sth", 46: "lmw", 47: "stmw", 48: "lfs", 50: "lfd", 52: "stfs", 54: "stfd", 14: "addi",
         58: "ld", 62: "std"}
for lo, hi in CODE:
    for off in range(lo, hi, 4):
        ins = struct.unpack_from(">I", d, off)[0]
        op = ins >> 26
        if op not in NAMES:
            continue
        disp = ins & 0xFFFF
        if op in (58, 62):
            disp &= 0xFFFC
        if disp & 0x8000:
            disp -= 0x10000
        if disp in want:
            rt = (ins >> 21) & 31
            ra = (ins >> 16) & 31
            print(f"{BASE + off:08X}  {NAMES[op]} r{rt}, 0x{disp:x}(r{ra})")
