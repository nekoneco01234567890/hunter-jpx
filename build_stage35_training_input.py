from pathlib import Path
import csv

FEATURES = Path("data/hunter/stage34_standardized_matrix.csv")
TARGETS  = Path("data/hunter/jpx_hunter_train_dataset_2025.csv")
OUTPUT   = Path("data/hunter/stage35_training_input.csv")

feature_rows = list(csv.DictReader(FEATURES.open("r", encoding="utf-8-sig")))
target_rows  = list(csv.DictReader(TARGETS.open("r", encoding="utf-8-sig")))

target_map = {r["PERIOD_INDEX"]: r["TARGET_RETURN"] for r in target_rows}

out_rows = []
for r in feature_rows:
    row = dict(r)
    row["TARGET_RETURN"] = target_map[r["PERIOD_INDEX"]]
    out_rows.append(row)

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=out_rows[0].keys())
    w.writeheader()
    w.writerows(out_rows)

print("========================================")
print("STAGE35 TRAINING INPUT")
print("========================================")
print("ROWS            :", len(out_rows))
print("FEATURE_COLUMNS :", len(feature_rows[0]) - 1)
print("TARGET          : TARGET_RETURN")
print("OUTPUT          :", OUTPUT)
print("STAGE35_STEP1   : PASS")
