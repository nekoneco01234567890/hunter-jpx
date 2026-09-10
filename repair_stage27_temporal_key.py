from pathlib import Path
import csv
import re
import struct
from datetime import date, datetime, timedelta

XLS_DIR = Path("/sdcard/Download")
FEATURE_FILE = Path("data/hunter/jpx_hunter_features_weekly.csv")
OUT_FILE = Path("data/hunter/jpx_hunter_features_weekly_temporal.csv")
AUDIT_FILE = Path("data/hunter/jpx_stage27_temporal_audit.csv")


# ============================================================
# OLE / BIFF8
# ============================================================

def ole_stream(path):
    data = path.read_bytes()

    if data[:8] != bytes.fromhex("D0CF11E0A1B11AE1"):
        raise ValueError("NOT_OLE")

    sector_shift = struct.unpack_from("<H", data, 30)[0]
    sector_size = 1 << sector_shift

    first_dir_sector = struct.unpack_from("<I", data, 48)[0]
    mini_cutoff = struct.unpack_from("<I", data, 56)[0]
    first_mini_fat = struct.unpack_from("<I", data, 60)[0]
    num_mini_fat = struct.unpack_from("<I", data, 64)[0]
    first_difat = struct.unpack_from("<I", data, 68)[0]
    num_difat = struct.unpack_from("<I", data, 72)[0]

    def sector(n):
        p = (n + 1) * sector_size
        return data[p:p + sector_size]

    difat = list(struct.unpack_from("<109I", data, 76))

    cur = first_difat
    for _ in range(num_difat):
        if cur in (0xFFFFFFFE, 0xFFFFFFFF):
            break
        s = sector(cur)
        vals = list(struct.unpack_from("<127I", s, 0))
        difat.extend(vals)
        cur = struct.unpack_from("<I", s, 508)[0]

    difat = [x for x in difat if x not in (0xFFFFFFFF,)]

    dir_data = bytearray()

    cur = first_dir_sector
    seen = set()

    while cur not in (0xFFFFFFFE, 0xFFFFFFFF) and cur not in seen:
        seen.add(cur)
        dir_data.extend(sector(cur))
        nxt = struct.unpack_from("<I", sector(cur), 508)[0]
        cur = nxt

    entries = []

    for off in range(0, len(dir_data), 128):
        e = dir_data[off:off + 128]
        if len(e) < 128:
            continue

        name_len = struct.unpack_from("<H", e, 64)[0]
        name = ""
        if name_len >= 2:
            raw = e[:name_len - 2]
            try:
                name = raw.decode("utf-16le")
            except Exception:
                name = ""

        obj_type = e[66]
        left = struct.unpack_from("<I", e, 68)[0]
        right = struct.unpack_from("<I", e, 72)[0]
        child = struct.unpack_from("<I", e, 76)[0]
        start = struct.unpack_from("<I", e, 116)[0]
        size = struct.unpack_from("<Q", e, 120)[0]

        entries.append({
            "name": name,
            "type": obj_type,
            "left": left,
            "right": right,
            "child": child,
            "start": start,
            "size": size,
        })

    root = None
    workbook = None

    for e in entries:
        if e["type"] == 5:
            root = e
        elif e["type"] == 2 and e["name"] == "Workbook":
            workbook = e

    if workbook is None:
        for e in entries:
            if e["type"] == 2 and e["name"].lower() in ("workbook", "book"):
                workbook = e
                break

    if workbook is None:
        raise ValueError("WORKBOOK_STREAM_NOT_FOUND")

    def read_chain(start, size):
        out = bytearray()
        cur = start
        seen = set()

        while cur not in (0xFFFFFFFE, 0xFFFFFFFF) and cur not in seen:
            seen.add(cur)
            s = sector(cur)
            out.extend(s)
            fat_index = cur
            if fat_index >= len(difat):
                break
            cur = difat[fat_index]

        return bytes(out[:size])

    return read_chain(workbook["start"], workbook["size"])


def records(wb):
    pos = 0
    n = len(wb)

    while pos + 4 <= n:
        rid, ln = struct.unpack_from("<HH", wb, pos)
        pos += 4
        payload = wb[pos:pos + ln]
        pos += ln
        yield rid, payload


