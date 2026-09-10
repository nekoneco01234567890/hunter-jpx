from pathlib import Path
import csv
from statistics import mean

INPUT = Path("data/hunter/jpx_hunter_train_matrix_2025.csv")
OUTPUT = Path("data/hunter/stage33_predictions.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

predictions = []

# 5週目から予測開始（最低5週を学習に使う）
for i in range(5, len(rows)):
    train = rows[:i]
    test = rows[i]

    # ベースライン予測：過去TARGET_RETURN平均
    pred = mean(float(r["TARGET_RETURN"]) for r in train)
    actual = float(test["TARGET_RETURN"])

    predictions.append({
        "PERIOD_INDEX": test["PERIOD_INDEX"],
        "PREDICTED_RETURN": round(pred, 6),
        "ACTUAL_RETURN": round(actual, 6),
        "ABS_ERROR": round(abs(pred - actual), 6),
        "DIRECTION_MATCH": int((pred >= 0) == (actual >= 0))
    })

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=predictions[0].keys())
    writer.writeheader()
    writer.writerows(predictions)

print("========================================")
print("STAGE33 WALK-FORWARD")
print("========================================")
print("TRAIN_PERIODS :", len(rows))
print("PREDICTIONS   :", len(predictions))
print("OUTPUT        :", OUTPUT)
print("STAGE33_STEP1 : PASS")
