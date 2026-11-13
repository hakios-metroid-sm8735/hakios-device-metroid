#!/usr/bin/env python3
"""Split the DTBs out of a vendor_boot (v3/v4) image and the DTBOs out of a dtbo image.

usage: tools/dtextract.py VENDOR_BOOT DTBO OUTDIR
"""
import os
import struct
import sys

FDT_MAGIC = 0xD00DFEED


def align(n, page):
    return (n + page - 1) // page * page


def split_fdts(blob):
    """Return every FDT that starts at an FDT magic in blob, using its totalsize."""
    out, i = [], 0
    while i + 8 <= len(blob):
        if struct.unpack_from(">I", blob, i)[0] == FDT_MAGIC:
            size = struct.unpack_from(">I", blob, i + 4)[0]
            if 0x40 <= size <= len(blob) - i:
                out.append(blob[i:i + size])
                i += size
                continue
        i += 4
    return out


def vendor_boot_dtb(path):
    data = open(path, "rb").read()
    if data[:8] != b"VNDRBOOT":
        sys.exit("%s: not a vendor_boot image" % path)
    version, page = struct.unpack_from("<II", data, 8)
    # magic(8) version(4) page(4) kernel_addr(4) ramdisk_addr(4) vendor_ramdisk_size(4) cmdline(2048)
    # tags_addr(4) name(16) header_size(4) dtb_size(4) dtb_addr(8)
    off = 8 + 4 + 4 + 4 + 4
    ramdisk_size = struct.unpack_from("<I", data, off)[0]
    off += 4
    cmdline = data[off:off + 2048].split(b"\0")[0].decode(errors="replace")
    off += 2048 + 4 + 16
    header_size, dtb_size = struct.unpack_from("<II", data, off)
    dtb_off = align(header_size, page) + align(ramdisk_size, page)
    print("vendor_boot: header v%d, page %d, ramdisk %d bytes, dtb %d bytes at 0x%x" %
          (version, page, ramdisk_size, dtb_size, dtb_off))
    print("vendor_boot cmdline: %s" % cmdline)
    return data[dtb_off:dtb_off + dtb_size], cmdline


def dtbo_entries(path):
    data = open(path, "rb").read()
    magic, total, hdr, entry_size, count, entries_off = struct.unpack_from(">IIIIII", data, 0)
    if magic != 0xD7B7AB1E:
        sys.exit("%s: not a DT table image" % path)
    out = []
    for n in range(count):
        e = entries_off + n * entry_size
        size, offset, ident, rev = struct.unpack_from(">IIII", data, e)
        out.append((n, ident, rev, data[offset:offset + size]))
    print("dtbo: %d entries" % count)
    return out


def main():
    vb, dtbo, outdir = sys.argv[1:4]
    os.makedirs(outdir, exist_ok=True)
    dtb, cmdline = vendor_boot_dtb(vb)
    with open(os.path.join(outdir, "vendor_boot.cmdline"), "w") as f:
        f.write(cmdline + "\n")
    for n, fdt in enumerate(split_fdts(dtb)):
        name = os.path.join(outdir, "base-%02d.dtb" % n)
        open(name, "wb").write(fdt)
        print("wrote %s (%d bytes)" % (name, len(fdt)))
    for n, ident, rev, blob in dtbo_entries(dtbo):
        name = os.path.join(outdir, "overlay-%02d.dtbo" % n)
        open(name, "wb").write(blob)
        print("wrote %s (%d bytes, id 0x%x, rev 0x%x)" % (name, len(blob), ident, rev))


if __name__ == "__main__":
    main()
