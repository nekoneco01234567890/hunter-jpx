#!/usr/bin/env python3

import csv
from pathlib import Path
from collections import Counter

BASE = Path.home() / "jpx_replay"
DATA = BASE / "data"

FEATURE = DATA / "jpx_replay_feature.csv"
QUALITY = DATA / "jpx_replay_quality_audit.csv"

AUDIT = DATA / "jpx_replay_feature_audit.csv"
SUMMARY = DATA / "jpx_replay_feature_summary.csv"


# ---------------------------------------------
# LOAD QUALITY
# ---------------------------------------------

quality = {}

with QUALITY.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    for row in reader:

        key = (
            row["DATE"].strip(),
            row["CODE"].strip()
        )

        quality[key] = {
            "DUPLICATE_KEY":
                row["DUPLICATE_KEY"].strip(),

            "QUALITY_STATUS":
                row["QUALITY_STATUS"].strip(),

            "PRICE_FIELD_STATUS":
                row["PRICE_FIELD_STATUS"].strip(),
        }


# ---------------------------------------------
# AUDIT
# ---------------------------------------------

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

counter = Counter()
total = 0


with FEATURE.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as fin, AUDIT.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as fout:

    reader = csv.DictReader(fin)

    writer = csv.DictWriter(
        fout,
        fieldnames=audit_fields
    )

    writer.writeheader()

    for row in reader:

        total += 1

        date = row["DATE"].strip()
        code = row["CODE"].strip()

        q = quality.get(
            (date, code),
            {
                "DUPLICATE_KEY": "UNKNOWN",
                "QUALITY_STATUS": "UNKNOWN",
                "PRICE_FIELD_STATUS": "UNKNOWN",
            }
        )

        feature_status = row[
            "FEATURE_STATUS"
        ].strip()

        prev_available = row[
            "PREV_DATA_AVAILABLE"
        ].strip()

        open_available = row[
            "CURRENT_OPEN_AVAILABLE"
        ].strip()

        future_session = row[
            "FUTURE_SESSION_FIELDS_USED"
        ].strip()

        future_intraday = row[
            "FUTURE_INTRADAY_FIELDS_USED"
        ].strip()

        duplicate = q[
            "DUPLICATE_KEY"
        ]

        # -----------------------------------------
        # AUDIT PRIORITY
        # -----------------------------------------

        if duplicate not in (
            "UNIQUE",
            "FALSE",
            "0",
            "NO",
        ):
            status = "FAIL"
            reason = "DUPLICATE_KEY"

        elif future_session == "TRUE":
            status = "FAIL"
            reason = "FUTURE_SESSION_DATA_USED"

        elif future_intraday == "TRUE":
            status = "FAIL"
            reason = "FUTURE_INTRADAY_DATA_USED"

        elif feature_status == "READY_09_10":

            status = "PASS"
            reason = "POINT_IN_TIME_OK"

        else:

            status = "LIMITED"
            reason = "REQUIRED_FEATURE_DATA_MISSING"

        counter[status] += 1

        writer.writerow({
            "DATE": date,
            "CODE": code,
            "DECISION_TIME":
                row["DECISION_TIME"],

            "FEATURE_STATUS":
                feature_status,

            "QUALITY_STATUS":
                q["QUALITY_STATUS"],

            "PRICE_FIELD_STATUS":
                q["PRICE_FIELD_STATUS"],

            "PREV_DATA_AVAILABLE":
                prev_available,

            "CURRENT_OPEN_AVAILABLE":
                open_available,

            "FUTURE_SESSION_FIELDS_USED":
                future_session,

            "FUTURE_INTRADAY_FIELDS_USED":
                future_intraday,

            "AUDIT_STATUS":
                status,

            "AUDIT_REASON":
                reason,
        })


# ---------------------------------------------
# SUMMARY
# ---------------------------------------------

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

    for status, count in sorted(counter.items()):

        writer.writerow([
            "AUDIT_STATUS",
            status,
            count
        ])


# ---------------------------------------------
# CONSOLE
# ---------------------------------------------

print()
print("========================================")
print(" REPLAY FEATURE AUDIT REPAIR")
print("========================================")
print()

print(f"FEATURE RECORDS : {total:,}")
print()

print("AUDIT STATUS:")

for status, count in sorted(counter.items()):

    print(
        f"  {status:20s}: {count:,}"
    )

print()

print(
    "FAIL = "
    f"{counter.get('FAIL', 0):,}"
)

print(
    "PASS = "
    f"{counter.get('PASS', 0):,}"
)

print(
    "LIMITED = "
    f"{counter.get('LIMITED', 0):,}"
)

print()

print(f"AUDIT   : {AUDIT}")
print(f"SUMMARY : {SUMMARY}")
print()

