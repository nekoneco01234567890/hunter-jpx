from pathlib import Path
import csv

JPX_FILE = Path(
    "data/hunter/jpx_hunter_features_weekly.csv"
)

TEMPORAL_FILE = Path(
    "data/hunter/jpx_temporal_master_2025.csv"
)

N225_FILE = Path(
    "data/hunter/n225_jpx_period_2025.csv"
)

OUT_FILE = Path(
    "data/hunter/jpx_hunter_temporal_merged_2025.csv"
)

AUDIT_FILE = Path(
    "data/hunter/jpx_hunter_temporal_merge_audit.csv"
)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(csv.DictReader(f))


# ============================================================
# LOAD
# ============================================================

jpx = read_csv(JPX_FILE)
temporal = read_csv(TEMPORAL_FILE)
n225 = read_csv(N225_FILE)

print("========================================")
print("STAGE27C TEMPORAL MERGE")
print("========================================")

print("JPX_FEATURE_ROWS :", len(jpx))
print("TEMPORAL_ROWS    :", len(temporal))
print("N225_PERIOD_ROWS  :", len(n225))


# ============================================================
# BASIC VALIDATION
# ============================================================

if len(jpx) != 52:
    raise SystemExit(
        f"FAIL: JPX feature rows != 52: {len(jpx)}"
    )

if len(temporal) != 52:
    raise SystemExit(
        f"FAIL: temporal rows != 52: {len(temporal)}"
    )

if len(n225) != 52:
    raise SystemExit(
        f"FAIL: N225 period rows != 52: {len(n225)}"
    )


# ============================================================
# SORT BY PERIOD INDEX
# ============================================================

def period_index(row):
    return int(row["PERIOD_INDEX"])


temporal = sorted(
    temporal,
    key=period_index
)

n225 = sorted(
    n225,
    key=period_index
)


# ============================================================
# PERIOD INDEX INTEGRITY
# ============================================================

expected_indexes = list(range(1, 53))

temporal_indexes = [
    int(r["PERIOD_INDEX"])
    for r in temporal
]

n225_indexes = [
    int(r["PERIOD_INDEX"])
    for r in n225
]

if temporal_indexes != expected_indexes:
    raise SystemExit(
        "FAIL: temporal PERIOD_INDEX is not exactly 1..52"
    )

if n225_indexes != expected_indexes:
    raise SystemExit(
        "FAIL: N225 PERIOD_INDEX is not exactly 1..52"
    )


# ============================================================
# JPX FEATURE ORDER
#
# IMPORTANT:
# WEEK is NOT a temporal key.
# It is a source/file identifier.
#
# Therefore:
#   JPX feature row order
#       ↕
#   TEMPORAL PERIOD_INDEX
#
# is validated structurally rather than by WEEK text.
# ============================================================

jpx = list(jpx)

if len(jpx) != 52:
    raise SystemExit("FAIL: JPX feature count changed")


# ============================================================
# BUILD INDEXES
# ============================================================

temporal_by_index = {
    int(r["PERIOD_INDEX"]): r
    for r in temporal
}

n225_by_index = {
    int(r["PERIOD_INDEX"]): r
    for r in n225
}


# ============================================================
# MERGE
# ============================================================

merged = []
audit = []

missing_n225 = 0
available_n225 = 0
chronology_errors = 0
period_alignment_errors = 0


for position, feature in enumerate(jpx, start=1):

    t = temporal_by_index.get(position)

    if t is None:
        raise SystemExit(
            f"FAIL: missing temporal PERIOD_INDEX: {position}"
        )

    n = n225_by_index.get(position)

    # --------------------------------------------------------
    # Verify temporal identity
    # --------------------------------------------------------

    if t["PERIOD_INDEX"] != str(position):
        period_alignment_errors += 1

    # --------------------------------------------------------
    # Verify actual chronology
    # --------------------------------------------------------

    start = t["OBSERVATION_START"]
    end = t["OBSERVATION_END"]

    if start > end:
        chronology_errors += 1

    # --------------------------------------------------------
    # N225 status
    # --------------------------------------------------------

    if n is None:

        missing_n225 += 1
        n225_status = "NO_PERIOD_RECORD"

    elif n["DATA_STATUS"] == "DAY_DATA_AVAILABLE":

        available_n225 += 1
        n225_status = "AVAILABLE"

    else:

        missing_n225 += 1
        n225_status = "NO_DAY_DATA"

    # --------------------------------------------------------
    # CREATE ROW
    # --------------------------------------------------------

    row = dict(feature)

    # Original WEEK is preserved as source identifier.
    row["SOURCE_WEEK_IDENTIFIER"] = feature["WEEK"]

    # Real temporal identity.
    row["PERIOD_INDEX"] = t["PERIOD_INDEX"]
    row["PERIOD_KEY"] = t["PERIOD_KEY"]
    row["OBSERVATION_WEEK"] = t["OBSERVATION_WEEK"]
    row["OBSERVATION_START"] = start
    row["OBSERVATION_END"] = end

    row["N225_DATA_STATUS"] = (
        n["DATA_STATUS"]
        if n is not None
        else "NO_PERIOD_RECORD"
    )

    # --------------------------------------------------------
    # N225 DATA
    # --------------------------------------------------------

    if n is not None:

        for key, value in n.items():

            if key in (
                "PERIOD_INDEX",
                "OBSERVATION_WEEK",
                "OBSERVATION_START",
                "OBSERVATION_END",
                "PERIOD_KEY",
                "DATA_STATUS",
            ):
                continue

            row[key] = value

    else:

        for key in (
            "N225_DAY_BAR_COUNT",
            "N225_DAY_OPEN",
            "N225_DAY_HIGH",
            "N225_DAY_LOW",
            "N225_DAY_CLOSE",
            "N225_DAY_VOLUME",
            "N225_NIGHT_BAR_COUNT",
            "N225_NIGHT_OPEN",
            "N225_NIGHT_HIGH",
            "N225_NIGHT_LOW",
            "N225_NIGHT_CLOSE",
            "N225_NIGHT_VOLUME",
        ):
            row[key] = ""

    merged.append(row)

    audit.append(
        {
            "PERIOD_INDEX":
                t["PERIOD_INDEX"],
            "SOURCE_WEEK_IDENTIFIER":
                feature["WEEK"],
            "OBSERVATION_WEEK":
                t["OBSERVATION_WEEK"],
            "PERIOD_KEY":
                t["PERIOD_KEY"],
            "OBSERVATION_START":
                start,
            "OBSERVATION_END":
                end,
            "N225_STATUS":
                n225_status,
            "N225_DAY_BARS":
                n["N225_DAY_BAR_COUNT"]
                if n is not None else "",
            "N225_NIGHT_BARS":
                n["N225_NIGHT_BAR_COUNT"]
                if n is not None else "",
        }
    )


