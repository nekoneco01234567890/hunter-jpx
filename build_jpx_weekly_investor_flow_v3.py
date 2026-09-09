#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

RAW_OUT = OUT_DIR / "jpx_weekly_investor_flow_v3_raw.csv"
AUDIT_OUT = OUT_DIR / "jpx_weekly_investor_flow_v3_audit.csv"
SUMMARY_OUT = OUT_DIR / "jpx_weekly_investor_flow_v3_summary.csv"

FILES = sorted(SRC_DIR.glob("stock_val_1_*.xls"))

EXPECTED_FILES = 52

# ------------------------------------------------------------
# Canonical source hierarchy
# ------------------------------------------------------------

ROWS = [
    # SECTION, SUBSECTION, CATEGORY, SELL_ROW, BUY_ROW
    ("委託内訳", "", "法人", 24, 25),
    ("委託内訳", "", "個人", 27, 28),
    ("委託内訳", "", "海外投資家", 30, 31),
    ("委託内訳", "", "証券会社", 33, 34),

    ("委託内訳", "法人内訳", "投資信託", 38, 39),
    ("委託内訳", "法人内訳", "事業法人", 41, 42),
    ("委託内訳", "法人内訳", "その他法人等", 44, 45),
    ("委託内訳", "法人内訳", "金融機関", 47, 48),

    ("委託内訳", "金融機関内訳", "生保・損保", 52, 53),
    ("委託内訳", "金融機関内訳", "都銀・地銀等", 55, 56),
    ("委託内訳", "金融機関内訳", "信託銀行", 58, 59),
    ("委託内訳", "金融機関内訳", "その他金融機関", 61, 62),
]

EXPECTED_CATEGORIES = {
    x[2] for x in ROWS
}


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


def file_identifier_date(path):
    m = re.search(
        r"stock_val_1_(\d{6})\.xls$",
        path.name
    )
    if not m:
        raise ValueError(
            f"BAD_FILENAME={path.name}"
        )

    s = m.group(1)

    return (
        f"20{s[:2]}-{s[2:4]}-{s[4:6]}"
    )


