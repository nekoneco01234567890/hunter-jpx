from pathlib import Path
import csv
import math

INPUT = Path("data/hunter/stage33_predictions.csv")
OUTPUT = Path("data/hunter/stage33_metrics.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

mae = sum(float(r["ABS_ERROR"]) for r in rows) / len(rows)

rmse = math.sqrt(
    sum(
        (float(r["PREDICTED_RETURN"]) - float(r["ACTUAL_RETURN"])) ** 2
        for r in rows
    ) / len(rows)
)

direction_accuracy = (
    sum(int(r["DIRECTION_MATCH"]) for r in rows) / len(rows)
)

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["ROWS", "MAE", "RMSE", "DIRECTION_ACCURACY"]
    )
    writer.writeheader()
    writer.writerow({
        "ROWS": len(rows),
        "MAE": round(mae, 6),
        "RMSE": round(rmse, 6),
        "DIRECTION_ACCURACY": round(direction_accuracy, 4)
    })

print("========================================")
print("STAGE33 METRICS")
print("========================================")
print("ROWS       :", len(rows))
print("MAE        :", round(mae, 6))
print("RMSE       :", round(rmse, 6))
print("DIRECTION  :", round(direction_accuracy * 100, 2), "%")
print("OUTPUT     :", OUTPUT)
print("STAGE33_STEP2 : PASS")
