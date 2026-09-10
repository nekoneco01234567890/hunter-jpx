from config import TOP_K, HUNTER_DIR
import csv

RANK_FILE = HUNTER_DIR / "stage38_feature_importance.csv"
TRAIN_FILE = HUNTER_DIR / "stage35_training_input.csv"
OUTPUT = HUNTER_DIR / "stage38_selected_training.csv"

rank = list(csv.DictReader(open(RANK_FILE, encoding="utf-8-sig")))
selected = [r["FEATURE"] for r in rank[:TOP_K]]

rows = list(csv.DictReader(open(TRAIN_FILE, encoding="utf-8-sig")))

out_rows = []
for r in rows:
    row = {"PERIOD_INDEX": r["PERIOD_INDEX"], "TARGET_RETURN": r["TARGET_RETURN"]}
    for c in selected:
        row[c] = r[c]
    out_rows.append(row)

with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=out_rows[0].keys())
    w.writeheader()
    w.writerows(out_rows)

print("STAGE41A : PASS")
print("TOP_K :", TOP_K)
