from pathlib import Path
import csv
import sys

BASE = Path("data")
JPX = BASE / "jpx_replay_feature.csv"
N225 = BASE / "n225_raw/N225_MARKET_CONTEXT_2025_01_09.csv"

OUT = BASE / "jpx_replay_feature_n225_context.csv"
AUDIT = BASE / "jpx_replay_feature_n225_context_audit.csv"
SUMMARY = BASE / "jpx_replay_feature_n225_context_summary.csv"

BUF = 1024 * 1024

START_DATE = "2025-01-01"
END_DATE = "2025-09-30"

EXPECTED_JPX_ROWS = 705485
EXPECTED_N225_DATES = 191

def normalize_date(v):
    v = (v or "").strip()

    if len(v) == 8 and v.isdigit():
        return f"{v[0:4]}-{v[4:6]}-{v[6:8]}"

    if len(v) == 10 and v[4] == "-" and v[7] == "-":
        return v

    return ""

def in_range(d):
    return START_DATE <= d <= END_DATE

print("========================================")
print("JPX × N225 FUTURES MARKET CONTEXT v2")
print("========================================")
print()

# ------------------------------------------------------------
# N225 context
# ------------------------------------------------------------

n225 = {}

with open(
    N225,
    "r",
    newline="",
    encoding="utf-8-sig",
    buffering=BUF
) as f:

    reader = csv.DictReader(f)

    required = {
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
    }

    if not required.issubset(reader.fieldnames or []):
        print("FAIL: N225_REQUIRED_COLUMNS_MISSING")
        sys.exit(2)

    for r in reader:

        raw_date = r["DATE"]
        date = normalize_date(raw_date)

        if not date:
            print("FAIL: INVALID_N225_DATE =", raw_date)
            sys.exit(3)

        if date in n225:
            print("FAIL: DUPLICATE_N225_DATE =", date)
            sys.exit(4)

        if r["POINT_IN_TIME_STATUS"] != "PASS":
            print("FAIL: N225_PIT_STATUS =", date)
            sys.exit(5)

        if r["DATA_STATUS"] != "09:09_OR_EARLIER_ONLY":
            print("FAIL: N225_LOOKAHEAD_STATUS =", date)
            sys.exit(6)

        n225[date] = r

if len(n225) != EXPECTED_N225_DATES:
    print(
        "FAIL: N225_DATE_COUNT_EXPECTED=",
        EXPECTED_N225_DATES,
        "ACTUAL=",
        len(n225)
    )
    sys.exit(7)

print("N225_FUTURES_CONTEXT_DATES =", len(n225))
print()

# ------------------------------------------------------------
# JPX integration
# ------------------------------------------------------------

total = 0
in_range = 0
joined = 0
missing = 0
duplicate_key = 0
invalid_key = 0
pit_fail = 0

date_counts = {}
date_join_counts = {}

seen = set()

