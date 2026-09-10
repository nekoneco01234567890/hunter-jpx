from pathlib import Path
import csv

FILES = [
    Path("data/n225_raw/N225_MARKET_CONTEXT_2025_01_09.csv"),
    Path("data/n225_raw/N225_1MIN_RAW_2025_01_09.csv"),
]

print("========================================")
print("STAGE27B N225 SOURCE INSPECTION")
print("========================================")

for path in FILES:

    print()
    print("FILE :", path)

    if not path.exists():
        print("STATUS : NOT_FOUND")
        continue

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        reader = csv.reader(f)

        rows = []

        for i, row in enumerate(reader):
            rows.append(row)

            if i >= 5:
                break

    print("STATUS : FOUND")

    if not rows:
        print("ROWS : 0")
        continue

    print("COLUMN_COUNT :", len(rows[0]))

    print()
    print("HEADER:")
    for i, col in enumerate(rows[0]):
        print(f"[{i}] {col}")

    print()
    print("SAMPLE:")
    for row in rows[1:]:
        print(row)

    print()
    print("----------------------------------------")

print()
print("INSPECTION_COMPLETE")
