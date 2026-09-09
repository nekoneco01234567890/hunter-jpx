import csv
import os
import math

BASE = os.path.expanduser("~/jpx_replay/data")

FEATURE = os.path.join(BASE, "jpx_replay_feature.csv")
SESSION = os.path.join(BASE, "jpx_replay_session.csv")
GUARD = os.path.join(BASE, "jpx_replay_v15_guard_audit.csv")

OUT = os.path.join(BASE, "jpx_replay_session_level_evaluation.csv")
SUMMARY = os.path.join(BASE, "jpx_replay_session_level_evaluation_summary.csv")


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
    except:
        return None


def pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return (a / b - 1.0) * 100.0


print()
print("========================================")
print("Ω∞-DAYTRADE-JP SESSION LEVEL EVALUATION")
print("MODE=BLIND_DECISION -> SESSION_OUTCOME")
print("RAM=STREAM")
print("NO_REAL_FILL_RECONSTRUCTION")
print("========================================")


counts = {
    "TOTAL": 0,
    "DECISION_OBSERVABLE": 0,
    "DECISION_LIMITED": 0,
    "OUTCOME_OBSERVABLE": 0,
    "OUTCOME_LIMITED": 0,
    "FULL_SESSION_EVALUABLE": 0,
    "NO_TRADE_PREFERENCE": 0,
    "GUARD_PASS": 0,
    "GUARD_LIMITED": 0,
    "KEY_MISMATCH": 0,
    "INVALID_NUMERIC": 0,
}

max_up_sum = 0.0
max_down_sum = 0.0
close_sum = 0.0

max_up_count = 0
max_down_count = 0
close_count = 0

max_up_ge_1 = 0
max_up_ge_3 = 0
max_up_ge_5 = 0

max_down_le_m1 = 0
max_down_le_m3 = 0
max_down_le_m5 = 0

close_positive = 0
close_negative = 0
close_flat = 0


