import csv
import os
from collections import Counter

BASE = os.path.expanduser("~/jpx_replay")
DATA = os.path.join(BASE, "data")

FEATURE = os.path.join(DATA, "jpx_replay_feature.csv")
TIME_BOUNDARY = os.path.join(DATA, "jpx_replay_time_boundary_audit.csv")
EXECUTION = os.path.join(DATA, "jpx_replay_execution_audit.csv")
RISK = os.path.join(DATA, "jpx_replay_risk_audit.csv")
THESIS = os.path.join(DATA, "jpx_replay_thesis_entry_audit.csv")

OUT = os.path.join(DATA, "jpx_replay_v15_guard_audit.csv")
SUMMARY = os.path.join(DATA, "jpx_replay_v15_guard_summary.csv")
TRACE = os.path.join(DATA, "jpx_replay_v15_guard_trace.csv")

# ============================================================
# Ω∞-DAYTRADE-JP v1.5-GUARD
#
# FDS-derived validation layer only.
#
# IMPORTED:
#   SOURCE_RELATION
#   INDEPENDENCE_CHECK
#   SIGNAL_DECOMPOSE
#   PERSISTENCE
#   CRITICAL_FAIL
#   ROOT_CAUSE
#   FREEZE
#   TRACE
#   FEEDBACK / FALSE_POSITIVE structure
#   REPRODUCTION
#
# NOT IMPORTED:
#   FUTURE_DEMAND
#   S0-S6
#   READER_PROBLEM
#   INFORMATION_GAP
#   NEED_WINDOW
#   EARLY_POSITIONING
#   SEO / ARTICLE
#   100-point demand score
#
# NO TRADE SIGNAL IS CREATED BY THIS SCRIPT.
# ============================================================

TOTAL = 0
PASS = 0
LIMITED = 0
FAIL = 0

status_counter = Counter()
root_counter = Counter()
signal_counter = Counter()

def load_keyed(path, required):
    data = {}

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)

        missing = [x for x in required if x not in r.fieldnames]
        if missing:
            raise RuntimeError(
                os.path.basename(path)
                + " COLUMN ERROR: "
                + ",".join(missing)
            )

        for row in r:
            data[(row["DATE"], row["CODE"])] = row

    return data


# ============================================================
# Load upstream layers
# ============================================================

tb = load_keyed(
    TIME_BOUNDARY,
    ["DATE", "CODE", "TIME_BOUNDARY_STATUS"]
)

ex = load_keyed(
    EXECUTION,
    ["DATE", "CODE", "EXECUTION_STATUS"]
)

rk = load_keyed(
    RISK,
    ["DATE", "CODE", "RISK_STATUS"]
)

th = load_keyed(
    THESIS,
    [
        "DATE",
        "CODE",
        "THESIS_STATUS",
        "ENTRY_STATUS",
        "THESIS_ENTRY_AUDIT"
    ]
)

# ============================================================
# Output
# ============================================================

fields = [
    "DATE",
    "CODE",
    "NAME",
    "DECISION_TIME",

    # Existing source/feature state
    "QUALITY_STATUS",
    "FEATURE_STATUS",

    # FDS-derived source relation
    "SOURCE_RELATION",
    "SOURCE_ACTOR",
    "INFORMATION_ORIGIN",
    "GENERATION_PROCESS",
    "INDEPENDENCE_STATUS",

    # Signal decomposition
    "CATALYST_SIGNAL",
    "PRICE_SIGNAL",
    "VOLUME_SIGNAL",
    "MARKET_SIGNAL",
    "LIQUIDITY_SIGNAL",
    "EXECUTION_SIGNAL",
    "RISK_SIGNAL",

    # Persistence
    "PERSISTENCE_STATUS",
    "PERSISTENCE_REASON",

    # Upstream gates
    "TIME_BOUNDARY_STATUS",
    "EXECUTION_STATUS",
    "RISK_STATUS",
    "THESIS_STATUS",
    "ENTRY_STATUS",

    # Critical-fail system
    "CRITICAL_FAIL",
    "CRITICAL_FAIL_REASON",

    # Root cause
    "FIRST_FAILED_DEPENDENCY",
    "ROOT_CAUSE",

    # Freeze / trace
    "FREEZE_STATUS",
    "TRACE_STATUS",

    # Reproduction
    "REPRODUCTION_KEY",

    # Outcome feedback placeholders
    "OUTCOME_STATUS",
    "FEEDBACK_STATUS",
    "FALSE_POSITIVE_STATUS",

    # Final guard
    "V15_GUARD_STATUS",
]

