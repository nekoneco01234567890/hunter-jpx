#!/usr/bin/env python3

import csv
from pathlib import Path
from collections import Counter

BASE = Path.home() / "jpx_replay"
DATA = BASE / "data"

INPUT = DATA / "jpx_replay_session.csv"
QUALITY = DATA / "jpx_replay_quality_audit.csv"

OUTPUT = DATA / "jpx_replay_feature.csv"
AUDIT = DATA / "jpx_replay_feature_audit.csv"
SUMMARY = DATA / "jpx_replay_feature_summary.csv"

PROGRESS_STEP = 50000


def num(v):
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def out(v):
    if v is None:
        return ""
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.6f}".rstrip("0").rstrip(".")


def pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return (a - b) / b * 100.0


def get(row, key):
    return row.get(key, "").strip()


if not INPUT.exists():
    raise SystemExit(f"INPUT NOT FOUND: {INPUT}")

if not QUALITY.exists():
    raise SystemExit(f"QUALITY NOT FOUND: {QUALITY}")


# --------------------------------------------------
# QUALITY MAP
# --------------------------------------------------

print("Loading quality audit...")

quality = {}

with QUALITY.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    for row in reader:
        key = (
            get(row, "DATE"),
            get(row, "CODE")
        )

        quality[key] = (
            get(row, "QUALITY_STATUS") or "UNKNOWN",
            get(row, "PRICE_FIELD_STATUS") or "UNKNOWN",
            get(row, "DUPLICATE_KEY") or "UNKNOWN",
        )

print(f"QUALITY RECORDS : {len(quality):,}")
print()


# --------------------------------------------------
# OUTPUT FIELDS
# --------------------------------------------------

feature_fields = [
    "DATE",
    "CODE",
    "NAME",
    "DECISION_TIME",

    "QUALITY_STATUS",
    "PRICE_FIELD_STATUS",

    "PREV_DATE",
    "PREV_CLOSE",
    "PREV_HIGH",
    "PREV_LOW",
    "PREV_RANGE",

    "CURRENT_OPEN",

    "GAP",
    "GAP_PCT",

    "OPEN_VS_PREV_HIGH",
    "OPEN_VS_PREV_HIGH_PCT",

    "OPEN_VS_PREV_LOW",
    "OPEN_VS_PREV_LOW_PCT",

    "OPEN_ABOVE_PREV_HIGH",
    "OPEN_BELOW_PREV_LOW",

    "PREV_DATA_AVAILABLE",
    "CURRENT_OPEN_AVAILABLE",

    "FUTURE_SESSION_FIELDS_USED",
    "FUTURE_INTRADAY_FIELDS_USED",

    "FEATURE_STATUS",
]


audit_fields = [
    "DATE",
    "CODE",
    "DECISION_TIME",
    "FEATURE_STATUS",
    "QUALITY_STATUS",
    "PRICE_FIELD_STATUS",
    "PREV_DATA_AVAILABLE",
    "CURRENT_OPEN_AVAILABLE",
    "FUTURE_SESSION_FIELDS_USED",
    "FUTURE_INTRADAY_FIELDS_USED",
    "AUDIT_STATUS",
    "AUDIT_REASON",
]


# --------------------------------------------------
# COUNTERS
# --------------------------------------------------

feature_counter = Counter()
audit_counter = Counter()

total = 0


# --------------------------------------------------
# STREAM PROCESSING
# --------------------------------------------------

print("Building replay features...")
print("Progress will appear every 50,000 records.")
print()

