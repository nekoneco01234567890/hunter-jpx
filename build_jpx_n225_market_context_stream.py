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

# ------------------------------------------------------------
# N225 context is one row per DATE.
# It was independently PIT-validated:
# 09:10 decision -> <=09:09 N225 data only.
# ------------------------------------------------------------

n225 = {}

print("========================================")
print("JPX × N225 MARKET CONTEXT INTEGRATION")
print("========================================")
print()

# ------------------------------------------------------------
# Load only the small N225 context table.
# 191 rows only.
# ------------------------------------------------------------

with open(N225, "r", newline="", encoding="utf-8-sig",
          buffering=BUF) as f:

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
        print("ERROR: N225_REQUIRED_COLUMNS_MISSING")
        print(reader.fieldnames)
        sys.exit(2)

    for r in reader:

        date = r["DATE"]

        if date in n225:
            print("ERROR: N225_DUPLICATE_DATE =", date)
            sys.exit(3)

        if r["POINT_IN_TIME_STATUS"] != "PASS":
            print("ERROR: N225_PIT_NOT_PASS =", date)
            sys.exit(4)

        if r["DATA_STATUS"] != "09:09_OR_EARLIER_ONLY":
            print("ERROR: N225_DATA_STATUS_INVALID =", date)
            sys.exit(5)

        n225[date] = r

print("N225_CONTEXT_DATES =", len(n225))
print()

# ------------------------------------------------------------
# Output
# ------------------------------------------------------------

total = 0
in_range = 0
joined = 0
missing_context = 0
duplicate_jpx_key = 0
invalid_date = 0
pit_fail = 0

seen = set()

with open(JPX, "r", newline="", encoding="utf-8-sig",
          buffering=BUF) as fin, \
     open(OUT, "w", newline="", encoding="utf-8",
          buffering=BUF) as fout:

    reader = csv.DictReader(fin)

    if not reader.fieldnames:
        print("ERROR: JPX_HEADER_MISSING")
        sys.exit(6)

    # Preserve the complete JPX feature schema.
    jpx_fields = reader.fieldnames

    extra_fields = [
        "N225_CONTEXT_AVAILABLE",
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
        fieldnames=jpx_fields + extra_fields,
        extrasaction="ignore"
    )

    writer.writeheader()

    for row in reader:

        total += 1

        date = row.get("DATE", "")
        code = row.get("CODE", "")

        if not date or not code:
            invalid_date += 1
            continue

        if date < START_DATE or date > END_DATE:
            writer.writerow({
                **row,
                **{x: "" for x in extra_fields}
            })
            continue

        in_range += 1

        key = (date, code)

        if key in seen:
            duplicate_jpx_key += 1

        seen.add(key)

        ctx = n225.get(date)

        if ctx is None:

            missing_context += 1

            writer.writerow({
                **row,
                "N225_CONTEXT_AVAILABLE": "NO",
                "MARKET_CONTEXT_STATUS": "UNKNOWN"
            })

            continue

        # N225 context must already be independently PIT-safe.
        if ctx["POINT_IN_TIME_STATUS"] != "PASS":
            pit_fail += 1

        joined += 1

        writer.writerow({
            **row,

            "N225_CONTEXT_AVAILABLE": "YES",
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

print("========== INTEGRATION RESULT ==========")
print("JPX_TOTAL_ROWS =", total)
print("JPX_IN_RANGE_ROWS =", in_range)
print("N225_CONTEXT_DATES =", len(n225))
print("JOINED_ROWS =", joined)
print("MISSING_CONTEXT =", missing_context)
print("DUPLICATE_JPX_DATE_CODE =", duplicate_jpx_key)
print("INVALID_JPX_KEY =", invalid_date)
print("N225_PIT_FAIL =", pit_fail)
print()

# ------------------------------------------------------------
# Audit
# ------------------------------------------------------------

audit_pass = (
    total > 0 and
    len(n225) > 0 and
    joined == in_range and
    missing_context == 0 and
    duplicate_jpx_key == 0 and
    invalid_date == 0 and
    pit_fail == 0
)

with open(AUDIT, "w", newline="", encoding="utf-8",
          buffering=BUF) as f:

    w = csv.writer(f)

    w.writerow([
        "AUDIT_ITEM",
        "VALUE",
        "STATUS"
    ])

    w.writerow([
        "JPX_TOTAL_ROWS",
        total,
        "PASS" if total > 0 else "FAIL"
    ])

    w.writerow([
        "JPX_IN_RANGE_ROWS",
        in_range,
        "PASS"
    ])

    w.writerow([
        "N225_CONTEXT_DATES",
        len(n225),
        "PASS" if len(n225) > 0 else "FAIL"
    ])

    w.writerow([
        "JOINED_ROWS",
        joined,
        "PASS" if joined == in_range else "FAIL"
    ])

    w.writerow([
        "MISSING_CONTEXT",
        missing_context,
        "PASS" if missing_context == 0 else "FAIL"
    ])

    w.writerow([
        "DUPLICATE_JPX_DATE_CODE",
        duplicate_jpx_key,
        "PASS" if duplicate_jpx_key == 0 else "FAIL"
    ])

    w.writerow([
        "INVALID_JPX_KEY",
        invalid_date,
        "PASS" if invalid_date == 0 else "FAIL"
    ])

    w.writerow([
        "N225_PIT_FAIL",
        pit_fail,
        "PASS" if pit_fail == 0 else "FAIL"
    ])

    w.writerow([
        "INTEGRATION_POLICY",
        "N225 is MARKET_CONTEXT only",
        "PASS"
    ])

    w.writerow([
        "LOOKAHEAD_POLICY",
        "N225 <=09:09 for 09:10 decision",
        "PASS"
    ])

    w.writerow([
        "RULE_CHANGE",
        "NONE",
        "PASS"
    ])

    w.writerow([
        "INTEGRATION_AUDIT",
        "PASS" if audit_pass else "FAIL",
        "PASS" if audit_pass else "FAIL"
    ])

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

with open(SUMMARY, "w", newline="", encoding="utf-8",
          buffering=BUF) as f:

    w = csv.writer(f)

    w.writerow([
        "METRIC",
        "VALUE"
    ])

    w.writerow(["JPX_TOTAL_ROWS", total])
    w.writerow(["JPX_IN_RANGE_ROWS", in_range])
    w.writerow(["N225_CONTEXT_DATES", len(n225)])
    w.writerow(["JOINED_ROWS", joined])
    w.writerow(["MISSING_CONTEXT", missing_context])
    w.writerow(["DUPLICATE_JPX_DATE_CODE", duplicate_jpx_key])
    w.writerow(["INVALID_JPX_KEY", invalid_date])
    w.writerow(["N225_PIT_FAIL", pit_fail])
    w.writerow([
        "DECISION_TIME",
        "09:10:00"
    ])
    w.writerow([
        "LATEST_N225_BAR",
        "09:09:00"
    ])
    w.writerow([
        "N225_ROLE",
        "MARKET_CONTEXT_ONLY"
    ])
    w.writerow([
        "RULE_CHANGE",
        "NONE"
    ])
    w.writerow([
        "INTEGRATION_AUDIT",
        "PASS" if audit_pass else "FAIL"
    ])

print("========== FINAL AUDIT ==========")
print(
    "JPX_N225_MARKET_CONTEXT_AUDIT =",
    "PASS" if audit_pass else "FAIL"
)
print()
print("OUT     =", OUT)
print("AUDIT   =", AUDIT)
print("SUMMARY =", SUMMARY)

if not audit_pass:
    sys.exit(10)
