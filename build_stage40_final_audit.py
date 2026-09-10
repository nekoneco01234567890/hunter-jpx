from pathlib import Path
import csv
import math

FILES = {
    "BASELINE": "data/hunter/stage33_predictions.csv",
    "RIDGE66": "data/hunter/stage36_predictions.csv",
    "RIDGE20": "data/hunter/stage39_predictions.csv",
}

def check(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))

    periods = [int(r["PERIOD_INDEX"]) for r in rows]
    dup = len(periods) - len(set(periods))
    ordered = periods == sorted(periods)

    mae = sum(float(r["ABS_ERROR"]) for r in rows) / len(rows)
    rmse = math.sqrt(sum(
        (float(r["PREDICTED_RETURN"]) - float(r["ACTUAL_RETURN"]))**2
        for r in rows
    ) / len(rows))
    acc = sum(int(r["DIRECTION_MATCH"]) for r in rows) / len(rows)

    return {
        "rows": len(rows),
        "dup": dup,
        "ordered": ordered,
        "mae": mae,
        "rmse": rmse,
        "acc": acc,
    }

results = {k: check(v) for k, v in FILES.items()}

print("========================================")
print("STAGE40 FINAL AUDIT")
print("========================================")

hard_fail = False

for name, r in results.items():
    print(f"\n[{name}]")
    print("ROWS      :", r["rows"])
    print("DUPLICATES:", r["dup"])
    print("ORDERED   :", r["ordered"])
    print("MAE       :", round(r["mae"],6))
    print("RMSE      :", round(r["rmse"],6))
    print("DIR ACC   :", round(r["acc"]*100,2), "%")

    if r["rows"] != 33 or r["dup"] != 0 or not r["ordered"]:
        hard_fail = True

print("\n========================================")
if hard_fail:
    print("STAGE40_FINAL_AUDIT : FAIL")
else:
    print("STAGE40_FINAL_AUDIT : PASS")
