import csv
from pathlib import Path

INPUT = Path("data/jpx_replay_feature_n225_context.csv")

total = 0
ok = True

with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        total += 1
        if row["N225_POINT_IN_TIME_STATUS"] != "PASS":
            ok = False
        if row["N225_DATA_STATUS"] != "09:09_OR_EARLIER_ONLY":
            ok = False
        if row["N225_LATEST_ALLOWED_BAR"] != "09:09:00":
            ok = False

print("========================================")
print("PHASE41 PIT BREAK TEST (STREAM MODE)")
print("========================================")
print("TOTAL_ROWS =", total)
print("T01_NORMAL_CONTEXT =", "PASS" if ok else "FAIL")
print("PIT_BREAK_TEST_FINAL =", "PASS" if ok else "FAIL")
