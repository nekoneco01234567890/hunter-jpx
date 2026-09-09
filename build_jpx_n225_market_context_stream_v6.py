#!/usr/bin/env python3

import csv
import os
import sys

BUF = 1024 * 1024

BASE = "data"

JPX_IN = os.path.join(BASE, "jpx_replay_feature.csv")
N225_IN = os.path.join(
    BASE,
    "n225_raw",
    "N225_MARKET_CONTEXT_2025_01_09.csv"
)

OUT = os.path.join(
    BASE,
    "jpx_replay_feature_n225_context.csv"
)

AUDIT = os.path.join(
    BASE,
    "jpx_replay_feature_n225_context_audit.csv"
)

SUMMARY = os.path.join(
    BASE,
    "jpx_replay_feature_n225_context_summary.csv"
)

INVALID_PREVIOUS = os.path.join(
    BASE,
    "jpx_replay_feature_n225_context.invalid_previous.csv"
)


def normalize_date(value):
    value = value.strip()

    if len(value) == 8 and value.isdigit():
        return (
            value[0:4] + "-" +
            value[4:6] + "-" +
            value[6:8]
        )

    if (
        len(value) == 10
        and value[4] == "-"
        and value[7] == "-"
    ):
        return value

    return None


def read_n225_context():
    context = {}

    with open(
        N225_IN,
        "r",
        newline="",
        encoding="utf-8-sig",
        buffering=BUF
    ) as f:

        r = csv.DictReader(f)

        required = {
            "DATE",
            "POINT_IN_TIME_STATUS",
            "DATA_STATUS"
        }

        if not required.issubset(set(r.fieldnames or [])):
            print("ERROR: N225 required columns missing")
            sys.exit(2)

        for row in r:
            date = normalize_date(row["DATE"])

            if date is None:
                print("ERROR: INVALID N225 DATE =", row["DATE"])
                sys.exit(3)

            if date in context:
                print("ERROR: DUPLICATE N225 DATE =", date)
                sys.exit(4)

            pit = row["POINT_IN_TIME_STATUS"].strip()
            data_status = row["DATA_STATUS"].strip()

            if pit != "PASS":
                print(
                    "ERROR: N225 PIT FAIL =",
                    date,
                    pit
                )
                sys.exit(5)

            if data_status != "09:09_OR_EARLIER_ONLY":
                print(
                    "ERROR: N225 DATA STATUS INVALID =",
                    date,
                    data_status
                )
                sys.exit(6)

            context[date] = row

    return context


def is_in_range(date):
    return date in n225


print("========================================")
print("JPX × N225 FUTURES MARKET CONTEXT v3")
print("========================================")
print()

n225 = read_n225_context()

print(
    "N225_FUTURES_CONTEXT_DATES =",
    len(n225)
)

if len(n225) != 191:
    print("ERROR: EXPECTED 191 N225 CONTEXT DATES")
    sys.exit(7)


# 以前の不正なV2出力が存在する場合は退避
if os.path.exists(OUT):
    try:
        os.replace(OUT, INVALID_PREVIOUS)
        print("PREVIOUS_OUTPUT_BACKUP =", INVALID_PREVIOUS)
    except Exception as e:
        print("ERROR: CANNOT BACKUP PREVIOUS OUTPUT")
        print(e)
        sys.exit(8)


total = 0
in_range_rows = 0
joined = 0
missing = 0
duplicate_key = 0
invalid_key = 0
pit_fail = 0

jpx_dates = set()
missing_dates = set()
mismatch_dates = set()

seen_keys = set()

with open(
    JPX_IN,
    "r",
    newline="",
    encoding="utf-8-sig",
    buffering=BUF
) as fin, open(
    OUT,
    "w",
    newline="",
    encoding="utf-8",
    buffering=BUF
) as fout:

    reader = csv.DictReader(fin)

    if not reader.fieldnames:
        print("ERROR: JPX FEATURE HEADER MISSING")
        sys.exit(9)

    fields = list(reader.fieldnames)

    extra_fields = [
        "N225_ASSET_TYPE",
        "N225_ROLE",
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
        "N225_DATA_STATUS"
    ]

    output_fields = fields + extra_fields

    writer = csv.DictWriter(
        fout,
        fieldnames=output_fields
    )

    writer.writeheader()

    for row in reader:

        total += 1

        raw_date = row.get("DATE", "")
        raw_code = row.get("CODE", "")

        date = normalize_date(raw_date)
        code = raw_code.strip()

        if date is None or not code:
            invalid_key += 1
            continue

        jpx_dates.add(date)

        key = (date, code)

        if key in seen_keys:
            duplicate_key += 1

        seen_keys.add(key)

        if not is_in_range(date):
            continue

        in_range_rows += 1

        ctx = n225.get(date)

        if ctx is None:
            missing += 1
            missing_dates.add(date)
            continue

        if ctx.get("POINT_IN_TIME_STATUS", "").strip() != "PASS":
            pit_fail += 1
            continue

        if ctx.get("DATA_STATUS", "").strip() != "09:09_OR_EARLIER_ONLY":
            pit_fail += 1
            continue

        joined += 1

        outrow = dict(row)

        outrow["N225_ASSET_TYPE"] = "NIKKEI_225_FUTURES"
        outrow["N225_ROLE"] = "MARKET_CONTEXT_ONLY"
        outrow["N225_DECISION_TIME"] = "09:10:00"
        outrow["N225_LATEST_ALLOWED_BAR"] = "09:09:00"

        for key_name in extra_fields:
            if key_name in (
                "N225_ASSET_TYPE",
                "N225_ROLE",
                "N225_DECISION_TIME",
                "N225_LATEST_ALLOWED_BAR"
            ):
                continue

            # 元N225コンテキストCSVの列名をそのまま使用
            source_name = key_name

            # 元CSVでN225_ prefixを持たない列だけ明示変換
            if key_name == "N225_PIT_BAR_COUNT":
                source_name = "PIT_BAR_COUNT"
            elif key_name == "N225_NIGHT_BAR_COUNT":
                source_name = "NIGHT_BAR_COUNT"
            elif key_name == "N225_POINT_IN_TIME_STATUS":
                source_name = "POINT_IN_TIME_STATUS"
            elif key_name == "N225_DATA_STATUS":
                source_name = "DATA_STATUS"

            outrow[key_name] = ctx.get(
                source_name,
                ""
            )

        # ★重要：統合済み1行を必ず出力
        writer.writerow(outrow)

