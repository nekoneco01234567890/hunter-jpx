import csv
import os
from pathlib import Path
from collections import Counter, defaultdict

BASE = Path.home() / "jpx_replay"
DATA_DIR = BASE / "data"

RAW = DATA_DIR / "jpx_replay_raw_v2.csv"

SESSION = DATA_DIR / "jpx_replay_session.csv"
QUALITY = DATA_DIR / "jpx_replay_quality_audit.csv"
SUMMARY = DATA_DIR / "jpx_replay_quality_summary.csv"


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def fmt(v):
    if v is None:
        return ""
    if float(v).is_integer():
        return str(int(v))
    return str(v)


def calc_range(high, low):
    if high is None or low is None:
        return None
    return high - low


def calc_change(close, open_price):
    if close is None or open_price is None:
        return None
    return close - open_price


def calc_change_pct(close, open_price):
    if close is None or open_price in (None, 0):
        return None
    return (close - open_price) / open_price * 100.0


if not RAW.exists():
    raise SystemExit(f"RAW FILE NOT FOUND: {RAW}")


session_fields = [
    "DATE",
    "CODE",
    "NAME",

    "AM_OPEN",
    "AM_HIGH",
    "AM_LOW",
    "AM_CLOSE",

    "PM_OPEN",
    "PM_HIGH",
    "PM_LOW",
    "PM_CLOSE",

    "SESSION_HIGH",
    "SESSION_LOW",
    "SESSION_CLOSE",

    "AM_RANGE",
    "PM_RANGE",
    "SESSION_RANGE",

    "AM_CHANGE",
    "AM_CHANGE_PCT",

    "PM_CHANGE",
    "PM_CHANGE_PCT",

    "SESSION_CHANGE",
    "SESSION_CHANGE_PCT",

    "VALUE_COUNT",
    "DATA_STATUS",
    "SOURCE_FILE",
]


quality_fields = [
    "DATE",
    "CODE",
    "NAME",
    "DATE_VALID",
    "CODE_VALID",
    "NAME_VALID",
    "VALUE_COUNT",
    "DATA_STATUS",
    "DUPLICATE_KEY",
    "PRICE_FIELD_STATUS",
    "QUALITY_STATUS",
    "SOURCE_FILE",
]


rows = []
quality_rows = []

key_counter = Counter()

with RAW.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for r in reader:
        date = r["DATE"].strip()
        code = r["CODE"].strip()
        name = r["NAME"].strip()

        am_open = num(r["AM_OPEN"])
        am_high = num(r["AM_HIGH"])
        am_low = num(r["AM_LOW"])
        am_close = num(r["AM_CLOSE"])

        pm_open = num(r["PM_OPEN"])
        pm_high = num(r["PM_HIGH"])
        pm_low = num(r["PM_LOW"])
        pm_close = num(r["PM_CLOSE"])

        value_count = int(r["VALUE_COUNT"] or 0)
        data_status = r["STATUS"]
        source_file = r["SOURCE_FILE"]

        key = (date, code)
        key_counter[key] += 1

        # セッション高安は「存在する観測値」だけから作る
        highs = [
            x for x in (am_high, pm_high)
            if x is not None
        ]

        lows = [
            x for x in (am_low, pm_low)
            if x is not None
        ]

        session_high = max(highs) if highs else None
        session_low = min(lows) if lows else None

        # 終値は後場終値が存在する場合のみ採用
        # なければ前場終値をSESSION_CLOSEとはしない
        session_close = pm_close

        am_range = calc_range(am_high, am_low)
        pm_range = calc_range(pm_high, pm_low)
        session_range = calc_range(session_high, session_low)

        am_change = calc_change(am_close, am_open)
        am_change_pct = calc_change_pct(am_close, am_open)

        pm_change = calc_change(pm_close, pm_open)
        pm_change_pct = calc_change_pct(pm_close, pm_open)

        session_change = calc_change(session_close, am_open)
        session_change_pct = calc_change_pct(
            session_close,
            am_open
        )

        rows.append([
            date,
            code,
            name,

            fmt(am_open),
            fmt(am_high),
            fmt(am_low),
            fmt(am_close),

            fmt(pm_open),
            fmt(pm_high),
            fmt(pm_low),
            fmt(pm_close),

            fmt(session_high),
            fmt(session_low),
            fmt(session_close),

            fmt(am_range),
            fmt(pm_range),
            fmt(session_range),

            fmt(am_change),
            fmt(am_change_pct),

            fmt(pm_change),
            fmt(pm_change_pct),

            fmt(session_change),
            fmt(session_change_pct),

            value_count,
            data_status,
            source_file,
        ])


