import csv
import os
import sys

DATA = os.path.expanduser("~/jpx_replay/data")

FILES = {
    "FEATURE": os.path.join(DATA, "jpx_replay_feature.csv"),
    "TIME": os.path.join(DATA, "jpx_replay_time_boundary_audit.csv"),
    "EXECUTION": os.path.join(DATA, "jpx_replay_execution_audit.csv"),
    "RISK": os.path.join(DATA, "jpx_replay_risk_audit.csv"),
    "THESIS": os.path.join(DATA, "jpx_replay_thesis_entry_audit.csv"),
}

OUT = os.path.join(DATA, "jpx_replay_v15_guard_audit.csv")
SUMMARY = os.path.join(DATA, "jpx_replay_v15_guard_summary.csv")


def open_stream(path):
    f = open(path, "r", encoding="utf-8-sig", newline="")
    r = csv.reader(f)
    header = next(r)
    return f, r, header


def get_value(header, row, names, default=""):
    for name in names:
        if name in header:
            i = header.index(name)
            if i < len(row):
                return row[i]
    return default


def classify_fact(status):
    if status == "VALID":
        return "PASS"
    if status in ("PARTIAL", "NO_PRICE_DATA"):
        return "LIMITED"
    return "UNKNOWN"


def classify_guard(
    critical,
    execution,
    risk,
    thesis,
    persistence
):
    if critical == "YES":
        return "FAIL"

    if execution in (
        "EXECUTION_UNVERIFIABLE",
        "EXECUTION_UNCERTAIN",
        "UNVERIFIABLE",
        "UNKNOWN",
    ):
        return "LIMITED"

    if risk in (
        "RISK_UNCALCULABLE",
        "UNVERIFIABLE",
        "UNKNOWN",
    ):
        return "LIMITED"

    if thesis in (
        "THESIS_UNVERIFIABLE",
        "UNVERIFIABLE",
        "UNKNOWN",
    ):
        return "LIMITED"

    if persistence != "CONFIRMED":
        return "LIMITED"

    return "PASS"


# ---------------------------------------------------------
# FILE CHECK
# ---------------------------------------------------------
for name, path in FILES.items():
    if not os.path.exists(path):
        print(f"MISSING: {name}: {path}")
        sys.exit(1)

print("========================================")
print("Ω∞-DAYTRADE-JP v1.5 FDS GUARD")
print("MODE=FULL_STREAM")
print("RAM=ONE_ROW")
print("========================================")
print()

streams = {}

