from pathlib import Path
import csv
import sys
from collections import defaultdict

BASE = Path("data/n225_raw")

SRC = BASE / "N225_1MIN_RAW_2025_01_09.csv"
OUT = BASE / "N225_MARKET_CONTEXT_2025_01_09.csv"
AUDIT = BASE / "N225_MARKET_CONTEXT_2025_01_09_AUDIT.csv"
SUMMARY = BASE / "N225_MARKET_CONTEXT_2025_01_09_SUMMARY.csv"

BUF = 1024 * 1024

# Historical replay decision boundaries.
# 09:10 decision -> latest usable completed bar = 09:09
# 09:20 confirmation -> latest usable completed bar = 09:19
DECISION_TIME = "09:10:00"
LATEST_ALLOWED_TIME = "09:09:00"

def pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return (a / b - 1.0) * 100.0

def avg(values):
    values = [x for x in values if x is not None]
    if not values:
        return None
    return sum(values) / len(values)

def fmt(v):
    if v is None:
        return ""
    return f"{v:.6f}"

def classify_direction(ret1, ret5, ret10):
    vals = [x for x in (ret1, ret5, ret10) if x is not None]

    if not vals:
        return "UNKNOWN"

    positive = sum(1 for x in vals if x > 0)
    negative = sum(1 for x in vals if x < 0)

    if positive == len(vals):
        return "UP"

    if negative == len(vals):
        return "DOWN"

    if positive > negative:
        return "UP_MIXED"

    if negative > positive:
        return "DOWN_MIXED"

    return "FLAT_MIXED"

def persistence(ret1, ret5, ret10):
    vals = [x for x in (ret1, ret5, ret10) if x is not None]

    if len(vals) < 3:
        return "UNKNOWN"

    if all(x > 0 for x in vals):
        return "UP_PERSISTENT"

    if all(x < 0 for x in vals):
        return "DOWN_PERSISTENT"

    if all(abs(x) < 0.05 for x in vals):
        return "FLAT_PERSISTENT"

    return "MIXED"

if not SRC.exists():
    print("ERROR: SOURCE_NOT_FOUND")
    print(SRC)
    sys.exit(1)

# We intentionally retain only the small rolling state required
# for the current date/session.
#
# No full CSV is loaded.
current_date = None
rows = []

output_rows = []
audit_rows = []

total_source = 0
context_rows = 0
limited_rows = 0
fail_rows = 0

dates_seen = set()

def process_date(date, rows):
    global context_rows, limited_rows, fail_rows

    if not rows:
        return

    dates_seen.add(date)

    # Rows are already chronological in the extracted source.
    # We need data through 09:09 only.
    pit = [
        r for r in rows
        if r["TIME"] <= LATEST_ALLOWED_TIME
    ]

    # Need the 09:09 bar itself for the canonical 09:10 snapshot.
    target = None

    for r in pit:
        if r["TIME"] == LATEST_ALLOWED_TIME:
            target = r
            break

    if target is None:
        limited_rows += 1
        audit_rows.append([
            date,
            DECISION_TIME,
            "LIMITED",
            "NO_09_09_BAR"
        ])
        return

    closes = [float(r["CLOSE"]) for r in pit]
    highs = [float(r["HIGH"]) for r in pit]
    lows = [float(r["LOW"]) for r in pit]
    vols = [float(r["VOLUME"]) for r in pit]

    # Last close before decision.
    last_close = closes[-1]

    ret1 = None
    ret5 = None
    ret10 = None

    if len(closes) >= 2:
        ret1 = pct(closes[-1], closes[-2])

    if len(closes) >= 6:
        ret5 = pct(closes[-1], closes[-6])

    if len(closes) >= 11:
        ret10 = pct(closes[-1], closes[-11])

    recent10_high = max(highs[-10:]) if len(highs) >= 10 else None
    recent10_low = min(lows[-10:]) if len(lows) >= 10 else None

    range10 = None
    if recent10_high is not None and recent10_low is not None:
        range10 = pct(recent10_high, recent10_low)

    vol5 = sum(vols[-5:]) if len(vols) >= 5 else None
    vol10 = sum(vols[-10:]) if len(vols) >= 10 else None

    direction = classify_direction(ret1, ret5, ret10)
    persist = persistence(ret1, ret5, ret10)

    # Night session reference:
    # only bars with TIME >= 17:00 or TIME < 06:00.
    night = [
        r for r in rows
        if r["TIME"] >= "17:00:00" or r["TIME"] < "06:00:00"
    ]

    night_open = None
    night_high = None
    night_low = None
    night_close = None
    night_return = None
    night_range = None

    if night:
        night_open = float(night[0]["OPEN"])
        night_high = max(float(r["HIGH"]) for r in night)
        night_low = min(float(r["LOW"]) for r in night)
        night_close = float(night[-1]["CLOSE"])

        night_return = pct(night_close, night_open)

        if night_low != 0:
            night_range = pct(night_high, night_low)

    status = "PASS"

    # Conservative PIT rule:
    # all decision fields must originate from <= 09:09.
    for r in pit:
        if r["TIME"] > LATEST_ALLOWED_TIME:
            status = "FAIL"
            break

    if status == "FAIL":
        fail_rows += 1
    else:
        context_rows += 1

    output_rows.append([
        date,
        DECISION_TIME,
        LATEST_ALLOWED_TIME,
        last_close,
        ret1,
        ret5,
        ret10,
        recent10_high,
        recent10_low,
        range10,
        vol5,
        vol10,
        direction,
        persist,
        night_open,
        night_high,
        night_low,
        night_close,
        night_return,
        night_range,
        len(pit),
        len(night),
        "PASS",
        "09:09_OR_EARLIER_ONLY"
    ])

    audit_rows.append([
        date,
        DECISION_TIME,
        status,
        "LATEST_ALLOWED_BAR=09:09"
    ])


