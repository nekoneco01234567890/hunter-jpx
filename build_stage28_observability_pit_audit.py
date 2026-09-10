from pathlib import Path
import csv
from datetime import datetime

INPUT_FILE = Path(
    "data/hunter/jpx_hunter_temporal_merged_2025.csv"
)

OUTPUT_FILE = Path(
    "data/hunter/jpx_stage28_observability_audit.csv"
)


def read_csv(path):
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(csv.DictReader(f))


rows = read_csv(INPUT_FILE)

print("========================================")
print("STAGE28 OBSERVABILITY / PIT AUDIT")
print("========================================")

print("INPUT_ROWS :", len(rows))


# ============================================================
# REQUIRED TEMPORAL FIELDS
# ============================================================

required = [
    "PERIOD_INDEX",
    "PERIOD_KEY",
    "OBSERVATION_WEEK",
    "OBSERVATION_START",
    "OBSERVATION_END",
    "N225_DATA_STATUS",
]

missing_columns = [
    c for c in required
    if c not in rows[0]
]

if missing_columns:
    raise SystemExit(
        "FAIL: missing columns: "
        + ",".join(missing_columns)
    )


# ============================================================
# N225 FEATURE CLASSES
# ============================================================

# BAR COUNT is structural metadata.
# Zero is valid when no source bars exist.
count_features = [
    "N225_DAY_BAR_COUNT",
    "N225_NIGHT_BAR_COUNT",
]

# These are actual observed market values.
# They must remain blank when N225 data is unavailable.
observed_value_features = [
    "N225_DAY_OPEN",
    "N225_DAY_HIGH",
    "N225_DAY_LOW",
    "N225_DAY_CLOSE",
    "N225_DAY_VOLUME",
    "N225_NIGHT_OPEN",
    "N225_NIGHT_HIGH",
    "N225_NIGHT_LOW",
    "N225_NIGHT_CLOSE",
    "N225_NIGHT_VOLUME",
]


# ============================================================
# AUDIT
# ============================================================

audit = []

errors = 0
bad_dates = 0
duplicate_keys = 0
coverage_available = 0
coverage_missing = 0

seen_keys = set()


for row in rows:

    period_index = row["PERIOD_INDEX"]
    period_key = row["PERIOD_KEY"]
    start = row["OBSERVATION_START"]
    end = row["OBSERVATION_END"]
    status = row["N225_DATA_STATUS"]

    row_errors = []

    # --------------------------------------------------------
    # DATE VALIDATION
    # --------------------------------------------------------

    try:

        start_date = datetime.strptime(
            start,
            "%Y-%m-%d"
        ).date()

        end_date = datetime.strptime(
            end,
            "%Y-%m-%d"
        ).date()

        if start_date > end_date:
            row_errors.append(
                "START_AFTER_END"
            )

    except Exception:

        row_errors.append(
            "INVALID_DATE"
        )

        bad_dates += 1

    # --------------------------------------------------------
    # UNIQUE PERIOD KEY
    # --------------------------------------------------------

    if period_key in seen_keys:

        row_errors.append(
            "DUPLICATE_PERIOD_KEY"
        )

        duplicate_keys += 1

    seen_keys.add(period_key)

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if status == "DAY_DATA_AVAILABLE":

        coverage_available += 1

    elif status in (
        "NO_DAY_DATA",
        "NO_PERIOD_RECORD",
    ):

        coverage_missing += 1

    else:

        row_errors.append(
            "UNKNOWN_N225_STATUS"
        )

    # --------------------------------------------------------
    # ZERO-FILL AUDIT
    #
    # BAR_COUNT = 0 is VALID metadata.
    #
    # Actual OHLC / VOLUME values must be blank when
    # N225 data is unavailable.
    # --------------------------------------------------------

    if status != "DAY_DATA_AVAILABLE":

        for feature in observed_value_features:

            value = row.get(
                feature,
                ""
            )

            if value not in (
                "",
                None,
            ):

                row_errors.append(
                    "N225_OBSERVED_VALUE_PRESENT_WITHOUT_DATA_STATUS:"
                    + feature
                )

    # --------------------------------------------------------
    # BAR COUNT SEMANTIC CHECK
    # --------------------------------------------------------

    if status != "DAY_DATA_AVAILABLE":

        for feature in count_features:

            value = row.get(
                feature,
                ""
            )

            if value not in (
                "",
                "0",
                "0.0",
                "0.000000",
            ):

                row_errors.append(
                    "N225_NONZERO_BAR_COUNT_WITHOUT_DATA_STATUS:"
                    + feature
                )

    # --------------------------------------------------------
    # OBSERVABILITY SEMANTICS
    # --------------------------------------------------------

    if status == "DAY_DATA_AVAILABLE":

        semantic_status = (
            "OBSERVED_AFTER_PERIOD"
        )

        pit_status = (
            "REQUIRES_SHIFT_BEFORE_PREPERIOD_USE"
        )

    else:

        semantic_status = (
            "NOT_OBSERVED"
        )

        pit_status = (
            "UNAVAILABLE"
        )

    # --------------------------------------------------------
    # AUDIT ROW
    # --------------------------------------------------------

    audit.append(
        {
            "PERIOD_INDEX":
                period_index,

            "PERIOD_KEY":
                period_key,

            "OBSERVATION_START":
                start,

            "OBSERVATION_END":
                end,

            "N225_DATA_STATUS":
                status,

            "N225_SEMANTIC_STATUS":
                semantic_status,

            "PIT_STATUS":
                pit_status,

            "ROW_ERROR_COUNT":
                len(row_errors),

            "ROW_ERRORS":
                "|".join(row_errors),
        }
    )

    errors += len(row_errors)


