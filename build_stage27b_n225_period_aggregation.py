from pathlib import Path
import csv
from datetime import datetime
from collections import defaultdict

JPX_FILE = Path(
    "data/hunter/jpx_temporal_master_2025.csv"
)

N225_FILE = Path(
    "data/n225_raw/N225_1MIN_RAW_2025_01_09.csv"
)

OUT_FILE = Path(
    "data/hunter/n225_jpx_period_2025.csv"
)

AUDIT_FILE = Path(
    "data/hunter/n225_jpx_period_2025_audit.csv"
)


# ============================================================
# LOAD JPX TEMPORAL MASTER
# ============================================================

with JPX_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:
    jpx_rows = list(csv.DictReader(f))

if len(jpx_rows) != 52:
    raise SystemExit(
        f"FAIL: JPX temporal master must contain 52 rows: "
        f"{len(jpx_rows)}"
    )


# ============================================================
# LOAD N225 1MIN
# ============================================================

with N225_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:
    n225_rows = list(csv.DictReader(f))

if not n225_rows:
    raise SystemExit("FAIL: N225 source is empty")


# ============================================================
# PREPARE N225
# ============================================================

valid_n225 = []
invalid_n225 = 0

for r in n225_rows:

    date_text = r["DATE"].strip()
    time_text = r["TIME"].strip()

    try:
        d = datetime.strptime(
            date_text,
            "%Y-%m-%d"
        ).date()
    except Exception:
        invalid_n225 += 1
        continue

    try:
        o = float(r["OPEN"])
        h = float(r["HIGH"])
        l = float(r["LOW"])
        c = float(r["CLOSE"])
        v = float(r["VOLUME"])
    except Exception:
        invalid_n225 += 1
        continue

    valid_n225.append(
        {
            "DATE": d,
            "TIME": time_text,
            "SESSION": r["SESSION"].strip(),
            "OPEN": o,
            "HIGH": h,
            "LOW": l,
            "CLOSE": c,
            "VOLUME": v,
            "POINT_IN_TIME_STATUS":
                r["POINT_IN_TIME_STATUS"].strip(),
            "DATA_STATUS":
                r["DATA_STATUS"].strip(),
        }
    )


# ============================================================
# SORT N225
# ============================================================

valid_n225.sort(
    key=lambda r: (
        r["DATE"],
        r["TIME"]
    )
)


# ============================================================
# AGGREGATION FUNCTION
# ============================================================

def aggregate(rows):

    if not rows:
        return None

    rows = sorted(
        rows,
        key=lambda r: r["TIME"]
    )

    return {
        "BAR_COUNT": len(rows),
        "OPEN": rows[0]["OPEN"],
        "HIGH": max(r["HIGH"] for r in rows),
        "LOW": min(r["LOW"] for r in rows),
        "CLOSE": rows[-1]["CLOSE"],
        "VOLUME": sum(r["VOLUME"] for r in rows),
    }


# ============================================================
# BUILD PERIOD DATA
# ============================================================

out = []
audit = []

