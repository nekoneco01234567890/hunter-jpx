from pathlib import Path
import csv

JPX="data/hunter/jpx_hunter_features_weekly.csv"
N225="data/n225/n225_weekly.csv"
OUT="data/hunter/n225_jpx_hunter_dataset.csv"

def jpx_week_to_key(s):
    # 2025-03-02 → 2025-W09 （月×4週方式）
    y,m,w = map(int, s.split("-"))
    return f"{y}-W{((m-1)*4 + (w-1)):02d}"

jpx={}
for r in csv.DictReader(open(JPX,encoding="utf-8-sig")):
    jpx[jpx_week_to_key(r["WEEK"])] = r

merged=[]; missing=0

for r in csv.DictReader(open(N225,encoding="utf-8-sig")):
    wk=r["WEEK"]
    if wk in jpx:
        x=dict(r)
        x.update(jpx[wk])
        merged.append(x)
    else:
        missing += 1

with open(OUT,"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=merged[0].keys())
    w.writeheader()
    w.writerows(merged)

print("=== STAGE27 STEP2 PASS ===")
print("JPX_ROWS:",len(jpx))
print("N225_ROWS:",len(merged)+missing)
print("MERGED_ROWS:",len(merged))
print("MISSING_WEEKS:",missing)
print("DATASET_COLS:",len(merged[0]))