# ============================================================
# FINAL STRUCTURAL VALIDATION
# ============================================================

if len(merged) != 52:
    raise SystemExit(
        f"FAIL: merged rows != 52: {len(merged)}"
    )


merged_period_indexes = [
    int(r["PERIOD_INDEX"])
    for r in merged
]

if merged_period_indexes != expected_indexes:
    raise SystemExit(
        "FAIL: merged PERIOD_INDEX is not exactly 1..52"
    )


merged_keys = [
    r["PERIOD_KEY"]
    for r in merged
]

unique_keys = len(set(merged_keys))

duplicate_keys = (
    len(merged_keys) - unique_keys
)

if duplicate_keys != 0:
    raise SystemExit(
        f"FAIL: duplicate PERIOD_KEY: {duplicate_keys}"
    )


# ============================================================
# CHRONOLOGY VALIDATION
# ============================================================

for i in range(1, len(merged)):

    previous = merged[
        i - 1
    ]["OBSERVATION_START"]

    current = merged[
        i
    ]["OBSERVATION_START"]

    if current <= previous:
        chronology_errors += 1


if chronology_errors != 0:
    raise SystemExit(
        f"FAIL: chronology errors: {chronology_errors}"
    )


# ============================================================
# WRITE MERGED DATASET
# ============================================================

fields = list(merged[0].keys())

with OUT_FILE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(merged)


# ============================================================
# WRITE AUDIT
# ============================================================

audit_fields = list(audit[0].keys())

with AUDIT_FILE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=audit_fields
    )

    writer.writeheader()
    writer.writerows(audit)


# ============================================================
# ADAPTIVE CONTROL
# ============================================================

if missing_n225 == 0:

    structure_status = "VALIDATED"

    current_limitation = "NONE"

    expected_capability = (
        "JPX_WEEKLY_FLOW_PLUS_N225_PERIOD_CONTEXT"
    )

    repair_action = "NONE"

    validation_status = "PASS"

else:

    structure_status = "CONDITIONALLY_VALID"

    current_limitation = (
        "N225_SOURCE_COVERAGE_ENDS_AT_2025_10_03"
    )

    expected_capability = (
        "USE_N225_CONTEXT_ONLY_WHEN_PERIOD_DATA_EXISTS"
    )

    repair_action = (
        "PRESERVE_NO_DATA_AND_PREVENT_ZERO_FILL"
    )

    validation_status = (
        "PASS_WITH_COVERAGE_LIMITATION"
    )


# ============================================================
# REPORT
# ============================================================

print()
print("=== MERGE RESULT ===")

print("MERGED_ROWS        :", len(merged))
print("UNIQUE_PERIOD_KEYS :", unique_keys)
print("DUPLICATE_KEYS     :", duplicate_keys)
print("CHRONOLOGY_ERRORS  :", chronology_errors)
print("ALIGNMENT_ERRORS   :", period_alignment_errors)

print()
print("N225_AVAILABLE     :", available_n225)
print("N225_NO_DATA       :", missing_n225)

print()
print("STRUCTURE_STATUS   :", structure_status)
print("CURRENT_LIMITATION :", current_limitation)
print("EXPECTED_CAPABILITY:", expected_capability)
print("REPAIR_ACTION      :", repair_action)
print("VALIDATION_STATUS  :", validation_status)

print()
print("OUTPUT :", OUT_FILE)
print("AUDIT  :", AUDIT_FILE)

print()
print("STAGE27C_AUDIT : PASS")

