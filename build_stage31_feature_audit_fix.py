from pathlib import Path
import csv

INPUT = Path("data/hunter/jpx_hunter_feature_matrix_2025.csv")
rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

text_cols = {
    "WEEK","LEGACY_WEEK","PERIOD_KEY",
    "OBSERVATION_WEEK","OBSERVATION_START","OBSERVATION_END",
    "SOURCE_WEEK_IDENTIFIER",
    "N225_DATA_STATUS","STRUCTURE_STATUS",
    "CURRENT_LIMITATION","EXPECTED_CAPABILITY",
    "REPAIR_ACTION","VALIDATION_STATUS"
}

missing = 0
numeric_errors = 0

for r in rows:
    for k, v in r.items():
        if v == "":
            missing += 1
            continue
        if k not in text_cols:
            try:
                float(v)
            except ValueError:
                numeric_errors += 1

print("========================================")
print("STAGE31 FEATURE AUDIT FINAL")
print("========================================")
print("ROWS           :", len(rows))
print("COLUMNS        :", len(rows[0]))
print("MISSING_VALUES :", missing)
print("NUMERIC_ERRORS :", numeric_errors)
print("STAGE31_STEP3B :", "PASS" if missing == 0 and numeric_errors == 0 else "FAIL")
