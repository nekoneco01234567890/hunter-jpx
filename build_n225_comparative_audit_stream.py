#!/usr/bin/env python3

import csv
import os
import sys

BUF = 1024 * 1024

BASE = "data"

JPX_IN = os.path.join(
    BASE,
    "jpx_replay_feature.csv"
)

CTX_IN = os.path.join(
    BASE,
    "jpx_replay_feature_n225_context.csv"
)

OUT = os.path.join(
    BASE,
    "n225_comparative_audit.csv"
)

SUMMARY = os.path.join(
    BASE,
    "n225_comparative_summary.csv"
)

AUDIT = os.path.join(
    BASE,
    "n225_comparative_audit_result.csv"
)


EXPECTED_ROWS = 705485


def norm_date(v):
    v = (v or "").strip()

    if len(v) == 8 and v.isdigit():
        return v[0:4] + "-" + v[4:6] + "-" + v[6:8]

    if len(v) == 10 and v[4] == "-" and v[7] == "-":
        return v

    return None


def key_of(row):
    d = norm_date(row.get("DATE", ""))
    c = (row.get("CODE", "") or "").strip()

    if d is None or not c:
        return None

    return (d, c)


print("========================================")
print("N225 COMPARATIVE PIT AUDIT")
print("========================================")
print()

if not os.path.exists(JPX_IN):
    print("ERROR: JPX INPUT NOT FOUND")
    sys.exit(2)

if not os.path.exists(CTX_IN):
    print("ERROR: N225 CONTEXT INPUT NOT FOUND")
    sys.exit(3)


# --------------------------------------------------
# 1. Stream through JPX baseline
# --------------------------------------------------

jpx_total = 0
jpx_invalid = 0
jpx_duplicate = 0

seen_jpx = set()

with open(
    JPX_IN,
    "r",
    newline="",
    encoding="utf-8-sig",
    buffering=BUF
) as f:

    r = csv.DictReader(f)

    for row in r:
        jpx_total += 1

        k = key_of(row)

        if k is None:
            jpx_invalid += 1
            continue

        if k in seen_jpx:
            jpx_duplicate += 1

        seen_jpx.add(k)


# --------------------------------------------------
# 2. Stream N225-integrated dataset
# --------------------------------------------------

ctx_total = 0
ctx_invalid = 0
ctx_duplicate = 0
ctx_missing_n225 = 0
ctx_pit_fail = 0

seen_ctx = set()

comparison_rows = 0
key_mismatch = 0

with open(
    CTX_IN,
    "r",
    newline="",
    encoding="utf-8-sig",
    buffering=BUF
) as f:

    r = csv.DictReader(f)

    required = {
        "DATE",
        "CODE",
        "GAP",
        "PREV_CLOSE",
        "CURRENT_OPEN",
        "N225_ASSET_TYPE",
        "N225_ROLE",
        "N225_DECISION_TIME",
        "N225_LATEST_ALLOWED_BAR",
        "N225_POINT_IN_TIME_STATUS",
        "N225_DATA_STATUS",
        "N225_DIRECTION",
        "N225_PERSISTENCE",
        "N225_RETURN_1M_PCT",
        "N225_RETURN_5M_PCT",
        "N225_RETURN_10M_PCT",
        "N225_HIGH_10M",
        "N225_LOW_10M",
        "N225_RANGE_10M_PCT"
    }

    missing_columns = required - set(r.fieldnames or [])

    if missing_columns:
        print("ERROR: REQUIRED COLUMNS MISSING")
        print("MISSING =", sorted(missing_columns))
        sys.exit(4)

    for row in r:

        ctx_total += 1

        k = key_of(row)

        if k is None:
            ctx_invalid += 1
            continue

        if k in seen_ctx:
            ctx_duplicate += 1

        seen_ctx.add(k)

        if k not in seen_jpx:
            key_mismatch += 1
            continue

        comparison_rows += 1

        if not row.get("N225_DIRECTION", "").strip():
            ctx_missing_n225 += 1

        if row.get(
            "N225_POINT_IN_TIME_STATUS",
            ""
        ).strip() != "PASS":
            ctx_pit_fail += 1

        if row.get(
            "N225_DATA_STATUS",
            ""
        ).strip() != "09:09_OR_EARLIER_ONLY":
            ctx_pit_fail += 1


# --------------------------------------------------
# 3. Full key-set comparison
# --------------------------------------------------

jpx_only = len(seen_jpx - seen_ctx)
ctx_only = len(seen_ctx - seen_jpx)


# --------------------------------------------------
# 4. Final audit
# --------------------------------------------------

