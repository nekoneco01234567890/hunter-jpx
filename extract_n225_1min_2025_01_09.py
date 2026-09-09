from zipfile import ZipFile
from xml.etree.ElementTree import iterparse
from datetime import datetime, timedelta
from pathlib import Path
import csv
import sys

XLSX = Path("data/n225_raw/N225f_2025.xlsx")
OUT_DIR = Path("data/n225_raw")

RAW_OUT = OUT_DIR / "N225_1MIN_RAW_2025_01_09.csv"
AUDIT_OUT = OUT_DIR / "N225_1MIN_RAW_2025_01_09_AUDIT.csv"
SUMMARY_OUT = OUT_DIR / "N225_1MIN_RAW_2025_01_09_SUMMARY.csv"

START_DATE = "2025-01-01"
END_DATE = "2025-09-30"

EPOCH = datetime(1899, 12, 30)
BUF = 1024 * 1024

def xdate(v):
    return (EPOCH + timedelta(days=float(v))).strftime("%Y-%m-%d")

def xtime(v):
    sec = round(float(v) * 86400) % 86400
    return f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"

def to_num(v):
    return float(v)

def time_sec(t):
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s

def session_of(t):
    s = time_sec(t)

    if 17 * 3600 <= s or s < 6 * 3600:
        return "NIGHT"

    if 6 * 3600 <= s < 8 * 3600 + 45 * 60:
        return "BREAK"

    if 8 * 3600 + 45 * 60 <= s <= 15 * 3600 + 45 * 60:
        return "DAY"

    return "OTHER"

def is_valid_ohlcv(o, h, l, c, v):
    if h < l:
        return False
    if o < l or o > h:
        return False
    if c < l or c > h:
        return False
    if v < 0:
        return False
    return True

if not XLSX.exists():
    print("ERROR: FILE_NOT_FOUND")
    print(XLSX)
    sys.exit(1)

OUT_DIR.mkdir(parents=True, exist_ok=True)

print("========================================")
print("N225 1MIN EXTRACTION 2025-01 ~ 2025-09")
print("========================================")
print("INPUT =", XLSX)
print("SHEET = 1min")
print("RANGE =", START_DATE, "~", END_DATE)
print()

total = 0
exported = 0
header_rows = 0
invalid_rows = 0
outside_rows = 0
duplicate_rows = 0
backward_rows = 0
interval_anomaly = 0
session_breaks = 0

min_date = None
max_date = None

last_key = None
last_date = None
last_time_sec = None

date_counts = {}

seen_keys = set()

with ZipFile(XLSX) as z:
    with z.open("xl/worksheets/sheet1.xml") as f, \
         open(RAW_OUT, "w", newline="", encoding="utf-8", buffering=BUF) as out:

        writer = csv.writer(out)
        writer.writerow([
            "DATE",
            "TIME",
            "DATETIME",
            "SESSION",
            "OPEN",
            "HIGH",
            "LOW",
            "CLOSE",
            "VOLUME",
            "SOURCE_FILE",
            "SOURCE_SHEET",
            "POINT_IN_TIME_STATUS",
            "DATA_STATUS"
        ])

        for event, elem in iterparse(f, events=("end",)):

            if not elem.tag.endswith("}row"):
                continue

            row_no = elem.attrib.get("r", "")

            if row_no == "1":
                header_rows += 1
                elem.clear()
                continue

            cells = {}

            for c in elem:
                if not c.tag.endswith("}c"):
                    continue

                ref = c.attrib.get("r", "")
                col = "".join(ch for ch in ref if ch.isalpha())

                v = c.findtext(".//{*}v")

                if v is not None:
                    cells[col] = v

            elem.clear()

            if not all(k in cells for k in ("A", "B", "C", "D", "E", "F", "G")):
                continue

            total += 1

            try:
                date = xdate(cells["A"])
                time = xtime(cells["B"])

                o = to_num(cells["C"])
                h = to_num(cells["D"])
                l = to_num(cells["E"])
                c = to_num(cells["F"])
                v = to_num(cells["G"])

            except Exception:
                invalid_rows += 1
                continue

            if date < START_DATE or date > END_DATE:
                outside_rows += 1
                continue

            if not is_valid_ohlcv(o, h, l, c, v):
                invalid_rows += 1
                continue

            key = (date, time)

            if key in seen_keys:
                duplicate_rows += 1
                continue

            seen_keys.add(key)

            tsec = time_sec(time)

            if last_date == date and last_time_sec is not None:

                diff = tsec - last_time_sec

                # Midnight crossing
                if diff < 0:
                    diff += 86400

                # Expected session break
                if last_time_sec == 15 * 3600 + 45 * 60 and \
                   tsec == 17 * 3600:
                    session_breaks += 1

                elif last_time_sec == 6 * 3600 and \
                     tsec == 8 * 3600 + 45 * 60:
                    session_breaks += 1

                elif diff != 60:
                    interval_anomaly += 1

                if tsec < last_time_sec and diff < 0:
                    backward_rows += 1

            last_date = date
            last_time_sec = tsec
            last_key = key

            session = session_of(time)

            writer.writerow([
                date,
                time,
                f"{date} {time}",
                session,
                int(o) if o.is_integer() else o,
                int(h) if h.is_integer() else h,
                int(l) if l.is_integer() else l,
                int(c) if c.is_integer() else c,
                int(v) if v.is_integer() else v,
                XLSX.name,
                "1min",
                "AVAILABLE_AT_OR_BEFORE_BAR_TIME",
                "VALID"
            ])

            exported += 1

            date_counts[date] = date_counts.get(date, 0) + 1

            if min_date is None or date < min_date:
                min_date = date

            if max_date is None or date > max_date:
                max_date = date

