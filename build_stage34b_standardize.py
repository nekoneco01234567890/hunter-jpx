from pathlib import Path
import csv
import math

INPUT = Path("data/hunter/stage34_numeric_matrix.csv")
OUTPUT = Path("data/hunter/stage34_standardized_matrix.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

id_col = "PERIOD_INDEX"
feature_cols = [c for c in rows[0] if c != id_col]

means, stds = {}, {}

for c in feature_cols:
    vals = [float(r[c]) for r in rows]
    means[c] = sum(vals) / len(vals)
    var = sum((v - means[c])**2 for v in vals) / len(vals)
    stds[c] = math.sqrt(var) if var > 0 else 1.0

out = []
for r in rows:
    row = {id_col: r[id_col]}
    for c in feature_cols:
        row[c] = round((float(r[c]) - means[c]) / stds[c], 6)
    out.append(row)

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=out[0].keys())
    w.writeheader()
    w.writerows(out)

print("STAGE34B_STEP1 : PASS")
print("ROWS :", len(out))
print("FEATURE_COLUMNS :", len(feature_cols))
print("OUTPUT :", OUTPUT)
