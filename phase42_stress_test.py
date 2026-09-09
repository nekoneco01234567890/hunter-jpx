import csv
from pathlib import Path

CSV = Path("data/jpx_replay_feature_n225_context.csv")

total = 0
dup = 0
missing = 0
keys = set()

with CSV.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        total += 1

        key = f'{row["DATE"]}_{row["CODE"]}'
        if key in keys:
            dup += 1
        else:
            keys.add(key)

        for col in (
            "N225_DIRECTION",
            "N225_PERSISTENCE",
            "N225_POINT_IN_TIME_STATUS",
            "N225_DATA_STATUS",
        ):
            if row[col] == "":
                missing += 1

print("========================================")
print("PHASE42 STRESS TEST")
print("========================================")
print("TOTAL_ROWS =", total)
print("DUPLICATE_KEYS =", dup)
print("MISSING_REQUIRED_FIELDS =", missing)

ok = (
    total == 705485 and
    dup == 0 and
    missing == 0
)

print("----------------------------------------")
print("PHASE42_STRESS_TEST =", "PASS" if ok else "FAIL")