# --------------------------------------------------
# QUALITY AUDIT
# --------------------------------------------------

for r in rows:
    date = r[0]
    code = r[1]
    name = r[2]
    value_count = int(r[23])
    data_status = r[24]
    source_file = r[25]

    date_valid = (
        len(date) == 8
        and date.isdigit()
    )

    code_valid = (
        len(code) == 5
        and all(c in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                for c in code)
    )

    name_valid = bool(name)

    duplicate_key = (
        "DUPLICATE"
        if key_counter[(date, code)] > 1
        else "UNIQUE"
    )

    if value_count == 8:
        price_field_status = "COMPLETE"
    elif value_count == 0:
        price_field_status = "NO_PRICE_DATA"
    else:
        price_field_status = "PARTIAL"

    if not date_valid or not code_valid or not name_valid:
        quality_status = "INVALID"

    elif duplicate_key == "DUPLICATE":
        quality_status = "DUPLICATE"

    elif price_field_status == "COMPLETE":
        quality_status = "VALID"

    elif price_field_status == "PARTIAL":
        quality_status = "PARTIAL"

    else:
        quality_status = "NO_PRICE_DATA"

    quality_rows.append([
        date,
        code,
        name,
        "VALID" if date_valid else "INVALID",
        "VALID" if code_valid else "INVALID",
        "VALID" if name_valid else "INVALID",
        value_count,
        data_status,
        duplicate_key,
        price_field_status,
        quality_status,
        source_file,
    ])


# --------------------------------------------------
# QUALITY SUMMARY
# --------------------------------------------------

summary_counter = Counter(
    r[10] for r in quality_rows
)

price_counter = Counter(
    r[9] for r in quality_rows
)

source_counter = Counter(
    r[11] for r in quality_rows
)


# --------------------------------------------------
# WRITE SESSION
# --------------------------------------------------

with SESSION.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:
    writer = csv.writer(f)
    writer.writerow(session_fields)
    writer.writerows(rows)


# --------------------------------------------------
# WRITE QUALITY
# --------------------------------------------------

with QUALITY.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:
    writer = csv.writer(f)
    writer.writerow(quality_fields)
    writer.writerows(quality_rows)


# --------------------------------------------------
# WRITE SUMMARY
# --------------------------------------------------

with SUMMARY.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:
    writer = csv.writer(f)

    writer.writerow([
        "CATEGORY",
        "STATUS",
        "COUNT",
    ])

    for status, count in sorted(summary_counter.items()):
        writer.writerow([
            "QUALITY_STATUS",
            status,
            count,
        ])

    for status, count in sorted(price_counter.items()):
        writer.writerow([
            "PRICE_FIELD_STATUS",
            status,
            count,
        ])

    for source, count in sorted(source_counter.items()):
        writer.writerow([
            "SOURCE_FILE",
            source,
            count,
        ])


# --------------------------------------------------
# CONSOLE AUDIT
# --------------------------------------------------

print()
print("========================================")
print(" JPX SESSION + QUALITY BUILDER")
print("========================================")
print()

print(f"RAW RECORDS      : {len(rows):,}")
print(f"SESSION RECORDS  : {len(rows):,}")
print(f"UNIQUE DATE+CODE: {len(key_counter):,}")
print()

print("QUALITY STATUS:")

for status, count in sorted(summary_counter.items()):
    print(f"  {status:20s}: {count:,}")

print()
print("PRICE FIELD STATUS:")

for status, count in sorted(price_counter.items()):
    print(f"  {status:20s}: {count:,}")

print()
print("FILES:")
print(f"SESSION : {SESSION}")
print(f"QUALITY : {QUALITY}")
print(f"SUMMARY : {SUMMARY}")
print()

