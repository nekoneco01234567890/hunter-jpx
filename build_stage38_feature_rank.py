from pathlib import Path
import csv
import numpy as np

INPUT = Path("data/hunter/stage35_training_input.csv")
OUTPUT = Path("data/hunter/stage38_feature_importance.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

feature_cols = [
    c for c in rows[0]
    if c not in ("PERIOD_INDEX", "TARGET_RETURN")
]

X = np.array([[float(r[c]) for c in feature_cols] for r in rows])
y = np.array([float(r["TARGET_RETURN"]) for r in rows])

# 相関係数の絶対値を重要度にする
scores = []
for i, col in enumerate(feature_cols):
    corr = np.corrcoef(X[:, i], y)[0, 1]
    if np.isnan(corr):
        corr = 0.0
    scores.append({
        "FEATURE": col,
        "IMPORTANCE": abs(corr),
        "CORRELATION": corr
    })

scores.sort(key=lambda x: x["IMPORTANCE"], reverse=True)

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=scores[0].keys())
    w.writeheader()
    w.writerows(scores)

print("========================================")
print("STAGE38 FEATURE RANK")
print("========================================")
print("ROWS             :", len(rows))
print("FEATURES         :", len(feature_cols))
print("TOP10")
for s in scores[:10]:
    print(s["FEATURE"], round(s["CORRELATION"],4))
print("OUTPUT :", OUTPUT)
print("STAGE38A_STEP1 : PASS")
