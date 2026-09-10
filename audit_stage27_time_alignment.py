from pathlib import Path
import csv
from datetime import datetime

JPX = Path("data/hunter/jpx_hunter_features_weekly.csv")
N225 = Path("data/n225/n225_weekly.csv")

def read_csv(path):
    with path.open("r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

jpx_rows = read_csv(JPX)
n225_rows = read_csv(N225)

print("========================================")
print("HUNTER STAGE27 TIME ALIGNMENT AUDIT")
print("========================================")

print("JPX_ROWS_RAW  :", len(jpx_rows))
print("N225_ROWS_RAW :", len(n225_rows))

# -----------------------------
# JPX WEEK の実体を確認
# -----------------------------
jpx_dates = []
jpx_week_keys = {}

for r in jpx_rows:
    raw = r["WEEK"]

    try:
        d = datetime.fromisoformat(raw)
        iso_week = d.strftime("%Y-W%U")
        iso_year_week = d.strftime("%G-W%V")
    except Exception:
        iso_week = "INVALID"
        iso_year_week = "INVALID"

    jpx_dates.append(raw)

    if iso_week not in jpx_week_keys:
        jpx_week_keys[iso_week] = []
    jpx_week_keys[iso_week].append(raw)

# -----------------------------
# N225 WEEK
# -----------------------------
n225_keys = [r["WEEK"] for r in n225_rows]

print()
print("JPX_DATE_MIN  :", min(jpx_dates))
print("JPX_DATE_MAX  :", max(jpx_dates))

print()
print("JPX_UNIQUE_RAW :", len(set(jpx_dates)))
print("JPX_UNIQUE_W00 :", len(jpx_week_keys))
print("N225_UNIQUE    :", len(set(n225_keys)))

print()
print("=== JPX -> N225 WEEK MAPPING ===")

for key in sorted(jpx_week_keys):
    vals = jpx_week_keys[key]
    exists = key in n225_keys

    print(
        key,
        "=>",
        "MATCH" if exists else "NO_MATCH",
        "SOURCE_DATES=",
        ",".join(vals)
    )

# -----------------------------
# 重複・欠落監査
# -----------------------------
duplicate_jpx_keys = {
    k: v for k, v in jpx_week_keys.items()
    if len(v) > 1
}

missing_n225 = [
    k for k in n225_keys
    if k not in jpx_week_keys
]

print()
print("========================================")
print("ALIGNMENT SUMMARY")
print("========================================")
print("JPX_UNIQUE_WEEK_KEYS :", len(jpx_week_keys))
print("JPX_DUPLICATE_KEYS   :", len(duplicate_jpx_keys))
print("N225_MISSING_JPX     :", len(missing_n225))

print()
print("N225 KEYS WITHOUT JPX:")
for x in missing_n225:
    print(x)

print()
print("=== DIAGNOSIS ===")

if len(jpx_rows) == 52 and len(jpx_week_keys) < 52:
    print("STRUCTURAL_ISSUE : JPX WEEK values are not unique weekly keys")
    print("LIKELY_CAUSE     : WEEK field represents a date/source identifier")
    print("NEXT_ACTION      : RECONSTRUCT TEMPORAL KEY BEFORE MERGE")
elif len(jpx_week_keys) == len(n225_keys):
    print("ALIGNMENT        : READY")
else:
    print("ALIGNMENT        : PARTIAL")
    print("DO_NOT_FORCE_MERGE = TRUE")