# ============================================================
# GLOBAL TEMPORAL ORDER
# ============================================================

ordered = sorted(
    rows,
    key=lambda r: int(
        r["PERIOD_INDEX"]
    )
)

temporal_order_errors = 0

for i in range(1, len(ordered)):

    prev = ordered[
        i - 1
    ]["OBSERVATION_START"]

    curr = ordered[
        i
    ]["OBSERVATION_START"]

    if curr <= prev:

        temporal_order_errors += 1


# ============================================================
# PERIOD INDEX VALIDATION
# ============================================================

indexes = [
    int(r["PERIOD_INDEX"])
    for r in rows
]

index_errors = (
    indexes != list(range(1, 53))
)


# ============================================================
# WRITE AUDIT
# ============================================================

fields = list(
    audit[0].keys()
)

with OUTPUT_FILE.open(
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fields
    )

    writer.writeheader()
    writer.writerows(audit)


# ============================================================
# ADAPTIVE CONTROL
# ============================================================

if coverage_missing == 0:

    structure_status = "VALIDATED"

    current_limitation = "NONE"

    expected_capability = (
        "PERIOD_CONTEXT_AVAILABLE_FOR_ALL_PERIODS"
    )

    repair_action = "NONE"

    validation_status = "PASS"

else:

    structure_status = "CONDITIONALLY_VALID"

    current_limitation = (
        "N225_PERIOD_CONTEXT_MISSING_FOR_13_PERIODS"
    )

    expected_capability = (
        "USE_ONLY_OBSERVED_PERIOD_CONTEXT_AND_SHIFT_BEFORE_PREDICTION"
    )

    repair_action = (
        "KEEP_MISSING_PERIODS_MISSING_AND_REQUIRE_TEMPORAL_SHIFT"
    )

    validation_status = (
        "PASS_WITH_COVERAGE_LIMITATION"
    )


# ============================================================
# FINAL DECISION
# ============================================================

hard_fail = (
    len(rows) != 52
    or duplicate_keys != 0
    or bad_dates != 0
    or temporal_order_errors != 0
    or index_errors
    or errors != 0
)


print()
print("=== COVERAGE ===")

print(
    "PERIODS_TOTAL       :",
    len(rows)
)

print(
    "N225_AVAILABLE      :",
    coverage_available
)

print(
    "N225_MISSING        :",
    coverage_missing
)

print()
print("=== STRUCTURE ===")

print(
    "DUPLICATE_KEYS      :",
    duplicate_keys
)

print(
    "BAD_DATES           :",
    bad_dates
)

print(
    "TEMPORAL_ORDER_ERR  :",
    temporal_order_errors
)

print(
    "PERIOD_INDEX_ERROR  :",
    int(index_errors)
)

print(
    "ROW_ERRORS          :",
    errors
)

print()
print("=== PIT SEMANTICS ===")

print(
    "N225_PERIOD_FEATURES : "
    "OBSERVED_AFTER_PERIOD"
)

print(
    "PREPERIOD_USE        : "
    "REQUIRES_SHIFT"
)

print(
    "ZERO_FILL_POLICY     : "
    "FORBIDDEN"
)

print(
    "BAR_COUNT_ZERO       : "
    "VALID_MISSING_METADATA"
)

print()
print(
    "STRUCTURE_STATUS    :",
    structure_status
)

print(
    "CURRENT_LIMITATION  :",
    current_limitation
)

print(
    "EXPECTED_CAPABILITY :",
    expected_capability
)

print(
    "REPAIR_ACTION       :",
    repair_action
)

print(
    "VALIDATION_STATUS   :",
    validation_status
)

print()
print(
    "OUTPUT :",
    OUTPUT_FILE
)

print()

if hard_fail:

    print(
        "STAGE28_AUDIT : FAIL"
    )

    raise SystemExit(1)

else:

    print(
        "STAGE28_AUDIT : PASS"
    )

