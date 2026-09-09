import re
import csv
from pathlib import Path
from collections import Counter

BASE = Path.home() / "jpx_replay"
TXT_DIR = BASE / "txt"
DATA_DIR = BASE / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# 5文字の銘柄コード
# 数字だけでなく英字入りにも対応
CODE = r"[0-9A-Z]{5}"

# 1レコードを
# DATE + CODE + NAME + 普通株式 + 最大8個の価格
# として取得する
PATTERN = re.compile(
    rf"(?P<date>\d{{8}})\s+"
    rf"(?P<code>{CODE})\s+"
    rf"(?P<name>.*?)\s+普通株式"
    rf"(?P<values>(?:\s+[-0-9.]+){{0,8}})"
    rf"(?=\s+\d{{8}}\s+{CODE}\s+|\s*$)"
)

FIELDS = [
    "DATE",
    "CODE",
    "NAME",
    "AM_OPEN",
    "AM_HIGH",
    "AM_LOW",
    "AM_CLOSE",
    "PM_OPEN",
    "PM_HIGH",
    "PM_LOW",
    "PM_CLOSE",
    "VALUE_COUNT",
    "STATUS",
    "SOURCE_FILE",
]

def parse_file(txt_file):
    text = txt_file.read_text(
        encoding="utf-8",
        errors="replace"
    )

    rows = []
    matches = list(PATTERN.finditer(text))

    for m in matches:
        date = m.group("date")
        code = m.group("code")
        name = " ".join(m.group("name").split())

        raw_values = m.group("values").strip().split()

        values = raw_values[:8]

        while len(values) < 8:
            values.append("")

        if len(raw_values) == 8:
            status = "OK"
        elif len(raw_values) == 0:
            status = "NO_PRICE_DATA"
        else:
            status = "PARTIAL_PRICE_DATA"

        rows.append([
            date,
            code,
            name,
            *values,
            len(raw_values),
            status,
            txt_file.name,
        ])

    return rows, len(matches)


all_rows = []
audit = []

for txt_file in sorted(TXT_DIR.glob("*.txt")):
    rows, matches = parse_file(txt_file)

    status = "OK" if rows else "NO_RECORD"

    audit.append([
        txt_file.name,
        matches,
        len(rows),
        status,
    ])

    all_rows.extend(rows)


# --------------------------------------------------
# DATE + CODE 重複監査
# --------------------------------------------------

keys = [
    (r[0], r[1])
    for r in all_rows
]

counter = Counter(keys)

duplicates = [
    (key, count)
    for key, count in counter.items()
    if count > 1
]


# --------------------------------------------------
# ステータス集計
# --------------------------------------------------

status_counter = Counter(
    r[12]
    for r in all_rows
)


# --------------------------------------------------
# 出力
# --------------------------------------------------

out_csv = DATA_DIR / "jpx_replay_raw_v2.csv"
audit_csv = DATA_DIR / "jpx_replay_audit_v2.csv"
dup_csv = DATA_DIR / "jpx_replay_duplicates_v2.csv"
status_csv = DATA_DIR / "jpx_replay_status_v2.csv"


with out_csv.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:
    writer = csv.writer(f)
    writer.writerow(FIELDS)
    writer.writerows(all_rows)


with audit_csv.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:
    writer = csv.writer(f)

    writer.writerow([
        "SOURCE_FILE",
        "MATCH_COUNT",
        "ROW_COUNT",
        "STATUS",
    ])

    writer.writerows(audit)


with dup_csv.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:
    writer = csv.writer(f)

    writer.writerow([
        "DATE",
        "CODE",
        "COUNT",
    ])

    for (date, code), count in duplicates:
        writer.writerow([
            date,
            code,
            count,
        ])


with status_csv.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:
    writer = csv.writer(f)

    writer.writerow([
        "STATUS",
        "COUNT",
    ])

    for status, count in sorted(status_counter.items()):
        writer.writerow([
            status,
            count,
        ])


# --------------------------------------------------
# コンソール監査
# --------------------------------------------------

print()
print("========================================")
print(" JPX REPLAY PARSER V2")
print("========================================")
print()

print(f"TOTAL RECORDS      : {len(all_rows):,}")
print(f"UNIQUE DATE+CODE   : {len(counter):,}")
print(f"DUPLICATES         : {len(duplicates):,}")
print()

print("STATUS:")
for status, count in sorted(status_counter.items()):
    print(f"  {status:20s}: {count:,}")

print()

for item in audit:
    print(
        f"{item[0]} : "
        f"{item[1]:,} matches / "
        f"{item[2]:,} rows "
        f"[{item[3]}]"
    )

print()
print(f"CSV    : {out_csv}")
print(f"AUDIT  : {audit_csv}")
print(f"DUP    : {dup_csv}")
print(f"STATUS : {status_csv}")
print()

