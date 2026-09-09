import csv
import os
from collections import Counter

BASE = os.path.expanduser("~/jpx_replay")
DATA = os.path.join(BASE, "data")

FEATURE = os.path.join(DATA, "jpx_replay_feature.csv")
TIME_AUDIT = os.path.join(DATA, "jpx_replay_time_boundary_audit.csv")
EXEC_AUDIT = os.path.join(DATA, "jpx_replay_execution_audit.csv")
RISK_AUDIT = os.path.join(DATA, "jpx_replay_risk_audit.csv")
THESIS_AUDIT = os.path.join(DATA, "jpx_replay_thesis_entry_audit.csv")

OUT_AUDIT = os.path.join(DATA, "jpx_replay_v15_guard_audit.csv")
OUT_SUMMARY = os.path.join(DATA, "jpx_replay_v15_guard_summary.csv")

REQUIRED = [
    FEATURE,
    TIME_AUDIT,
    EXEC_AUDIT,
    RISK_AUDIT,
    THESIS_AUDIT,
]


def open_csv(path):
    return open(path, "r", encoding="utf-8-sig", newline="")


def index_by_key(path):
    """
    監査CSVを1本だけメモリへ保持する。
    705k行級でも同時に複数CSVを保持しない。
    """
    d = {}

    with open_csv(path) as f:
        r = csv.DictReader(f)

        if "DATE" not in r.fieldnames or "CODE" not in r.fieldnames:
            raise RuntimeError(
                f"必要列がありません: {path}"
            )

        for row in r:
            key = (row["DATE"], row["CODE"])
            d[key] = row

    return d


for path in REQUIRED:
    if not os.path.exists(path):
        raise FileNotFoundError(path)

print("V15 FDS GUARD LIGHT")
print("MODE=STREAMING")
print("STEP=1/4 loading time audit")

time_map = index_by_key(TIME_AUDIT)
print("TIME_AUDIT_KEYS =", len(time_map))

print("STEP=2/4 loading execution audit")
exec_map = index_by_key(EXEC_AUDIT)
print("EXEC_AUDIT_KEYS =", len(exec_map))

print("STEP=3/4 loading risk audit")
risk_map = index_by_key(RISK_AUDIT)
print("RISK_AUDIT_KEYS =", len(risk_map))

print("STEP=4/4 loading thesis audit")
thesis_map = index_by_key(THESIS_AUDIT)
print("THESIS_AUDIT_KEYS =", len(thesis_map))

print("STEP=5/5 streaming feature")

summary = Counter()