with open(
    JPX,
    "r",
    newline="",
    encoding="utf-8-sig",
    buffering=BUF
) as fin, \
open(
    OUT,
    "w",
    newline="",
    encoding="utf-8",
    buffering=BUF
) as fout:

    reader = csv.DictReader(fin)

    if not reader.fieldnames:
        print("FAIL: JPX_HEADER_MISSING")
        sys.exit(8)

    jpx_fields = reader.fieldnames

    extra = [
        "N225_CONTEXT_AVAILABLE",
        "N225_ASSET_TYPE",
        "N225_DECISION_TIME",
        "N225_LATEST_ALLOWED_BAR",
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
        "N225_PIT_BAR_COUNT",
        "N225_NIGHT_BAR_COUNT",
        "N225_POINT_IN_TIME_STATUS",
        "N225_DATA_STATUS",
        "MARKET_CONTEXT_STATUS"
    ]

    writer = csv.DictWriter(
        fout,
        fieldnames=jpx_fields + extra,
        extrasaction="ignore"
    )

    writer.writeheader()

    for row in reader:

        total += 1

        raw_date = row.get("DATE", "")
        code = row.get("CODE", "")

        date = normalize_date(raw_date)

        if not date or not code:
            invalid_key += 1
            continue

        if not is_in_range(date):
            continue

        in_range += 1

        key = (date, code)

        if key in seen:
            duplicate_key += 1
        else:
            seen.add(key)

        date_counts[date] = date_counts.get(date, 0) + 1

        ctx = n225.get(date)

        if ctx is None:
            missing += 1

            writer.writerow({
                **row,
                "N225_CONTEXT_AVAILABLE": "NO",
                "N225_ASSET_TYPE": "NIKKEI_225_FUTURES",
                "MARKET_CONTEXT_STATUS": "UNKNOWN"
            })

            continue

        joined += 1
        date_join_counts[date] = date_join_counts.get(date, 0) + 1

        if ctx["POINT_IN_TIME_STATUS"] != "PASS":
            pit_fail += 1

        writer.writerow({
            **row,

            "N225_CONTEXT_AVAILABLE": "YES",
            "N225_ASSET_TYPE": "NIKKEI_225_FUTURES",

            "N225_DECISION_TIME": ctx["DECISION_TIME"],
            "N225_LATEST_ALLOWED_BAR": ctx["LATEST_ALLOWED_BAR"],

            "N225_LAST_CLOSE": ctx["N225_LAST_CLOSE"],
            "N225_RETURN_1M_PCT": ctx["N225_RETURN_1M_PCT"],
            "N225_RETURN_5M_PCT": ctx["N225_RETURN_5M_PCT"],
            "N225_RETURN_10M_PCT": ctx["N225_RETURN_10M_PCT"],

            "N225_HIGH_10M": ctx["N225_HIGH_10M"],
            "N225_LOW_10M": ctx["N225_LOW_10M"],
            "N225_RANGE_10M_PCT": ctx["N225_RANGE_10M_PCT"],

            "N225_VOLUME_5M": ctx["N225_VOLUME_5M"],
            "N225_VOLUME_10M": ctx["N225_VOLUME_10M"],

            "N225_DIRECTION": ctx["N225_DIRECTION"],
            "N225_PERSISTENCE": ctx["N225_PERSISTENCE"],

            "N225_NIGHT_OPEN": ctx["N225_NIGHT_OPEN"],
            "N225_NIGHT_HIGH": ctx["N225_NIGHT_HIGH"],
            "N225_NIGHT_LOW": ctx["N225_NIGHT_LOW"],
            "N225_NIGHT_CLOSE": ctx["N225_NIGHT_CLOSE"],
            "N225_NIGHT_RETURN_PCT": ctx["N225_NIGHT_RETURN_PCT"],
            "N225_NIGHT_RANGE_PCT": ctx["N225_NIGHT_RANGE_PCT"],

            "N225_PIT_BAR_COUNT": ctx["PIT_BAR_COUNT"],
            "N225_NIGHT_BAR_COUNT": ctx["NIGHT_BAR_COUNT"],

            "N225_POINT_IN_TIME_STATUS":
                ctx["POINT_IN_TIME_STATUS"],

            "N225_DATA_STATUS":
                ctx["DATA_STATUS"],

            "MARKET_CONTEXT_STATUS":
                "AVAILABLE_PIT_SAFE"
        })

# ------------------------------------------------------------
# Strong date-level audit
# ------------------------------------------------------------

missing_dates = []
mismatch_dates = []

for date in sorted(date_counts):

    expected = date_counts[date]
    actual = date_join_counts.get(date, 0)

    if actual != expected:
        mismatch_dates.append(
            (date, expected, actual)
        )

for date in sorted(date_counts):

    if date not in n225:
        missing_dates.append(date)

# ------------------------------------------------------------
# Final conditions
# ------------------------------------------------------------

audit_pass = (
    total == EXPECTED_JPX_ROWS and
    in_range == EXPECTED_JPX_ROWS and
    len(n225) == EXPECTED_N225_DATES and
    joined == in_range and
    missing == 0 and
    duplicate_key == 0 and
    invalid_key == 0 and
    pit_fail == 0 and
    len(mismatch_dates) == 0 and
    len(missing_dates) == 0
)

print("========== INTEGRATION RESULT ==========")
print("JPX_TOTAL_ROWS =", total)
print("JPX_IN_RANGE_ROWS =", in_range)
print("N225_CONTEXT_DATES =", len(n225))
print("JOINED_ROWS =", joined)
print("MISSING_CONTEXT =", missing)
print("DUPLICATE_JPX_DATE_CODE =", duplicate_key)
print("INVALID_JPX_KEY =", invalid_key)
print("N225_PIT_FAIL =", pit_fail)
print("DATE_COUNT_MISMATCHES =", len(mismatch_dates))
print("MISSING_CONTEXT_DATES =", len(missing_dates))
print()

print("========== FINAL AUDIT ==========")
print(
    "JPX_N225_MARKET_CONTEXT_AUDIT =",
    "PASS" if audit_pass else "FAIL"
)

