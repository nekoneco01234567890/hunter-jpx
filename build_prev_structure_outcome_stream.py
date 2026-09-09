import csv
import os
import math

BASE = os.path.expanduser("~/jpx_replay/data")

FEATURE = os.path.join(BASE, "jpx_replay_feature.csv")
EVAL = os.path.join(
    BASE,
    "jpx_replay_session_level_evaluation.csv"
)

OUT = os.path.join(
    BASE,
    "jpx_replay_prev_structure_outcome.csv"
)

SUMMARY = os.path.join(
    BASE,
    "jpx_replay_prev_structure_outcome_summary.csv"
)


def idx(h, name):
    if name not in h:
        raise RuntimeError(f"REQUIRED_COLUMN_MISSING: {name}")
    return h.index(name)


def num(v):
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except:
        return None


def pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return (a / b - 1.0) * 100.0


def bucket(x, cuts, labels):
    if x is None:
        return "UNKNOWN"
    for c, label in zip(cuts, labels):
        if x < c:
            return label
    return labels[-1]


def gap_bucket(x):
    return bucket(
        x,
        [-5, -3, -1, 0, 1, 3, 5],
        [
            "GD_GE_5",
            "GD_3_TO_5",
            "GD_1_TO_3",
            "GD_0_TO_1",
            "GU_0_TO_1",
            "GU_1_TO_3",
            "GU_3_TO_5",
            "GU_GE_5",
        ]
    )


def range_bucket(x):
    if x is None:
        return "UNKNOWN"
    if x < 1:
        return "RANGE_LT_1"
    if x < 3:
        return "RANGE_1_TO_3"
    if x < 5:
        return "RANGE_3_TO_5"
    if x < 10:
        return "RANGE_5_TO_10"
    return "RANGE_GE_10"


def relation(open_px, prev_high, prev_low):
    if (
        open_px is None
        or prev_high is None
        or prev_low is None
    ):
        return "UNKNOWN"

    if open_px > prev_high:
        return "ABOVE_PREV_HIGH"

    if open_px < prev_low:
        return "BELOW_PREV_LOW"

    if open_px == prev_high:
        return "AT_PREV_HIGH"

    if open_px == prev_low:
        return "AT_PREV_LOW"

    return "INSIDE_PREV_RANGE"


def new_stat():
    return {
        "n": 0,

        "up_sum": 0.0,
        "up_n": 0,

        "down_sum": 0.0,
        "down_n": 0,

        "close_sum": 0.0,
        "close_n": 0,

        "up1": 0,
        "up3": 0,
        "up5": 0,

        "down1": 0,
        "down3": 0,
        "down5": 0,

        "close_pos": 0,
        "close_neg": 0,
        "close_flat": 0,
    }


def update(s, up, down, close):
    s["n"] += 1

    if up is not None:
        s["up_sum"] += up
        s["up_n"] += 1

        if up >= 1:
            s["up1"] += 1
        if up >= 3:
            s["up3"] += 1
        if up >= 5:
            s["up5"] += 1

    if down is not None:
        s["down_sum"] += down
        s["down_n"] += 1

        if down <= -1:
            s["down1"] += 1
        if down <= -3:
            s["down3"] += 1
        if down <= -5:
            s["down5"] += 1

    if close is not None:
        s["close_sum"] += close
        s["close_n"] += 1

        if close > 0:
            s["close_pos"] += 1
        elif close < 0:
            s["close_neg"] += 1
        else:
            s["close_flat"] += 1


def emit(w, dim, val, s):
    n = s["n"]

    avg_up = s["up_sum"] / s["up_n"] if s["up_n"] else ""
    avg_down = s["down_sum"] / s["down_n"] if s["down_n"] else ""
    avg_close = s["close_sum"] / s["close_n"] if s["close_n"] else ""

    def ratio(x):
        return x / n * 100 if n else ""

    w.writerow([
        dim,
        val,
        n,

        avg_up,
        avg_down,
        avg_close,

        s["up1"],
        s["up3"],
        s["up5"],

        s["down1"],
        s["down3"],
        s["down5"],

        s["close_pos"],
        s["close_neg"],
        s["close_flat"],

        ratio(s["up1"]),
        ratio(s["up3"]),
        ratio(s["up5"]),

        ratio(s["down1"]),
        ratio(s["down3"]),
        ratio(s["down5"]),

        ratio(s["close_pos"]),
        ratio(s["close_neg"]),
    ])


print()
print("========================================")
print("Ω∞-DAYTRADE-JP PREV STRUCTURE ANALYSIS")
print("MODE=POINT_IN_TIME_FEATURE -> SESSION_OUTCOME")
print("RAM=STREAM")
print("NO_RULE_CHANGE")
print("NO_REAL_FILL")
print("========================================")


stats = {
    "ALL": new_stat(),
    "GAP": {},
    "PREV_RANGE": {},
    "OPEN_LOCATION": {},
}


counts = {
    "TOTAL": 0,
    "EVALUATED": 0,
    "LIMITED": 0,
    "KEY_MISMATCH": 0,
    "INVALID": 0,
}


