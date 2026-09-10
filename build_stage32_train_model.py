from pathlib import Path
import csv

INPUT = Path("data/hunter/jpx_hunter_train_dataset_2025.csv")
OUTPUT = Path("data/hunter/jpx_hunter_train_matrix_2025.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

# 学習に使わない列（ID・日時・ターゲット）
exclude = {
    "WEEK","LEGACY_WEEK","PERIOD_KEY","SOURCE_WEEK_IDENTIFIER",
    "OBSERVATION_WEEK","OBSERVATION_START","OBSERVATION_END",
    "TARGET_PERIOD_INDEX","TARGET_PERIOD_KEY","TARGET_OBSERVATION_WEEK",
    "TARGET_START","TARGET_END",
    "TARGET_N225_DAY_CLOSE","TARGET_N225_DAY_HIGH",
    "TARGET_N225_DAY_LOW","TARGET_N225_DAY_VOLUME",
    "TARGET_N225_STATUS","TARGET_RETURN",
    "TARGET_RANGE","TARGET_DIRECTION"
}

feature_cols = [c for c in rows[0].keys() if c not in exclude]

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["PERIOD_INDEX"] + feature_cols + ["TARGET_RETURN"])
    for r in rows:
        writer.writerow(
            [r["PERIOD_INDEX"]]
            + [r[c] for c in feature_cols]
            + [r["TARGET_RETURN"]]
        )

print("========================================")
print("STAGE32 TRAIN MATRIX")
print("========================================")
print("ROWS            :", len(rows))
print("FEATURE_COLUMNS :", len(feature_cols))
print("TARGET          : TARGET_RETURN")
print("OUTPUT          :", OUTPUT)
print("STAGE32_STEP1   : PASS")
