from pathlib import Path
import csv

INPUT = Path("data/hunter/jpx_hunter_train_dataset_2025.csv")

rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

dup = len(rows) - len(set(r["PERIOD_KEY"] for r in rows))

missing_target = sum(
    not r["TARGET_RETURN"] or
    not r["TARGET_RANGE"] or
    not r["TARGET_DIRECTION"]
    for r in rows
)

bad_status = sum(
    r["TARGET_N225_STATUS"] != "DAY_DATA_AVAILABLE"
    for r in rows
)

print("========================================")
print("STAGE31 DATASET AUDIT")
print("========================================")
print("TRAIN_ROWS      :", len(rows))
print("UNIQUE_PERIODS  :", len(set(r["PERIOD_KEY"] for r in rows)))
print("DUPLICATES      :", dup)
print("MISSING_TARGETS :", missing_target)
print("BAD_STATUS_ROWS :", bad_status)

if len(rows)==38 and dup==0 and missing_target==0 and bad_status==0:
    print()
    print("STAGE31_STEP1 : PASS")
else:
    print()
    print("STAGE31_STEP1 : FAIL")
