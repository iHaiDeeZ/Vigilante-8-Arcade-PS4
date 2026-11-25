"""Find PM4 type-3 packet headers built in code (lis rX,0xC0nn + ori/addi rY,rX,opcode<<8|pred) in the XEX image.

usage: find_pm4.py image.bin
"""
import struct
import sys

d = open(sys.argv[1], "rb").read()
BASE = 0x82000000
OPS = {0x5A: "EVENT_WRITE_EXT", 0x50: "SET_BIN_MASK", 0x51: "SET_BIN_SELECT", 0x60: "SET_BIN_MASK_LO",
       0x61: "SET_BIN_MASK_HI", 0x62: "SET_BIN_SELECT_LO", 0x63: "SET_BIN_SELECT_HI", 0x34: "DRAW_INDX_BIN",
       0x35: "DRAW_INDX_2_BIN", 0x4B: "SET_BIN_BASE_OFFSET", 0x22: "DRAW_INDX", 0x36: "DRAW_INDX_2",
       0x23: "VIZ_QUERY", 0x5B: "EVENT_WRITE_ZPD", 0x44: "COND_EXEC", 0x45: "COND_WRITE", 0x3F: "INDIRECT_BUFFER",
       0x37: "INDIRECT_BUFFER_PFD", 0x46: "EVENT_WRITE", 0x3C: "WAIT_REG_MEM", 0x3D: "MEM_WRITE", 0x21: "REG_RMW"}
CODE = [(0x90000, 0x90000 + 0x29EF64), (0x32F000, 0x390000)]
hits = []
for lo, hi in CODE:
    for off in range(lo, hi, 4):
        ins = struct.unpack_from(">I", d, off)[0]
        op = ins >> 26
        if op not in (24, 14):  # ori, addi
            continue
        rd = (ins >> 21) & 31
        ra = (ins >> 16) & 31
        imm = ins & 0xFFFF
        if op == 24:  # ori rA, rS, imm: source is rd field
            src, dst = rd, ra
        else:  # addi rD, rA, imm
            src, dst = ra, rd
            if src == 0:
                continue
        opc = imm >> 8
        if opc not in OPS or (imm & 0xFE) != 0:
            continue
        # look back for lis src, 0xC0nn
        for back in range(1, 12):
            o2 = off - 4 * back
            if o2 < lo:
                break
            i2 = struct.unpack_from(">I", d, o2)[0]
            if (i2 >> 26) == 15 and ((i2 >> 16) & 31) == 0 and ((i2 >> 21) & 31) == src:
                hi16 = i2 & 0xFFFF
                if (hi16 & 0xC000) == 0xC000:
                    count = (hi16 & 0x3FFF) + 1
                    hits.append((BASE + off, OPS[opc], count, imm & 1))
                break
for addr, name, count, pred in hits:
    print(f"{addr:08X}  {name:20s} count {count}{'  predicated' if pred else ''}")
print(len(hits), "hits")