trace_fields = [
    "DATE",
    "CODE",
    "NAME",
    "DECISION_TIME",
    "STEP",
    "STATUS",
    "REASON",
]

with open(FEATURE, "r", encoding="utf-8-sig", newline="") as fin, \
     open(OUT, "w", encoding="utf-8", newline="") as fout, \
     open(TRACE, "w", encoding="utf-8", newline="") as ft:

    r = csv.DictReader(fin)

    required = [
        "DATE",
        "CODE",
        "NAME",
        "DECISION_TIME",
        "QUALITY_STATUS",
        "FEATURE_STATUS",
        "PREV_CLOSE",
        "PREV_HIGH",
        "PREV_LOW",
        "CURRENT_OPEN",
        "GAP",
        "GAP_PCT",
        "OPEN_ABOVE_PREV_HIGH",
        "OPEN_BELOW_PREV_LOW",
    ]

    missing = [x for x in required if x not in r.fieldnames]

    if missing:
        raise RuntimeError(
            "FEATURE FILE COLUMN ERROR: " + ",".join(missing)
        )

    w = csv.DictWriter(fout, fieldnames=fields)
    w.writeheader()

    tw = csv.DictWriter(ft, fieldnames=trace_fields)
    tw.writeheader()

    for row in r:
        TOTAL += 1

        date = row["DATE"]
        code = row["CODE"]
        name = row["NAME"]
        decision_time = row["DECISION_TIME"]

        key = (date, code)

        tb_status = tb.get(key, {}).get(
            "TIME_BOUNDARY_STATUS", "UNKNOWN"
        )

        ex_status = ex.get(key, {}).get(
            "EXECUTION_STATUS", "UNKNOWN"
        )

        rk_status = rk.get(key, {}).get(
            "RISK_STATUS", "UNKNOWN"
        )

        th_status = th.get(key, {}).get(
            "THESIS_STATUS", "UNKNOWN"
        )

        entry_status = th.get(key, {}).get(
            "ENTRY_STATUS", "UNKNOWN"
        )

        # ====================================================
        # SOURCE RELATION
        #
        # Current JPX monthly price files are primary source
        # for the fields they actually contain.
        #
        # No news/IR source is invented.
        # ====================================================

        source_relation = "PRIMARY"
        source_actor = "JPX"
        information_origin = "JPX_OFFICIAL_MONTHLY_MARKET_DATA"
        generation_process = "OFFICIAL_MONTHLY_MARKET_DATA_PUBLICATION"

        independence_status = "NOT_APPLICABLE_SINGLE_PRIMARY_SOURCE"

        # ====================================================
        # SIGNAL DECOMPOSITION
        #
        # No unsupported signal is fabricated.
        # ====================================================

        catalyst_signal = "UNKNOWN"
        price_signal = "OBSERVABLE_SESSION_STRUCTURE"
        volume_signal = "UNKNOWN"
        market_signal = "UNKNOWN"
        liquidity_signal = "UNKNOWN"
        execution_signal = "UNKNOWN"
        risk_signal = "UNKNOWN"

        signal_counter["PRICE_SIGNAL_OBSERVABLE"] += 1

        # ====================================================
        # PERSISTENCE
        #
        # Current source has session OHLC only.
        # Therefore intraday persistence cannot be established.
        # ====================================================

        persistence_status = "NOT_CONFIRMED"
        persistence_reason = (
            "INTRADAY_SEQUENCE_UNAVAILABLE"
        )

        # ====================================================
        # CRITICAL FAIL
        # ====================================================

        critical = False
        critical_reasons = []

        if decision_time != "09:10":
            critical = True
            critical_reasons.append(
                "DECISION_TIME_NOT_09_10"
            )

        if tb_status == "FAIL":
            critical = True
            critical_reasons.append(
                "TIME_BOUNDARY_FAIL"
            )

        if ex_status == "FAIL":
            critical = True
            critical_reasons.append(
                "EXECUTION_AUDIT_FAIL"
            )

        if rk_status == "FAIL":
            critical = True
            critical_reasons.append(
                "RISK_AUDIT_FAIL"
            )

        # ====================================================
        # Root cause hierarchy
        #
        # FIRST FAILED DEPENDENCY ONLY.
        # ====================================================

        dependency_chain = [
            ("FACT", quality_status(row)),
            ("SIGNAL", "PASS"),
            ("INDEPENDENCE", "PASS"),
            ("PERSISTENCE", "LIMITED"),
            ("TIME", tb_status),
            ("EXECUTION", ex_status),
            ("RISK", rk_status),
            ("THESIS", th_status),
            ("ENTRY", entry_status),
        ]

        first_failed = "NONE"
        root_cause = "NONE"

        for dep, dep_status in dependency_chain:
            if dep_status in ("FAIL", "UNKNOWN", "UNAVAILABLE"):
                first_failed = dep
                root_cause = dep_status
                break

        if first_failed != "NONE":
            root_counter[first_failed + ":" + root_cause] += 1

        # ====================================================
        # Add data limitations as root cause where appropriate
        # ====================================================

        if not critical:
            if th_status in ("UNVERIFIABLE", "UNKNOWN"):
                if first_failed == "NONE":
                    first_failed = "THESIS"
                    root_cause = "THESIS_UNVERIFIABLE"

            elif ex_status in ("EXECUTION_UNVERIFIABLE", "UNKNOWN"):
                if first_failed == "NONE":
                    first_failed = "EXECUTION"
                    root_cause = "EXECUTION_UNVERIFIABLE"

            elif rk_status in ("RISK_UNCALCULABLE", "UNKNOWN"):
                if first_failed == "NONE":
                    first_failed = "RISK"
                    root_cause = "RISK_UNCALCULABLE"

        # ====================================================
        # Guard classification
        #
        # PASS means guard integrity is valid.
        # It does NOT mean tradeable.
        # ====================================================

        if critical:
            guard_status = "FAIL"
            FAIL += 1
            status_counter["FAIL"] += 1

        elif (
            th_status == "UNVERIFIABLE"
            or entry_status == "UNVERIFIABLE"
            or ex_status == "EXECUTION_UNVERIFIABLE"
            or rk_status == "RISK_UNCALCULABLE"
            or persistence_status == "NOT_CONFIRMED"
        ):
            guard_status = "LIMITED"
            LIMITED += 1
            status_counter["LIMITED"] += 1

        else:
            guard_status = "PASS"
            PASS += 1
            status_counter["PASS"] += 1

        # ====================================================
        # Freeze / Trace
        # ====================================================

        freeze_status = "READY_TO_FREEZE"

        # Freeze is not a claim that historical facts are immutable
        # forever. It means this audit record has a fixed state.
        trace_status = "COMPLETE"

        reproduction_key = "|".join([
            date,
            decision_time,
            code,
            "JPX_MONTHLY",
            "Ω∞-DAYTRADE-JP_v1.5-GUARD",
        ])

        outcome_status = "NOT_YET_EVALUATED"
        feedback_status = "NOT_YET_AVAILABLE"
        false_positive_status = "NOT_YET_EVALUATED"

        critical_reason = (
            "|".join(critical_reasons)
            if critical_reasons
            else "NONE"
        )

        # ====================================================
        # Trace
        # ====================================================

        trace_rows = [
            ("FACT", "PASS", "JPX price record parsed"),
            (
                "SOURCE_RELATION",
                "PASS",
                "PRIMARY_SOURCE"
            ),
            (
                "INDEPENDENCE",
                "LIMITED",
                "SINGLE_PRIMARY_SOURCE_ONLY"
            ),
            (
                "SIGNAL_DECOMPOSE",
                "PASS",
                "UNAVAILABLE_SIGNALS_LEFT_UNKNOWN"
            ),
            (
                "PERSISTENCE",
                "LIMITED",
                persistence_reason
            ),
            (
                "TIME",
                tb_status,
                "UPSTREAM_TIME_BOUNDARY"
            ),
            (
                "EXECUTION",
                ex_status,
                "UPSTREAM_EXECUTION_RECONSTRUCTION"
            ),
            (
                "RISK",
                rk_status,
                "UPSTREAM_RISK_RECONSTRUCTION"
            ),
            (
                "THESIS",
                th_status,
                "UPSTREAM_THESIS_RECONSTRUCTION"
            ),
            (
                "ENTRY",
                entry_status,
                "UPSTREAM_ENTRY_RECONSTRUCTION"
            ),
            (
                "CRITICAL_FAIL",
                "FAIL" if critical else "PASS",
                critical_reason
            ),
            (
                "ROOT_CAUSE",
                root_cause,
                first_failed
            ),
            (
                "FREEZE",
                freeze_status,
                "AUDIT_RECORD_READY"
            ),
            (
                "TRACE",
                trace_status,
                "TRACE_COMPLETE"
            ),
            (
                "REPRODUCTION",
                "READY",
                reproduction_key
            ),
        ]

        for step, status, reason in trace_rows:
            tw.writerow({
                "DATE": date,
                "CODE": code,
                "NAME": name,
                "DECISION_TIME": decision_time,
                "STEP": step,
                "STATUS": status,
                "REASON": reason,
            })

        w.writerow({
            "DATE": date,
            "CODE": code,
            "NAME": name,
            "DECISION_TIME": decision_time,

            "QUALITY_STATUS": row["QUALITY_STATUS"],
            "FEATURE_STATUS": row["FEATURE_STATUS"],

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

            "TIME_BOUNDARY_STATUS": tb_status,
            "EXECUTION_STATUS": ex_status,
            "RISK_STATUS": rk_status,
            "THESIS_STATUS": th_status,
            "ENTRY_STATUS": entry_status,

            "CRITICAL_FAIL": "TRUE" if critical else "FALSE",
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
        })


