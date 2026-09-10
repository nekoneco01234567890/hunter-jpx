from pathlib import Path
import csv

INPUT = Path("data/hunter/jpx_hunter_temporal_merged_2025.csv")
OUTPUT = Path("data/hunter/jpx_hunter_target_dataset_2025.csv")

with INPUT.open("r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

rows.sort(key=lambda r: int(r["PERIOD_INDEX"]))

dataset = []

for i in range(len(rows)-1):

    current = dict(rows[i])
    target = rows[i+1]

    current["TARGET_PERIOD_INDEX"] = target["PERIOD_INDEX"]
    current["TARGET_PERIOD_KEY"] = target["PERIOD_KEY"]
    current["TARGET_OBSERVATION_WEEK"] = target["OBSERVATION_WEEK"]
    current["TARGET_START"] = target["OBSERVATION_START"]
    current["TARGET_END"] = target["OBSERVATION_END"]

    current["TARGET_N225_DAY_CLOSE"] = target["N225_DAY_CLOSE"]
    current["TARGET_N225_DAY_HIGH"] = target["N225_DAY_HIGH"]
    current["TARGET_N225_DAY_LOW"] = target["N225_DAY_LOW"]
    current["TARGET_N225_DAY_VOLUME"] = target["N225_DAY_VOLUME"]
    current["TARGET_N225_STATUS"] = target["N225_DATA_STATUS"]

    dataset.append(current)

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
    writer.writeheader()
    writer.writerows(dataset)

print("========================================")
print("STAGE29 TARGET DATASET")
print("========================================")
print("INPUT_PERIODS  :", len(rows))
print("OUTPUT_ROWS    :", len(dataset))
print("FIRST_TARGET   :", dataset[0]["TARGET_OBSERVATION_WEEK"])
print("LAST_FEATURE   :", dataset[-1]["OBSERVATION_WEEK"])
print("LAST_TARGET    :", dataset[-1]["TARGET_OBSERVATION_WEEK"])
print("STAGE29_STEP1  : PASS")
