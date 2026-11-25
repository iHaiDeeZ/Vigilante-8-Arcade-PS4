#!/usr/bin/env python3
"""Lays out your Vigilante 8 Arcade DLC packages the way Xenia's (and the SDK's) "install content" leaves them, for
the package's /app0/content (the SDK's content_marketplace_root; the MGR port's scripts/dlc-install-layout.py):

    <out>/0000000000000000/584108A8/00000002/<package>/...          the package's files (stfs-extract.py's folder)
    <out>/0000000000000000/584108A8/Headers/00000002/<package>.header

The .header is the SDK's XCONTENT_AGGREGATE_DATA (0x148 bytes, big-endian fields: device 1 = HDD, content type 2,
the display name from the package, its 42-character file name, xuid 0, the title id) and, when the package's own
license table grants bits, that license mask (ContentManager::InstallContent's rule), as the console would write them.
Files are hard-linked where they can be.

    python3 dlc-layout.py <packages folder> <unpacked folder> <out>
"""
import os
import shutil
import struct
import sys

TITLE = 0x584108A8


def header_record(package_path, name):
    head = open(package_path, "rb").read(0x1000)
    if head[:4] not in (b"LIVE", b"PIRS", b"CON "):
        raise ValueError(f"{package_path}: not an STFS package")
    if struct.unpack_from(">I", head, 0x360)[0] != TITLE:
        raise ValueError(f"{package_path}: not a Vigilante 8 Arcade package")
    display = head[0x411:0x411 + 0x100].decode("utf-16-be", "replace").split("\0")[0]
    mask = 0
    for i in range(0x10):
        _license_id, bits, flags = struct.unpack_from(">QII", head, 0x22C + 16 * i)
        if flags:
            mask |= bits
    rec = bytearray(0x148)
    struct.pack_into(">II", rec, 0, 1, 2)                       # device_id HDD, content_type marketplace
    raw = display.encode("utf-16-be")[:254]
    rec[8:8 + len(raw)] = raw                                   # display_name_raw[128], big-endian, NUL-padded
    rec[0x108:0x108 + 42] = name.encode("ascii")[:42]           # file_name_raw[42] (+2 padding bytes left 0)
    struct.pack_into(">Q", rec, 0x138, 0)                       # xuid
    struct.pack_into(">I", rec, 0x140, TITLE)                   # title_id
    if mask:
        rec += struct.pack("<I", mask)                          # written by the console as a host (little-endian) word
    return bytes(rec), display, mask


def link_or_copy(src, dst):
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    packages, unpacked, out = sys.argv[1:]
    base = os.path.join(out, "0000000000000000", f"{TITLE:08X}")
    content = os.path.join(base, "00000002")
    headers = os.path.join(base, "Headers", "00000002")
    os.makedirs(content, exist_ok=True)
    os.makedirs(headers, exist_ok=True)
    for name in sorted(os.listdir(packages)):
        src = os.path.join(unpacked, name)
        if not os.path.isdir(src):
            print(f"{name[:8]}: not unpacked, skipped")
            continue
        dest = os.path.join(content, name)
        if not os.path.exists(dest):
            shutil.copytree(src, dest, copy_function=link_or_copy, ignore=shutil.ignore_patterns(".extracted"))
        rec, display, mask = header_record(os.path.join(packages, name), name)
        with open(os.path.join(headers, name + ".header"), "wb") as f:
            f.write(rec)
        print(f"DLC {name[:8]}: '{display}', license mask {mask:#x}")


if __name__ == "__main__":
    main()
