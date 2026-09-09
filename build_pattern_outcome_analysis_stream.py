import csv
import os
import math

BASE = os.path.expanduser("~/jpx_replay/data")

INPUT = os.path.join(
    BASE,
    "jpx_replay_session_level_evaluation.csv"
)

OUT = os.path.join(
    BASE,
    "jpx_replay_pattern_outcome_analysis.csv"
)

SUMMARY = os.path.join(
    BASE,
    "jpx_replay_pattern_outcome_summary.csv"
)


def idx(header, name):
    if name not in header:
        raise RuntimeError(f"REQUIRED_COLUMN_MISSING: {name}")
    return header.index(name)


def to_float(v):
    if v is None:
        return None
    v = str(v).strip()
    if v == "":
        return None
    try:
        x = float(v)
        if not math.isfinite(x):
            return None
        return x
    except Exception:
        return None


def bucket_gap(x):
    if x is None:
        return "UNKNOWN"
    if x >= 5:
        return "GAP_UP_GE_5"
    if x >= 3:
        return "GAP_UP_3_TO_5"
    if x >= 1:
        return "GAP_UP_1_TO_3"
    if x > 0:
        return "GAP_UP_0_TO_1"
    if x == 0:
        return "FLAT_0"
    if x > -1:
        return "GAP_DOWN_0_TO_1"
    if x > -3:
        return "GAP_DOWN_1_TO_3"
    if x > -5:
        return "GAP_DOWN_3_TO_5"
    return "GAP_DOWN_GE_5"


def bucket_prev_range(x):
    if x is None:
        return "UNKNOWN"
    if x < 1:
        return "PREV_RANGE_LT_1"
    if x < 3:
        return "PREV_RANGE_1_TO_3"
    if x < 5:
        return "PREV_RANGE_3_TO_5"
    if x < 10:
        return "PREV_RANGE_5_TO_10"
    return "PREV_RANGE_GE_10"


def bucket_max_up(x):
    if x is None:
        return "UNKNOWN"
    if x < 0:
        return "MAX_UP_LT_0"
    if x < 1:
        return "MAX_UP_0_TO_1"
    if x < 3:
        return "MAX_UP_1_TO_3"
    if x < 5:
        return "MAX_UP_3_TO_5"
    if x < 10:
        return "MAX_UP_5_TO_10"
    return "MAX_UP_GE_10"


def bucket_max_down(x):
    if x is None:
        return "UNKNOWN"
    if x > 0:
        return "MAX_DOWN_GT_0"
    if x > -1:
        return "MAX_DOWN_0_TO_M1"
    if x > -3:
        return "MAX_DOWN_M1_TO_M3"
    if x > -5:
        return "MAX_DOWN_M3_TO_M5"
    if x > -10:
        return "MAX_DOWN_M5_TO_M10"
    return "MAX_DOWN_LE_M10"


def new_bucket():
    return {
        "count": 0,
        "up_sum": 0.0,
        "up_count": 0,
        "down_sum": 0.0,
        "down_count": 0,
        "close_sum": 0.0,
        "close_count": 0,

        "up_ge_1": 0,
        "up_ge_3": 0,
        "up_ge_5": 0,

        "down_le_m1": 0,
        "down_le_m3": 0,
        "down_le_m5": 0,

        "close_positive": 0,
        "close_negative": 0,
        "close_flat": 0,
    }


def update(d, max_up, max_down, close_pct):
    d["count"] += 1

    if max_up is not None:
        d["up_sum"] += max_up
        d["up_count"] += 1

        if max_up >= 1:
            d["up_ge_1"] += 1
        if max_up >= 3:
            d["up_ge_3"] += 1
        if max_up >= 5:
            d["up_ge_5"] += 1

    if max_down is not None:
        d["down_sum"] += max_down
        d["down_count"] += 1

        if max_down <= -1:
            d["down_le_m1"] += 1
        if max_down <= -3:
            d["down_le_m3"] += 1
        if max_down <= -5:
            d["down_le_m5"] += 1

    if close_pct is not None:
        d["close_sum"] += close_pct
        d["close_count"] += 1

        if close_pct > 0:
            d["close_positive"] += 1
        elif close_pct < 0:
            d["close_negative"] += 1
        else:
            d["close_flat"] += 1


