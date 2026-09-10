from pathlib import Path
import csv

RANK_FILE = Path("data/hunter/stage38_feature_importance.csv")
TRAIN_FILE = Path("data/hunter/stage35_training_input.csv")
OUTPUT = Path("data/hunter/stage38_selected_training.csv")

TOP_K = 20   # ← 必要ならここだけ変更

rank = list(csv.DictReader(RANK_FILE.open("r", encoding="utf-8-sig")))
selected = [r["FEATURE"] for r in rank[:TOP_K]]

rows = list(csv.DictReader(TRAIN_FILE.open("r", encoding="utf-8-sig")))

out_rows = []
for r in rows:
    row = {
        "PERIOD_INDEX": r["PERIOD_INDEX"],
        "TARGET_RETURN": r["TARGET_RETURN"]
    }
    for c in selected:
        row[c] = r[c]
    out_rows.append(row)

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=out_rows[0].keys())
    w.writeheader()
    w.writerows(out_rows)

print("========================================")
print("STAGE38B FEATURE SELECTION")
print("========================================")
print("INPUT_FEATURES :", len(rank))
print("SELECTED_TOP_K :", TOP_K)
print("OUTPUT_COLUMNS :", len(out_rows[0]) - 2)
print("ROWS           :", len(out_rows))
print("OUTPUT         :", OUTPUT)
print("STAGE38B_STEP1 : PASS")