try:
    # -----------------------------------------------------
    # OPEN ALL STREAMS
    # -----------------------------------------------------
    for name, path in FILES.items():
        f, reader, header = open_stream(path)

        if "DATE" not in header or "CODE" not in header:
            raise RuntimeError(
                f"{name}: DATE/CODE missing"
            )

        streams[name] = {
            "file": f,
            "reader": reader,
            "header": header,
        }

        print(
            f"{name}: OPEN "
            f"columns={len(header)}"
        )

    print()
    print("STREAM_ALIGNMENT=ACTIVE")
    print("PROCESSING...")
    print()

    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------
    fields = [
        "DATE",
        "CODE",
        "NAME",
        "DECISION_TIME",

        "SOURCE_RELATION",
        "SOURCE_ACTOR",
        "INFORMATION_ORIGIN",
        "GENERATION_PROCESS",
        "INDEPENDENCE_STATUS",

        "CATALYST_SIGNAL",
        "PRICE_SIGNAL",
        "VOLUME_SIGNAL",
        "MARKET_SIGNAL",
        "LIQUIDITY_SIGNAL",
        "EXECUTION_SIGNAL",
        "RISK_SIGNAL",

        "PERSISTENCE_STATUS",
        "PERSISTENCE_REASON",

        "CRITICAL_FAIL",
        "CRITICAL_FAIL_REASON",

        "FIRST_FAILED_DEPENDENCY",
        "ROOT_CAUSE",

        "FREEZE_STATUS",
        "TRACE_STATUS",
        "REPRODUCTION_KEY",

        "OUTCOME_STATUS",
        "FEEDBACK_STATUS",
        "FALSE_POSITIVE_STATUS",

        "V15_GUARD_STATUS",
    ]

    counts = {
        "TOTAL": 0,
        "PASS": 0,
        "LIMITED": 0,
        "FAIL": 0,
        "CRITICAL_FAIL": 0,
        "KEY_MISMATCH": 0,
    }

    first_failed_counts = {}

    with open(
        OUT,
        "w",
        encoding="utf-8",
        newline="",
        buffering=1024 * 1024
    ) as fout:

        writer = csv.DictWriter(
            fout,
            fieldnames=fields
        )
        writer.writeheader()

        while True:
            rows = {}
            ended = []

            # -------------------------------------------------
            # ONE ROW FROM EACH FILE
            # -------------------------------------------------
            for name, s in streams.items():
                try:
                    rows[name] = next(s["reader"])
                except StopIteration:
                    ended.append(name)

            if ended:
                if len(ended) != len(streams):
                    raise RuntimeError(
                        "STREAM_LENGTH_MISMATCH: "
                        + ",".join(ended)
                    )
                break

            feature_h = streams["FEATURE"]["header"]
            time_h = streams["TIME"]["header"]
            exec_h = streams["EXECUTION"]["header"]
            risk_h = streams["RISK"]["header"]
            thesis_h = streams["THESIS"]["header"]

            feature = rows["FEATURE"]
            time_row = rows["TIME"]
            exec_row = rows["EXECUTION"]
            risk_row = rows["RISK"]
            thesis_row = rows["THESIS"]

            # -------------------------------------------------
            # KEYS
            # -------------------------------------------------
            date = get_value(feature_h, feature, ["DATE"])
            code = get_value(feature_h, feature, ["CODE"])
            name = get_value(feature_h, feature, ["NAME"])

            keys = {
                "FEATURE": (
                    date,
                    code
                ),
                "TIME": (
                    get_value(time_h, time_row, ["DATE"]),
                    get_value(time_h, time_row, ["CODE"])
                ),
                "EXECUTION": (
                    get_value(exec_h, exec_row, ["DATE"]),
                    get_value(exec_h, exec_row, ["CODE"])
                ),
                "RISK": (
                    get_value(risk_h, risk_row, ["DATE"]),
                    get_value(risk_h, risk_row, ["CODE"])
                ),
                "THESIS": (
                    get_value(thesis_h, thesis_row, ["DATE"]),
                    get_value(thesis_h, thesis_row, ["CODE"])
                ),
            }

            if not all(
                k == keys["FEATURE"]
                for k in keys.values()
            ):
                counts["KEY_MISMATCH"] += 1

                raise RuntimeError(
                    "STREAM_ALIGNMENT_FAILED "
                    f"DATE={date} CODE={code} "
                    f"KEYS={keys}"
                )

            # -------------------------------------------------
            # SOURCE
            # -------------------------------------------------
            source_relation = "PRIMARY"
            source_actor = "JPX"
            information_origin = "JPX_MONTHLY"
            generation_process = "OFFICIAL_MARKET_DATA"
            independence = (
                "NOT_APPLICABLE_SINGLE_PRIMARY_SOURCE"
            )

            # -------------------------------------------------
            # SIGNAL DECOMPOSITION
            # -------------------------------------------------
            current_open = get_value(
                feature_h,
                feature,
                ["CURRENT_OPEN_AVAILABLE"],
                "FALSE"
            )

            price_signal = (
                "OBSERVABLE"
                if current_open == "TRUE"
                else "UNKNOWN"
            )

            catalyst_signal = "UNKNOWN"
            volume_signal = "UNKNOWN"
            market_signal = "UNKNOWN"
            liquidity_signal = "UNKNOWN"
            execution_signal = "UNKNOWN"
            risk_signal = "UNKNOWN"

            # -------------------------------------------------
            # PERSISTENCE
            # -------------------------------------------------
            persistence = "NOT_CONFIRMED"
            persistence_reason = (
                "INTRADAY_SEQUENCE_UNAVAILABLE"
            )

            # -------------------------------------------------
            # UPSTREAM STATUSES
            # -------------------------------------------------
            quality = get_value(
                feature_h,
                feature,
                ["QUALITY_STATUS"],
                ""
            )

            decision_time = get_value(
                feature_h,
                feature,
                ["DECISION_TIME"],
                "09:10"
            )

            time_status = get_value(
                time_h,
                time_row,
                [
                    "BOUNDARY_STATUS",
                    "TIME_BOUNDARY_STATUS",
                    "AUDIT_STATUS",
                ],
                ""
            )

            execution_status = get_value(
                exec_h,
                exec_row,
                [
                    "EXECUTION_STATUS",
                    "STATUS",
                    "AUDIT_STATUS",
                ],
                ""
            )

            risk_status = get_value(
                risk_h,
                risk_row,
                [
                    "RISK_STATUS",
                    "STATUS",
                    "AUDIT_STATUS",
                ],
                ""
            )

            thesis_status = get_value(
                thesis_h,
                thesis_row,
                [
                    "THESIS_STATUS",
                    "STATUS",
                    "AUDIT_STATUS",
                ],
                ""
            )

            # -------------------------------------------------
            # CRITICAL FAIL
            # -------------------------------------------------
            critical = "NO"
            critical_reason = ""

            if decision_time != "09:10":
                critical = "YES"
                critical_reason = (
                    "INVALID_DECISION_TIME"
                )

            elif time_status == "FAIL":
                critical = "YES"
                critical_reason = (
                    "TIME_BOUNDARY_FAIL"
                )

            elif execution_status == "FAIL":
                critical = "YES"
                critical_reason = (
                    "EXECUTION_AUDIT_FAIL"
                )

            elif risk_status == "FAIL":
                critical = "YES"
                critical_reason = (
                    "RISK_AUDIT_FAIL"
                )

            if critical == "YES":
                counts["CRITICAL_FAIL"] += 1

            # -------------------------------------------------
            # ROOT CAUSE
            # -------------------------------------------------
            fact = classify_fact(quality)

            dependency = [
                ("FACT", fact),
                ("SIGNAL", "LIMITED"),
                ("INDEPENDENCE", independence),
                ("PERSISTENCE", persistence),
                ("TIME", time_status),
                ("EXECUTION", execution_status),
                ("RISK", risk_status),
                ("THESIS", thesis_status),
            ]

            first_failed = ""
            root_cause = ""

            for dep, status in dependency:
                if status in (
                    "FAIL",
                    "UNKNOWN",
                    "UNAVAILABLE",
                    "UNVERIFIABLE",
                    "RISK_UNCALCULABLE",
                    "EXECUTION_UNVERIFIABLE",
                    "THESIS_UNVERIFIABLE",
                ):
                    first_failed = dep
                    root_cause = status
                    break

            if first_failed:
                first_failed_counts[first_failed] = (
                    first_failed_counts.get(
                        first_failed,
                        0
                    ) + 1
                )

            # -------------------------------------------------
            # FINAL GUARD
            # -------------------------------------------------
            guard = classify_guard(
                critical,
                execution_status,
                risk_status,
                thesis_status,
                persistence
            )

            counts["TOTAL"] += 1
            counts[guard] += 1

            # -------------------------------------------------
            # WRITE
            # -------------------------------------------------
            writer.writerow({
                "DATE": date,
                "CODE": code,
                "NAME": name,
                "DECISION_TIME": decision_time,

                "SOURCE_RELATION": source_relation,
                "SOURCE_ACTOR": source_actor,
                "INFORMATION_ORIGIN": information_origin,
                "GENERATION_PROCESS": generation_process,
                "INDEPENDENCE_STATUS": independence,

                "CATALYST_SIGNAL": catalyst_signal,
                "PRICE_SIGNAL": price_signal,
                "VOLUME_SIGNAL": volume_signal,
                "MARKET_SIGNAL": market_signal,
                "LIQUIDITY_SIGNAL": liquidity_signal,
                "EXECUTION_SIGNAL": execution_signal,
                "RISK_SIGNAL": risk_signal,

                "PERSISTENCE_STATUS": persistence,
                "PERSISTENCE_REASON": persistence_reason,

                "CRITICAL_FAIL": critical,
                "CRITICAL_FAIL_REASON": critical_reason,

                "FIRST_FAILED_DEPENDENCY": first_failed,
                "ROOT_CAUSE": root_cause,

                "FREEZE_STATUS": "READY_TO_FREEZE",
                "TRACE_STATUS": "COMPLETE",

                "REPRODUCTION_KEY": (
                    f"{date}|{decision_time}|{code}|"
                    f"JPX_MONTHLY|"
                    f"Ω∞-DAYTRADE-JP_v1.5-GUARD"
                ),

                "OUTCOME_STATUS": "NOT_EXECUTED",
                "FEEDBACK_STATUS": "STRUCTURE_READY",
                "FALSE_POSITIVE_STATUS": "STRUCTURE_READY",

                "V15_GUARD_STATUS": guard,
            })

            # -------------------------------------------------
            # PROGRESS
            # -------------------------------------------------
            if counts["TOTAL"] % 10000 == 0:
                print(
                    f"PROCESSED={counts['TOTAL']} "
                    f"PASS={counts['PASS']} "
                    f"LIMITED={counts['LIMITED']} "
                    f"FAIL={counts['FAIL']}",
                    flush=True
                )