def parse_sst(wb):
    sst = []
    total = None
    unique = None

    strings = []

    for rid, p in records(wb):
        if rid == 0x00FC:
            total, unique = struct.unpack_from("<II", p, 0)
            strings.append(p[8:])

        elif rid == 0x003C:
            strings.append(p)

    if not strings:
        return sst

    blob = b"".join(strings)
    pos = 0

    for _ in range(unique):
        if pos + 3 > len(blob):
            break

        cch = struct.unpack_from("<H", blob, pos)[0]
        pos += 2

        flags = blob[pos]
        pos += 1

        is16 = bool(flags & 0x01)
        has_rich = bool(flags & 0x08)
        has_ext = bool(flags & 0x04)

        runs = 0
        ext_len = 0

        if has_rich:
            runs = struct.unpack_from("<H", blob, pos)[0]
            pos += 2

        if has_ext:
            ext_len = struct.unpack_from("<I", blob, pos)[0]
            pos += 4

        byte_len = cch * (2 if is16 else 1)

        raw = blob[pos:pos + byte_len]
        pos += byte_len

        try:
            text = raw.decode("utf-16le") if is16 else raw.decode("latin1")
        except Exception:
            text = ""

        pos += runs * 4
        pos += ext_len

        sst.append(text)

    return sst


def get_cells(wb, sst):
    cells = {}

    for rid, p in records(wb):

        if rid == 0x0203:  # NUMBER
            if len(p) >= 14:
                row, col = struct.unpack_from("<HH", p, 0)
                value = struct.unpack_from("<d", p, 6)[0]
                cells[(row, col)] = value

        elif rid == 0x00FD:  # LABELSST
            if len(p) >= 10:
                row, col, sst_id = struct.unpack_from("<HHI", p, 0)
                if 0 <= sst_id < len(sst):
                    cells[(row, col)] = sst[sst_id]

        elif rid == 0x0204:  # LABEL
            if len(p) >= 8:
                row, col, ln = struct.unpack_from("<HHH", p, 0)
                raw = p[6:6 + ln]
                try:
                    cells[(row, col)] = raw.decode("latin1")
                except Exception:
                    pass

        elif rid == 0x0201:  # BLANK
            pass

    return cells


# ============================================================
# Temporal extraction
# ============================================================

def extract_observation_period(path):
    wb = ole_stream(path)
    sst = parse_sst(wb)
    cells = get_cells(wb, sst)

    candidates = []

    for (row, col), value in cells.items():
        if not isinstance(value, str):
            continue

        text = value.strip()

        # Example:
        # 2025年1月第1週 2025/1 week1 ( 1/6 - 1/10 )
        if "week" in text.lower() and "-" in text:
            candidates.append(text)

    if not candidates:
        raise ValueError("OBSERVATION_PERIOD_NOT_FOUND")

    text = candidates[0]

    m = re.search(
        r"(\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})",
        text
    )

    if not m:
        raise ValueError("OBSERVATION_DATE_RANGE_NOT_FOUND")

    m_month1, m_day1, m_month2, m_day2 = map(int, m.groups())

    # Year comes from filename identifier.
    # Files are stock_val_1_YYMMDD.xls
    fm = re.search(r"stock_val_1_(\d{6})\.xls$", path.name)

    if not fm:
        raise ValueError("FILE_DATE_NOT_FOUND")

    yymmdd = fm.group(1)
    year = 2000 + int(yymmdd[:2])

    start = date(year, m_month1, m_day1)
    end = date(year, m_month2, m_day2)

    return text, start.isoformat(), end.isoformat()


# ============================================================
# Main
# ============================================================

with FEATURE_FILE.open("r", encoding="utf-8-sig") as f:
    feature_rows = list(csv.DictReader(f))

if len(feature_rows) != 52:
    raise SystemExit(
        f"FAIL: expected 52 feature rows but got {len(feature_rows)}"
    )

files = sorted(XLS_DIR.glob("stock_val_1_*.xls"))

if len(files) != 52:
    raise SystemExit(
        f"FAIL: expected 52 XLS files but got {len(files)}"
    )

periods = []

audit_rows = []

