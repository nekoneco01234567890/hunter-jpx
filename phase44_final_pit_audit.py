import csv
from pathlib import Path

CSV = Path("data/jpx_replay_feature_n225_context.csv")

total = 0
pit_fail = 0
status_fail = 0
time_fail = 0
dup = 0
keys = set()

with CSV.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        total += 1

        k = f'{row["DATE"]}_{row["CODE"]}'
        if k in keys:
            dup += 1
        keys.add(k)

        if row["N225_POINT_IN_TIME_STATUS"] != "PASS":
            pit_fail += 1

        if row["N225_DATA_STATUS"] != "09:09_OR_EARLIER_ONLY":
            status_fail += 1

        if row["N225_LATEST_ALLOWED_BAR"] != "09:09:00":
            time_fail += 1

audit = (
    total == 705485 and
    dup == 0 and
    pit_fail == 0 and
    status_fail == 0 and
    time_fail == 0
)

print("========================================")
print("PHASE44 FINAL PIT AUDIT")
print("========================================")
print("TOTAL_ROWS =", total)
print("DUPLICATE_KEYS =", dup)
print("PIT_FAIL_ROWS =", pit_fail)
print("STATUS_FAIL_ROWS =", status_fail)
print("TIME_FAIL_ROWS =", time_fail)
print("----------------------------------------")
print("PHASE44_FINAL_PIT_AUDIT =", "PASS" if audit else "FAIL")