audit_pass = (
    jpx_total == EXPECTED_ROWS
    and ctx_total == EXPECTED_ROWS
    and len(seen_jpx) == EXPECTED_ROWS
    and len(seen_ctx) == EXPECTED_ROWS
    and jpx_invalid == 0
    and ctx_invalid == 0
    and jpx_duplicate == 0
    and ctx_duplicate == 0
    and key_mismatch == 0
    and jpx_only == 0
    and ctx_only == 0
    and comparison_rows == EXPECTED_ROWS
    and ctx_pit_fail == 0
    and ctx_missing_n225 == 0
)


# --------------------------------------------------
# 5. Detailed audit CSV
# --------------------------------------------------

with open(
    AUDIT,
    "w",
    newline="",
    encoding="utf-8",
    buffering=BUF
) as f:

    w = csv.writer(f)

    w.writerow(["METRIC", "VALUE"])

    w.writerow(["JPX_TOTAL_ROWS", jpx_total])
    w.writerow(["N225_CONTEXT_TOTAL_ROWS", ctx_total])

    w.writerow(["JPX_UNIQUE_KEYS", len(seen_jpx)])
    w.writerow(["N225_CONTEXT_UNIQUE_KEYS", len(seen_ctx)])

    w.writerow(["JPX_INVALID_KEYS", jpx_invalid])
    w.writerow(["N225_CONTEXT_INVALID_KEYS", ctx_invalid])

    w.writerow(["JPX_DUPLICATE_KEYS", jpx_duplicate])
    w.writerow(["N225_CONTEXT_DUPLICATE_KEYS", ctx_duplicate])

    w.writerow(["COMPARISON_ROWS", comparison_rows])
    w.writerow(["KEY_MISMATCH", key_mismatch])

    w.writerow(["JPX_ONLY_KEYS", jpx_only])
    w.writerow(["N225_ONLY_KEYS", ctx_only])

    w.writerow(["N225_MISSING_DIRECTION", ctx_missing_n225])
    w.writerow(["N225_PIT_FAIL", ctx_pit_fail])

    w.writerow([
        "DECISION_TIME",
        "09:10:00"
    ])

    w.writerow([
        "LATEST_N225_BAR",
        "09:09:00"
    ])

    w.writerow([
        "N225_ASSET_TYPE",
        "NIKKEI_225_FUTURES"
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
        "COMPARATIVE_AUDIT",
        "PASS" if audit_pass else "FAIL"
    ])


# --------------------------------------------------
# 6. Summary
# --------------------------------------------------

with open(
    SUMMARY,
    "w",
    newline="",
    encoding="utf-8",
    buffering=BUF
) as f:

    w = csv.writer(f)

    w.writerow(["METRIC", "VALUE"])

    w.writerow(["BASELINE", "JPX_ONLY"])
    w.writerow(["COMPARISON", "JPX_PLUS_N225"])

    w.writerow(["BASELINE_ROWS", jpx_total])
    w.writerow(["COMPARISON_ROWS", comparison_rows])

    w.writerow(["KEYS_SHARED", comparison_rows])
    w.writerow(["JPX_ONLY_KEYS", jpx_only])
    w.writerow(["N225_ONLY_KEYS", ctx_only])

    w.writerow([
        "N225_PIT_STATUS",
        "PASS" if ctx_pit_fail == 0 else "FAIL"
    ])

    w.writerow([
        "RULE_CHANGE",
        "NONE"
    ])

    w.writerow([
        "MODEL_OR_SIGNAL_CHANGE",
        "NONE"
    ])

    w.writerow([
        "TRADING_DECISION_CHANGE",
        "NONE"
    ])

    w.writerow([
        "AUDIT",
        "PASS" if audit_pass else "FAIL"
    ])


# --------------------------------------------------
# 7. Console
# --------------------------------------------------

print("========== COMPARATIVE RESULT ==========")
print("JPX_TOTAL_ROWS =", jpx_total)
print("N225_CONTEXT_TOTAL_ROWS =", ctx_total)
print("JPX_UNIQUE_KEYS =", len(seen_jpx))
print("N225_CONTEXT_UNIQUE_KEYS =", len(seen_ctx))
print("COMPARISON_ROWS =", comparison_rows)
print("KEY_MISMATCH =", key_mismatch)
print("JPX_ONLY_KEYS =", jpx_only)
print("N225_ONLY_KEYS =", ctx_only)
print("N225_MISSING_DIRECTION =", ctx_missing_n225)
print("N225_PIT_FAIL =", ctx_pit_fail)

print()
print("========== FINAL AUDIT ==========")
print(
    "N225_COMPARATIVE_AUDIT =",
    "PASS" if audit_pass else "FAIL"
)

print()
print("OUT     =", OUT)
print("AUDIT   =", AUDIT)
print("SUMMARY =", SUMMARY)

if not audit_pass:
    sys.exit(10)