with open(FEATURE, "r", encoding="utf-8-sig", newline="", buffering=1024*1024) as ff, \
     open(SESSION, "r", encoding="utf-8-sig", newline="", buffering=1024*1024) as sf, \
     open(GUARD, "r", encoding="utf-8-sig", newline="", buffering=1024*1024) as gf, \
     open(OUT, "w", encoding="utf-8", newline="", buffering=1024*1024) as fo:

    fr = csv.reader(ff)
    sr = csv.reader(sf)
    gr = csv.reader(gf)

    fh = next(fr)
    sh = next(sr)
    gh = next(gr)

    fi_date = idx(fh, "DATE")
    fi_code = idx(fh, "CODE")
    fi_quality = idx(fh, "QUALITY_STATUS")
    fi_feature = idx(fh, "FEATURE_STATUS")
    fi_open = idx(fh, "CURRENT_OPEN")
    fi_prev = idx(fh, "PREV_CLOSE")
    fi_gap = idx(fh, "GAP_PCT")

    si_date = idx(sh, "DATE")
    si_code = idx(sh, "CODE")
    si_high = idx(sh, "SESSION_HIGH")
    si_low = idx(sh, "SESSION_LOW")
    si_close = idx(sh, "SESSION_CLOSE")

    gi_date = idx(gh, "DATE")
    gi_code = idx(gh, "CODE")
    gi_guard = idx(gh, "V15_GUARD_STATUS")
    gi_critical = idx(gh, "CRITICAL_FAIL")
    gi_persistence = idx(gh, "PERSISTENCE_STATUS")

    writer = csv.writer(fo)

    writer.writerow([
        "DATE",
        "CODE",
        "QUALITY_STATUS",
        "FEATURE_STATUS",
        "V15_GUARD_STATUS",
        "CRITICAL_FAIL",
        "PERSISTENCE_STATUS",

        "DECISION_OBSERVABLE",
        "DECISION_FREEZE",
        "DECISION_REFERENCE",

        "CURRENT_OPEN",
        "PREV_CLOSE",
        "GAP_PCT",

        "SESSION_HIGH",
        "SESSION_LOW",
        "SESSION_CLOSE",

        "MAX_UP_PCT",
        "MAX_DOWN_PCT",
        "CLOSE_PCT",

        "SESSION_OUTCOME_OBSERVABLE",
        "SESSION_LEVEL_EVALUATION_STATUS",

        "REAL_FILL_RECONSTRUCTED",
        "STOP_HIT_RECONSTRUCTED",
        "REALIZED_PNL_RECONSTRUCTED",
        "SLIPPAGE_RECONSTRUCTED",

        "FUTURE_DATA_USED_FOR_DECISION",
    ])

    while True:
        try:
            frow = next(fr)
            srow = next(sr)
            grow = next(gr)
        except StopIteration:
            break

        counts["TOTAL"] += 1

        fkey = (frow[fi_date], frow[fi_code])
        skey = (srow[si_date], srow[si_code])
        gkey = (grow[gi_date], grow[gi_code])

        if fkey != skey or fkey != gkey:
            counts["KEY_MISMATCH"] += 1

            writer.writerow([
                frow[fi_date],
                frow[fi_code],
                frow[fi_quality],
                frow[fi_feature],
                grow[gi_guard],
                grow[gi_critical],
                grow[gi_persistence],
                "NO",
                "NO",
                "UNVERIFIABLE",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "NO",
                "KEY_MISMATCH",
                "NO",
                "NO",
                "NO",
                "NO",
                "NO",
            ])
            continue

        quality = frow[fi_quality]
        feature_status = frow[fi_feature]
        guard_status = grow[gi_guard]
        critical = grow[gi_critical]
        persistence = grow[gi_persistence]

        current_open = to_float(frow[fi_open])
        prev_close = to_float(frow[fi_prev])
        gap_pct = to_float(frow[fi_gap])

        session_high = to_float(srow[si_high])
        session_low = to_float(srow[si_low])
        session_close = to_float(srow[si_close])

        decision_observable = (
            quality == "VALID"
            and feature_status == "READY_09_10"
            and current_open is not None
        )

        if decision_observable:
            counts["DECISION_OBSERVABLE"] += 1
            decision_freeze = "YES"
            decision_reference = "CURRENT_OPEN_AS_REFERENCE_ONLY"
        else:
            counts["DECISION_LIMITED"] += 1
            decision_freeze = "NO"
            decision_reference = "UNVERIFIABLE"

        outcome_observable = (
            session_high is not None
            and session_low is not None
            and session_close is not None
            and current_open is not None
            and current_open != 0
        )

        if outcome_observable:
            counts["OUTCOME_OBSERVABLE"] += 1
        else:
            counts["OUTCOME_LIMITED"] += 1

        full_eval = decision_observable and outcome_observable

        if full_eval:
            counts["FULL_SESSION_EVALUABLE"] += 1

        max_up = pct(session_high, current_open)
        max_down = pct(session_low, current_open)
        close_pct = pct(session_close, current_open)

        if max_up is not None:
            max_up_sum += max_up
            max_up_count += 1

            if max_up >= 1:
                max_up_ge_1 += 1
            if max_up >= 3:
                max_up_ge_3 += 1
            if max_up >= 5:
                max_up_ge_5 += 1

        if max_down is not None:
            max_down_sum += max_down
            max_down_count += 1

            if max_down <= -1:
                max_down_le_m1 += 1
            if max_down <= -3:
                max_down_le_m3 += 1
            if max_down <= -5:
                max_down_le_m5 += 1

        if close_pct is not None:
            close_sum += close_pct
            close_count += 1

            if close_pct > 0:
                close_positive += 1
            elif close_pct < 0:
                close_negative += 1
            else:
                close_flat += 1

        if not decision_observable:
            eval_status = "DECISION_LIMITED"
        elif not outcome_observable:
            eval_status = "OUTCOME_LIMITED"
        else:
            eval_status = "SESSION_LEVEL_OBSERVABLE"

        if guard_status == "PASS":
            counts["GUARD_PASS"] += 1
        else:
            counts["GUARD_LIMITED"] += 1

        no_trade_preference = (
            not decision_observable
            or critical == "YES"
            or guard_status == "FAIL"
        )

        if no_trade_preference:
            counts["NO_TRADE_PREFERENCE"] += 1

        writer.writerow([
            frow[fi_date],
            frow[fi_code],
            quality,
            feature_status,
            guard_status,
            critical,
            persistence,

            "YES" if decision_observable else "NO",
            decision_freeze,
            decision_reference,

            current_open if current_open is not None else "",
            prev_close if prev_close is not None else "",
            gap_pct if gap_pct is not None else "",

            session_high if session_high is not None else "",
            session_low if session_low is not None else "",
            session_close if session_close is not None else "",

            max_up if max_up is not None else "",
            max_down if max_down is not None else "",
            close_pct if close_pct is not None else "",

            "YES" if outcome_observable else "NO",
            eval_status,

            "NO",
            "NO",
            "NO",
            "NO",

            "NO",
        ])

        if counts["TOTAL"] % 50000 == 0:
            observable = counts["OUTCOME_OBSERVABLE"]
            limited = counts["OUTCOME_LIMITED"]

            print(
                f"PROCESSED={counts['TOTAL']} "
                f"OUTCOME_OBSERVABLE={observable} "
                f"LIMITED={limited}"
            )


