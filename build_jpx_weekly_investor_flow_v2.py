#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JPX Weekly Investor Flow V2
- Existing V1 output is never overwritten
- Preserve source hierarchy
- Preserve previous/current period separately
- Preserve Balance as BALANCE
- Preserve blank cells as empty/NULL
- Keep source file identity separate from observation period
- Fail closed on structural anomalies
"""

from pathlib import Path
import csv
import re
import sys

from build_jpx_weekly_investor_flow import (
    ole_stream,
    parse_sst,
    get_cells,
)

SRC_DIR = Path("/sdcard/Download")

OUT_DIR = Path("data/jpx_weekly_investor")

RAW_OUT = OUT_DIR / "jpx_weekly_investor_flow_v2_raw.csv"
AUDIT_OUT = OUT_DIR / "jpx_weekly_investor_flow_v2_audit.csv"
SUMMARY_OUT = OUT_DIR / "jpx_weekly_investor_flow_v2_summary.csv"

PREFIX = "stock_val_1_"
FILES = sorted(SRC_DIR.glob(f"{PREFIX}*.xls"))

EXPECTED_FILES = 52


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def clean(v):
    if v is None:
        return ""
    return str(v).strip()


def amount(v):
    v = clean(v)
    if not v:
        return ""
    v = v.replace(",", "")
    try:
        return str(int(v))
    except ValueError:
        return v


def ratio(v):
    v = clean(v)
    if not v:
        return ""
    try:
        return str(float(v))
    except ValueError:
        return v


def parse_file_identifier(path):
    m = re.search(r"stock_val_1_(\d{6})\.xls$", path.name)
    if not m:
        raise ValueError(f"BAD_FILENAME={path.name}")

    s = m.group(1)

    return (
        f"20{s[0:2]}-{s[2:4]}-{s[4:6]}"
    )


def parse_observation_period(cells):
    """
    Row 4 contains:
      2025年1月第1週 2025/1 week1 ( 1/6 - 1/10 )

    Return:
      observation_week
      observation_start
      observation_end
    """

    raw = clean(cells.get((3, 0), ""))

    if not raw:
        raise ValueError("OBSERVATION_PERIOD_MISSING")

    m = re.search(
        r"(\d{4})年(\d{1,2})月第(\d+)週.*?\(\s*(\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\s*\)",
        raw
    )

    if not m:
        raise ValueError(
            f"OBSERVATION_PERIOD_UNPARSED={raw!r}"
        )

    year = int(m.group(1))
    month = int(m.group(2))
    week = int(m.group(3))

    sm = int(m.group(4))
    sd = int(m.group(5))
    em = int(m.group(6))
    ed = int(m.group(7))

    start_year = year
    end_year = year

    # Defensive year rollover handling
    if sm > month:
        start_year -= 1

    if em < month and month == 12:
        end_year += 1

    return (
        f"{year}-{month:02d}-W{week}",
        f"{start_year}-{sm:02d}-{sd:02d}",
        f"{end_year}-{em:02d}-{ed:02d}",
    )


def parse_period_headers(cells):
    """
    Row 11/12 structure:

      C3 = Value
      C5 = Ratio
      C6 = Balance

      C7 = Value
      C9 = Ratio
      C10 = Balance

    Row 10:
      C3 = previous period
      C7 = current period
    """

    previous_raw = clean(cells.get((10, 3), ""))
    current_raw = clean(cells.get((10, 7), ""))

    if not previous_raw:
        raise ValueError("PREVIOUS_PERIOD_HEADER_MISSING")

    if not current_raw:
        raise ValueError("CURRENT_PERIOD_HEADER_MISSING")

    return previous_raw, current_raw


def normalize_side(v):
    v = clean(v)

    if v == "売り":
        return "SELL"

    if v == "買い":
        return "BUY"

    if v == "合計":
        return "TOTAL"

    return v


def is_data_side(v):
    return v in ("売り", "買い")


# ------------------------------------------------------------
# Hierarchy
# ------------------------------------------------------------

# English rows following Japanese labels are continuation rows.
# The hierarchy is therefore carried forward until a new section
# header is encountered.

TOP_SECTION_ROWS = {
    "委託内訳 Brokerage Trading": "委託内訳",
    "法人内訳 Institutions": "法人内訳",
    "金融機関内訳 Financial institutions": "金融機関内訳",
    "個人、自己の現金・信用取引数値 Individual & Proprietary":
        "個人、自己の現金・信用取引数値",
}


def detect_section_header(c0):
    c0 = clean(c0)

    if c0 in TOP_SECTION_ROWS:
        return TOP_SECTION_ROWS[c0]

    return None


# ------------------------------------------------------------
# Parse one XLS
# ------------------------------------------------------------

def parse_xls(path):

    wb = ole_stream(path)

    total, unique, sst = parse_sst(wb)

    cells = get_cells(wb, sst)

    file_identifier_date = parse_file_identifier(path)

    observation_week, observation_start, observation_end = (
        parse_observation_period(cells)
    )

    previous_period, current_period = parse_period_headers(cells)

    rows = []

    section = ""
    subsection = ""
    category = ""

    # Source rows 23 onward contain investor-type hierarchy.
    for r in range(22, 65):

        c0 = clean(cells.get((r, 0), ""))
        c1 = clean(cells.get((r, 1), ""))
        c2 = clean(cells.get((r, 2), ""))

        # ----------------------------------------------------
        # Section headers
        # ----------------------------------------------------

        new_section = detect_section_header(c0)

        if new_section:
            section = "委託内訳"
            subsection = new_section
            category = ""
            continue

        # Top-level "法人" / "個人" / "海外投資家" / "証券会社"
        # are direct children of 委託内訳.
        if c1 in ("売り", "買い", "合計") and c0:
            # If this row introduces a new Japanese category,
            # update category.
            if c0 not in (
                "Proprietary",
                "Brokerage",
                "Total",
                "Institutions",
                "Individuals",
                "Foreigners",
                "Securities Cos.",
                "Business Cos.",
                "Other Cos.",
                "Financial",
                "Life & Non-Life",
                "City & Regional BK",
                "Trust BK",
                "Other Financials",
            ):
                category = c0

        # English continuation rows must inherit category.
        if c0 in (
            "Institutions",
            "Individuals",
            "Foreigners",
            "Securities Cos.",
            "Business Cos.",
            "Other Cos.",
            "Financial",
            "Life & Non-Life",
            "City & Regional BK",
            "Trust BK",
            "Other Financials",
        ):
            continue

        # Skip total rows.
        if c1 != "売り" and c1 != "買い":
            continue

        # Determine hierarchy from source position.
        #
        # Rows 24-35:
        #   direct children of 委託内訳
        #
        # Rows 38-49:
        #   children of 法人内訳 / 金融機関
        #
        # Rows 52-63:
        #   children of 金融機関内訳

        if 23 <= r <= 34:
            row_section = "委託内訳"
            row_subsection = ""
        elif 37 <= r <= 48:
            row_section = "委託内訳"
            row_subsection = "法人内訳"
        elif 51 <= r <= 62:
            row_section = "委託内訳"
            row_subsection = "金融機関内訳"
        else:
            continue

        # Japanese category is present on the SELL row.
        row_category = c0

        if not row_category:
            continue

        sell_buy = normalize_side(c1)

        # Previous period
        prev_value = amount(cells.get((r, 4), ""))
        prev_ratio = ratio(cells.get((r, 5), ""))
        prev_balance = amount(cells.get((r, 6), ""))

        # Current period
        curr_value = amount(cells.get((r, 8), ""))
        curr_ratio = ratio(cells.get((r, 9), ""))
        curr_balance = amount(cells.get((r, 10), ""))

        base = {
            "SOURCE_FILE": path.name,
            "FILE_IDENTIFIER_DATE": file_identifier_date,
            "OBSERVATION_WEEK": observation_week,
            "OBSERVATION_START": observation_start,
            "OBSERVATION_END": observation_end,
            "SECTION": row_section,
            "SUBSECTION": row_subsection,
            "CATEGORY": row_category,
            "SIDE": sell_buy,
        }

        rows.append({
            **base,
            "PERIOD_TYPE": "PREVIOUS",
            "PERIOD_START": previous_period,
            "PERIOD_END": previous_period,
            "AMOUNT": prev_value,
            "RATIO": prev_ratio,
            "BALANCE": prev_balance,
        })

        rows.append({
            **base,
            "PERIOD_TYPE": "CURRENT",
            "PERIOD_START": observation_start,
            "PERIOD_END": observation_end,
            "AMOUNT": curr_value,
            "RATIO": curr_ratio,
            "BALANCE": curr_balance,
        })

    return {
        "file": path.name,
        "file_identifier_date": file_identifier_date,
        "observation_week": observation_week,
        "observation_start": observation_start,
        "observation_end": observation_end,
        "sst_total": total,
        "sst_unique": unique,
        "row_count": len(rows),
        "rows": rows,
    }


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if len(FILES) != EXPECTED_FILES:
        raise SystemExit(
            f"FAIL: EXPECTED_FILES={EXPECTED_FILES} "
            f"ACTUAL_FILES={len(FILES)}"
        )

    raw_fields = [
        "FILE_IDENTIFIER_DATE",
        "SOURCE_FILE",
        "OBSERVATION_WEEK",
        "OBSERVATION_START",
        "OBSERVATION_END",
        "PERIOD_TYPE",
        "PERIOD_START",
        "PERIOD_END",
        "SECTION",
        "SUBSECTION",
        "CATEGORY",
        "SIDE",
        "AMOUNT",
        "RATIO",
        "BALANCE",
    ]

    audit_fields = [
        "SOURCE_FILE",
        "STATUS",
        "SST_TOTAL",
        "SST_UNIQUE",
        "ROW_COUNT",
        "OBSERVATION_WEEK",
        "OBSERVATION_START",
        "OBSERVATION_END",
        "ERROR",
    ]

    all_rows = []
    audits = []

    pass_files = 0
    fail_files = 0

    for i, path in enumerate(FILES, 1):

        try:

            result = parse_xls(path)

            rows = result["rows"]

            # Structural fail-closed checks
            if not rows:
                raise ValueError("NO_DATA_ROWS")

            if not result["observation_week"]:
                raise ValueError("NO_OBSERVATION_WEEK")

            if not result["observation_start"]:
                raise ValueError("NO_OBSERVATION_START")

            if not result["observation_end"]:
                raise ValueError("NO_OBSERVATION_END")

            # Check expected hierarchy
            for row in rows:

                if row["SECTION"] != "委託内訳":
                    raise ValueError(
                        f"BAD_SECTION={row['SECTION']}"
                    )

                if row["SUBSECTION"] not in (
                    "",
                    "法人内訳",
                    "金融機関内訳",
                ):
                    raise ValueError(
                        f"BAD_SUBSECTION={row['SUBSECTION']}"
                    )

                if row["SIDE"] not in ("SELL", "BUY"):
                    raise ValueError(
                        f"BAD_SIDE={row['SIDE']}"
                    )

            all_rows.extend(rows)

            audits.append({
                "SOURCE_FILE": path.name,
                "STATUS": "PASS",
                "SST_TOTAL": result["sst_total"],
                "SST_UNIQUE": result["sst_unique"],
                "ROW_COUNT": result["row_count"],
                "OBSERVATION_WEEK": result["observation_week"],
                "OBSERVATION_START": result["observation_start"],
                "OBSERVATION_END": result["observation_end"],
                "ERROR": "",
            })

            pass_files += 1

            print(
                f"[{i:02d}/{len(FILES)}] PASS "
                f"{path.name} rows={result['row_count']}"
            )

        except Exception as e:

            fail_files += 1

            audits.append({
                "SOURCE_FILE": path.name,
                "STATUS": "FAIL",
                "SST_TOTAL": "",
                "SST_UNIQUE": "",
                "ROW_COUNT": "",
                "OBSERVATION_WEEK": "",
                "OBSERVATION_START": "",
                "OBSERVATION_END": "",
                "ERROR": repr(e),
            })

            print(
                f"[{i:02d}/{len(FILES)}] FAIL "
                f"{path.name} error={e}"
            )

    # --------------------------------------------------------
    # Never write a partial official V2 dataset
    # --------------------------------------------------------

    if fail_files:
        print()
        print("V2 BUILD ABORTED")
        print(f"PASS_FILES={pass_files}")
        print(f"FAIL_FILES={fail_files}")
        print("NO_V2_RAW_WRITTEN")
        sys.exit(1)

    # --------------------------------------------------------
    # Duplicate key audit
    # --------------------------------------------------------

    keys = {}

    for row in all_rows:

        key = (
            row["OBSERVATION_START"],
            row["OBSERVATION_END"],
            row["PERIOD_TYPE"],
            row["SECTION"],
            row["SUBSECTION"],
            row["CATEGORY"],
            row["SIDE"],
        )

        keys[key] = keys.get(key, 0) + 1

    duplicate_keys = {
        k: v for k, v in keys.items()
        if v > 1
    }

    if duplicate_keys:
        print()
        print("FAIL: DUPLICATE_CANONICAL_KEYS")
        for k, v in list(duplicate_keys.items())[:20]:
            print(v, k)
        sys.exit(1)

    # --------------------------------------------------------
    # Write RAW
    # --------------------------------------------------------

    with RAW_OUT.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        w = csv.DictWriter(
            f,
            fieldnames=raw_fields,
            lineterminator="\n"
        )

        w.writeheader()

        for row in all_rows:
            w.writerow(row)

    # --------------------------------------------------------
    # Write AUDIT
    # --------------------------------------------------------

    with AUDIT_OUT.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        w = csv.DictWriter(
            f,
            fieldnames=audit_fields,
            lineterminator="\n"
        )

        w.writeheader()

        for row in audits:
            w.writerow(row)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    section_counts = {}
    subsection_counts = {}
    category_counts = {}
    period_counts = {}

    for row in all_rows:

        section_counts[row["SECTION"]] = (
            section_counts.get(row["SECTION"], 0) + 1
        )

        subsection_counts[row["SUBSECTION"]] = (
            subsection_counts.get(row["SUBSECTION"], 0) + 1
        )

        category_counts[row["CATEGORY"]] = (
            category_counts.get(row["CATEGORY"], 0) + 1
        )

        period_counts[row["PERIOD_TYPE"]] = (
            period_counts.get(row["PERIOD_TYPE"], 0) + 1
        )

    with SUMMARY_OUT.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        w = csv.writer(
            f,
            lineterminator="\n"
        )

        w.writerow(["METRIC", "VALUE"])

        w.writerow(["SOURCE_FILES", len(FILES)])
        w.writerow(["PASS_FILES", pass_files])
        w.writerow(["FAIL_FILES", fail_files])
        w.writerow(["TOTAL_ROWS", len(all_rows)])
        w.writerow(["DUPLICATE_CANONICAL_KEYS", len(duplicate_keys)])

        for k, v in sorted(period_counts.items()):
            w.writerow([f"PERIOD_TYPE:{k}", v])

        for k, v in sorted(section_counts.items()):
            w.writerow([f"SECTION:{k}", v])

        for k, v in sorted(subsection_counts.items()):
            w.writerow([f"SUBSECTION:{k}", v])

        for k, v in sorted(category_counts.items()):
            w.writerow([f"CATEGORY:{k}", v])

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print()
    print("========================================")
    print("JPX WEEKLY INVESTOR FLOW V2 = PASS")
    print("========================================")
    print(f"SOURCE_FILES = {len(FILES)}")
    print(f"PASS_FILES   = {pass_files}")
    print(f"FAIL_FILES   = {fail_files}")
    print(f"TOTAL_ROWS   = {len(all_rows)}")
    print(f"RAW          = {RAW_OUT}")
    print(f"AUDIT        = {AUDIT_OUT}")
    print(f"SUMMARY      = {SUMMARY_OUT}")
    print()
    print("HIERARCHY:")
    print("  委託内訳")
    print("    ├─ 法人")
    print("    ├─ 個人")
    print("    ├─ 海外投資家")
    print("    └─ 証券会社")
    print("  法人内訳")
    print("    ├─ 投資信託")
    print("    ├─ 事業法人")
    print("    └─ その他法人等")
    print("  金融機関内訳")
    print("    ├─ 生保・損保")
    print("    ├─ 都銀・地銀等")
    print("    ├─ 信託銀行")
    print("    └─ その他金融機関")


if __name__ == "__main__":
    main()