def emit_summary(w, dimension, bucket, d):
    avg_up = (
        d["up_sum"] / d["up_count"]
        if d["up_count"] else ""
    )

    avg_down = (
        d["down_sum"] / d["down_count"]
        if d["down_count"] else ""
    )

    avg_close = (
        d["close_sum"] / d["close_count"]
        if d["close_count"] else ""
    )

    def ratio(n):
        return (
            n / d["count"] * 100
            if d["count"] else ""
        )

    w.writerow([
        dimension,
        bucket,
        d["count"],

        avg_up,
        avg_down,
        avg_close,

        d["up_ge_1"],
        d["up_ge_3"],
        d["up_ge_5"],

        d["down_le_m1"],
        d["down_le_m3"],
        d["down_le_m5"],

        d["close_positive"],
        d["close_negative"],
        d["close_flat"],

        ratio(d["up_ge_1"]),
        ratio(d["up_ge_3"]),
        ratio(d["up_ge_5"]),

        ratio(d["down_le_m1"]),
        ratio(d["down_le_m3"]),
        ratio(d["down_le_m5"]),

        ratio(d["close_positive"]),
        ratio(d["close_negative"]),
    ])


print()
print("========================================")
print("Ω∞-DAYTRADE-JP PATTERN OUTCOME ANALYSIS")
print("MODE=BLIND_FEATURE -> SESSION_OUTCOME")
print("RAM=STREAM")
print("NO_RULE_CHANGE")
print("NO_REAL_FILL")
print("========================================")


dims = {
    "ALL": new_bucket(),
    "GAP": {},
    "PREV_RANGE": {},
    "OPEN_VS_PREV_HIGH": {},
    "OPEN_VS_PREV_LOW": {},
}


counts = {
    "TOTAL": 0,
    "EVALUATED": 0,
    "LIMITED": 0,
    "INVALID": 0,
}


with open(
    INPUT,
    "r",
    encoding="utf-8-sig",
    newline="",
    buffering=1024 * 1024
) as f:

    r = csv.reader(f)
    h = next(r)

    i_date = idx(h, "DATE")
    i_code = idx(h, "CODE")
    i_decision = idx(h, "DECISION_OBSERVABLE")
    i_eval = idx(h, "SESSION_LEVEL_EVALUATION_STATUS")
    i_gap = idx(h, "GAP_PCT")
    i_open = idx(h, "CURRENT_OPEN")
    i_prev = idx(h, "PREV_CLOSE")
    i_high = idx(h, "SESSION_HIGH")
    i_low = idx(h, "SESSION_LOW")
    i_close = idx(h, "SESSION_CLOSE")

    for row in r:

        counts["TOTAL"] += 1

        if (
            row[i_decision] != "YES"
            or row[i_eval] != "SESSION_LEVEL_OBSERVABLE"
        ):
            counts["LIMITED"] += 1
            continue

        current_open = to_float(row[i_open])
        prev_close = to_float(row[i_prev])
        session_high = to_float(row[i_high])
        session_low = to_float(row[i_low])
        session_close = to_float(row[i_close])
        gap = to_float(row[i_gap])

        if (
            current_open is None
            or current_open == 0
            or session_high is None
            or session_low is None
            or session_close is None
        ):
            counts["INVALID"] += 1
            continue

        max_up = (session_high / current_open - 1) * 100
        max_down = (session_low / current_open - 1) * 100
        close_pct = (session_close / current_open - 1) * 100

        counts["EVALUATED"] += 1

        update(
            dims["ALL"],
            max_up,
            max_down,
            close_pct
        )

        gap_bucket = bucket_gap(gap)

        if gap_bucket not in dims["GAP"]:
            dims["GAP"][gap_bucket] = new_bucket()

        update(
            dims["GAP"][gap_bucket],
            max_up,
            max_down,
            close_pct
        )

        if prev_close is not None and prev_close != 0:
            prev_range = (
                to_float(row[h.index("SESSION_HIGH")])
                if False else None
            )

        # PREV_RANGE is not directly present in the evaluation file.
        # Derive it only from fields already available in the file
        # when possible. No future data is used for classification.
        #
        # The original feature file contains PREV_RANGE but this layer
        # intentionally avoids reopening it. Therefore PREV_RANGE is
        # not used here.

        # Open relative to previous high / low
        # Reconstruct the boundary relation from available values.
        #
        # Previous high/low are not present in this output layer.
        # Therefore these dimensions are intentionally omitted rather
        # than guessed.

        if counts["TOTAL"] % 50000 == 0:
            print(
                f"PROCESSED={counts['TOTAL']} "
                f"EVALUATED={counts['EVALUATED']} "
                f"LIMITED={counts['LIMITED']}"
            )