avg_max_up = (
    max_up_sum / max_up_count
    if max_up_count else None
)

avg_max_down = (
    max_down_sum / max_down_count
    if max_down_count else None
)

avg_close = (
    close_sum / close_count
    if close_count else None
)


with open(SUMMARY, "w", encoding="utf-8", newline="") as fs:
    w = csv.writer(fs)

    w.writerow(["METRIC", "VALUE"])

    w.writerow(["TOTAL", counts["TOTAL"]])
    w.writerow(["DECISION_OBSERVABLE", counts["DECISION_OBSERVABLE"]])
    w.writerow(["DECISION_LIMITED", counts["DECISION_LIMITED"]])
    w.writerow(["OUTCOME_OBSERVABLE", counts["OUTCOME_OBSERVABLE"]])
    w.writerow(["OUTCOME_LIMITED", counts["OUTCOME_LIMITED"]])
    w.writerow(["FULL_SESSION_EVALUABLE", counts["FULL_SESSION_EVALUABLE"]])

    w.writerow(["GUARD_PASS", counts["GUARD_PASS"]])
    w.writerow(["GUARD_LIMITED", counts["GUARD_LIMITED"]])
    w.writerow(["NO_TRADE_PREFERENCE", counts["NO_TRADE_PREFERENCE"]])

    w.writerow(["KEY_MISMATCH", counts["KEY_MISMATCH"]])
    w.writerow(["INVALID_NUMERIC", counts["INVALID_NUMERIC"]])

    w.writerow(["MAX_UP_COUNT", max_up_count])
    w.writerow(["MAX_UP_AVERAGE_PCT", avg_max_up if avg_max_up is not None else ""])

    w.writerow(["MAX_UP_GE_1PCT", max_up_ge_1])
    w.writerow(["MAX_UP_GE_3PCT", max_up_ge_3])
    w.writerow(["MAX_UP_GE_5PCT", max_up_ge_5])

    w.writerow(["MAX_DOWN_COUNT", max_down_count])
    w.writerow(["MAX_DOWN_AVERAGE_PCT", avg_max_down if avg_max_down is not None else ""])

    w.writerow(["MAX_DOWN_LE_M1PCT", max_down_le_m1])
    w.writerow(["MAX_DOWN_LE_M3PCT", max_down_le_m3])
    w.writerow(["MAX_DOWN_LE_M5PCT", max_down_le_m5])

    w.writerow(["CLOSE_COUNT", close_count])
    w.writerow(["CLOSE_AVERAGE_PCT", avg_close if avg_close is not None else ""])

    w.writerow(["CLOSE_POSITIVE", close_positive])
    w.writerow(["CLOSE_NEGATIVE", close_negative])
    w.writerow(["CLOSE_FLAT", close_flat])

    w.writerow(["REAL_FILL_RECONSTRUCTED", "NO"])
    w.writerow(["STOP_HIT_RECONSTRUCTED", "NO"])
    w.writerow(["REALIZED_PNL_RECONSTRUCTED", "NO"])
    w.writerow(["SLIPPAGE_RECONSTRUCTED", "NO"])

    w.writerow(["FUTURE_DATA_USED_FOR_DECISION", "NO"])


print()
print("========================================")
print("SESSION LEVEL EVALUATION RESULT")
print("========================================")
print("TOTAL                    =", counts["TOTAL"])
print("DECISION OBSERVABLE     =", counts["DECISION_OBSERVABLE"])
print("DECISION LIMITED        =", counts["DECISION_LIMITED"])
print("OUTCOME OBSERVABLE      =", counts["OUTCOME_OBSERVABLE"])
print("OUTCOME LIMITED         =", counts["OUTCOME_LIMITED"])
print("FULL SESSION EVALUABLE  =", counts["FULL_SESSION_EVALUABLE"])
print("GUARD PASS              =", counts["GUARD_PASS"])
print("GUARD LIMITED           =", counts["GUARD_LIMITED"])
print("NO_TRADE PREFERENCE     =", counts["NO_TRADE_PREFERENCE"])
print("KEY MISMATCH             =", counts["KEY_MISMATCH"])
print("========================================")

if counts["KEY_MISMATCH"] == 0:
    print("SESSION_LEVEL_EVALUATION_AUDIT = PASS")
else:
    print("SESSION_LEVEL_EVALUATION_AUDIT = FAIL")

print()
print("OUT =", OUT)
print("SUMMARY =", SUMMARY)
