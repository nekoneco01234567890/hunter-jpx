from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent
JPX_DIR = ROOT / "data" / "jpx_weekly_investor"
OUT = ROOT / "data" / "hunter" / "jpx_weekly_investor_flow_all_years.csv"

# このフォルダにある年別CSVを全部読む
sources = sorted(JPX_DIR.glob("jpx_weekly_investor_flow_v3_raw*.csv"))

rows = []
years = set()

for file in sources:
    with file.open(encoding="utf-8-sig") as f:
        data = list(csv.DictReader(f))
        rows.extend(data)
        for r in data:
            years.add(int(r["FILE_IDENTIFIER_DATE"][:4]))

rows.sort(key=lambda r: (
    r["FILE_IDENTIFIER_DATE"],
    r["OBSERVATION_START"],
    r["CATEGORY"],
    r["SIDE"]
))

with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

print("========================================")
print("STAGE41B MERGE YEARS")
print("========================================")
print("SOURCE_FILES :", len(sources))
print("YEARS        :", sorted(years))
print("TOTAL_ROWS   :", len(rows))
print("OUTPUT       :", OUT)
print("STAGE41B_STEP1 : PASS")