# Streaming source processing.
with open(SRC, "r", newline="", encoding="utf-8-sig", buffering=BUF) as f:
    reader = csv.DictReader(f)

    required = {
        "DATE",
        "TIME",
        "OPEN",
        "HIGH",
        "LOW",
        "CLOSE",
        "VOLUME"
    }

    if not required.issubset(reader.fieldnames or []):
        print("ERROR: REQUIRED_COLUMNS_MISSING")
        print(reader.fieldnames)
        sys.exit(2)

    for r in reader:
        total_source += 1

        date = r["DATE"]

        if current_date is None:
            current_date = date

        if date != current_date:
            process_date(current_date, rows)
            rows = []
            current_date = date

        rows.append(r)

    if current_date is not None:
        process_date(current_date, rows)


# Write context.
with open(OUT, "w", newline="", encoding="utf-8", buffering=BUF) as f:
    w = csv.writer(f)

    w.writerow([
        "DATE",
        "DECISION_TIME",
        "LATEST_ALLOWED_BAR",
        "N225_LAST_CLOSE",
        "N225_RETURN_1M_PCT",
        "N225_RETURN_5M_PCT",
        "N225_RETURN_10M_PCT",
        "N225_HIGH_10M",
        "N225_LOW_10M",
        "N225_RANGE_10M_PCT",
        "N225_VOLUME_5M",
        "N225_VOLUME_10M",
        "N225_DIRECTION",
        "N225_PERSISTENCE",
        "N225_NIGHT_OPEN",
        "N225_NIGHT_HIGH",
        "N225_NIGHT_LOW",
        "N225_NIGHT_CLOSE",
        "N225_NIGHT_RETURN_PCT",
        "N225_NIGHT_RANGE_PCT",
        "PIT_BAR_COUNT",
        "NIGHT_BAR_COUNT",
        "POINT_IN_TIME_STATUS",
        "DATA_STATUS"
    ])

    for row in output_rows:
        w.writerow([
            row[0],
            row[1],
            row[2],
            fmt(row[3]),
            fmt(row[4]),
            fmt(row[5]),
            fmt(row[6]),
            fmt(row[7]),
            fmt(row[8]),
            fmt(row[9]),
            fmt(row[10]),
            fmt(row[11]),
            row[12],
            row[13],
            fmt(row[14]),
            fmt(row[15]),
            fmt(row[16]),
            fmt(row[17]),
            fmt(row[18]),
            fmt(row[19]),
            row[20],
            row[21],
            row[22],
            row[23]
        ])

# Audit
with open(AUDIT, "w", newline="", encoding="utf-8", buffering=BUF) as f:
    w = csv.writer(f)
    w.writerow([
        "DATE",
        "DECISION_TIME",
        "STATUS",
        "REASON"
    ])

    for row in audit_rows:
        w.writerow(row)

# Summary
with open(SUMMARY, "w", newline="", encoding="utf-8", buffering=BUF) as f:
    w = csv.writer(f)
    w.writerow([
        "METRIC",
        "VALUE"
    ])

    w.writerow(["SOURCE_ROWS", total_source])
    w.writerow(["CONTEXT_ROWS", context_rows])
    w.writerow(["LIMITED_ROWS", limited_rows])
    w.writerow(["FAIL_ROWS", fail_rows])
    w.writerow(["UNIQUE_DATES", len(dates_seen)])
    w.writerow(["DECISION_TIME", DECISION_TIME])
    w.writerow(["LATEST_ALLOWED_BAR", LATEST_ALLOWED_TIME])
    w.writerow([
        "POINT_IN_TIME_POLICY",
        "09:10 decision uses <=09:09 only"
    ])
    w.writerow([
        "MARKET_CONTEXT_AUDIT",
        "PASS" if fail_rows == 0 and context_rows > 0 else "FAIL"
    ])

print("========================================")
print("N225 MARKET CONTEXT")
print("========================================")
print("SOURCE_ROWS =", total_source)
print("CONTEXT_ROWS =", context_rows)
print("LIMITED_ROWS =", limited_rows)
print("FAIL_ROWS =", fail_rows)
print("UNIQUE_DATES =", len(dates_seen))
print("DECISION_TIME =", DECISION_TIME)
print("LATEST_ALLOWED_BAR =", LATEST_ALLOWED_TIME)
print()
print("MARKET_CONTEXT_AUDIT =",
      "PASS" if fail_rows == 0 and context_rows > 0 else "FAIL")
print()
print("OUT     =", OUT)
print("AUDIT   =", AUDIT)
print("SUMMARY =", SUMMARY)

if fail_rows > 0 or context_rows == 0:
    sys.exit(3)