with open(
    OUT,
    "w",
    encoding="utf-8",
    newline=""
) as fo:

    w = csv.writer(fo)

    w.writerow([
        "DIMENSION",
        "BUCKET",
        "COUNT",

        "AVG_MAX_UP_PCT",
        "AVG_MAX_DOWN_PCT",
        "AVG_CLOSE_PCT",

        "MAX_UP_GE_1_COUNT",
        "MAX_UP_GE_3_COUNT",
        "MAX_UP_GE_5_COUNT",

        "MAX_DOWN_LE_M1_COUNT",
        "MAX_DOWN_LE_M3_COUNT",
        "MAX_DOWN_LE_M5_COUNT",

        "CLOSE_POSITIVE_COUNT",
        "CLOSE_NEGATIVE_COUNT",
        "CLOSE_FLAT_COUNT",

        "MAX_UP_GE_1_PCT",
        "MAX_UP_GE_3_PCT",
        "MAX_UP_GE_5_PCT",

        "MAX_DOWN_LE_M1_PCT",
        "MAX_DOWN_LE_M3_PCT",
        "MAX_DOWN_LE_M5_PCT",

        "CLOSE_POSITIVE_PCT",
        "CLOSE_NEGATIVE_PCT",
    ])

    emit_summary(
        w,
        "ALL",
        "ALL",
        dims["ALL"]
    )

    for bucket in sorted(dims["GAP"]):
        emit_summary(
            w,
            "GAP",
            bucket,
            dims["GAP"][bucket]
        )


with open(
    SUMMARY,
    "w",
    encoding="utf-8",
    newline=""
) as fs:

    w = csv.writer(fs)

    w.writerow(["METRIC", "VALUE"])

    w.writerow(["TOTAL", counts["TOTAL"]])
    w.writerow(["EVALUATED", counts["EVALUATED"]])
    w.writerow(["LIMITED", counts["LIMITED"]])
    w.writerow(["INVALID", counts["INVALID"]])

    w.writerow([
        "ANALYSIS_SCOPE",
        "SESSION_LEVEL_ONLY"
    ])

    w.writerow([
        "REFERENCE_PRICE",
        "CURRENT_OPEN_NOT_REAL_FILL"
    ])

    w.writerow([
        "REAL_FILL_RECONSTRUCTED",
        "NO"
    ])

    w.writerow([
        "STOP_HIT_RECONSTRUCTED",
        "NO"
    ])

    w.writerow([
        "REALIZED_PNL_RECONSTRUCTED",
        "NO"
    ])

    w.writerow([
        "RULE_CHANGED",
        "NO"
    ])

    w.writerow([
        "FUTURE_DATA_USED_FOR_CLASSIFICATION",
        "NO"
    ])

    w.writerow([
        "KEY_ALIGNMENT",
        "INHERITED_FROM_PREVIOUS_AUDIT"
    ])


print()
print("========================================")
print("PATTERN OUTCOME ANALYSIS RESULT")
print("========================================")
print("TOTAL     =", counts["TOTAL"])
print("EVALUATED =", counts["EVALUATED"])
print("LIMITED   =", counts["LIMITED"])
print("INVALID   =", counts["INVALID"])
print("========================================")

if counts["INVALID"] == 0:
    print("PATTERN_OUTCOME_ANALYSIS_AUDIT = PASS")
else:
    print("PATTERN_OUTCOME_ANALYSIS_AUDIT = LIMITED")

print()
print("OUT =", OUT)
print("SUMMARY =", SUMMARY)
