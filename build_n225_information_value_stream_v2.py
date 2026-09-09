import csv
from pathlib import Path

FEATURE = Path("data/jpx_replay_feature.csv")
CTX = Path("data/jpx_replay_feature_n225_context.csv")
OUTCOME = Path("data/jpx_replay_session_level_evaluation.csv")

OUT = Path("data/n225_information_value_analysis_v2.csv")
SUMMARY = Path("data/n225_information_value_summary_v2.csv")

BUF = 1024 * 1024
MIN_SAMPLE = 30


def clean(v):
    return (v or "").strip()


def num(v):
    try:
        return float(v)
    except Exception:
        return None


def bucket(v, edges, labels):
    x = num(v)

    if x is None:
        return "UNKNOWN"

    for edge, label in zip(edges, labels):
        if x < edge:
            return label

    return labels[-1]


def open_location(row):
    above = clean(row.get("OPEN_ABOVE_PREV_HIGH"))
    below = clean(row.get("OPEN_BELOW_PREV_LOW"))

    if above == "TRUE":
        return "ABOVE_PREV_HIGH"

    if below == "TRUE":
        return "BELOW_PREV_LOW"

    if above == "FALSE" and below == "FALSE":
        return "BETWEEN_PREV_HIGH_LOW"

    return "UNKNOWN"


def add_stat(stats, key, up, down, close):

    if up is None or down is None or close is None:
        return

    if key not in stats:
        stats[key] = [0, 0.0, 0.0, 0.0]

    s = stats[key]

    s[0] += 1
    s[1] += up
    s[2] += down
    s[3] += close


def avg(s, index):
    if not s or s[0] == 0:
        return ""

    return s[index] / s[0]


