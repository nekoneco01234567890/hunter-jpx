from pathlib import Path
import csv
import numpy as np

INPUT = Path("data/hunter/stage35_training_input.csv")
OUTPUT = Path("data/hunter/stage36_predictions.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

feature_cols = [
    c for c in rows[0].keys()
    if c not in ("PERIOD_INDEX", "TARGET_RETURN")
]

predictions = []
RIDGE_ALPHA = 0.1      # 必要ならここだけ変更

for i in range(5, len(rows)):
    train = rows[:i]
    test = rows[i]

    X = np.array([[float(r[c]) for c in feature_cols] for r in train])
    y = np.array([float(r["TARGET_RETURN"]) for r in train])

    X = np.column_stack([np.ones(len(X)), X])

    XtX = X.T @ X
    ridge = RIDGE_ALPHA * np.eye(X.shape[1])
    ridge[0, 0] = 0.0           # 切片は正則化しない

    beta = np.linalg.solve(XtX + ridge, X.T @ y)

    x_test = np.array([1.0] + [float(test[c]) for c in feature_cols])
    pred = float(x_test @ beta)
    actual = float(test["TARGET_RETURN"])

    predictions.append({
        "PERIOD_INDEX": test["PERIOD_INDEX"],
        "PREDICTED_RETURN": round(pred, 6),
        "ACTUAL_RETURN": round(actual, 6),
        "ABS_ERROR": round(abs(pred - actual), 6),
        "DIRECTION_MATCH": int((pred >= 0) == (actual >= 0))
    })

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=predictions[0].keys())
    w.writeheader()
    w.writerows(predictions)

print("========================================")
print("STAGE36 NUMPY RIDGE")
print("========================================")
print("TRAIN_ROWS       :", len(rows))
print("PREDICTIONS      :", len(predictions))
print("FEATURE_COLUMNS  :", len(feature_cols))
print("RIDGE_ALPHA      :", RIDGE_ALPHA)
print("OUTPUT           :", OUTPUT)
print("STAGE36_STEP1    : PASS")