def observation_period(cells):

    raw = clean(cells.get((3, 0), ""))

    m = re.search(
        r"(\d{4})年(\d{1,2})月第(\d+)週.*?"
        r"\(\s*(\d{1,2})/(\d{1,2})\s*-\s*"
        r"(\d{1,2})/(\d{1,2})\s*\)",
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

    return (
        f"{year}-{month:02d}-W{week}",
        f"{year}-{sm:02d}-{sd:02d}",
        f"{year}-{em:02d}-{ed:02d}",
    )


def period_headers(cells):

    previous = clean(cells.get((10, 3), ""))
    current = clean(cells.get((10, 7), ""))

    if not previous:
        raise ValueError("PREVIOUS_PERIOD_MISSING")

    if not current:
        raise ValueError("CURRENT_PERIOD_MISSING")

    return previous, current


def extract_side(cells, row):

    c1 = clean(cells.get((row - 1, 1), ""))

    if c1 == "売り":
        return "SELL"

    if c1 == "買い":
        return "BUY"

    raise ValueError(
        f"UNEXPECTED_SIDE row={row} value={c1!r}"
    )


def extract_row(
    cells,
    source_file,
    file_date,
    obs_week,
    obs_start,
    obs_end,
    section,
    subsection,
    category,
    row,
    period_type,
    period_start,
    period_end,
):

    # Excel displayed row -> zero-based BIFF row
    r = row - 1

    side = extract_side(cells, row)

    # Previous-period columns
    if period_type == "PREVIOUS":
        value_col = 4
        ratio_col = 5
        balance_col = 6

    # Current-period columns
    else:
        value_col = 8
        ratio_col = 9
        balance_col = 10

    return {
        "FILE_IDENTIFIER_DATE": file_date,
        "SOURCE_FILE": source_file,
        "OBSERVATION_WEEK": obs_week,
        "OBSERVATION_START": obs_start,
        "OBSERVATION_END": obs_end,

        "PERIOD_TYPE": period_type,
        "PERIOD_START": period_start,
        "PERIOD_END": period_end,

        "SECTION": section,
        "SUBSECTION": subsection,
        "CATEGORY": category,
        "SIDE": side,

        "AMOUNT": amount(
            cells.get((r, value_col), "")
        ),

        "RATIO": ratio(
            cells.get((r, ratio_col), "")
        ),

        "BALANCE": amount(
            cells.get((r, balance_col), "")
        ),
    }


def parse_file(path):

    wb = ole_stream(path)

    sst_total, sst_unique, sst = parse_sst(wb)

    cells = get_cells(wb, sst)

    file_date = file_identifier_date(path)

    obs_week, obs_start, obs_end = (
        observation_period(cells)
    )

    previous_header, current_header = (
        period_headers(cells)
    )

    rows = []

    for (
        section,
        subsection,
        category,
        sell_row,
        buy_row,
    ) in ROWS:

        for period_type in (
            "PREVIOUS",
            "CURRENT",
        ):

            if period_type == "PREVIOUS":
                p_start = previous_header
                p_end = previous_header
            else:
                p_start = obs_start
                p_end = obs_end

            for row in (
                sell_row,
                buy_row,
            ):

                rows.append(
                    extract_row(
                        cells,
                        path.name,
                        file_date,
                        obs_week,
                        obs_start,
                        obs_end,
                        section,
                        subsection,
                        category,
                        row,
                        period_type,
                        p_start,
                        p_end,
                    )
                )

    return (
        rows,
        sst_total,
        sst_unique,
        obs_week,
        obs_start,
        obs_end,
    )


def main():

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if len(FILES) != EXPECTED_FILES:
        raise SystemExit(
            f"FAIL FILE_COUNT "
            f"expected={EXPECTED_FILES} "
            f"actual={len(FILES)}"
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

    for i, path in enumerate(FILES, 1):

        try:

            (
                rows,
                sst_total,
                sst_unique,
                obs_week,
                obs_start,
                obs_end,
            ) = parse_file(path)

            # Exact expected source rows:
            # 12 categories × 2 sides × 2 periods
            if len(rows) != 48:
                raise ValueError(
                    f"ROW_COUNT_EXPECTED_48_ACTUAL_{len(rows)}"
                )

            categories = {
                r["CATEGORY"]
                for r in rows
            }

            if categories != EXPECTED_CATEGORIES:
                raise ValueError(
                    "CATEGORY_SET_MISMATCH "
                    f"actual={sorted(categories)}"
                )

            sides = {
                r["SIDE"]
                for r in rows
            }

            if sides != {"SELL", "BUY"}:
                raise ValueError(
                    f"SIDE_SET_MISMATCH={sides}"
                )

            periods = {
                r["PERIOD_TYPE"]
                for r in rows
            }

            if periods != {
                "PREVIOUS",
                "CURRENT",
            }:
                raise ValueError(
                    f"PERIOD_SET_MISMATCH={periods}"
                )

            all_rows.extend(rows)

            audits.append({
                "SOURCE_FILE": path.name,
                "STATUS": "PASS",
                "SST_TOTAL": sst_total,
                "SST_UNIQUE": sst_unique,
                "ROW_COUNT": len(rows),
                "OBSERVATION_WEEK": obs_week,
                "OBSERVATION_START": obs_start,
                "OBSERVATION_END": obs_end,
                "ERROR": "",
            })

            print(
                f"[{i:02d}/{len(FILES)}] PASS "
                f"{path.name} rows={len(rows)}"
            )

        except Exception as e:

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

    if any(
        a["STATUS"] == "FAIL"
        for a in audits
    ):
        print()
        print("V3 BUILD ABORTED")
        print("NO PARTIAL RAW WRITTEN")
        sys.exit(1)

    # --------------------------------------------------------
    # Global duplicate-key audit
    # --------------------------------------------------------

    seen = set()

    for r in all_rows:

        key = (
            r["OBSERVATION_START"],
            r["OBSERVATION_END"],
            r["PERIOD_TYPE"],
            r["SECTION"],
            r["SUBSECTION"],
            r["CATEGORY"],
            r["SIDE"],
        )

        if key in seen:
            raise SystemExit(
                f"FAIL DUPLICATE_KEY={key}"
            )

        seen.add(key)

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

        w.writerows(all_rows)

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

        w.writerows(audits)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    from collections import Counter

    category_count = Counter(
        r["CATEGORY"]
        for r in all_rows
    )

    subsection_count = Counter(
        r["SUBSECTION"] or "(direct)"
        for r in all_rows
    )

    period_count = Counter(
        r["PERIOD_TYPE"]
        for r in all_rows
    )

    side_count = Counter(
        r["SIDE"]
        for r in all_rows
    )

    file_count = Counter(
        r["SOURCE_FILE"]
        for r in all_rows
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

        w.writerow([
            "METRIC",
            "VALUE"
        ])

        w.writerow([
            "SOURCE_FILES",
            len(FILES)
        ])

        w.writerow([
            "PASS_FILES",
            len(FILES)
        ])

        w.writerow([
            "FAIL_FILES",
            0
        ])

        w.writerow([
            "TOTAL_ROWS",
            len(all_rows)
        ])

        w.writerow([
            "ROWS_PER_FILE",
            48
        ])

        w.writerow([
            "CANONICAL_KEYS",
            len(seen)
        ])

        for k, v in sorted(
            period_count.items()
        ):
            w.writerow([
                "PERIOD:" + k,
                v
            ])

        for k, v in sorted(
            side_count.items()
        ):
            w.writerow([
                "SIDE:" + k,
                v
            ])

        for k, v in sorted(
            subsection_count.items()
        ):
            w.writerow([
                "SUBSECTION:" + k,
                v
            ])

        for k, v in sorted(
            category_count.items()
        ):
            w.writerow([
                "CATEGORY:" + k,
                v
            ])

        for k, v in sorted(
            file_count.items()
        ):
            if v != 48:
                raise SystemExit(
                    f"FAIL FILE_ROW_COUNT "
                    f"{k}={v}"
                )

    print()
    print("========================================")
    print("JPX WEEKLY INVESTOR FLOW V3 = PASS")
    print("========================================")
    print(f"SOURCE_FILES = {len(FILES)}")
    print(f"PASS_FILES   = {len(FILES)}")
    print("FAIL_FILES   = 0")
    print(f"TOTAL_ROWS   = {len(all_rows)}")
    print("ROWS_PER_FILE = 48")
    print(f"CANONICAL_KEYS = {len(seen)}")
    print()
    print(f"RAW     = {RAW_OUT}")
    print(f"AUDIT   = {AUDIT_OUT}")
    print(f"SUMMARY = {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
