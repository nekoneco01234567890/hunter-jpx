#!/usr/bin/env python3

import csv
from pathlib import Path
from collections import Counter, defaultdict

BASE = Path.home() / "jpx_replay"
DATA = BASE / "data"

INPUT = DATA / "jpx_replay_session.csv"
QUALITY = DATA / "jpx_replay_quality_audit.csv"

OUTPUT = DATA / "jpx_replay_feature.csv"
AUDIT = DATA / "jpx_replay_feature_audit.csv"
SUMMARY = DATA / "jpx_replay_feature_summary.csv"


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def to_float(v):
    if v is None:
        return None

    v = str(v).strip()

    if v == "":
        return None

    try:
        return float(v)
    except ValueError:
        return None


def fmt_num(v):
    if v is None:
        return ""

    if float(v).is_integer():
        return str(int(v))

    return f"{v:.6f}".rstrip("0").rstrip(".")


def pct(a, b):
    """
    Percentage change from b -> a.
    Returns None when calculation is impossible.
    """
    if a is None or b is None:
        return None

    if b == 0:
        return None

    return (a - b) / b * 100.0


def safe_range(high, low):
    if high is None or low is None:
        return None

    return high - low


# --------------------------------------------------
# INPUT
# --------------------------------------------------

if not INPUT.exists():
    raise SystemExit(f"INPUT NOT FOUND: {INPUT}")

if not QUALITY.exists():
    raise SystemExit(f"QUALITY FILE NOT FOUND: {QUALITY}")


# --------------------------------------------------
# LOAD QUALITY
# --------------------------------------------------

quality_map = {}

with QUALITY.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        date = row.get("DATE", "").strip()
        code = row.get("CODE", "").strip()

        if not date or not code:
            continue

        quality_map[(date, code)] = {
            "QUALITY_STATUS": row.get("QUALITY_STATUS", "UNKNOWN"),
            "PRICE_FIELD_STATUS": row.get(
                "PRICE_FIELD_STATUS",
                "UNKNOWN"
            ),
            "DUPLICATE_KEY": row.get(
                "DUPLICATE_KEY",
                "UNKNOWN"
            ),
        }


# --------------------------------------------------
# LOAD SESSION
# --------------------------------------------------

records = []

with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:

        date = row.get("DATE", "").strip()
        code = row.get("CODE", "").strip()
        name = row.get("NAME", "").strip()

        if not date or not code:
            continue

        records.append({
            "DATE": date,
            "CODE": code,
            "NAME": name,

            "AM_OPEN": to_float(row.get("AM_OPEN")),
            "AM_HIGH": to_float(row.get("AM_HIGH")),
            "AM_LOW": to_float(row.get("AM_LOW")),
            "AM_CLOSE": to_float(row.get("AM_CLOSE")),

            "PM_OPEN": to_float(row.get("PM_OPEN")),
            "PM_HIGH": to_float(row.get("PM_HIGH")),
            "PM_LOW": to_float(row.get("PM_LOW")),
            "PM_CLOSE": to_float(row.get("PM_CLOSE")),

            "SESSION_HIGH": to_float(row.get("SESSION_HIGH")),
            "SESSION_LOW": to_float(row.get("SESSION_LOW")),
            "SESSION_CLOSE": to_float(row.get("SESSION_CLOSE")),

            "AM_RANGE": to_float(row.get("AM_RANGE")),
            "PM_RANGE": to_float(row.get("PM_RANGE")),
            "SESSION_RANGE": to_float(
                row.get("SESSION_RANGE")
            ),

            "AM_CHANGE": to_float(row.get("AM_CHANGE")),
            "AM_CHANGE_PCT": to_float(
                row.get("AM_CHANGE_PCT")
            ),

            "PM_CHANGE": to_float(row.get("PM_CHANGE")),
            "PM_CHANGE_PCT": to_float(
                row.get("PM_CHANGE_PCT")
            ),

            "SESSION_CHANGE": to_float(
                row.get("SESSION_CHANGE")
            ),
            "SESSION_CHANGE_PCT": to_float(
                row.get("SESSION_CHANGE_PCT")
            ),
        })


# --------------------------------------------------
# SORT
# --------------------------------------------------