with open(
    FEATURE,
    "r",
    encoding="utf-8-sig",
    newline="",
    buffering=1024 * 1024
) as ff, open(
    EVAL,
    "r",
    encoding="utf-8-sig",
    newline="",
    buffering=1024 * 1024
) as ef, open(
    OUT,
    "w",
    encoding="utf-8",
    newline="",
    buffering=1024 * 1024
) as fo:

    fr = csv.reader(ff)
    er = csv.reader(ef)

    fh = next(fr)
    eh = next(er)

    fi_date = idx(fh, "DATE")
    fi_code = idx(fh, "CODE")
    fi_quality = idx(fh, "QUALITY_STATUS")
    fi_feature = idx(fh, "FEATURE_STATUS")

    fi_open = idx(fh, "CURRENT_OPEN")
    fi_prev_close = idx(fh, "PREV_CLOSE")
    fi_prev_high = idx(fh, "PREV_HIGH")
    fi_prev_low = idx(fh, "PREV_LOW")
    fi_prev_range = idx(fh, "PREV_RANGE")
    fi_gap = idx(fh, "GAP_PCT")

    ei_date = idx(eh, "DATE")
    ei_code = idx(eh, "CODE")
    ei_decision = idx(eh, "DECISION_OBSERVABLE")
    ei_eval = idx(eh, "SESSION_LEVEL_EVALUATION_STATUS")
    ei_up = idx(eh, "MAX_UP_PCT")
    ei_down = idx(eh, "MAX_DOWN_PCT")
    ei_close = idx(eh, "CLOSE_PCT")

    w = csv.writer(fo)

    w.writerow([
        "DATE",
        "CODE",

        "GAP_PCT",
        "GAP_BUCKET",

        "PREV_RANGE",
        "PREV_RANGE_BUCKET",

        "OPEN_LOCATION",

        "OPEN_ABOVE_PREV_HIGH",
        "OPEN_BELOW_PREV_LOW",

        "MAX_UP_PCT",
        "MAX_DOWN_PCT",
        "CLOSE_PCT",

        "EVALUATION_STATUS",

        "FUTURE_DATA_USED_FOR_CLASSIFICATION",
    ])

    while True:
        try:
            frow = next(fr)
            erow = next(er)
        except StopIteration:
            break

        counts["TOTAL"] += 1

        fk = (frow[fi_date], frow[fi_code])
        ek = (erow[ei_date], erow[ei_code])

        if fk != ek:
            counts["KEY_MISMATCH"] += 1

            w.writerow([
                frow[fi_date],
                frow[fi_code],
                "",
                "UNKNOWN",
                "",
                "UNKNOWN",
                "UNKNOWN",
                "",
                "",
                "",
                "",
                "",
                "KEY_MISMATCH",
                "NO",
            ])
            continue

        if (
            erow[ei_decision] != "YES"
            or erow[ei_eval] != "SESSION_LEVEL_OBSERVABLE"
        ):
            counts["LIMITED"] += 1
            continue

        open_px = num(frow[fi_open])
        prev_close = num(frow[fi_prev_close])
        prev_high = num(frow[fi_prev_high])
        prev_low = num(frow[fi_prev_low])
        prev_range = num(frow[fi_prev_range])
        gap = num(frow[fi_gap])

        up = num(erow[ei_up])
        down = num(erow[ei_down])
        close = num(erow[ei_close])

        if (
            open_px is None
            or up is None
            or down is None
            or close is None
        ):
            counts["INVALID"] += 1
            continue

        gb = gap_bucket(gap)
        rb = range_bucket(prev_range)
        ol = relation(open_px, prev_high, prev_low)

        counts["EVALUATED"] += 1

        update(stats["ALL"], up, down, close)

        if gb not in stats["GAP"]:
            stats["GAP"][gb] = new_stat()
        update(stats["GAP"][gb], up, down, close)

        if rb not in stats["PREV_RANGE"]:
            stats["PREV_RANGE"][rb] = new_stat()
        update(stats["PREV_RANGE"][rb], up, down, close)

        if ol not in stats["OPEN_LOCATION"]:
            stats["OPEN_LOCATION"][ol] = new_stat()
        update(stats["OPEN_LOCATION"][ol], up, down, close)

        w.writerow([
            frow[fi_date],
            frow[fi_code],

            gap if gap is not None else "",
            gb,

            prev_range if prev_range is not None else "",
            rb,

            ol,

            "YES" if (
                prev_high is not None and open_px > prev_high
            ) else "NO",

            "YES" if (
                prev_low is not None and open_px < prev_low
            ) else "NO",

            up,
            down,
            close,

            "SESSION_LEVEL_OBSERVABLE",

            "NO",
        ])

        if counts["TOTAL"] % 50000 == 0:
            print(
                f"PROCESSED={counts['TOTAL']} "
                f"EVALUATED={counts['EVALUATED']} "
                f"LIMITED={counts['LIMITED']}"
            )


with open(
    SUMMARY,
    "w",
    encoding="utf-8",
    newline=""
) as fs:

    w = csv.writer(fs)

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

    emit(w, "ALL", "ALL", stats["ALL"])

    for k in sorted(stats["GAP"]):
        emit(w, "GAP", k, stats["GAP"][k])

    for k in sorted(stats["PREV_RANGE"]):
        emit(w, "PREV_RANGE", k, stats["PREV_RANGE"][k])

    for k in sorted(stats["OPEN_LOCATION"]):
        emit(w, "OPEN_LOCATION", k, stats["OPEN_LOCATION"][k])


print()
print("========================================")
print("PREV STRUCTURE ANALYSIS RESULT")
print("========================================")
print("TOTAL       =", counts["TOTAL"])
print("EVALUATED   =", counts["EVALUATED"])
print("LIMITED     =", counts["LIMITED"])
print("INVALID     =", counts["INVALID"])
print("KEY MISMATCH=", counts["KEY_MISMATCH"])
print("========================================")

if counts["KEY_MISMATCH"] == 0 and counts["INVALID"] == 0:
    print("PREV_STRUCTURE_ANALYSIS_AUDIT = PASS")
else:
    print("PREV_STRUCTURE_ANALYSIS_AUDIT = LIMITED")

print()
print("OUT =", OUT)
print("SUMMARY =", SUMMARY)