# JPX -> N225 の必要日付監査
# JPX側の全取引日がN225コンテキストを持つことを必須とする
# N225側にJPX現物より多いセッションが存在してもエラーにはしない

jpx_missing_n225_dates = set()

for date in jpx_dates:
    if date not in n225:
        jpx_missing_n225_dates.add(date)

# N225側にのみ存在する余剰セッション
n225_extra_dates = set()

for date in n225:
    if date not in jpx_dates:
        n225_extra_dates.add(date)

# 互換性のため mismatch_dates は
# 「JPX側でN225が欠落した日」のみをFAIL対象として保持
mismatch_dates = jpx_missing_n225_dates

# 全体監査
audit_pass = (
    total == 705485
    and in_range_rows == 705485
    and len(n225) == 191
    and joined == 705485
    and missing == 0
    and duplicate_key == 0
    and invalid_key == 0
    and pit_fail == 0
    and len(mismatch_dates) == 0
    and len(missing_dates) == 0
)


# AUDIT
with open(
    AUDIT,
    "w",
    newline="",
    encoding="utf-8",
    buffering=BUF
) as f:

    w = csv.writer(f)

    w.writerow([
        "METRIC",
        "VALUE"
    ])

    w.writerow(["JPX_TOTAL_ROWS", total])
    w.writerow(["JPX_IN_RANGE_ROWS", in_range_rows])
    w.writerow(["N225_CONTEXT_DATES", len(n225)])
    w.writerow(["JPX_UNIQUE_DATES", len(jpx_dates)])
    w.writerow(["JPX_MISSING_N225_DATES", len(jpx_missing_n225_dates)])
    w.writerow(["N225_EXTRA_DATES", len(n225_extra_dates)])
    w.writerow(["JOINED_ROWS", joined])
    w.writerow(["MISSING_CONTEXT", missing])
    w.writerow(["DUPLICATE_JPX_DATE_CODE", duplicate_key])
    w.writerow(["INVALID_JPX_KEY", invalid_key])
    w.writerow(["N225_PIT_FAIL", pit_fail])
    w.writerow([
        "DATE_COUNT_MISMATCHES",
        len(mismatch_dates)
    ])
    w.writerow([
        "MISSING_CONTEXT_DATES",
        len(missing_dates)
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
        "DECISION_TIME",
        "09:10:00"
    ])
    w.writerow([
        "LATEST_N225_BAR",
        "09:09:00"
    ])
    w.writerow([
        "RULE_CHANGE",
        "NONE"
    ])
    w.writerow([
        "INTEGRATION_AUDIT",
        "PASS" if audit_pass else "FAIL"
    ])


# SUMMARY
with open(
    SUMMARY,
    "w",
    newline="",
    encoding="utf-8",
    buffering=BUF
) as f:

    w = csv.writer(f)

    w.writerow([
        "METRIC",
        "VALUE"
    ])

    w.writerow(["JPX_TOTAL_ROWS", total])
    w.writerow(["JPX_IN_RANGE_ROWS", in_range_rows])
    w.writerow(["N225_CONTEXT_DATES", len(n225)])
    w.writerow(["JPX_UNIQUE_DATES", len(jpx_dates)])
    w.writerow(["JPX_MISSING_N225_DATES", len(jpx_missing_n225_dates)])
    w.writerow(["N225_EXTRA_DATES", len(n225_extra_dates)])
    w.writerow(["JOINED_ROWS", joined])
    w.writerow(["MISSING_CONTEXT", missing])
    w.writerow(["DUPLICATE_JPX_DATE_CODE", duplicate_key])
    w.writerow(["INVALID_JPX_KEY", invalid_key])
    w.writerow(["N225_PIT_FAIL", pit_fail])
    w.writerow([
        "DATE_COUNT_MISMATCHES",
        len(mismatch_dates)
    ])
    w.writerow([
        "MISSING_CONTEXT_DATES",
        len(missing_dates)
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
        "DECISION_TIME",
        "09:10:00"
    ])
    w.writerow([
        "LATEST_N225_BAR",
        "09:09:00"
    ])
    w.writerow([
        "RULE_CHANGE",
        "NONE"
    ])
    w.writerow([
        "INTEGRATION_AUDIT",
        "PASS" if audit_pass else "FAIL"
    ])


print()
print("========== INTEGRATION RESULT ==========")
print("JPX_TOTAL_ROWS =", total)
print("JPX_IN_RANGE_ROWS =", in_range_rows)
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

print()
print("OUT     =", OUT)
print("AUDIT   =", AUDIT)
print("SUMMARY =", SUMMARY)

if not audit_pass:
    sys.exit(10)
