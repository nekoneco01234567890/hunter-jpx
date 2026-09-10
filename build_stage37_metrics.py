from pathlib import Path
import csv
import math

INPUT = Path("data/hunter/stage36_predictions.csv")
OUTPUT = Path("data/hunter/stage37_metrics.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

mae = sum(float(r["ABS_ERROR"]) for r in rows) / len(rows)

rmse = math.sqrt(
    sum(
        (float(r["PREDICTED_RETURN"]) - float(r["ACTUAL_RETURN"])) ** 2
        for r in rows
    ) / len(rows)
)

direction = sum(int(r["DIRECTION_MATCH"]) for r in rows) / len(rows)

pred_mean = sum(float(r["PREDICTED_RETURN"]) for r in rows) / len(rows)
actual_mean = sum(float(r["ACTUAL_RETURN"]) for r in rows) / len(rows)

worst = max(rows, key=lambda r: float(r["ABS_ERROR"]))

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(
        f,
        fieldnames=[
            "ROWS",
            "MAE",
            "RMSE",
            "DIRECTION_ACCURACY",
            "PREDICTED_MEAN",
            "ACTUAL_MEAN",
            "WORST_PERIOD",
            "WORST_ABS_ERROR"
        ]
    )
    w.writeheader()
    w.writerow({
        "ROWS": len(rows),
        "MAE": round(mae, 6),
        "RMSE": round(rmse, 6),
        "DIRECTION_ACCURACY": round(direction, 4),
        "PREDICTED_MEAN": round(pred_mean, 6),
        "ACTUAL_MEAN": round(actual_mean, 6),
        "WORST_PERIOD": worst["PERIOD_INDEX"],
        "WORST_ABS_ERROR": round(float(worst["ABS_ERROR"]), 6)
    })

print("========================================")
print("STAGE37 RIDGE METRICS")
print("========================================")
print("ROWS       :", len(rows))
print("MAE        :", round(mae, 6))
print("RMSE       :", round(rmse, 6))
print("DIRECTION  :", round(direction * 100, 2), "%")
print("WORST_WEEK :", worst["PERIOD_INDEX"])
print("OUTPUT     :", OUTPUT)
print("STAGE37_STEP1 : PASS")
