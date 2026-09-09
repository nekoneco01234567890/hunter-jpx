import re
import csv
from pathlib import Path

BASE = Path.home() / "jpx_replay"
TXT_DIR = BASE / "txt"
DATA_DIR = BASE / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

PATTERN = re.compile(
    r'(\d{8})\s+'
    r'(\d{5})\s+'
    r'(.*?)\s+普通株式\s+'
    r'([-0-9.]+)\s+'
    r'([-0-9.]+)\s+'
    r'([-0-9.]+)\s+'
    r'([-0-9.]+)\s+'
    r'([-0-9.]+)\s+'
    r'([-0-9.]+)\s+'
    r'([-0-9.]+)\s+'
    r'([-0-9.]+)'
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
]

def parse_file(txt_file):
    text = txt_file.read_text(encoding="utf-8", errors="replace")

    rows = []

    for m in PATTERN.finditer(text):
        (
            date,
            code,
            name,
            am_open,
            am_high,
            am_low,
            am_close,
            pm_open,
            pm_high,
            pm_low,
            pm_close,
        ) = m.groups()

        rows.append([
            date,
            code,
            " ".join(name.split()),
            am_open,
            am_high,
            am_low,
            am_close,
            pm_open,
            pm_high,
            pm_low,
            pm_close,
        ])

    return rows


all_rows = []
audit = []

for txt_file in sorted(TXT_DIR.glob("*.txt")):
    rows = parse_file(txt_file)

    audit.append([
        txt_file.name,
        len(rows),
        "OK" if rows else "NO_RECORD"
    ])

    all_rows.extend(rows)

out_csv = DATA_DIR / "jpx_replay_raw.csv"
audit_csv = DATA_DIR / "jpx_replay_audit.csv"

with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(FIELDS)
    writer.writerows(all_rows)

with audit_csv.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["SOURCE_FILE", "RECORD_COUNT", "STATUS"])
    writer.writerows(audit)

print()
print("=== JPX PARSE RESULT ===")
print(f"Records : {len(all_rows):,}")
print(f"CSV     : {out_csv}")
print(f"Audit   : {audit_csv}")
print()

for item in audit:
    print(f"{item[0]} : {item[1]:,} records [{item[2]}]")