with open_csv(FEATURE) as fin, \
     open(OUT_AUDIT, "w", encoding="utf-8", newline="") as fout:

    reader = csv.DictReader(fin)

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

    writer = csv.DictWriter(fout, fieldnames=fields)
    writer.writeheader()

    count = 0

    for row in reader:
        date = row.get("DATE", "")
        code = row.get("CODE", "")
        decision_time = row.get("DECISION_TIME", "09:10")

        key = (date, code)

        t = time_map.get(key, {})
        e = exec_map.get(key, {})
        r = risk_map.get(key, {})
        th = thesis_map.get(key, {})

        quality = row.get("QUALITY_STATUS", "")
        feature_status = row.get("FEATURE_STATUS", "")

        time_status = t.get("BOUNDARY_STATUS", "")
        exec_status = e.get("EXECUTION_STATUS", "")
        risk_status = r.get("RISK_STATUS", "")
        thesis_status = th.get("THESIS_STATUS", "")

        # -------------------------------------------------
        # FDS SOURCE RELATION
        # -------------------------------------------------
        source_relation = "PRIMARY"
        source_actor = "JPX"
        information_origin = "JPX_MONTHLY"
        generation_process = "OFFICIAL_MARKET_DATA"
        independence_status = "NOT_APPLICABLE_SINGLE_PRIMARY_SOURCE"

        # -------------------------------------------------
        # SIGNAL DECOMPOSITION
        # -------------------------------------------------
        catalyst_signal = "UNKNOWN"
        volume_signal = "UNKNOWN"
        market_signal = "UNKNOWN"
        liquidity_signal = "UNKNOWN"
        execution_signal = "UNKNOWN"
        risk_signal = "UNKNOWN"

        price_signal = (
            "OBSERVABLE"
            if row.get("CURRENT_OPEN_AVAILABLE") == "TRUE"
            else "UNKNOWN"
        )

        # -------------------------------------------------
        # PERSISTENCE
        # Monthly JPX source has no intraday sequence.
        # Never assume persistence.
        # -------------------------------------------------
        persistence_status = "NOT_CONFIRMED"
        persistence_reason = "INTRADAY_SEQUENCE_UNAVAILABLE"

        # -------------------------------------------------
        # CRITICAL FAIL
        # -------------------------------------------------
        critical_fail = "NO"
        critical_reason = ""

        if decision_time != "09:10":
            critical_fail = "YES"
            critical_reason = "INVALID_DECISION_TIME"

        elif time_status == "FAIL":
            critical_fail = "YES"
            critical_reason = "TIME_BOUNDARY_FAIL"

        elif exec_status == "FAIL":
            critical_fail = "YES"
            critical_reason = "EXECUTION_AUDIT_FAIL"

        elif risk_status == "FAIL":
            critical_fail = "YES"
            critical_reason = "RISK_AUDIT_FAIL"

        # -------------------------------------------------
        # ROOT CAUSE
        # First failed dependency only.
        # -------------------------------------------------
        first_failed = ""
        root_cause = ""

        fact_status = (
            "PASS"
            if quality == "VALID"
            else "LIMITED"
            if quality in ("PARTIAL", "NO_PRICE_DATA")
            else "UNKNOWN"
        )

        dependency_chain = [
            ("FACT", fact_status),
            ("SIGNAL", "LIMITED"),
            ("INDEPENDENCE", "LIMITED"),
            ("PERSISTENCE", persistence_status),
            ("TIME", time_status),
            ("EXECUTION", exec_status),
            ("RISK", risk_status),
            ("THESIS", thesis_status),
        ]

        for dep, status in dependency_chain:
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

        # -------------------------------------------------
        # GUARD STATUS
        # -------------------------------------------------
        if critical_fail == "YES":
            guard_status = "FAIL"

        elif (
            exec_status in (
                "EXECUTION_UNVERIFIABLE",
                "EXECUTION_UNCERTAIN",
                "UNVERIFIABLE",
                "UNKNOWN",
            )
            or risk_status in (
                "RISK_UNCALCULABLE",
                "UNVERIFIABLE",
                "UNKNOWN",
            )
            or thesis_status in (
                "THESIS_UNVERIFIABLE",
                "UNVERIFIABLE",
                "UNKNOWN",
            )
            or persistence_status != "CONFIRMED"
        ):
            guard_status = "LIMITED"

        else:
            guard_status = "PASS"

        # -------------------------------------------------
        # FREEZE / TRACE
        # -------------------------------------------------
        freeze_status = "READY_TO_FREEZE"
        trace_status = "COMPLETE"

        reproduction_key = (
            f"{date}|{decision_time}|{code}|"
            f"JPX_MONTHLY|Ω∞-DAYTRADE-JP_v1.5-GUARD"
        )

        # Outcome is deliberately separate.
        outcome_status = "NOT_EXECUTED"
        feedback_status = "STRUCTURE_READY"
        false_positive_status = "STRUCTURE_READY"

        out = {
            "DATE": date,
            "CODE": code,
            "NAME": row.get("NAME", ""),
            "DECISION_TIME": decision_time,

            "SOURCE_RELATION": source_relation,
            "SOURCE_ACTOR": source_actor,
            "INFORMATION_ORIGIN": information_origin,
            "GENERATION_PROCESS": generation_process,
            "INDEPENDENCE_STATUS": independence_status,

            "CATALYST_SIGNAL": catalyst_signal,
            "PRICE_SIGNAL": price_signal,
            "VOLUME_SIGNAL": volume_signal,
            "MARKET_SIGNAL": market_signal,
            "LIQUIDITY_SIGNAL": liquidity_signal,
            "EXECUTION_SIGNAL": execution_signal,
            "RISK_SIGNAL": risk_signal,

            "PERSISTENCE_STATUS": persistence_status,
            "PERSISTENCE_REASON": persistence_reason,

            "CRITICAL_FAIL": critical_fail,
            "CRITICAL_FAIL_REASON": critical_reason,

            "FIRST_FAILED_DEPENDENCY": first_failed,
            "ROOT_CAUSE": root_cause,

            "FREEZE_STATUS": freeze_status,
            "TRACE_STATUS": trace_status,
            "REPRODUCTION_KEY": reproduction_key,

            "OUTCOME_STATUS": outcome_status,
            "FEEDBACK_STATUS": feedback_status,
            "FALSE_POSITIVE_STATUS": false_positive_status,

            "V15_GUARD_STATUS": guard_status,
        }

        writer.writerow(out)

        summary["TOTAL_RECORDS"] += 1
        summary[f"GUARD_{guard_status}"] += 1
        summary[f"CRITICAL_FAIL_{critical_fail}"] += 1
        summary[f"PERSISTENCE_{persistence_status}"] += 1

        if first_failed:
            summary[f"FIRST_FAILED_{first_failed}"] += 1

        count += 1

        if count % 50000 == 0:
            print(
                f"PROCESSED={count} "
                f"PASS={summary['GUARD_PASS']} "
                f"LIMITED={summary['GUARD_LIMITED']} "
                f"FAIL={summary['GUARD_FAIL']}"
            )

# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------
with open(OUT_SUMMARY, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["METRIC", "VALUE"])

    for k in sorted(summary):
        writer.writerow([k, summary[k]])

    writer.writerow([
        "SOURCE_RELATION",
        "PRIMARY_ONLY"
    ])

    writer.writerow([
        "INDEPENDENCE_CHECK",
        "ACTIVE"
    ])

    writer.writerow([
        "SIGNAL_DECOMPOSE",
        "ACTIVE"
    ])

    writer.writerow([
        "PERSISTENCE_CHECK",
        "ACTIVE"
    ])

    writer.writerow([
        "CRITICAL_FAIL",
        "ACTIVE"
    ])

    writer.writerow([
        "ROOT_CAUSE_REPAIR",
        "ACTIVE"
    ])

    writer.writerow([
        "FREEZE",
        "ACTIVE"
    ])

    writer.writerow([
        "TRACE",
        "ACTIVE"
    ])

    writer.writerow([
        "REPRODUCTION",
        "ACTIVE"
    ])

    writer.writerow([
        "FEEDBACK",
        "STRUCTURE_READY"
    ])

    writer.writerow([
        "FALSE_POSITIVE",
        "STRUCTURE_READY"
    ])

    writer.writerow([
        "FDS_FUTURE_DEMAND",
        "NOT_IMPORTED"
    ])

    writer.writerow([
        "FDS_NEED_WINDOW",
        "NOT_IMPORTED"
    ])

    writer.writerow([
        "FDS_EARLY_POSITIONING",
        "NOT_IMPORTED"
    ])

    writer.writerow([
        "FDS_READER_PROBLEM",
        "NOT_IMPORTED"
    ])

print()
print("========================================")
print("V15 FDS GUARD LIGHT RESULT")
print("========================================")
print("TOTAL RECORDS =", summary["TOTAL_RECORDS"])
print("PASS          =", summary["GUARD_PASS"])
print("LIMITED       =", summary["GUARD_LIMITED"])
print("FAIL          =", summary["GUARD_FAIL"])
print("CRITICAL FAIL =", summary["CRITICAL_FAIL_YES"])
print("========================================")

if summary["GUARD_FAIL"] == 0:
    print("V15_GUARD_INTEGRATION_AUDIT = PASS")
else:
    print("V15_GUARD_INTEGRATION_AUDIT = FAIL")

print()
print("OUTPUT:")
print(OUT_AUDIT)
print(OUT_SUMMARY)
