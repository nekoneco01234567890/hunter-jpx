import csv
import math
from pathlib import Path

BASE = Path("data/jpx_replay_feature.csv")
CTX = Path("data/jpx_replay_feature_n225_context.csv")
OUT = Path("data/n225_information_value_analysis.csv")
SUMMARY = Path("data/n225_information_value_summary.csv")

BUF = 1024 * 1024
MIN_SAMPLE = 30

BASE_REQUIRED = {
    "DATE",
    "CODE",
    "GAP",
    "PREV_RANGE",
    "OPEN_LOCATION",
}

CTX_REQUIRED = {
    "DATE",
    "CODE",
    "GAP",
    "PREV_RANGE",
    "OPEN_LOCATION",
    "N225_DIRECTION",
    "N225_PERSISTENCE",
    "N225_RETURN_5M_PCT",
    "N225_RETURN_10M_PCT",
    "N225_RANGE_10M_PCT",
    "N225_NIGHT_RETURN_PCT",
    "N225_POINT_IN_TIME_STATUS",
}

OUT_REQUIRED = {
    "MAX_UP_PCT",
    "MAX_DOWN_PCT",
    "CLOSE_PCT",
}


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


def add_stat(d, key, up, down, close):
    if up is None or down is None or close is None:
        return

    if key not in d:
        d[key] = [0, 0.0, 0.0, 0.0]

    s = d[key]
    s[0] += 1
    s[1] += up
    s[2] += down
    s[3] += close


def mean(s, idx):
    return s[idx] / s[0] if s and s[0] else None


def main():

    # --------------------------------------------------
    # 集計
    # --------------------------------------------------
    base_stats = {}
    n225_stats = {}

    total = 0
    evaluated = 0
    limited = 0
    mismatch = 0
    pit_fail = 0

    with open(
        BASE,
        "r",
        newline="",
        encoding="utf-8-sig",
        buffering=BUF,
    ) as fb, open(
        CTX,
        "r",
        newline="",
        encoding="utf-8-sig",
        buffering=BUF,
    ) as fc:

        rb = csv.DictReader(fb)
        rc = csv.DictReader(fc)

        if not BASE_REQUIRED.issubset(set(rb.fieldnames or [])):
            raise SystemExit("BASE_REQUIRED_COLUMNS_FAIL")

        if not CTX_REQUIRED.issubset(set(rc.fieldnames or [])):
            raise SystemExit("CTX_REQUIRED_COLUMNS_FAIL")

        rb_it = iter(rb)
        rc_it = iter(rc)

        while True:

            try:
                b = next(rb_it)
            except StopIteration:
                b = None

            try:
                c = next(rc_it)
            except StopIteration:
                c = None

            if b is None and c is None:
                break

            if b is None or c is None:
                raise SystemExit("ROW_COUNT_ALIGNMENT_FAIL")

            total += 1

            kb = (clean(b["DATE"]), clean(b["CODE"]))
            kc = (clean(c["DATE"]), clean(c["CODE"]))

            if kb != kc:
                mismatch += 1
                continue

            if clean(c["N225_POINT_IN_TIME_STATUS"]) != "PASS":
                pit_fail += 1
                continue

            up = num(c.get("MAX_UP_PCT"))
            down = num(c.get("MAX_DOWN_PCT"))
            close = num(c.get("CLOSE_PCT"))

            if up is None or down is None or close is None:
                limited += 1
                continue

            evaluated += 1

            # ------------------------------------------
            # JPX-only baseline
            # ------------------------------------------
            gap_b = bucket(
                b["GAP"],
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

            range_b = bucket(
                b["PREV_RANGE"],
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

            location = clean(b["OPEN_LOCATION"]) or "UNKNOWN"

            base_key = (
                gap_b,
                range_b,
                location,
            )

            add_stat(base_stats, base_key, up, down, close)

            # ------------------------------------------
            # N225 categories
            # ------------------------------------------
            direction = clean(c["N225_DIRECTION"]) or "UNKNOWN"
            persistence = clean(c["N225_PERSISTENCE"]) or "UNKNOWN"

            ret5 = bucket(
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
            )

            ret10 = bucket(
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
            )

            range10 = bucket(
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
            )

            night = bucket(
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
            )

            dimensions = [
                ("DIRECTION", direction),
                ("PERSISTENCE", persistence),
                ("RETURN_5M", ret5),
                ("RETURN_10M", ret10),
                ("RANGE_10M", range10),
                ("NIGHT_RETURN", night),
            ]

            for dim, val in dimensions:
                key = (
                    dim,
                    val,
                )
                add_stat(n225_stats, key, up, down, close)

    # --------------------------------------------------
    # 出力
    # --------------------------------------------------
    rows = []

    for key, s in base_stats.items():
        if s[0] < MIN_SAMPLE:
            continue

        gap, prev_range, location = key

        rows.append([
            "BASELINE",
            "JPX_ONLY",
            gap,
            prev_range,
            location,
            "",
            "",
            "",
            "",
            s[0],
            mean(s, 1),
            mean(s, 2),
            mean(s, 3),
        ])

    for key, s in n225_stats.items():
        if s[0] < MIN_SAMPLE:
            continue

        dim, value = key

        rows.append([
            "N225_CONTEXT",
            "JPX_PLUS_N225",
            "",
            "",
            "",
            dim,
            value,
            "",
            "",
            s[0],
            mean(s, 1),
            mean(s, 2),
            mean(s, 3),
        ])

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
            "N225_RETURN_5M_BUCKET",
            "N225_RETURN_10M_BUCKET",
            "SAMPLE_COUNT",
            "AVG_MAX_UP_PCT",
            "AVG_MAX_DOWN_PCT",
            "AVG_CLOSE_PCT",
        ])
        w.writerows(rows)

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
        w.writerow(["BASELINE_GROUPS", len(base_stats)])
        w.writerow(["N225_GROUPS", len(n225_stats)])
        w.writerow(["MIN_SAMPLE", MIN_SAMPLE])

        if mismatch == 0 and pit_fail == 0:
            status = "PASS"
        else:
            status = "FAIL"

        w.writerow(["N225_INFORMATION_VALUE_AUDIT", status])

    print("========================================")
    print("N225 INFORMATION VALUE ANALYSIS")
    print("========================================")
    print("TOTAL_ROWS =", total)
    print("EVALUATED_ROWS =", evaluated)
    print("LIMITED_ROWS =", limited)
    print("KEY_MISMATCH =", mismatch)
    print("N225_PIT_FAIL =", pit_fail)
    print("BASELINE_GROUPS =", len(base_stats))
    print("N225_GROUPS =", len(n225_stats))
    print("MIN_SAMPLE =", MIN_SAMPLE)
    print("========================================")
    print("N225_INFORMATION_VALUE_AUDIT =", "PASS" if mismatch == 0 and pit_fail == 0 else "FAIL")
    print("OUT =", OUT)
    print("SUMMARY =", SUMMARY)


if __name__ == "__main__":
    main()