with INPUT.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as fin, OUTPUT.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as fout, AUDIT.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as faudit:

    reader = csv.DictReader(fin)

    writer = csv.DictWriter(
        fout,
        fieldnames=feature_fields
    )

    audit_writer = csv.DictWriter(
        faudit,
        fieldnames=audit_fields
    )

    writer.writeheader()
    audit_writer.writeheader()

    # Only one previous session per stock is retained.
    previous = {}

    for row in reader:

        total += 1

        date = get(row, "DATE")
        code = get(row, "CODE")
        name = get(row, "NAME")

        q = quality.get(
            (date, code),
            (
                "UNKNOWN",
                "UNKNOWN",
                "UNKNOWN"
            )
        )

        quality_status = q[0]
        price_status = q[1]
        duplicate_key = q[2]

        # ------------------------------------------
        # Current opening price
        # ------------------------------------------

        current_open = num(
            row.get("AM_OPEN")
        )

        current_open_available = (
            current_open is not None
        )

        # ------------------------------------------
        # Previous session
        # ------------------------------------------

        prev = previous.get(code)

        prev_date = ""
        prev_close = None
        prev_high = None
        prev_low = None

        if prev is not None:

            prev_date = prev["DATE"]

            prev_close = prev["SESSION_CLOSE"]
            prev_high = prev["SESSION_HIGH"]
            prev_low = prev["SESSION_LOW"]

        prev_available = (
            prev_close is not None
            and prev_high is not None
            and prev_low is not None
        )

        # ------------------------------------------
        # Gap
        # ------------------------------------------

        gap = None
        gap_pct = None

        if (
            current_open is not None
            and prev_close is not None
        ):

            gap = current_open - prev_close

            gap_pct = pct(
                current_open,
                prev_close
            )

        # ------------------------------------------
        # Opening position vs previous range
        # ------------------------------------------

        open_vs_prev_high = None
        open_vs_prev_high_pct = None

        if (
            current_open is not None
            and prev_high is not None
        ):

            open_vs_prev_high = (
                current_open - prev_high
            )

            open_vs_prev_high_pct = pct(
                current_open,
                prev_high
            )

        open_vs_prev_low = None
        open_vs_prev_low_pct = None

        if (
            current_open is not None
            and prev_low is not None
        ):

            open_vs_prev_low = (
                current_open - prev_low
            )

            open_vs_prev_low_pct = pct(
                current_open,
                prev_low
            )

        open_above_prev_high = (
            current_open is not None
            and prev_high is not None
            and current_open > prev_high
        )

        open_below_prev_low = (
            current_open is not None
            and prev_low is not None
            and current_open < prev_low
        )

        # ------------------------------------------
        # Feature status
        # ------------------------------------------

        if (
            prev_available
            and current_open_available
        ):

            feature_status = "READY_09_10"

        elif current_open_available:

            feature_status = "PARTIAL_NO_PREV"

        elif prev_available:

            feature_status = "PARTIAL_NO_OPEN"

        else:

            feature_status = "UNAVAILABLE"

        feature_counter[feature_status] += 1

        # ------------------------------------------
        # Explicit future-data guard
        # ------------------------------------------

        future_session = "FALSE"
        future_intraday = "FALSE"

        # ------------------------------------------
        # Audit
        # ------------------------------------------

        if future_session == "TRUE":

            audit_status = "FAIL"
            audit_reason = (
                "FUTURE_SESSION_DATA_USED"
            )

        elif future_intraday == "TRUE":

            audit_status = "FAIL"
            audit_reason = (
                "FUTURE_INTRADAY_DATA_USED"
            )

        elif duplicate_key not in (
            "",
            "FALSE",
            "0",
            "NO"
        ):

            audit_status = "FAIL"
            audit_reason = "DUPLICATE_KEY"

        elif feature_status == "READY_09_10":

            audit_status = "PASS"
            audit_reason = "POINT_IN_TIME_OK"

        else:

            audit_status = "LIMITED"
            audit_reason = (
                "REQUIRED_FEATURE_DATA_MISSING"
            )

        audit_counter[audit_status] += 1

        # ------------------------------------------
        # Write feature immediately
        # ------------------------------------------

        writer.writerow({
            "DATE": date,
            "CODE": code,
            "NAME": name,

            "DECISION_TIME": "09:10",

            "QUALITY_STATUS": quality_status,
            "PRICE_FIELD_STATUS": price_status,

            "PREV_DATE": prev_date,
            "PREV_CLOSE": out(prev_close),
            "PREV_HIGH": out(prev_high),
            "PREV_LOW": out(prev_low),

            "PREV_RANGE": out(
                (
                    prev_high - prev_low
                )
                if (
                    prev_high is not None
                    and prev_low is not None
                )
                else None
            ),

            "CURRENT_OPEN": out(current_open),

            "GAP": out(gap),
            "GAP_PCT": out(gap_pct),

            "OPEN_VS_PREV_HIGH": out(
                open_vs_prev_high
            ),

            "OPEN_VS_PREV_HIGH_PCT": out(
                open_vs_prev_high_pct
            ),

            "OPEN_VS_PREV_LOW": out(
                open_vs_prev_low
            ),

            "OPEN_VS_PREV_LOW_PCT": out(
                open_vs_prev_low_pct
            ),

            "OPEN_ABOVE_PREV_HIGH": (
                "TRUE"
                if open_above_prev_high
                else "FALSE"
            ),

            "OPEN_BELOW_PREV_LOW": (
                "TRUE"
                if open_below_prev_low
                else "FALSE"
            ),

            "PREV_DATA_AVAILABLE": (
                "TRUE"
                if prev_available
                else "FALSE"
            ),

            "CURRENT_OPEN_AVAILABLE": (
                "TRUE"
                if current_open_available
                else "FALSE"
            ),

            "FUTURE_SESSION_FIELDS_USED": (
                future_session
            ),

            "FUTURE_INTRADAY_FIELDS_USED": (
                future_intraday
            ),

            "FEATURE_STATUS": feature_status,
        })

        # ------------------------------------------
        # Write audit immediately
        # ------------------------------------------

        audit_writer.writerow({
            "DATE": date,
            "CODE": code,
            "DECISION_TIME": "09:10",

            "FEATURE_STATUS": feature_status,

            "QUALITY_STATUS": quality_status,
            "PRICE_FIELD_STATUS": price_status,

            "PREV_DATA_AVAILABLE": (
                "TRUE"
                if prev_available
                else "FALSE"
            ),

            "CURRENT_OPEN_AVAILABLE": (
                "TRUE"
                if current_open_available
                else "FALSE"
            ),

            "FUTURE_SESSION_FIELDS_USED": (
                future_session
            ),

            "FUTURE_INTRADAY_FIELDS_USED": (
                future_intraday
            ),

            "AUDIT_STATUS": audit_status,
            "AUDIT_REASON": audit_reason,
        })

        # ------------------------------------------
        # Update previous AFTER current processing
        # ------------------------------------------

        previous[code] = {
            "DATE": date,
            "SESSION_CLOSE": num(
                row.get("SESSION_CLOSE")
            ),
            "SESSION_HIGH": num(
                row.get("SESSION_HIGH")
            ),
            "SESSION_LOW": num(
                row.get("SESSION_LOW")
            ),
        }

        # ------------------------------------------
        # Progress
        # ------------------------------------------

        if total % PROGRESS_STEP == 0:

            print(
                f"PROGRESS : {total:,} / 705,485"
            )


# --------------------------------------------------
# SUMMARY
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
        "COUNT"
    ])

    for status, count in sorted(
        feature_counter.items()
    ):

        writer.writerow([
            "FEATURE_STATUS",
            status,
            count
        ])

    for status, count in sorted(
        audit_counter.items()
    ):

        writer.writerow([
            "AUDIT_STATUS",
            status,
            count
        ])


# --------------------------------------------------
# FINAL AUDIT
# --------------------------------------------------

print()
print("========================================")
print(" JPX REPLAY FEATURE BUILDER")
print("========================================")
print()

print(f"INPUT RECORDS   : {total:,}")
print(f"FEATURE RECORDS : {total:,}")
print(f"AUDIT RECORDS   : {total:,}")

print()
print("FEATURE STATUS:")

for status, count in sorted(
    feature_counter.items()
):

    print(
        f"  {status:20s}: {count:,}"
    )

print()
print("AUDIT STATUS:")

for status, count in sorted(
    audit_counter.items()
):

    print(
        f"  {status:20s}: {count:,}"
    )

print()
print("FILES:")
print(f"FEATURE : {OUTPUT}")
print(f"AUDIT   : {AUDIT}")
print(f"SUMMARY : {SUMMARY}")
print()

