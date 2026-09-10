from pathlib import Path
import csv

INPUT = Path("data/hunter/jpx_hunter_train_matrix_2025.csv")
rows = list(csv.DictReader(INPUT.open("r", encoding="utf-8-sig")))

leak_cols = [c for c in rows[0].keys() if "TARGET_" in c]
periods = [int(r["PERIOD_INDEX"]) for r in rows]

print("========================================")
print("STAGE32 LEAK AUDIT")
print("========================================")
print("ROWS          :", len(rows))
print("LEAK_COLUMNS  :", len(leak_cols))
print("PERIOD_SORTED :", periods == sorted(periods))

if len(leak_cols) == 1 and leak_cols[0] == "TARGET_RETURN" and periods == sorted(periods):
    print("STAGE32_STEP2 : PASS")
else:
    print("STAGE32_STEP2 : FAIL")
    print("FOUND_LEAKS:", leak_cols)