for path in files:
    try:
        text, start, end = extract_observation_period(path)

        periods.append({
            "file": path.name,
            "source_text": text,
            "start": start,
            "end": end,
        })

        audit_rows.append({
            "FILE": path.name,
            "STATUS": "PASS",
            "OBSERVATION_START": start,
            "OBSERVATION_END": end,
            "SOURCE_TEXT": text,
            "ERROR": "",
        })

    except Exception as e:
        audit_rows.append({
            "FILE": path.name,
            "STATUS": "FAIL",
            "OBSERVATION_START": "",
            "OBSERVATION_END": "",
            "SOURCE_TEXT": "",
            "ERROR": repr(e),
        })

if any(x["STATUS"] == "FAIL" for x in audit_rows):
    with AUDIT_FILE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=audit_rows[0].keys())
        w.writeheader()
        w.writerows(audit_rows)

    raise SystemExit("FAIL: observation period extraction failed")


# Sort by actual observation start
periods.sort(key=lambda x: x["start"])

# Exact uniqueness
keys = [
    (x["start"], x["end"])
    for x in periods
]

if len(set(keys)) != 52:
    raise SystemExit("FAIL: duplicate observation periods")


# Validate chronological order
for a, b in zip(periods, periods[1:]):
    if a["start"] >= b["start"]:
        raise SystemExit("FAIL: observation periods are not chronological")


# Existing feature rows are ordered by source file/month/week identifier.
# Reattach according to chronological order.
#
# The important point is that the old WEEK column is NOT trusted.
# We only preserve it as LEGACY_WEEK.

if len(feature_rows) != len(periods):
    raise SystemExit("FAIL: feature/period count mismatch")

for row, period in zip(feature_rows, periods):
    row["LEGACY_WEEK"] = row["WEEK"]
    row["OBSERVATION_START"] = period["start"]
    row["OBSERVATION_END"] = period["end"]
    row["PERIOD_KEY"] = (
        period["start"] + "__" + period["end"]
    )
    row["WEEK"] = period["start"]

# ============================================================
# Final structural validation
# ============================================================

out_fields = list(feature_rows[0].keys())

duplicate_periods = len(
    feature_rows
) - len(
    set(r["PERIOD_KEY"] for r in feature_rows)
)

missing_start = sum(
    not r["OBSERVATION_START"] for r in feature_rows
)

missing_end = sum(
    not r["OBSERVATION_END"] for r in feature_rows
)

bad_range = sum(
    r["OBSERVATION_START"] > r["OBSERVATION_END"]
    for r in feature_rows
)

# Audit
with AUDIT_FILE.open("w", newline="", encoding="utf-8") as f:
    fields = [
        "FILE",
        "STATUS",
        "OBSERVATION_START",
        "OBSERVATION_END",
        "SOURCE_TEXT",
        "ERROR",
    ]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(audit_rows)

if duplicate_periods:
    raise SystemExit("FAIL: duplicate PERIOD_KEY")

if missing_start or missing_end:
    raise SystemExit("FAIL: missing observation dates")

if bad_range:
    raise SystemExit("FAIL: invalid observation range")


with OUT_FILE.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=out_fields)
    w.writeheader()
    w.writerows(feature_rows)


print("========================================")
print("STAGE27A TEMPORAL REPAIR")
print("========================================")
print("FEATURE_ROWS          :", len(feature_rows))
print("XLS_FILES             :", len(files))
print("PERIOD_ROWS           :", len(periods))
print("UNIQUE_PERIODS        :", len(set(keys)))
print("DUPLICATE_PERIODS     :", duplicate_periods)
print("MISSING_START         :", missing_start)
print("MISSING_END           :", missing_end)
print("BAD_RANGE             :", bad_range)

print()
print("=== RECONSTRUCTED PERIODS ===")

for p in periods:
    print(
        p["file"],
        "=>",
        p["start"],
        "~",
        p["end"]
    )

print()
print("OUTPUT                :", OUT_FILE)
print("AUDIT                 :", AUDIT_FILE)

if (
    len(feature_rows) == 52
    and len(periods) == 52
    and duplicate_periods == 0
    and missing_start == 0
    and missing_end == 0
    and bad_range == 0
):
    print()
    print("TEMPORAL_REPAIR_AUDIT : PASS")
else:
    print()
    print("TEMPORAL_REPAIR_AUDIT : FAIL")

