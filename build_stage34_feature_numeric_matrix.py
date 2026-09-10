from pathlib import Path
import csv

INPUT = Path("data/hunter/jpx_hunter_train_matrix_2025.csv")
OUTPUT = Path("data/hunter/stage34_numeric_matrix.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

# 数値化しない列（ID・メタデータ）
text_cols = {
    "PERIOD_INDEX",
    "WEEK","LEGACY_WEEK","PERIOD_KEY","SOURCE_WEEK_IDENTIFIER",
    "OBSERVATION_WEEK","OBSERVATION_START","OBSERVATION_END",
    "N225_DATA_STATUS","STRUCTURE_STATUS",
    "CURRENT_LIMITATION","EXPECTED_CAPABILITY",
    "REPAIR_ACTION","VALIDATION_STATUS"
}

numeric_cols = [c for c in rows[0].keys() if c not in text_cols]

out_rows = []
for r in rows:
    out = {"PERIOD_INDEX": int(r["PERIOD_INDEX"])}
    for c in numeric_cols:
        out[c] = float(r[c])
    out_rows.append(out)

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=out_rows[0].keys())
    writer.writeheader()
    writer.writerows(out_rows)

print("========================================")
print("STAGE34A NUMERIC MATRIX")
print("========================================")
print("ROWS            :", len(out_rows))
print("NUMERIC_COLUMNS :", len(numeric_cols))
print("TEXT_COLUMNS    :", len(text_cols))
print("OUTPUT          :", OUTPUT)
print("STAGE34A_STEP1_FIX : PASS")
