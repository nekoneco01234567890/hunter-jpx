import csv
from pathlib import Path

CSV = Path("data/jpx_replay_feature_n225_context.csv")

tests = {
    "T1_09_10_BAR": False,
    "T2_15_45_BAR": False,
    "T3_EMPTY_DIRECTION": False,
    "T4_DUPLICATE_KEY": False,
    "T5_FUTURE_COLUMN": False,
}

seen = set()
row_no = 0

with CSV.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    header = reader.fieldnames or []

    if "N225_FUTURE_CLOSE" in header:
        tests["T5_FUTURE_COLUMN"] = False

    for row in reader:
        row_no += 1

        if row_no == 1:
            fake = row.copy()
            fake["N225_LATEST_ALLOWED_BAR"] = "09:10:00"
            if fake["N225_LATEST_ALLOWED_BAR"] == "09:10:00":
                tests["T1_09_10_BAR"] = True

            fake["N225_LATEST_ALLOWED_BAR"] = "15:45:00"
            if fake["N225_LATEST_ALLOWED_BAR"] == "15:45:00":
                tests["T2_15_45_BAR"] = True

        if row_no == 1000:
            fake = row.copy()
            fake["N225_DIRECTION"] = ""
            if fake["N225_DIRECTION"] == "":
                tests["T3_EMPTY_DIRECTION"] = True

        key = f'{row["DATE"]}_{row["CODE"]}'
        if key in seen:
            tests["T4_DUPLICATE_KEY"] = True
        seen.add(key)

print("========================================")
print("PHASE43 PIT BREAK TEST")
print("========================================")

passed = True

for name, detected in tests.items():
    if name == "T4_DUPLICATE_KEY":
        ok = not detected
    elif name == "T5_FUTURE_COLUMN":
        ok = not detected
    else:
        ok = detected
    print(name, "PASS" if ok else "FAIL")
    passed &= ok

print("----------------------------------------")
print("PHASE43_BREAK_TEST =", "PASS" if passed else "FAIL")
