#!/usr/bin/env python3
"""Extracts Xbox 360 content packages (STFS: LIVE, PIRS or CON) into folders: the game's XBLA package and its DLC,
for the build (from the MGR-PS4 port).

The block math follows the SDK's reader (sdk/src/filesystem/devices/stfs_container_device.cpp).

    python3 scripts/stfs-extract.py <package or folder of packages> <output folder>

Each package goes to <output folder>/<package file name>/. Packages already extracted (their folder has a
.extracted marker) are skipped.
"""
import os
import struct
import sys

BLOCK = 0x1000
PER_LEVEL = (0xAA, 0x70E4, 0x4AF768)  # blocks covered by one hash table at levels 0, 1, 2
END_OF_CHAIN = 0xFFFFFF


class Package:
    def __init__(self, path):
        self.f = open(path, "rb")
        head = self.f.read(0xA000)
        if head[:4] not in (b"LIVE", b"PIRS", b"CON "):
            raise ValueError("not an STFS package")
        self.header_size = struct.unpack_from(">I", head, 0x340)[0]
        if struct.unpack_from(">I", head, 0x3A9)[0] != 0:
            raise ValueError("SVOD package (not handled here)")
        flags = head[0x37B]
        self.read_only = bool(flags & 1)
        self.root_active = bool(flags & 2)
        self.table_count = struct.unpack_from("<H", head, 0x37C)[0]
        self.table_block = head[0x37E] | head[0x37F] << 8 | head[0x380] << 16
        self.total_blocks = struct.unpack_from(">I", head, 0x395)[0]
        self.per_table = 1 if self.read_only else 2
        self.step0 = PER_LEVEL[0] + self.per_table
        self.step1 = PER_LEVEL[1] + (PER_LEVEL[0] + 1) * self.per_table
        self.base = (self.header_size + BLOCK - 1) // BLOCK * BLOCK
        self.tables = {}

    def offset(self, block_index):
        base, block = PER_LEVEL[0], block_index
        for _ in range(3):
            block += ((block_index + base) // base) * self.per_table
            if block_index < base:
                break
            base *= PER_LEVEL[0]
        return self.base + (block << 12)

    def hash_block(self, block_index, level):
        if level == 0:
            if block_index < PER_LEVEL[0]:
                return 0
            block = (block_index // PER_LEVEL[0]) * self.step0
            block += ((block_index // PER_LEVEL[1]) + 1) * self.per_table
            return block if block_index < PER_LEVEL[1] else block + self.per_table
        if level == 1:
            if block_index < PER_LEVEL[1]:
                return self.step0
            return (block_index // PER_LEVEL[1]) * self.step1 + self.per_table
        return self.step1

    def table(self, offset):
        if offset not in self.tables:
            self.f.seek(offset)
            self.tables[offset] = self.f.read(BLOCK)
        return self.tables[offset]

    def entry_info(self, table, record):
        return struct.unpack_from(">I", table, record * 0x18 + 0x14)[0]

    def next_block(self, block_index):
        secondary = BLOCK if self.root_active else 0
        if self.read_only:
            secondary = 0
        else:
            if self.total_blocks > PER_LEVEL[1]:
                t2 = self.table(self.base + (self.hash_block(block_index, 2) << 12) + secondary)
                info = self.entry_info(t2, (block_index // PER_LEVEL[1]) % PER_LEVEL[0])
                secondary = BLOCK if (info >> 30) & 1 else 0
            if self.total_blocks > PER_LEVEL[0]:
                t1 = self.table(self.base + (self.hash_block(block_index, 1) << 12) + secondary)
                info = self.entry_info(t1, (block_index // PER_LEVEL[0]) % PER_LEVEL[0])
                secondary = BLOCK if (info >> 30) & 1 else 0
        t0 = self.table(self.base + (self.hash_block(block_index, 0) << 12) + secondary)
        return self.entry_info(t0, block_index % PER_LEVEL[0]) & 0xFFFFFF

    def entries(self):
        out, block = [], self.table_block
        for _ in range(self.table_count):
            self.f.seek(self.offset(block))
            data = self.f.read(BLOCK)
            for k in range(0x40):
                e = data[k * 0x40:(k + 1) * 0x40]
                if e[0] == 0:
                    break
                flags = e[0x28]
                out.append({
                    "name": e[:flags & 0x3F].decode("latin-1"),
                    "dir": bool(flags & 0x80),
                    "contiguous": bool(flags & 0x40),
                    "blocks": e[0x2C] | e[0x2D] << 8 | e[0x2E] << 16,
                    "start": e[0x2F] | e[0x30] << 8 | e[0x31] << 16,
                    "parent": struct.unpack_from(">H", e, 0x32)[0],
                    "length": struct.unpack_from(">I", e, 0x34)[0],
                })
            block = self.next_block(block)
            if block == END_OF_CHAIN:
                break
        return out

    def extract(self, dest):
        entries = self.entries()

        def path_of(i):
            parts, e = [], entries[i]
            while True:
                parts.append(e["name"])
                if e["parent"] == 0xFFFF:
                    break
                e = entries[e["parent"]]
            return os.path.join(dest, *reversed(parts))

        files = 0
        for i, e in enumerate(entries):
            p = path_of(i)
            if e["dir"]:
                os.makedirs(p, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(p), exist_ok=True)
            remaining, block = e["length"], e["start"]
            with open(p, "wb") as out:
                n = 0
                while remaining > 0 and block != END_OF_CHAIN:
                    self.f.seek(self.offset(block))
                    chunk = self.f.read(min(BLOCK, remaining))
                    out.write(chunk)
                    remaining -= len(chunk)
                    n += 1
                    block = block + 1 if e["contiguous"] else self.next_block(block)
            if remaining:
                raise IOError(f"{e['name']}: {remaining} bytes missing")
            files += 1
        return files


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    paths = [os.path.join(src, n) for n in sorted(os.listdir(src))] if os.path.isdir(src) else [src]
    for path in paths:
        if not os.path.isfile(path):
            continue
        dest = os.path.join(out, os.path.basename(path))
        if os.path.exists(os.path.join(dest, ".extracted")):
            print(f"{os.path.basename(path)}: already extracted")
            continue
        try:
            files = Package(path).extract(dest)
        except ValueError as e:
            print(f"{os.path.basename(path)}: skipped ({e})")
            continue
        open(os.path.join(dest, ".extracted"), "w").close()
        print(f"{os.path.basename(path)}: {files} files")


if __name__ == "__main__":
    main()
