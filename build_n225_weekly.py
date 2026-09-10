from pathlib import Path
import csv
from collections import OrderedDict
from datetime import datetime

SRC = Path("data/n225_raw/N225_1MIN_RAW_2025_01_09.csv")
OUTDIR = Path("data/n225")
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT = OUTDIR / "n225_weekly.csv"

weeks = OrderedDict()

with SRC.open("r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for r in reader:
        date = datetime.fromisoformat(r["DATE"][:10])
        week = date.strftime("%Y-W%U")

        open_ = float(str(r["OPEN"]).replace(",", ""))
        high = float(str(r["HIGH"]).replace(",", ""))
        low = float(str(r["LOW"]).replace(",", ""))
        close = float(str(r["CLOSE"]).replace(",", ""))
        volume = int(float(str(r["VOLUME"]).replace(",", "")))

        if week not in weeks:
            weeks[week] = {
                "WEEK": week,
                "OPEN": open_,
                "HIGH": high,
                "LOW": low,
                "CLOSE": close,
                "VOLUME": volume,
            }
        else:
            w = weeks[week]
            w["HIGH"] = max(w["HIGH"], high)
            w["LOW"] = min(w["LOW"], low)
            w["CLOSE"] = close
            w["VOLUME"] += volume

with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(weeks.values())[0].keys())
    writer.writeheader()
    writer.writerows(weeks.values())

print("=== STAGE27A STEP1 PASS ===")
print("SOURCE_FILE :", SRC.name)
print("WEEK_ROWS   :", len(weeks))
print("OUTPUT_FILE :", OUT)
