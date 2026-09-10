from pathlib import Path
import csv

INPUT = Path("data/hunter/jpx_hunter_feature_matrix_2025.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))
cols = rows[0].keys()

missing = 0
numeric_errors = 0

# 数値として扱わない列
text_cols = {
    "WEEK","LEGACY_WEEK","PERIOD_KEY",
    "OBSERVATION_WEEK","OBSERVATION_START","OBSERVATION_END"
}

for r in rows:
    for c in cols:
        v = r[c]

        if v == "":
            missing += 1
            continue

        if c not in text_cols:
            try:
                float(v)
            except ValueError:
                numeric_errors += 1

print("========================================")
print("STAGE31 FEATURE AUDIT")
print("========================================")
print("ROWS           :", len(rows))
print("COLUMNS        :", len(cols))
print("MISSING_VALUES :", missing)
print("NUMERIC_ERRORS :", numeric_errors)

if len(rows) == 38 and missing == 0 and numeric_errors == 0:
    print()
    print("STAGE31_STEP3 : PASS")
else:
    print()
    print("STAGE31_STEP3 : FAIL")