if not audit_pass:
    print()
    print("AUDIT FAILURE DETAILS")

    if total != EXPECTED_JPX_ROWS:
        print(
            "JPX_TOTAL_ROWS_EXPECTED=",
            EXPECTED_JPX_ROWS,
            "ACTUAL=",
            total
        )

    if in_range != EXPECTED_JPX_ROWS:
        print(
            "JPX_IN_RANGE_ROWS_EXPECTED=",
            EXPECTED_JPX_ROWS,
            "ACTUAL=",
            in_range
        )

    if joined != in_range:
        print(
            "JOIN_MISMATCH EXPECTED=",
            in_range,
            "ACTUAL=",
            joined
        )

    if missing:
        print("MISSING_CONTEXT =", missing)

    if duplicate_key:
        print("DUPLICATE_JPX_DATE_CODE =", duplicate_key)

    if invalid_key:
        print("INVALID_JPX_KEY =", invalid_key)

    if pit_fail:
        print("N225_PIT_FAIL =", pit_fail)

    if mismatch_dates:
        print("FIRST_DATE_MISMATCH =", mismatch_dates[:5])

    if missing_dates:
        print("FIRST_MISSING_DATES =", missing_dates[:10])

# ------------------------------------------------------------
# Audit CSV
# ------------------------------------------------------------

with open(
    AUDIT,
    "w",
    newline="",
    encoding="utf-8",
    buffering=BUF
) as f:

    w = csv.writer(f)

    w.writerow([
        "AUDIT_ITEM",
        "VALUE",
        "STATUS"
    ])

    checks = [
        ("JPX_TOTAL_ROWS", total, total == EXPECTED_JPX_ROWS),
        ("JPX_IN_RANGE_ROWS", in_range, in_range == EXPECTED_JPX_ROWS),
        ("N225_CONTEXT_DATES", len(n225), len(n225) == EXPECTED_N225_DATES),
        ("JOINED_ROWS", joined, joined == in_range),
        ("MISSING_CONTEXT", missing, missing == 0),
        ("DUPLICATE_JPX_DATE_CODE", duplicate_key, duplicate_key == 0),
        ("INVALID_JPX_KEY", invalid_key, invalid_key == 0),
        ("N225_PIT_FAIL", pit_fail, pit_fail == 0),
        ("DATE_COUNT_MISMATCHES", len(mismatch_dates), len(mismatch_dates) == 0),
        ("MISSING_CONTEXT_DATES", len(missing_dates), len(missing_dates) == 0),
        ("N225_ASSET_TYPE", "NIKKEI_225_FUTURES", True),
        ("N225_ROLE", "MARKET_CONTEXT_ONLY", True),
        ("LOOKAHEAD_POLICY", "09:10 uses <=09:09", True),
        ("RULE_CHANGE", "NONE", True),
        ("INTEGRATION_AUDIT", "PASS" if audit_pass else "FAIL", audit_pass),
    ]

    for item, value, ok in checks:
        w.writerow([
            item,
            value,
            "PASS" if ok else "FAIL"
        ])

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

with open(
    SUMMARY,
    "w",
    newline="",
    encoding="utf-8",
    buffering=BUF
) as f:

    w = csv.writer(f)

    w.writerow(["METRIC", "VALUE"])

    w.writerow(["JPX_TOTAL_ROWS", total])
    w.writerow(["JPX_IN_RANGE_ROWS", in_range])
    w.writerow(["N225_CONTEXT_DATES", len(n225)])
    w.writerow(["JOINED_ROWS", joined])
    w.writerow(["MISSING_CONTEXT", missing])
    w.writerow(["DUPLICATE_JPX_DATE_CODE", duplicate_key])
    w.writerow(["INVALID_JPX_KEY", invalid_key])
    w.writerow(["N225_PIT_FAIL", pit_fail])
    w.writerow(["DATE_COUNT_MISMATCHES", len(mismatch_dates)])
    w.writerow(["MISSING_CONTEXT_DATES", len(missing_dates)])
    w.writerow(["N225_ASSET_TYPE", "NIKKEI_225_FUTURES"])
    w.writerow(["N225_ROLE", "MARKET_CONTEXT_ONLY"])
    w.writerow(["DECISION_TIME", "09:10:00"])
    w.writerow(["LATEST_N225_BAR", "09:09:00"])
    w.writerow(["RULE_CHANGE", "NONE"])
    w.writerow([
        "INTEGRATION_AUDIT",
        "PASS" if audit_pass else "FAIL"
    ])

print()
print("OUT     =", OUT)
print("AUDIT   =", AUDIT)
print("SUMMARY =", SUMMARY)

if not audit_pass:
    sys.exit(10)
