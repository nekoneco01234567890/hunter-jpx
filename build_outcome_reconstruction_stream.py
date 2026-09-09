import csv
import os
import sys

DATA = os.path.expanduser("~/jpx_replay/data")

FEATURE = os.path.join(DATA, "jpx_replay_feature.csv")
SESSION = os.path.join(DATA, "jpx_replay_session.csv")
GUARD = os.path.join(DATA, "jpx_replay_v15_guard_audit.csv")

OUT = os.path.join(DATA, "jpx_replay_outcome_reconstruction.csv")
SUMMARY = os.path.join(DATA, "jpx_replay_outcome_summary.csv")


def open_csv(path):
    f = open(
        path,
        "r",
        encoding="utf-8-sig",
        newline="",
        buffering=1024 * 1024
    )
    r = csv.reader(f)
    header = next(r)
    return f, r, header


def idx(header, name):
    if name not in header:
        raise RuntimeError(
            f"REQUIRED_COLUMN_MISSING: {name}"
        )
    return header.index(name)


for path in (FEATURE, SESSION, GUARD):
    if not os.path.exists(path):
        print("MISSING:", path)
        sys.exit(1)


print("========================================")
print("Ω∞-DAYTRADE-JP OUTCOME RECONSTRUCTION")
print("MODE=BLIND_DECISION -> OUTCOME")
print("RAM=STREAM")
print("========================================")
print()

ff, fr, fh = open_csv(FEATURE)
sf, sr, sh = open_csv(SESSION)
gf, gr, gh = open_csv(GUARD)

