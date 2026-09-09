from pathlib import Path
import csv
from collections import defaultdict

INPUT = Path("data/jpx_weekly_investor/jpx_weekly_investor_flow_v3_raw.csv")
OUTDIR = Path("data/hunter")
OUTDIR.mkdir(parents=True, exist_ok=True)

OUTPUT = OUTDIR / "jpx_hunter_features_weekly.csv"

CORE = ["海外投資家","個人","法人","金融機関","信託銀行","投資信託"]

def num(v):
    if v in ("", None):
        return 0.0
    return float(str(v).replace(",", ""))

rows = []
with INPUT.open("r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for r in reader:
        r["AMOUNT"] = num(r["AMOUNT"])
        r["RATIO"] = num(r["RATIO"])
        rows.append(r)

weeks = defaultdict(list)
for r in rows:
    weeks[r["FILE_IDENTIFIER_DATE"]].append(r)

features = []

for week, recs in sorted(weeks.items()):
    idx = {(r["PERIOD_TYPE"], r["CATEGORY"], r["SIDE"]): r for r in recs}
    item = {"WEEK": week}

    for cat in CORE:
        pb = idx.get(("PREVIOUS", cat, "BUY"), {}).get("AMOUNT", 0)
        ps = idx.get(("PREVIOUS", cat, "SELL"), {}).get("AMOUNT", 0)
        cb = idx.get(("CURRENT", cat, "BUY"), {}).get("AMOUNT", 0)
        cs = idx.get(("CURRENT", cat, "SELL"), {}).get("AMOUNT", 0)

        item[f"{cat}_PREV_NET"] = pb - ps
        item[f"{cat}_CURR_NET"] = cb - cs
        item[f"{cat}_WOW_NET"] = (cb - cs) - (pb - ps)

        item[f"{cat}_BUY_RATIO"] = idx.get(("CURRENT", cat, "BUY"), {}).get("RATIO", 0)
        item[f"{cat}_SELL_RATIO"] = idx.get(("CURRENT", cat, "SELL"), {}).get("RATIO", 0)

    features.append(item)

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=features[0].keys())
    writer.writeheader()
    writer.writerows(features)

print("=== STAGE26A STEP2 PASS ===")
print("FEATURE_ROWS :", len(features))
print("FEATURE_COLUMNS :", len(features[0]))

# ===== Stage26A STEP3 : Audit =====

AUDIT_OUT = OUTDIR / "jpx_hunter_stage26_audit.csv"
SUMMARY_OUT = OUTDIR / "jpx_hunter_stage26_summary.csv"

audit_rows = []
missing_count = 0

for f in features:
    row = {"WEEK": f["WEEK"]}
    ok = True

    for k, v in f.items():
        if k == "WEEK":
            continue
        if v is None:
            ok = False
            missing_count += 1

    row["STATUS"] = "PASS" if ok else "FAIL"
    audit_rows.append(row)

with AUDIT_OUT.open("w", newline="", encoding="utf-8-sig") as fp:
    writer = csv.DictWriter(fp, fieldnames=audit_rows[0].keys())
    writer.writeheader()
    writer.writerows(audit_rows)

summary = [{
    "INPUT_ROWS": len(rows),
    "FEATURE_ROWS": len(features),
    "FEATURE_COLUMNS": len(features[0]),
    "AUDIT_ROWS": len(audit_rows),
    "MISSING_VALUES": missing_count,
    "DUPLICATES": len(features) - len({x["WEEK"] for x in features})
}]

with SUMMARY_OUT.open("w", newline="", encoding="utf-8-sig") as fp:
    writer = csv.DictWriter(fp, fieldnames=summary[0].keys())
    writer.writeheader()
    writer.writerows(summary)

print("=== STAGE26A STEP3 PASS ===")
print("AUDIT_ROWS :", len(audit_rows))
print("MISSING_VALUES :", missing_count)


# ===== Stage26A STEP4 : Deep Audit =====

EXPECTED_CORE = ["海外投資家","個人","法人","金融機関","信託銀行","投資信託"]

category_errors = 0

for f in features:
    for cat in EXPECTED_CORE:
        required = [
            f"{cat}_PREV_NET",
            f"{cat}_CURR_NET",
            f"{cat}_WOW_NET",
            f"{cat}_BUY_RATIO",
            f"{cat}_SELL_RATIO",
        ]
        for key in required:
            if key not in f:
                category_errors += 1

duplicate_weeks = len(features) - len({x["WEEK"] for x in features})

audit_pass = (
    len(features) == 52 and
    missing_count == 0 and
    duplicate_weeks == 0 and
    category_errors == 0
)

print("========================================")
print("HUNTER STAGE26A FINAL AUDIT")
print("========================================")
print("FEATURE_ROWS     :", len(features))
print("FEATURE_COLUMNS  :", len(features[0]))
print("CATEGORY_ERRORS  :", category_errors)
print("DUPLICATE_WEEKS  :", duplicate_weeks)
print("MISSING_VALUES   :", missing_count)
print("AUDIT            :", "PASS" if audit_pass else "FAIL")


# ===== Stage26B STEP1 : Rolling Features =====

ROLLING_CATS = ["海外投資家","個人","法人","金融機関","信託銀行","投資信託"]

# features は WEEK順なのでそのままローリング計算できる
for cat in ROLLING_CATS:

    history = []

    for row in features:
        history.append(row[f"{cat}_CURR_NET"])

        row[f"{cat}_ROLL4_NET"] = sum(history[-4:])
        row[f"{cat}_ROLL8_NET"] = sum(history[-8:])
        row[f"{cat}_ROLL12_NET"] = sum(history[-12:])

        row[f"{cat}_MOM4"] = (
            row[f"{cat}_CURR_NET"] -
            (history[-5] if len(history) >= 5 else 0)
        )

# CSVを書き直す（列追加後）
with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=features[0].keys())
    writer.writeheader()
    writer.writerows(features)

print("=== STAGE26B STEP1 PASS ===")
print("FEATURE_ROWS :", len(features))
print("FEATURE_COLUMNS :", len(features[0]))