print("========== EXTRACTION RESULT ==========")
print("TOTAL SOURCE ROWS =", total)
print("EXPORTED =", exported)
print("OUTSIDE_RANGE =", outside_rows)
print("INVALID =", invalid_rows)
print("DUPLICATES =", duplicate_rows)
print("BACKWARD_OR_INVALID =", backward_rows)
print("UNEXPECTED_INTERVALS =", interval_anomaly)
print("EXPECTED_SESSION_BREAKS =", session_breaks)
print("DATE_RANGE =", min_date, "~", max_date)
print("UNIQUE DATES =", len(date_counts))
print()

# Audit CSV
with open(AUDIT_OUT, "w", newline="", encoding="utf-8", buffering=BUF) as f:
    w = csv.writer(f)
    w.writerow([
        "AUDIT_ITEM",
        "VALUE",
        "STATUS"
    ])

    w.writerow(["SOURCE_FILE", str(XLSX), "PASS"])
    w.writerow(["SOURCE_SHEET", "1min", "PASS"])
    w.writerow(["EXPORTED_ROWS", exported, "PASS" if exported > 0 else "FAIL"])
    w.writerow(["DATE_RANGE", f"{min_date}~{max_date}", "PASS"])
    w.writerow(["UNIQUE_DATES", len(date_counts), "PASS"])
    w.writerow(["DUPLICATES", duplicate_rows, "PASS" if duplicate_rows == 0 else "FAIL"])
    w.writerow(["BACKWARD_OR_INVALID", backward_rows, "PASS" if backward_rows == 0 else "FAIL"])
    w.writerow(["INVALID_OHLCV", invalid_rows, "PASS" if invalid_rows == 0 else "FAIL"])
    w.writerow([
        "UNEXPECTED_INTERVALS",
        interval_anomaly,
        "PASS" if interval_anomaly == 0 else "FAIL"
    ])
    w.writerow([
        "EXPECTED_SESSION_BREAKS",
        session_breaks,
        "PASS"
    ])

# Summary CSV
with open(SUMMARY_OUT, "w", newline="", encoding="utf-8", buffering=BUF) as f:
    w = csv.writer(f)
    w.writerow([
        "DATE",
        "ROWS"
    ])

    for d in sorted(date_counts):
        w.writerow([d, date_counts[d]])

print("========== FINAL AUDIT ==========")

audit_pass = (
    exported > 0 and
    duplicate_rows == 0 and
    backward_rows == 0 and
    invalid_rows == 0 and
    interval_anomaly == 0
)

print("N225_1MIN_RAW_AUDIT =", "PASS" if audit_pass else "FAIL")
print()
print("RAW_OUT     =", RAW_OUT)
print("AUDIT_OUT   =", AUDIT_OUT)
print("SUMMARY_OUT =", SUMMARY_OUT)
print()

if not audit_pass:
    sys.exit(2)
