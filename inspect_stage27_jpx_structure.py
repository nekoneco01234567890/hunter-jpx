from pathlib import Path
import csv
from collections import Counter, defaultdict

SRC = Path("data/hunter/jpx_hunter_features_weekly.csv")

with SRC.open("r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print("========================================")
print("STAGE27 JPX STRUCTURE INSPECTION")
print("========================================")

print("ROWS :", len(rows))
print("COLS :", len(rows[0]))

# WEEK
weeks = [r["WEEK"] for r in rows]

print()
print("=== WEEK VALUES ===")
for x in weeks:
    print(x)

print()
print("=== PREFIX / MONTH STRUCTURE ===")

months = Counter()
for x in weeks:
    parts = x.split("-")
    if len(parts) == 3:
        months[f"{parts[0]}-{parts[1]}"] += 1

for k, v in sorted(months.items()):
    print(k, "ROWS=", v)

print()
print("=== FIRST ROW KEYS ===")
for k in rows[0].keys():
    print(k)

print()
print("=== WEEK DUPLICATE DISTRIBUTION ===")

groups = defaultdict(list)

from datetime import datetime

for r in rows:
    d = datetime.fromisoformat(r["WEEK"])
    key = d.strftime("%Y-W%U")
    groups[key].append(r["WEEK"])

for key, vals in sorted(groups.items()):
    print(key, "COUNT=", len(vals), "DATES=", ",".join(vals))

print()
print("=== VALUE TYPE CHECK ===")

numeric_errors = []

for r in rows:
    for k, v in r.items():
        if k == "WEEK":
            continue
        try:
            float(v)
        except Exception:
            numeric_errors.append((r["WEEK"], k, v))

print("NUMERIC_ERRORS :", len(numeric_errors))

if numeric_errors:
    for x in numeric_errors[:20]:
        print(x)

print()
print("========================================")
print("DIAGNOSIS")
print("========================================")

print("JPX_ROWS             :", len(rows))
print("JPX_UNIQUE_DATES     :", len(set(weeks)))
print("MONTH_GROUPS         :", len(months))
print("WEEK_GROUPS          :", len(groups))
print("WEEK_COLLISION       :", len(weeks) - len(groups))

if len(weeks) != len(groups):
    print("STATUS               : TEMPORAL_KEY_COLLISION")
    print("ACTION               : DO NOT MERGE YET")
else:
    print("STATUS               : NO_COLLISION")

