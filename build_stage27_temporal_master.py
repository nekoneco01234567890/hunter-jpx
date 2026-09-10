from pathlib import Path
import csv
from collections import Counter

SRC = Path(
    "data/jpx_weekly_investor/"
    "jpx_weekly_investor_flow_v3_raw.csv"
)

OUT = Path(
    "data/hunter/"
    "jpx_temporal_master_2025.csv"
)

AUDIT = Path(
    "data/hunter/"
    "jpx_stage27_temporal_master_audit.csv"
)


# ============================================================
# LOAD
# ============================================================

with SRC.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

if len(rows) != 2496:
    raise SystemExit(
        f"FAIL: unexpected source rows: {len(rows)}"
    )


# ============================================================
# GROUP BY EXACT OBSERVATION PERIOD
# ============================================================

groups = {}

for r in rows:

    obs_week = r["OBSERVATION_WEEK"].strip()
    start = r["OBSERVATION_START"].strip()
    end = r["OBSERVATION_END"].strip()

    if not obs_week:
        raise SystemExit("FAIL: empty OBSERVATION_WEEK")

    if not start:
        raise SystemExit("FAIL: empty OBSERVATION_START")

    if not end:
        raise SystemExit("FAIL: empty OBSERVATION_END")

    period_key = start + "__" + end

    groups.setdefault(
        period_key,
        {
            "OBSERVATION_WEEK": obs_week,
            "OBSERVATION_START": start,
            "OBSERVATION_END": end,
            "PERIOD_KEY": period_key,
            "SOURCE_FILES": set(),
            "ROWS": 0,
        }
    )

    g = groups[period_key]
    g["SOURCE_FILES"].add(r["SOURCE_FILE"])
    g["ROWS"] += 1


# ============================================================
# SORT
# ============================================================

masters = sorted(
    groups.values(),
    key=lambda x: (
        x["OBSERVATION_START"],
        x["OBSERVATION_END"]
    )
)


# ============================================================
# STRUCTURAL AUDIT
# ============================================================

audit = []

duplicate_period_keys = (
    len(groups) -
    len(set(g["PERIOD_KEY"] for g in masters))
)

bad_row_counts = []

for g in masters:

    source_count = len(g["SOURCE_FILES"])

    status = "PASS"

    error = ""

    if g["ROWS"] != 48:
        status = "FAIL"
        error = f"EXPECTED_48_ROWS_GOT_{g['ROWS']}"

        bad_row_counts.append(
            (
                g["PERIOD_KEY"],
                g["ROWS"]
            )
        )

    if source_count != 1:
        status = "FAIL"
        error = (
            f"EXPECTED_1_SOURCE_FILE_GOT_{source_count}"
        )

    audit.append(
        {
            "PERIOD_KEY": g["PERIOD_KEY"],
            "OBSERVATION_WEEK": g["OBSERVATION_WEEK"],
            "OBSERVATION_START": g["OBSERVATION_START"],
            "OBSERVATION_END": g["OBSERVATION_END"],
            "SOURCE_FILE_COUNT": source_count,
            "ROWS": g["ROWS"],
            "STATUS": status,
            "ERROR": error,
        }
    )


# ============================================================
# CHRONOLOGICAL VALIDATION
# ============================================================

chronology_error = 0

for a, b in zip(masters, masters[1:]):

    if a["OBSERVATION_START"] >= b["OBSERVATION_START"]:
        chronology_error += 1


# ============================================================
# GAP INFORMATION
# ============================================================

gap_days = []

from datetime import date

for a, b in zip(masters, masters[1:]):

    a_end = date.fromisoformat(
        a["OBSERVATION_END"]
    )

    b_start = date.fromisoformat(
        b["OBSERVATION_START"]
    )

    delta = (b_start - a_end).days

    gap_days.append(delta)


# ============================================================
# OUTPUT
# ============================================================

fields = [
    "PERIOD_INDEX",
    "OBSERVATION_WEEK",
    "OBSERVATION_START",
    "OBSERVATION_END",
    "PERIOD_KEY",
    "SOURCE_FILE",
    "SOURCE_FILE_COUNT",
    "SOURCE_ROWS",
]

out_rows = []

for i, g in enumerate(masters, 1):

    source_files = sorted(g["SOURCE_FILES"])

    out_rows.append(
        {
            "PERIOD_INDEX": i,
            "OBSERVATION_WEEK": g["OBSERVATION_WEEK"],
            "OBSERVATION_START": g["OBSERVATION_START"],
            "OBSERVATION_END": g["OBSERVATION_END"],
            "PERIOD_KEY": g["PERIOD_KEY"],
            "SOURCE_FILE": (
                source_files[0]
                if len(source_files) == 1
                else "|".join(source_files)
            ),
            "SOURCE_FILE_COUNT": len(source_files),
            "SOURCE_ROWS": g["ROWS"],
        }
    )


with OUT.open("w", newline="", encoding="utf-8") as f:

    w = csv.DictWriter(
        f,
        fieldnames=fields
    )

    w.writeheader()
    w.writerows(out_rows)


with AUDIT.open("w", newline="", encoding="utf-8") as f:

    fields_audit = list(audit[0].keys())

    w = csv.DictWriter(
        f,
        fieldnames=fields_audit
    )

    w.writeheader()
    w.writerows(audit)


# ============================================================
# REPORT
# ============================================================

print("========================================")
print("STAGE27A TEMPORAL MASTER")
print("========================================")

print("SOURCE_ROWS          :", len(rows))
print("TEMPORAL_PERIODS     :", len(masters))
print("EXPECTED_PERIODS     : 52")
print(
    "UNIQUE_PERIOD_KEYS   :",
    len(set(g["PERIOD_KEY"] for g in masters))
)
print("DUPLICATE_KEYS       :", duplicate_period_keys)
print("CHRONOLOGY_ERRORS    :", chronology_error)
print("BAD_ROW_COUNTS       :", len(bad_row_counts))

print()
print("=== PERIODS ===")

for g in masters:

    print(
        g["OBSERVATION_WEEK"],
        "=>",
        g["OBSERVATION_START"],
        "~",
        g["OBSERVATION_END"],
        "ROWS=",
        g["ROWS"]
    )

print()
print("=== GAP DAYS ===")

if gap_days:
    print(
        "MIN=",
        min(gap_days),
        "MAX=",
        max(gap_days)
    )

print()
print("OUTPUT :", OUT)
print("AUDIT  :", AUDIT)

if (
    len(rows) == 2496
    and len(masters) == 52
    and duplicate_period_keys == 0
    and chronology_error == 0
    and len(bad_row_counts) == 0
):
    print()
    print("TEMPORAL_MASTER_AUDIT : PASS")
else:
    print()
    print("TEMPORAL_MASTER_AUDIT : FAIL")