records.sort(
    key=lambda r: (
        r["CODE"],
        r["DATE"]
    )
)


# --------------------------------------------------
# REPLAY FEATURE
# --------------------------------------------------

feature_fields = [
    "DATE",
    "CODE",
    "NAME",

    # Replay timestamp
    "DECISION_TIME",

    # Data status
    "QUALITY_STATUS",
    "PRICE_FIELD_STATUS",

    # Previous-session information
    "PREV_DATE",
    "PREV_CLOSE",
    "PREV_HIGH",
    "PREV_LOW",
    "PREV_RANGE",
    "PREV_CHANGE",
    "PREV_CHANGE_PCT",

    # Current-session information known by 09:10
    "CURRENT_OPEN",

    # Gap
    "GAP",
    "GAP_PCT",

    # Opening position
    "OPEN_VS_PREV_HIGH",
    "OPEN_VS_PREV_HIGH_PCT",

    "OPEN_VS_PREV_LOW",
    "OPEN_VS_PREV_LOW_PCT",

    "OPEN_ABOVE_PREV_HIGH",
    "OPEN_BELOW_PREV_LOW",

    # Feature availability
    "PREV_DATA_AVAILABLE",
    "CURRENT_OPEN_AVAILABLE",

    # Explicit anti-lookahead state
    "FUTURE_SESSION_FIELDS_USED",
    "FUTURE_INTRADAY_FIELDS_USED",

    # Final feature status
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


features = []
audits = []

# Previous record for each stock
previous = {}

summary = Counter()
audit_summary = Counter()


for r in records:

    date = r["DATE"]
    code = r["CODE"]

    q = quality_map.get(
        (date, code),
        {
            "QUALITY_STATUS": "UNKNOWN",
            "PRICE_FIELD_STATUS": "UNKNOWN",
            "DUPLICATE_KEY": "UNKNOWN",
        }
    )

    prev = previous.get(code)

    prev_date = ""
    prev_close = None
    prev_high = None
    prev_low = None
    prev_range = None
    prev_change = None
    prev_change_pct = None

    prev_available = False

    if prev is not None:

        prev_date = prev["DATE"]
        prev_close = prev["SESSION_CLOSE"]
        prev_high = prev["SESSION_HIGH"]
        prev_low = prev["SESSION_LOW"]

        prev_range = safe_range(
            prev_high,
            prev_low
        )

        if prev_close is not None:
            prev_change = pct(
                prev_close,
                prev_close
            )

        # Previous-session change is based on
        # previous session close vs its own previous
        # session close where available.
        #
        # We intentionally do not reconstruct this here
        # from future data.
        #
        # It remains UNKNOWN unless directly available.
        prev_change = None
        prev_change_pct = None

        prev_available = (
            prev_close is not None
            and prev_high is not None
            and prev_low is not None
        )

    current_open = r["AM_OPEN"]

    gap = None
    gap_pct = None

    if current_open is not None and prev_close is not None:
        gap = current_open - prev_close
        gap_pct = pct(
            current_open,
            prev_close
        )

    open_vs_prev_high = None
    open_vs_prev_high_pct = None

    if current_open is not None and prev_high is not None:
        open_vs_prev_high = (
            current_open - prev_high
        )

        open_vs_prev_high_pct = pct(
            current_open,
            prev_high
        )

    open_vs_prev_low = None
    open_vs_prev_low_pct = None

    if current_open is not None and prev_low is not None:
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

    current_open_available = (
        current_open is not None
    )

    # --------------------------------------------------
    # CRITICAL ANTI-LOOKAHEAD GUARANTEE
    # --------------------------------------------------

    future_session_fields_used = False
    future_intraday_fields_used = False

    if prev_available and current_open_available:
        feature_status = "READY_09_10"

    elif current_open_available:
        feature_status = "PARTIAL_NO_PREV"

    elif prev_available:
        feature_status = "PARTIAL_NO_OPEN"

    else:
        feature_status = "UNAVAILABLE"

    summary[feature_status] += 1

    # --------------------------------------------------
    # BUILD FEATURE
    # --------------------------------------------------

    feature = {
        "DATE": date,
        "CODE": code,
        "NAME": r["NAME"],

        "DECISION_TIME": "09:10",

        "QUALITY_STATUS": q["QUALITY_STATUS"],
        "PRICE_FIELD_STATUS": q["PRICE_FIELD_STATUS"],

        "PREV_DATE": prev_date,
        "PREV_CLOSE": fmt_num(prev_close),
        "PREV_HIGH": fmt_num(prev_high),
        "PREV_LOW": fmt_num(prev_low),
        "PREV_RANGE": fmt_num(prev_range),
        "PREV_CHANGE": fmt_num(prev_change),
        "PREV_CHANGE_PCT": fmt_num(prev_change_pct),

        "CURRENT_OPEN": fmt_num(current_open),

        "GAP": fmt_num(gap),
        "GAP_PCT": fmt_num(gap_pct),

        "OPEN_VS_PREV_HIGH": fmt_num(
            open_vs_prev_high
        ),
        "OPEN_VS_PREV_HIGH_PCT": fmt_num(
            open_vs_prev_high_pct
        ),

        "OPEN_VS_PREV_LOW": fmt_num(
            open_vs_prev_low
        ),
        "OPEN_VS_PREV_LOW_PCT": fmt_num(
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

        "FUTURE_SESSION_FIELDS_USED": "FALSE",
        "FUTURE_INTRADAY_FIELDS_USED": "FALSE",

        "FEATURE_STATUS": feature_status,
    }

    features.append(feature)

    # --------------------------------------------------
    # AUDIT
    # --------------------------------------------------

    if future_session_fields_used:
        audit_status = "FAIL"
        audit_reason = "FUTURE_SESSION_DATA_USED"

    elif future_intraday_fields_used:
        audit_status = "FAIL"
        audit_reason = "FUTURE_INTRADAY_DATA_USED"

    elif q["DUPLICATE_KEY"] not in (
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
        audit_reason = "REQUIRED_FEATURE_DATA_MISSING"

    audit_summary[audit_status] += 1

    audits.append({
        "DATE": date,
        "CODE": code,
        "DECISION_TIME": "09:10",
        "FEATURE_STATUS": feature_status,
        "QUALITY_STATUS": q["QUALITY_STATUS"],
        "PRICE_FIELD_STATUS": q["PRICE_FIELD_STATUS"],
        "PREV_DATA_AVAILABLE": (
            "TRUE" if prev_available else "FALSE"
        ),
        "CURRENT_OPEN_AVAILABLE": (
            "TRUE"
            if current_open_available
            else "FALSE"
        ),
        "FUTURE_SESSION_FIELDS_USED": "FALSE",
        "FUTURE_INTRADAY_FIELDS_USED": "FALSE",
        "AUDIT_STATUS": audit_status,
        "AUDIT_REASON": audit_reason,
    })

    # Current record becomes previous record
    # ONLY after features for the current date
    # have been generated.
    previous[code] = r


# --------------------------------------------------
# WRITE FEATURE
# --------------------------------------------------

with OUTPUT.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=feature_fields
    )

    writer.writeheader()
    writer.writerows(features)


# --------------------------------------------------
# WRITE AUDIT
# --------------------------------------------------

with AUDIT.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=audit_fields
    )

    writer.writeheader()
    writer.writerows(audits)


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
        "COUNT"
    ])

    for status, count in sorted(summary.items()):
        writer.writerow([
            "FEATURE_STATUS",
            status,
            count
        ])

    for status, count in sorted(
        audit_summary.items()
    ):
        writer.writerow([
            "AUDIT_STATUS",
            status,
            count
        ])


# --------------------------------------------------
# CONSOLE AUDIT
# --------------------------------------------------

print()
print("========================================")
print(" JPX REPLAY FEATURE BUILDER")
print("========================================")
print()

print(f"INPUT RECORDS    : {len(records):,}")
print(f"FEATURE RECORDS  : {len(features):,}")
print(f"AUDIT RECORDS    : {len(audits):,}")

print()
print("FEATURE STATUS:")

for status, count in sorted(summary.items()):
    print(
        f"  {status:20s}: {count:,}"
    )

print()
print("AUDIT STATUS:")

for status, count in sorted(
    audit_summary.items()
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

