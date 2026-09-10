from pathlib import Path
import csv

INPUT = Path("data/hunter/jpx_hunter_target_dataset_2025.csv")
OUTPUT = Path("data/hunter/jpx_hunter_train_dataset_2025.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

train = []

for r in rows:
    if r["TARGET_N225_STATUS"] != "DAY_DATA_AVAILABLE":
        continue

    close = float(r["TARGET_N225_DAY_CLOSE"])
    low = float(r["TARGET_N225_DAY_LOW"])
    high = float(r["TARGET_N225_DAY_HIGH"])

    r["TARGET_RETURN"] = round((close - low) / low, 6)
    r["TARGET_RANGE"] = round((high - low) / low, 6)
    r["TARGET_DIRECTION"] = "UP" if close >= low else "DOWN"

    train.append(r)

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=train[0].keys())
    w.writeheader()
    w.writerows(train)

print("========================================")
print("STAGE30 LABEL DATASET")
print("========================================")
print("INPUT_ROWS :", len(rows))
print("TRAIN_ROWS :", len(train))
print("OUTPUT :", OUTPUT)
print("STAGE30_STEP1 : PASS")