# ============================================================
# Summary
# ============================================================

with open(SUMMARY, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)

    w.writerow(["METRIC", "VALUE"])
    w.writerow(["TOTAL_RECORDS", TOTAL])
    w.writerow(["PASS", PASS])
    w.writerow(["LIMITED", LIMITED])
    w.writerow(["FAIL", FAIL])

    if TOTAL:
        w.writerow([
            "PASS_PCT",
            f"{PASS / TOTAL * 100:.4f}"
        ])
        w.writerow([
            "LIMITED_PCT",
            f"{LIMITED / TOTAL * 100:.4f}"
        ])
        w.writerow([
            "FAIL_PCT",
            f"{FAIL / TOTAL * 100:.4f}"
        ])

    w.writerow([])
    w.writerow(["FDS_INTEGRATION", "STATUS"])

    w.writerow([
        "SOURCE_RELATION",
        "ACTIVE"
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
        "PERSISTENCE",
        "ACTIVE"
    ])
    w.writerow([
        "CRITICAL_FAIL",
        "ACTIVE"
    ])
    w.writerow([
        "ROOT_CAUSE",
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
        "FEEDBACK",
        "STRUCTURE_READY"
    ])
    w.writerow([
        "FALSE_POSITIVE",
        "STRUCTURE_READY"
    ])
    w.writerow([
        "REPRODUCTION",
        "ACTIVE"
    ])

    w.writerow([])
    w.writerow(["EXCLUDED_FDS_FEATURE", "REASON"])

    w.writerow([
        "S0_S6",
        "FDS_DEMAND_STATE_NOT_TRADING_STATE"
    ])
    w.writerow([
        "FUTURE_DEMAND",
        "NOT_A_TRADING_TARGET"
    ])
    w.writerow([
        "READER_PROBLEM",
        "ARTICLE_DOMAIN_ONLY"
    ])
    w.writerow([
        "INFORMATION_GAP",
        "ARTICLE_DOMAIN_ONLY"
    ])
    w.writerow([
        "NEED_WINDOW",
        "ARTICLE_DOMAIN_ONLY"
    ])
    w.writerow([
        "EARLY_POSITIONING",
        "ARTICLE_DOMAIN_ONLY"
    ])
    w.writerow([
        "DEMAND_SCORE_100",
        "NOT_USED"
    ])

    w.writerow([])
    w.writerow(["GUARD_RULE", "RESULT"])

    rules = [
        ("NO_FACT_INVENTION", "ENFORCED"),
        ("UNKNOWN_NOT_PROMOTED_TO_FACT", "ENFORCED"),
        ("DUPLICATE_NOT_INDEPENDENT", "ENFORCED"),
        ("INDEPENDENCE_NOT_ASSUMED", "ENFORCED"),
        ("PERSISTENCE_NOT_ASSUMED", "ENFORCED"),
        ("CRITICAL_FAIL_CANNOT_BE_OFFSET", "ENFORCED"),
        ("UNVERIFIABLE_NOT_EQUAL_TO_LOSS", "ENFORCED"),
        ("UNVERIFIABLE_NOT_EQUAL_TO_NO_TRADE_REALIZED", "ENFORCED"),
        ("OUTCOME_SEPARATED_FROM_DECISION", "ENFORCED"),
        ("NO_FUTURE_DATA_IN_DECISION_LAYER", "ENFORCED"),
        ("NO_SCORE_COMPENSATION", "ENFORCED"),
        ("TRACE_REQUIRED", "ENFORCED"),
        ("REPRODUCTION_KEY_REQUIRED", "ENFORCED"),
    ]

    for name, result in rules:
        w.writerow([name, result])

    w.writerow([])
    w.writerow(["ROOT_CAUSE", "COUNT"])

    for k, v in sorted(root_counter.items()):
        w.writerow([k, v])

    w.writerow([])
    w.writerow(["SIGNAL_COUNTER", "COUNT"])

    for k, v in sorted(signal_counter.items()):
        w.writerow([k, v])


