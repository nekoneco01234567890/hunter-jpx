from pathlib import Path
import csv

INPUT = Path("data/hunter/jpx_hunter_train_dataset_2025.csv")
OUTPUT = Path("data/hunter/jpx_hunter_feature_matrix_2025.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

exclude = {
    "TARGET_PERIOD_INDEX","TARGET_PERIOD_KEY","TARGET_OBSERVATION_WEEK",
    "TARGET_START","TARGET_END",
    "TARGET_N225_DAY_CLOSE","TARGET_N225_DAY_HIGH",
    "TARGET_N225_DAY_LOW","TARGET_N225_DAY_VOLUME",
    "TARGET_N225_STATUS",
    "TARGET_RETURN","TARGET_RANGE","TARGET_DIRECTION"
}

feature_cols = [c for c in rows[0].keys() if c not in exclude]

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=feature_cols)
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in feature_cols})

print("========================================")
print("STAGE31 FEATURE MATRIX")
print("========================================")
print("ROWS :", len(rows))
print("FEATURE_COLUMNS :", len(feature_cols))
print("OUTPUT :", OUTPUT)
print("STAGE31_STEP2 : PASS")
