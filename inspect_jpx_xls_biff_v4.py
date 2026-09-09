import struct
import sys

SECTOR_SIZE = 512
MINI_SECTOR_SIZE = 64


def u16(b, p):
    return struct.unpack_from("<H", b, p)[0]


def u32(b, p):
    return struct.unpack_from("<I", b, p)[0]


def ole_stream(path, stream_name="Workbook"):
    with open(path, "rb") as f:
        data = f.read()

    if data[:8] != bytes.fromhex("D0 CF 11 E0 A1 B1 1A E1"):
        raise ValueError("NOT_OLE")

    sec_shift = u16(data, 30)
    sec_size = 1 << sec_shift

    first_dir_sector = u32(data, 48)
    first_mini_fat_sector = u32(data, 60)
    num_mini_fat = u32(data, 64)
    first_difat = u32(data, 68)
    num_difat = u32(data, 72)

    FAT = []

    # DIFAT from header
    difat = []
    for i in range(109):
        x = u32(data, 76 + i * 4)
        if x != 0xFFFFFFFF:
            difat.append(x)

    # DIFAT extension
    cur = first_difat
    for _ in range(num_difat):
        if cur in (0xFFFFFFFE, 0xFFFFFFFF):
            break
        off = 512 + cur * sec_size
        for j in range((sec_size // 4) - 1):
            x = u32(data, off + j * 4)
            if x != 0xFFFFFFFF:
                difat.append(x)
        cur = u32(data, off + (sec_size // 4 - 1) * 4)

    for s in difat:
        off = 512 + s * sec_size
        for j in range(sec_size // 4):
            FAT.append(u32(data, off + j * 4))

    def chain(start):
        out = []
        s = start
        seen = set()
        while s not in (0xFFFFFFFE, 0xFFFFFFFF) and s < len(FAT):
            if s in seen:
                raise ValueError("OLE_CHAIN_LOOP")
            seen.add(s)
            out.append(s)
            s = FAT[s]
        return out

    # Directory
    directory = bytearray()
    for s in chain(first_dir_sector):
        off = 512 + s * sec_size
        directory += data[off:off + sec_size]

    entries = []

    for p in range(0, len(directory), 128):
        if p + 128 > len(directory):
            break

        name_len = u16(directory, p + 64)

        if name_len < 2:
            name = ""
        else:
            raw = directory[p:p + name_len - 2]
            name = raw.decode("utf-16le", errors="replace")

        obj_type = directory[p + 66]
        left = u32(directory, p)
        right = u32(directory, p + 4)
        child = u32(directory, p + 8)

        start_sector = u32(directory, p + 116)
        size = u32(directory, p + 120)

        entries.append({
            "name": name,
            "type": obj_type,
            "left": left,
            "right": right,
            "child": child,
            "start": start_sector,
            "size": size
        })

    target = None

    for e in entries:
        if e["name"] == stream_name and e["type"] == 2:
            target = e
            break

    if target is None:
        raise ValueError("WORKBOOK_STREAM_NOT_FOUND")

    size = target["size"]

    out = bytearray()

    # This workbook is large enough to use normal FAT stream
    for s in chain(target["start"]):
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

        payload = wb[p + 4:p + 4 + ln]

        yield rid, payload, p

        p += 4 + ln


def parse_sst_segments(wb):
    recs = list(records(wb))

    for i, (rid, payload, pos) in enumerate(recs):
        if rid != 0x00FC:
            continue

        if len(payload) < 8:
            raise ValueError("SST_HEADER_SHORT")

        total = u32(payload, 0)
        unique = u32(payload, 4)

        segments = [payload[8:]]

        j = i + 1

        while j < len(recs) and recs[j][0] == 0x003C:
            segments.append(recs[j][1])
            j += 1

        return total, unique, segments

    raise ValueError("SST_NOT_FOUND")


class SegReader:
    def __init__(self, segments):
        self.segments = segments
        self.si = 0
        self.pi = 0

    def remaining(self):
        if self.si >= len(self.segments):
            return 0
        return sum(len(x) for x in self.segments[self.si:]) - self.pi

    def read_byte(self):
        while self.si < len(self.segments):
            seg = self.segments[self.si]

            if self.pi < len(seg):
                b = seg[self.pi]
                self.pi += 1
                return b

            self.si += 1
            self.pi = 0

        raise ValueError("SST_STRING_EOF")

    def read_bytes(self, n):
        out = bytearray()

        for _ in range(n):
            out.append(self.read_byte())

        return bytes(out)

    def read_u16(self):
        return struct.unpack("<H", self.read_bytes(2))[0]

    def read_u32(self):
        return struct.unpack("<I", self.read_bytes(4))[0]

    def current_segment_remaining(self):
        if self.si >= len(self.segments):
            return 0
        return len(self.segments[self.si]) - self.pi

    def next_segment(self):
        if self.si + 1 >= len(self.segments):
            return False
        self.si += 1
        self.pi = 0
        return True


def parse_one_sst_string(reader):
    cch = reader.read_u16()
    option = reader.read_byte()

    is_unicode = bool(option & 0x01)
    has_rich = bool(option & 0x08)
    has_phonetic = bool(option & 0x04)

    rich_count = reader.read_u16() if has_rich else 0
    phonetic_size = reader.read_u32() if has_phonetic else 0

    # Rich-text formatting runs
    if rich_count:
        reader.read_bytes(rich_count * 4)

    # Character data
    raw = bytearray()

    if is_unicode:
        raw = bytearray(reader.read_bytes(cch * 2))
        text = bytes(raw).decode("utf-16le", errors="replace")
    else:
        raw = bytearray(reader.read_bytes(cch))
        text = bytes(raw).decode("latin1", errors="replace")

    # Phonetic data
    if phonetic_size:
        reader.read_bytes(phonetic_size)

    return text


def parse_sst(wb):
    total, unique, segments = parse_sst_segments(wb)

    # For this inspection stage, concatenate the SST + CONTINUE
    # payloads. Rich-text strings are handled correctly.
    combined = b"".join(segments)

    # Reparse with a normal byte reader.
    class SimpleReader:
        def __init__(self, data):
            self.data = data
            self.p = 0

        def read_byte(self):
            if self.p >= len(self.data):
                raise ValueError("SST_STRING_EOF")
            b = self.data[self.p]
            self.p += 1
            return b

        def read_bytes(self, n):
            if self.p + n > len(self.data):
                raise ValueError("SST_STRING_EOF")
            x = self.data[self.p:self.p+n]
            self.p += n
            return x

        def read_u16(self):
            return struct.unpack("<H", self.read_bytes(2))[0]

        def read_u32(self):
            return struct.unpack("<I", self.read_bytes(4))[0]

    r = SimpleReader(combined)

    strings = []

    try:
        for i in range(unique):
            strings.append(parse_one_sst_string(r))
    except Exception as e:
        return total, unique, strings, "PARTIAL:" + type(e).__name__ + ":" + str(e), r.p

    return total, unique, strings, "PASS", r.p


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "/sdcard/Download/stock_val_1_250101.xls"

    wb = ole_stream(path)

    total, unique, strings, status, used = parse_sst(wb)

    print("========================================")
    print("BIFF8 SST V4")
    print("========================================")
    print("TOTAL =", total)
    print("UNIQUE =", unique)
    print("PARSED =", len(strings))
    print("STATUS =", status)
    print("USED_BYTES =", used)
    print("========================================")
    print("SST SAMPLE")

    for i, s in enumerate(strings[:30]):
        print(f"{i}: {s!r}")

    print("========================================")
    print("TARGET CHECK")

    targets = [
        "(売り買い合計)",
        "総",
        "計",
        "Sales",
        "Purchases",
        "Proprietary",
    ]

    for t in targets:
        hits = [i for i, s in enumerate(strings) if t in s]
        print(repr(t), "=>", hits[:20])

    print("========================================")
    print("V4_COMPLETE")


if __name__ == "__main__":
    main()