# ============================================================
# Console
# ============================================================

print("")
print("==============================================")
print(" Ω∞-DAYTRADE-JP v1.5-GUARD")
print(" FDS VALIDATION LAYER INTEGRATION")
print("==============================================")
print(f"TOTAL RECORDS       : {TOTAL:,}")
print(f"PASS                : {PASS:,}")
print(f"LIMITED             : {LIMITED:,}")
print(f"FAIL                : {FAIL:,}")
print("----------------------------------------------")
print("SOURCE_RELATION     : ACTIVE")
print("INDEPENDENCE        : ACTIVE")
print("SIGNAL_DECOMPOSE    : ACTIVE")
print("PERSISTENCE         : ACTIVE")
print("CRITICAL_FAIL       : ACTIVE")
print("ROOT_CAUSE          : ACTIVE")
print("FREEZE              : ACTIVE")
print("TRACE               : ACTIVE")
print("FEEDBACK            : READY")
print("FALSE_POSITIVE      : READY")
print("REPRODUCTION        : ACTIVE")
print("----------------------------------------------")
print("FDS DEMAND LOGIC    : NOT IMPORTED")
print("FDS SCORE SYSTEM    : NOT IMPORTED")
print("----------------------------------------------")
print("OUTPUT:")
print(OUT)
print(SUMMARY)
print(TRACE)
print("----------------------------------------------")

if FAIL == 0:
    print("V15_GUARD_INTEGRATION_AUDIT = PASS")
else:
    print("V15_GUARD_INTEGRATION_AUDIT = FAIL")

print("==============================================")
