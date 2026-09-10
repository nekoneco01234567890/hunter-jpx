from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent

JPX_DIR = ROOT / "data" / "jpx_weekly_investor"
N225_DIR = ROOT / "data" / "n225"
HUNTER_DIR = ROOT / "data" / "hunter"

RAW_CSV = JPX_DIR / "jpx_weekly_investor_flow_v3_raw.csv"

YEARS = []
if RAW_CSV.exists():
    with RAW_CSV.open(encoding="utf-8-sig") as f:
        YEARS = sorted({
            int(row["FILE_IDENTIFIER_DATE"][:4])
            for row in csv.DictReader(f)
        })

TOP_K = 20
RIDGE_ALPHA = 0.1
MIN_TRAIN_WEEKS = 5

print("CONFIG_LOAD : PASS")
print("YEARS :", YEARS)
