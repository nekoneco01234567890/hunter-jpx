import struct
import sys

SECTOR_SIZE = 512


def u16(b, p):
    return struct.unpack_from("<H", b, p)[0]


def u32(b, p):
    return struct.unpack_from("<I", b, p)[0]


def ole_stream(path, stream_name="Workbook"):
    with open(path, "rb") as f:
        data = f.read()

    if data[:8] != bytes.fromhex("D0 CF 11 E0 A1 B1 1A E1"):
        raise ValueError("NOT_OLE")

    sec_size = 1 << u16(data, 30)
    first_dir = u32(data, 48)

    difat = []
    for i in range(109):
        x = u32(data, 76 + i * 4)
        if x != 0xFFFFFFFF:
            difat.append(x)

    first_difat = u32(data, 68)
    num_difat = u32(data, 72)

    cur = first_difat
    for _ in range(num_difat):
        if cur in (0xFFFFFFFE, 0xFFFFFFFF):
            break
        off = 512 + cur * sec_size
        for j in range(sec_size // 4 - 1):
            x = u32(data, off + j * 4)
            if x != 0xFFFFFFFF:
                difat.append(x)
        cur = u32(data, off + (sec_size // 4 - 1) * 4)

    fat = []
    for s in difat:
        off = 512 + s * sec_size
        for j in range(sec_size // 4):
            fat.append(u32(data, off + j * 4))

    def chain(start):
        out = []
        seen = set()
        s = start
        while s not in (0xFFFFFFFE, 0xFFFFFFFF) and s < len(fat):
            if s in seen:
                raise ValueError("OLE_CHAIN_LOOP")
            seen.add(s)
            out.append(s)
            s = fat[s]
        return out

    directory = bytearray()

    for s in chain(first_dir):
        off = 512 + s * sec_size
        directory += data[off:off + sec_size]

    target = None

    for p in range(0, len(directory), 128):
        if p + 128 > len(directory):
            break

        name_len = u16(directory, p + 64)

        if name_len >= 2:
            raw = directory[p:p + name_len - 2]
            name = raw.decode("utf-16le", errors="replace")
        else:
            name = ""

        obj_type = directory[p + 66]
        start = u32(directory, p + 116)
        size = u32(directory, p + 120)

        if obj_type == 2 and name == stream_name:
            target = (start, size)
            break

    if target is None:
        raise ValueError("WORKBOOK_NOT_FOUND")

    start, size = target
    out = bytearray()

    for s in chain(start):
        off = 512 + s * sec_size
        out += data[off:off + sec_size]
        if len(out) >= size:
            break

    return bytes(out[:size])


def records(wb):
    p = 0

    while p + 4 <= len(wb):
        rid = u16(wb, p)
        ln = u16(wb, p + 2)

        if p + 4 + ln > len(wb):
            break

        yield rid, wb[p + 4:p + 4 + ln], p

        p += 4 + ln


# ------------------------------------------------------------
# SST
# ------------------------------------------------------------

def parse_sst(wb):
    recs = list(records(wb))

    for i, (rid, payload, pos) in enumerate(recs):
        if rid != 0x00FC:
            continue

        total = u32(payload, 0)
        unique = u32(payload, 4)

        segments = [payload[8:]]

        j = i + 1

        while j < len(recs) and recs[j][0] == 0x003C:
            segments.append(recs[j][1])
            j += 1

        data = b"".join(segments)

        p = 0
        strings = []

        def read(n):
            nonlocal p
            if p + n > len(data):
                raise ValueError("SST_STRING_EOF")
            x = data[p:p+n]
            p += n
            return x

        def r8():
            return read(1)[0]

        def r16():
            return struct.unpack("<H", read(2))[0]

        def r32():
            return struct.unpack("<I", read(4))[0]

        for _ in range(unique):
            cch = r16()
            option = r8()

            is_unicode = bool(option & 0x01)
            has_rich = bool(option & 0x08)
            has_phonetic = bool(option & 0x04)

            rich_count = r16() if has_rich else 0
            phonetic_size = r32() if has_phonetic else 0

            if rich_count:
                read(rich_count * 4)

            if is_unicode:
                s = read(cch * 2).decode("utf-16le", errors="replace")
            else:
                s = read(cch).decode("latin1", errors="replace")

            if phonetic_size:
                read(phonetic_size)

            strings.append(s)

        return total, unique, strings


# ------------------------------------------------------------
# RK
# ------------------------------------------------------------

def decode_rk(raw):
    x = u32(raw, 0)

    is_int = x & 0x02
    is_div100 = x & 0x01

    if is_int:
        value = x >> 2

        if value & 0x20000000:
            value -= 0x40000000

    else:
        bits = (x & 0xFFFFFFFC) << 32
        value = struct.unpack("<d", struct.pack("<Q", bits))[0]

    if is_div100:
        value /= 100.0

    return value


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    path = sys.argv[1] if len(sys.argv) > 1 else \
        "/sdcard/Download/stock_val_1_250101.xls"

    wb = ole_stream(path)

    total, unique, sst = parse_sst(wb)

    print("========================================")
    print("BIFF CELL STRUCTURE V5")
    print("========================================")
    print("SST_TOTAL  =", total)
    print("SST_UNIQUE =", unique)
    print("SST_PARSED =", len(sst))
    print("========================================")

    cells = {}

    for rid, payload, pos in records(wb):

        # LABELSST
        if rid == 0x00FD and len(payload) >= 10:

            row = u16(payload, 0)
            col = u16(payload, 2)
            xf = u16(payload, 4)
            idx = u32(payload, 6)

            value = sst[idx] if idx < len(sst) else f"<BAD_SST:{idx}>"

            cells[(row, col)] = (
                "LABELSST",
                value
            )

        # NUMBER
        elif rid == 0x0203 and len(payload) >= 14:

            row = u16(payload, 0)
            col = u16(payload, 2)

            value = struct.unpack("<d", payload[6:14])[0]

            cells[(row, col)] = (
                "NUMBER",
                value
            )

        # RK
        elif rid == 0x027E and len(payload) >= 10:

            row = u16(payload, 0)
            col = u16(payload, 2)

            value = decode_rk(payload[6:10])

            cells[(row, col)] = (
                "RK",
                value
            )

        # MULRK
        elif rid == 0x00BD and len(payload) >= 6:

            row = u16(payload, 0)
            first_col = u16(payload, 2)

            # each RK cell = 6 bytes
            p = 4
            col = first_col

            while p + 6 <= len(payload) - 2:

                xf = u16(payload, p)
                value = decode_rk(payload[p + 2:p + 6])

                cells[(row, col)] = (
                    "MULRK",
                    value
                )

                col += 1
                p += 6

        # LABEL (old BIFF)
        elif rid == 0x0204 and len(payload) >= 8:

            row = u16(payload, 0)
            col = u16(payload, 2)

            value = payload[8:].decode("latin1", errors="replace")

            cells[(row, col)] = (
                "LABEL",
                value
            )

    print("CELL_COUNT =", len(cells))
    print("========================================")
    print("ROWS 1-40")
    print("========================================")

    current_row = None

    for (row, col) in sorted(cells):

        if row > 40:
            break

        if row != current_row:
            current_row = row
            print()
            print(f"--- ROW {row} ---")

        typ, value = cells[(row, col)]

        print(
            f"R={row:02d} C={col:02d} "
            f"{typ:8s} VALUE={value!r}"
        )

    print()
    print("========================================")
    print("RECORD TYPE COUNTS")
    print("========================================")

    counts = {}

    for rid, payload, pos in records(wb):
        counts[rid] = counts.get(rid, 0) + 1

    names = {
        0x00FC: "SST",
        0x003C: "CONTINUE",
        0x00FD: "LABELSST",
        0x0203: "NUMBER",
        0x027E: "RK",
        0x00BD: "MULRK",
        0x0204: "LABEL",
        0x0006: "FORMULA",
        0x000A: "EOF",
    }

    for rid in sorted(counts):
        if rid in names:
            print(
                hex(rid),
                names[rid],
                counts[rid]
            )

    print()
    print("V5_COMPLETE")


if __name__ == "__main__":
    main()