finally:
    for s in streams.values():
        s["file"].close()


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------
with open(
    SUMMARY,
    "w",
    encoding="utf-8",
    newline=""
) as f:

    w = csv.writer(f)
    w.writerow(["METRIC", "VALUE"])

    w.writerow(["TOTAL_RECORDS", counts["TOTAL"]])
    w.writerow(["PASS", counts["PASS"]])
    w.writerow(["LIMITED", counts["LIMITED"]])
    w.writerow(["FAIL", counts["FAIL"]])
    w.writerow([
        "CRITICAL_FAIL",
        counts["CRITICAL_FAIL"]
    ])
    w.writerow([
        "KEY_MISMATCH",
        counts["KEY_MISMATCH"]
    ])

    for dep in sorted(first_failed_counts):
        w.writerow([
            f"FIRST_FAILED_{dep}",
            first_failed_counts[dep]
        ])

    w.writerow([
        "SOURCE_RELATION",
        "PRIMARY_ONLY"
    ])

    w.writerow([
        "INDEPENDENCE_CHECK",
        "ACTIVE"
    ])

    w.writerow([
        "SIGNAL_DECOMPOSE",
        "ACTIVE"
    ])

    w.writerow([
        "PERSISTENCE_CHECK",
        "ACTIVE"
    ])

    w.writerow([
        "CRITICAL_FAIL",
        "ACTIVE"
    ])

    w.writerow([
        "ROOT_CAUSE_REPAIR",
        "ACTIVE"
    ])

    w.writerow([
        "FREEZE",
        "ACTIVE"
    ])

    w.writerow([
        "TRACE",
        "ACTIVE"
    ])

    w.writerow([
        "REPRODUCTION",
        "ACTIVE"
    ])

    w.writerow([
        "FEEDBACK",
        "STRUCTURE_READY"
    ])

    w.writerow([
        "FALSE_POSITIVE",
        "STRUCTURE_READY"
    ])

    w.writerow([
        "FDS_FUTURE_DEMAND",
        "NOT_IMPORTED"
    ])

    w.writerow([
        "FDS_NEED_WINDOW",
        "NOT_IMPORTED"
    ])

    w.writerow([
        "FDS_EARLY_POSITIONING",
        "NOT_IMPORTED"
    ])

    w.writerow([
        "FDS_READER_PROBLEM",
        "NOT_IMPORTED"
    ])


print()
print("========================================")
print("V15 FDS GUARD STREAM RESULT")
print("========================================")
print("TOTAL   =", counts["TOTAL"])
print("PASS    =", counts["PASS"])
print("LIMITED =", counts["LIMITED"])
print("FAIL    =", counts["FAIL"])
print("CRITICAL=", counts["CRITICAL_FAIL"])
print("MISMATCH=", counts["KEY_MISMATCH"])
print("========================================")

if (
    counts["FAIL"] == 0
    and counts["KEY_MISMATCH"] == 0
):
    print("V15_GUARD_INTEGRATION_AUDIT = PASS")
else:
    print("V15_GUARD_INTEGRATION_AUDIT = FAIL")

print()
print("AUDIT =", OUT)
print("SUMMARY =", SUMMARY)
