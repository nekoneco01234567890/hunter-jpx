from pathlib import Path
import csv, math

FILES = {
    "BASELINE": Path("data/hunter/stage33_predictions.csv"),
    "RIDGE66": Path("data/hunter/stage36_predictions.csv"),
    "RIDGE20": Path("data/hunter/stage39_predictions.csv"),
}

def metrics(path):
    rows = list(csv.DictReader(path.open("r", encoding="utf-8-sig")))
    mae = sum(float(r["ABS_ERROR"]) for r in rows) / len(rows)
    rmse = math.sqrt(sum(
        (float(r["PREDICTED_RETURN"]) - float(r["ACTUAL_RETURN"]))**2
        for r in rows
    ) / len(rows))
    acc = sum(int(r["DIRECTION_MATCH"]) for r in rows) / len(rows)
    return len(rows), mae, rmse, acc

print("========================================")
print("STAGE40 FINAL COMPARISON")
print("========================================")

for name, path in FILES.items():
    rows, mae, rmse, acc = metrics(path)
    print(f"{name:8} ROWS={rows} MAE={mae:.6f} RMSE={rmse:.6f} DIR={acc*100:.2f}%")

print("STAGE40_STEP1 : PASS")