for jpx in jpx_rows:

    start = datetime.strptime(
        jpx["OBSERVATION_START"],
        "%Y-%m-%d"
    ).date()

    end = datetime.strptime(
        jpx["OBSERVATION_END"],
        "%Y-%m-%d"
    ).date()

    period_key = jpx["PERIOD_KEY"]

    period_rows = [
        r for r in valid_n225
        if start <= r["DATE"] <= end
    ]

    day_rows = [
        r for r in period_rows
        if r["SESSION"] == "DAY"
    ]

    night_rows = [
        r for r in period_rows
        if r["SESSION"] == "NIGHT"
    ]

    day_agg = aggregate(day_rows)
    night_agg = aggregate(night_rows)

    if day_agg is None:
        status = "NO_DAY_DATA"
    else:
        status = "DAY_DATA_AVAILABLE"

    out.append(
        {
            "PERIOD_INDEX":
                jpx["PERIOD_INDEX"],
            "OBSERVATION_WEEK":
                jpx["OBSERVATION_WEEK"],
            "OBSERVATION_START":
                jpx["OBSERVATION_START"],
            "OBSERVATION_END":
                jpx["OBSERVATION_END"],
            "PERIOD_KEY":
                period_key,

            "N225_DAY_BAR_COUNT":
                day_agg["BAR_COUNT"]
                if day_agg else 0,

            "N225_DAY_OPEN":
                day_agg["OPEN"]
                if day_agg else "",

            "N225_DAY_HIGH":
                day_agg["HIGH"]
                if day_agg else "",

            "N225_DAY_LOW":
                day_agg["LOW"]
                if day_agg else "",

            "N225_DAY_CLOSE":
                day_agg["CLOSE"]
                if day_agg else "",

            "N225_DAY_VOLUME":
                day_agg["VOLUME"]
                if day_agg else "",

            "N225_NIGHT_BAR_COUNT":
                night_agg["BAR_COUNT"]
                if night_agg else 0,

            "N225_NIGHT_OPEN":
                night_agg["OPEN"]
                if night_agg else "",

            "N225_NIGHT_HIGH":
                night_agg["HIGH"]
                if night_agg else "",

            "N225_NIGHT_LOW":
                night_agg["LOW"]
                if night_agg else "",

            "N225_NIGHT_CLOSE":
                night_agg["CLOSE"]
                if night_agg else "",

            "N225_NIGHT_VOLUME":
                night_agg["VOLUME"]
                if night_agg else "",

            "DATA_STATUS":
                status,
        }
    )

    audit.append(
        {
            "PERIOD_KEY": period_key,
            "OBSERVATION_START":
                jpx["OBSERVATION_START"],
            "OBSERVATION_END":
                jpx["OBSERVATION_END"],
            "N225_DAY_BARS":
                day_agg["BAR_COUNT"]
                if day_agg else 0,
            "N225_NIGHT_BARS":
                night_agg["BAR_COUNT"]
                if night_agg else 0,
            "STATUS": status,
        }
    )


# ============================================================
# WRITE OUTPUT
# ============================================================

fields = list(out[0].keys())

with OUT_FILE.open(
    "w",
    newline="",
    encoding="utf-8"
) as f:

    w = csv.DictWriter(
        f,
        fieldnames=fields
    )

    w.writeheader()
    w.writerows(out)


audit_fields = list(audit[0].keys())

with AUDIT_FILE.open(
    "w",
    newline="",
    encoding="utf-8"
) as f:

    w = csv.DictWriter(
        f,
        fieldnames=audit_fields
    )

    w.writeheader()
    w.writerows(audit)


# ============================================================
# VALIDATION
# ============================================================

duplicate_keys = (
    len(out)
    - len(set(r["PERIOD_KEY"] for r in out))
)

no_data = sum(
    r["DATA_STATUS"] == "NO_DAY_DATA"
    for r in out
)

day_data = sum(
    r["DATA_STATUS"] == "DAY_DATA_AVAILABLE"
    for r in out
)

zero_bars_with_data = sum(
    r["DATA_STATUS"] == "DAY_DATA_AVAILABLE"
    and int(r["N225_DAY_BAR_COUNT"]) == 0
    for r in out
)


# ============================================================
# REPORT
# ============================================================

print("========================================")
print("STAGE27B N225 PERIOD AGGREGATION")
print("========================================")

print("JPX_PERIODS          :", len(jpx_rows))
print("N225_SOURCE_ROWS     :", len(n225_rows))
print("N225_VALID_ROWS      :", len(valid_n225))
print("N225_INVALID_ROWS    :", invalid_n225)

print()
print("DAY_DATA_PERIODS     :", day_data)
print("NO_DAY_DATA_PERIODS  :", no_data)
print("DUPLICATE_PERIODS    :", duplicate_keys)
print("ZERO_BAR_ANOMALIES   :", zero_bars_with_data)

print()
print("=== PERIOD RESULTS ===")

for r in out:

    print(
        r["OBSERVATION_WEEK"],
        "|",
        r["OBSERVATION_START"],
        "~",
        r["OBSERVATION_END"],
        "| DAY_BARS=",
        r["N225_DAY_BAR_COUNT"],
        "| NIGHT_BARS=",
        r["N225_NIGHT_BAR_COUNT"],
        "|",
        r["DATA_STATUS"]
    )

print()
print("OUTPUT :", OUT_FILE)
print("AUDIT  :", AUDIT_FILE)

if (
    len(out) == 52
    and duplicate_keys == 0
    and zero_bars_with_data == 0
):
    print()
    print("STAGE27B_AUDIT : PASS")
else:
    print()
    print("STAGE27B_AUDIT : FAIL")