def main():

    feature_stats = {}
    n225_stats = {}

    total = 0
    evaluated = 0
    limited = 0
    mismatch = 0
    pit_fail = 0

    with open(
        FEATURE,
        "r",
        newline="",
        encoding="utf-8-sig",
        buffering=BUF,
    ) as ff, open(
        CTX,
        "r",
        newline="",
        encoding="utf-8-sig",
        buffering=BUF,
    ) as fc, open(
        OUTCOME,
        "r",
        newline="",
        encoding="utf-8-sig",
        buffering=BUF,
    ) as fo:

        rf = csv.DictReader(ff)
        rc = csv.DictReader(fc)
        ro = csv.DictReader(fo)

        feature_required = {
            "DATE",
            "CODE",
            "GAP",
            "PREV_RANGE",
            "OPEN_ABOVE_PREV_HIGH",
            "OPEN_BELOW_PREV_LOW",
        }

        ctx_required = {
            "DATE",
            "CODE",
            "N225_DIRECTION",
            "N225_PERSISTENCE",
            "N225_RETURN_5M_PCT",
            "N225_RETURN_10M_PCT",
            "N225_RANGE_10M_PCT",
            "N225_NIGHT_RETURN_PCT",
            "N225_POINT_IN_TIME_STATUS",
        }

        outcome_required = {
            "DATE",
            "CODE",
            "MAX_UP_PCT",
            "MAX_DOWN_PCT",
            "CLOSE_PCT",
        }

        if not feature_required.issubset(set(rf.fieldnames or [])):
            raise SystemExit("FEATURE_REQUIRED_COLUMNS_FAIL")

        if not ctx_required.issubset(set(rc.fieldnames or [])):
            raise SystemExit("CTX_REQUIRED_COLUMNS_FAIL")

        if not outcome_required.issubset(set(ro.fieldnames or [])):
            raise SystemExit("OUTCOME_REQUIRED_COLUMNS_FAIL")

        fi = iter(rf)
        ci = iter(rc)
        oi = iter(ro)

        while True:

            try:
                f = next(fi)
            except StopIteration:
                f = None

            try:
                c = next(ci)
            except StopIteration:
                c = None

            try:
                o = next(oi)
            except StopIteration:
                o = None

            if f is None and c is None and o is None:
                break

            if f is None or c is None or o is None:
                raise SystemExit("ROW_COUNT_ALIGNMENT_FAIL")

            total += 1

            kf = (
                clean(f["DATE"]),
                clean(f["CODE"]),
            )

            kc = (
                clean(c["DATE"]),
                clean(c["CODE"]),
            )

            ko = (
                clean(o["DATE"]),
                clean(o["CODE"]),
            )

            if not (kf == kc == ko):
                mismatch += 1
                continue

            if clean(c["N225_POINT_IN_TIME_STATUS"]) != "PASS":
                pit_fail += 1
                continue

            up = num(o["MAX_UP_PCT"])
            down = num(o["MAX_DOWN_PCT"])
            close = num(o["CLOSE_PCT"])

            if up is None or down is None or close is None:
                limited += 1
                continue

            evaluated += 1

            # ------------------------------------------
            # JPX baseline
            # ------------------------------------------

            gap = bucket(
                f["GAP_PCT"],
                [-5, -3, -1, 0, 1, 3, 5],
                [
                    "<-5%",
                    "-5~-3%",
                    "-3~-1%",
                    "-1~0%",
                    "0~1%",
                    "1~3%",
                    "3~5%",
                    ">=5%",
                ],
            )

            prev_range = bucket(
                f["PREV_RANGE"],
                [1, 2, 3, 5, 10],
                [
                    "<1",
                    "1~2",
                    "2~3",
                    "3~5",
                    "5~10",
                    ">=10",
                ],
            )

            location = open_location(f)

            base_key = (
                gap,
                prev_range,
                location,
            )

            add_stat(
                feature_stats,
                base_key,
                up,
                down,
                close,
            )

            # ------------------------------------------
            # N225 dimensions
            # ------------------------------------------

            dimensions = [
                (
                    "DIRECTION",
                    clean(c["N225_DIRECTION"]) or "UNKNOWN",
                ),
                (
                    "PERSISTENCE",
                    clean(c["N225_PERSISTENCE"]) or "UNKNOWN",
                ),
                (
                    "RETURN_5M",
                    bucket(
                        c["N225_RETURN_5M_PCT"],
                        [-0.5, -0.2, -0.05, 0.05, 0.2, 0.5],
                        [
                            "<-0.5%",
                            "-0.5~-0.2%",
                            "-0.2~-0.05%",
                            "-0.05~0.05%",
                            "0.05~0.2%",
                            "0.2~0.5%",
                            ">=0.5%",
                        ],
                    ),
                ),
                (
                    "RETURN_10M",
                    bucket(
                        c["N225_RETURN_10M_PCT"],
                        [-1.0, -0.5, -0.2, 0.0, 0.2, 0.5, 1.0],
                        [
                            "<-1%",
                            "-1~-0.5%",
                            "-0.5~-0.2%",
                            "-0.2~0%",
                            "0~0.2%",
                            "0.2~0.5%",
                            "0.5~1%",
                            ">=1%",
                        ],
                    ),
                ),
                (
                    "RANGE_10M",
                    bucket(
                        c["N225_RANGE_10M_PCT"],
                        [0.1, 0.2, 0.5, 1.0, 2.0],
                        [
                            "<0.1%",
                            "0.1~0.2%",
                            "0.2~0.5%",
                            "0.5~1%",
                            "1~2%",
                            ">=2%",
                        ],
                    ),
                ),
                (
                    "NIGHT_RETURN",
                    bucket(
                        c["N225_NIGHT_RETURN_PCT"],
                        [-2, -1, -0.5, 0, 0.5, 1, 2],
                        [
                            "<-2%",
                            "-2~-1%",
                            "-1~-0.5%",
                            "-0.5~0%",
                            "0~0.5%",
                            "0.5~1%",
                            "1~2%",
                            ">=2%",
                        ],
                    ),
                ),
            ]

            for dimension, value in dimensions:

                key = (
                    dimension,
                    value,
                )

                add_stat(
                    n225_stats,
                    key,
                    up,
                    down,
                    close,
                )

    # ----------------------------------------------
    # 出力
    # ----------------------------------------------

    with open(
        OUT,
        "w",
        newline="",
        encoding="utf-8-sig",
        buffering=BUF,
    ) as f:

        w = csv.writer(f)

        w.writerow([
            "ANALYSIS_TYPE",
            "DATASET",
            "GAP_BUCKET",
            "PREV_RANGE_BUCKET",
            "OPEN_LOCATION",
            "N225_DIMENSION",
            "N225_VALUE",
            "SAMPLE_COUNT",
            "AVG_MAX_UP_PCT",
            "AVG_MAX_DOWN_PCT",
            "AVG_CLOSE_PCT",
        ])

        for key, s in feature_stats.items():

            if s[0] < MIN_SAMPLE:
                continue

            gap, prev_range, location = key

            w.writerow([
                "BASELINE",
                "JPX_ONLY",
                gap,
                prev_range,
                location,
                "",
                "",
                s[0],
                avg(s, 1),
                avg(s, 2),
                avg(s, 3),
            ])

        for key, s in n225_stats.items():

            if s[0] < MIN_SAMPLE:
                continue

            dimension, value = key

            w.writerow([
                "N225_CONTEXT",
                "JPX_PLUS_N225",
                "",
                "",
                "",
                dimension,
                value,
                s[0],
                avg(s, 1),
                avg(s, 2),
                avg(s, 3),
            ])

    status = (
        "PASS"
        if mismatch == 0 and pit_fail == 0
        else "FAIL"
    )

    with open(
        SUMMARY,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        w = csv.writer(f)

        w.writerow(["METRIC", "VALUE"])
        w.writerow(["TOTAL_ROWS", total])
        w.writerow(["EVALUATED_ROWS", evaluated])
        w.writerow(["LIMITED_ROWS", limited])
        w.writerow(["KEY_MISMATCH", mismatch])
        w.writerow(["N225_PIT_FAIL", pit_fail])
        w.writerow(["BASELINE_GROUPS", len(feature_stats)])
        w.writerow(["N225_GROUPS", len(n225_stats)])
        w.writerow(["MIN_SAMPLE", MIN_SAMPLE])
        w.writerow(["N225_INFORMATION_VALUE_AUDIT", status])

    print("========================================")
    print("N225 INFORMATION VALUE ANALYSIS V2")
    print("========================================")
    print("TOTAL_ROWS =", total)
    print("EVALUATED_ROWS =", evaluated)
    print("LIMITED_ROWS =", limited)
    print("KEY_MISMATCH =", mismatch)
    print("N225_PIT_FAIL =", pit_fail)
    print("BASELINE_GROUPS =", len(feature_stats))
    print("N225_GROUPS =", len(n225_stats))
    print("MIN_SAMPLE =", MIN_SAMPLE)
    print("========================================")
    print("N225_INFORMATION_VALUE_AUDIT =", status)
    print("OUT =", OUT)
    print("SUMMARY =", SUMMARY)


if __name__ == "__main__":
    main()