try:
    fi_date = idx(fh, "DATE")
    fi_code = idx(fh, "CODE")
    fi_open = idx(fh, "CURRENT_OPEN")
    fi_open_available = idx(
        fh,
        "CURRENT_OPEN_AVAILABLE"
    )
    fi_prev_close = idx(fh, "PREV_CLOSE")
    fi_gap_pct = idx(fh, "GAP_PCT")

    si_date = idx(sh, "DATE")
    si_code = idx(sh, "CODE")
    si_high = idx(sh, "SESSION_HIGH")
    si_low = idx(sh, "SESSION_LOW")
    si_close = idx(sh, "SESSION_CLOSE")
    si_status = (
        sh.index("QUALITY_STATUS")
        if "QUALITY_STATUS" in sh
        else None
    )

    gi_date = idx(gh, "DATE")
    gi_code = idx(gh, "CODE")
    gi_guard = idx(
        gh,
        "V15_GUARD_STATUS"
    )

    fields = [
        "DATE",
        "CODE",

        "DECISION_TIME",
        "DECISION_DATA_STATUS",

        "ENTRY_REFERENCE_STATUS",
        "ENTRY_REFERENCE",

        "OUTCOME_DATA_STATUS",

        "SESSION_HIGH",
        "SESSION_LOW",
        "SESSION_CLOSE",

        "MFE_REFERENCE",
        "MAE_REFERENCE",

        "MAX_UP_PCT",
        "MAX_DOWN_PCT",
        "CLOSE_PCT_FROM_ENTRY",

        "SESSION_UPSIDE_OBSERVED",
        "SESSION_DOWNSIDE_OBSERVED",

        "STOP_HIT_STATUS",
        "THESIS_INVALIDATION_STATUS",

        "EXIT_RECONSTRUCTION_STATUS",
        "EXIT_REASON",

        "REALIZED_PNL_STATUS",
        "REALIZED_PNL",

        "SLIPPAGE_STATUS",
        "FEE_STATUS",

        "OUTCOME_STATUS",
        "BLIND_DECISION_FROZEN",

        "V15_GUARD_STATUS",
    ]

    with open(
        OUT,
        "w",
        encoding="utf-8",
        newline="",
        buffering=1024 * 1024
    ) as outf:

        writer = csv.DictWriter(
            outf,
            fieldnames=fields
        )
        writer.writeheader()

        counts = {
            "TOTAL": 0,
            "DECISION_OBSERVABLE": 0,
            "DECISION_LIMITED": 0,
            "OUTCOME_OBSERVABLE": 0,
            "OUTCOME_LIMITED": 0,
            "GUARD_PASS": 0,
            "GUARD_LIMITED": 0,
            "KEY_MISMATCH": 0,
        }

        while True:
            try:
                feature = next(fr)
            except StopIteration:
                try:
                    next(sr)
                except StopIteration:
                    pass
                try:
                    next(gr)
                except StopIteration:
                    pass
                break

            try:
                session = next(sr)
            except StopIteration:
                raise RuntimeError(
                    "SESSION_SHORTER_THAN_FEATURE"
                )

            try:
                guard = next(gr)
            except StopIteration:
                raise RuntimeError(
                    "GUARD_SHORTER_THAN_FEATURE"
                )

            fkey = (
                feature[fi_date],
                feature[fi_code]
            )

            skey = (
                session[si_date],
                session[si_code]
            )

            gkey = (
                guard[gi_date],
                guard[gi_code]
            )

            if not (
                fkey == skey
                and fkey == gkey
            ):
                counts["KEY_MISMATCH"] += 1
                raise RuntimeError(
                    "KEY_ALIGNMENT_FAILED "
                    f"FEATURE={fkey} "
                    f"SESSION={skey} "
                    f"GUARD={gkey}"
                )

            date = feature[fi_date]
            code = feature[fi_code]

            open_available = feature[
                fi_open_available
            ]

            open_raw = feature[fi_open]

            prev_close_raw = feature[
                fi_prev_close
            ]

            guard_status = guard[
                gi_guard
            ]

            session_status = (
                session[si_status]
                if si_status is not None
                else "VALID"
            )

            high_raw = session[si_high]
            low_raw = session[si_low]
            close_raw = session[si_close]

            # ---------------------------------------------
            # BLIND DECISION DATA
            # ---------------------------------------------
            if (
                open_available == "TRUE"
                and open_raw != ""
                and prev_close_raw != ""
            ):
                decision_data_status = "OBSERVABLE"
                counts["DECISION_OBSERVABLE"] += 1
            else:
                decision_data_status = "LIMITED"
                counts["DECISION_LIMITED"] += 1

            # ---------------------------------------------
            # ENTRY REFERENCE
            #
            # IMPORTANT:
            # This is NOT a claimed 09:10 fill.
            # It is the current-open reference available
            # in this dataset.
            # ---------------------------------------------
            if decision_data_status == "OBSERVABLE":
                entry_status = (
                    "REFERENCE_ONLY_NOT_EXECUTION"
                )
                entry_reference = open_raw
            else:
                entry_status = "UNAVAILABLE"
                entry_reference = ""

            # ---------------------------------------------
            # OUTCOME DATA
            # ---------------------------------------------
            if (
                high_raw != ""
                and low_raw != ""
                and close_raw != ""
                and session_status in (
                    "VALID",
                    "PARTIAL"
                )
            ):
                outcome_data_status = "OBSERVABLE"
                counts["OUTCOME_OBSERVABLE"] += 1
            else:
                outcome_data_status = "LIMITED"
                counts["OUTCOME_LIMITED"] += 1

            max_up_pct = ""
            max_down_pct = ""
            close_pct = ""

            mfe_reference = "UNAVAILABLE"
            mae_reference = "UNAVAILABLE"

            if (
                decision_data_status == "OBSERVABLE"
                and outcome_data_status == "OBSERVABLE"
            ):
                try:
                    entry = float(open_raw)
                    high = float(high_raw)
                    low = float(low_raw)
                    close = float(close_raw)

                    if entry > 0:
                        max_up_pct = (
                            (high / entry) - 1
                        ) * 100

                        max_down_pct = (
                            (low / entry) - 1
                        ) * 100

                        close_pct = (
                            (close / entry) - 1
                        ) * 100

                        mfe_reference = (
                            "SESSION_HIGH_VS_OPEN"
                        )

                        mae_reference = (
                            "SESSION_LOW_VS_OPEN"
                        )

                except ValueError:
                    pass

            # ---------------------------------------------
            # NO INVENTED STOP / THESIS / EXIT
            # ---------------------------------------------
            stop_hit = "UNVERIFIABLE"
            thesis_invalid = "UNVERIFIABLE"

            exit_status = "UNVERIFIABLE"
            exit_reason = "NO_INTRADAY_EXIT_DATA"

            realized_status = "UNAVAILABLE"
            realized_pnl = ""

            slippage_status = "UNAVAILABLE"
            fee_status = "UNAVAILABLE"

            # ---------------------------------------------
            # SESSION OBSERVATION
            # ---------------------------------------------
            upside = (
                "OBSERVED"
                if max_up_pct != ""
                and float(max_up_pct) > 0
                else "NOT_OBSERVED"
                if max_up_pct != ""
                else "UNKNOWN"
            )

            downside = (
                "OBSERVED"
                if max_down_pct != ""
                and float(max_down_pct) < 0
                else "NOT_OBSERVED"
                if max_down_pct != ""
                else "UNKNOWN"
            )

            # ---------------------------------------------
            # FINAL OUTCOME STATUS
            # ---------------------------------------------
            if (
                decision_data_status == "OBSERVABLE"
                and outcome_data_status == "OBSERVABLE"
            ):
                outcome_status = (
                    "SESSION_LEVEL_OUTCOME_OBSERVABLE"
                )
            else:
                outcome_status = (
                    "SESSION_LEVEL_OUTCOME_LIMITED"
                )

            writer.writerow({
                "DATE": date,
                "CODE": code,

                "DECISION_TIME": "09:10",
                "DECISION_DATA_STATUS":
                    decision_data_status,

                "ENTRY_REFERENCE_STATUS":
                    entry_status,
                "ENTRY_REFERENCE":
                    entry_reference,

                "OUTCOME_DATA_STATUS":
                    outcome_data_status,

                "SESSION_HIGH":
                    high_raw,
                "SESSION_LOW":
                    low_raw,
                "SESSION_CLOSE":
                    close_raw,

                "MFE_REFERENCE":
                    mfe_reference,
                "MAE_REFERENCE":
                    mae_reference,

                "MAX_UP_PCT":
                    max_up_pct,
                "MAX_DOWN_PCT":
                    max_down_pct,
                "CLOSE_PCT_FROM_ENTRY":
                    close_pct,

                "SESSION_UPSIDE_OBSERVED":
                    upside,
                "SESSION_DOWNSIDE_OBSERVED":
                    downside,

                "STOP_HIT_STATUS":
                    stop_hit,
                "THESIS_INVALIDATION_STATUS":
                    thesis_invalid,

                "EXIT_RECONSTRUCTION_STATUS":
                    exit_status,
                "EXIT_REASON":
                    exit_reason,

                "REALIZED_PNL_STATUS":
                    realized_status,
                "REALIZED_PNL":
                    realized_pnl,

                "SLIPPAGE_STATUS":
                    slippage_status,
                "FEE_STATUS":
                    fee_status,

                "OUTCOME_STATUS":
                    outcome_status,

                "BLIND_DECISION_FROZEN":
                    "YES",

                "V15_GUARD_STATUS":
                    guard_status,
            })

            counts["TOTAL"] += 1

            if guard_status == "PASS":
                counts["GUARD_PASS"] += 1
            else:
                counts["GUARD_LIMITED"] += 1

            if counts["TOTAL"] % 50000 == 0:
                print(
                    f"PROCESSED={counts['TOTAL']} "
                    f"OBSERVABLE="
                    f"{counts['OUTCOME_OBSERVABLE']} "
                    f"LIMITED="
                    f"{counts['OUTCOME_LIMITED']}",
                    flush=True
                )

    # ---------------------------------------------
    # SUMMARY
    # ---------------------------------------------
    with open(
        SUMMARY,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        w = csv.writer(f)

        w.writerow(["METRIC", "VALUE"])

        for k in (
            "TOTAL",
            "DECISION_OBSERVABLE",
            "DECISION_LIMITED",
            "OUTCOME_OBSERVABLE",
            "OUTCOME_LIMITED",
            "GUARD_PASS",
            "GUARD_LIMITED",
            "KEY_MISMATCH",
        ):
            w.writerow([k, counts[k]])

        w.writerow([
            "ENTRY_REFERENCE",
            "CURRENT_OPEN_ONLY"
        ])

        w.writerow([
            "REAL_09_10_EXECUTION",
            "NOT_RECONSTRUCTED"
        ])

        w.writerow([
            "STOP_HIT",
            "NOT_RECONSTRUCTED"
        ])

        w.writerow([
            "THESIS_INVALIDATION",
            "NOT_RECONSTRUCTED"
        ])

        w.writerow([
            "REALIZED_PNL",
            "NOT_RECONSTRUCTED"
        ])

        w.writerow([
            "SLIPPAGE",
            "NOT_RECONSTRUCTED"
        ])

        w.writerow([
            "FEE",
            "NOT_RECONSTRUCTED"
        ])

        w.writerow([
            "OUTCOME_METHOD",
            "SESSION_LEVEL_ONLY"
        ])

        w.writerow([
            "LOOKAHEAD_IN_DECISION",
            "FORBIDDEN"
        ])

        w.writerow([
            "FUTURE_DATA_USED_FOR_DECISION",
            "NO"
        ])

finally:
    ff.close()
    sf.close()
    gf.close()


print()
print("========================================")
print("OUTCOME RECONSTRUCTION RESULT")
print("========================================")
print("TOTAL              =", counts["TOTAL"])
print("DECISION OBSERVABLE=", counts["DECISION_OBSERVABLE"])
print("DECISION LIMITED   =", counts["DECISION_LIMITED"])
print("OUTCOME OBSERVABLE =", counts["OUTCOME_OBSERVABLE"])
print("OUTCOME LIMITED    =", counts["OUTCOME_LIMITED"])
print("GUARD PASS         =", counts["GUARD_PASS"])
print("GUARD LIMITED      =", counts["GUARD_LIMITED"])
print("KEY MISMATCH       =", counts["KEY_MISMATCH"])
print("========================================")

if counts["KEY_MISMATCH"] == 0:
    print("OUTCOME_RECONSTRUCTION_AUDIT = PASS")
else:
    print("OUTCOME_RECONSTRUCTION_AUDIT = FAIL")

print()
print("OUT =", OUT)
print("SUMMARY =", SUMMARY)
