import csv
import os

BASE = os.path.expanduser("~/jpx_replay")
DATA = os.path.join(BASE, "data")

FEATURE = os.path.join(DATA, "jpx_replay_feature.csv")
TIME_BOUNDARY = os.path.join(DATA, "jpx_replay_time_boundary_audit.csv")
EXECUTION = os.path.join(DATA, "jpx_replay_execution_audit.csv")
RISK = os.path.join(DATA, "jpx_replay_risk_audit.csv")

OUT = os.path.join(DATA, "jpx_replay_thesis_entry_audit.csv")
SUMMARY = os.path.join(DATA, "jpx_replay_thesis_entry_summary.csv")

total = 0
observable = 0
conditional = 0
unverifiable = 0
no_trade = 0
fail = 0

reason_counts = {}

def add_reason(reason):
    reason_counts[reason] = reason_counts.get(reason, 0) + 1

# ============================================================
# Load upstream audit states
# ============================================================

time_status = {}
execution_status = {}
risk_status = {}

with open(TIME_BOUNDARY, "r", encoding="utf-8-sig", newline="") as f:
    r = csv.DictReader(f)

    required = [
        "DATE",
        "CODE",
        "TIME_BOUNDARY_STATUS",
    ]

    missing = [x for x in required if x not in r.fieldnames]
    if missing:
        raise RuntimeError(
            "TIME BOUNDARY FILE COLUMN ERROR: " + ",".join(missing)
        )

    for row in r:
        time_status[(row["DATE"], row["CODE"])] = row["TIME_BOUNDARY_STATUS"]


with open(EXECUTION, "r", encoding="utf-8-sig", newline="") as f:
    r = csv.DictReader(f)

    required = [
        "DATE",
        "CODE",
        "EXECUTION_STATUS",
    ]

    missing = [x for x in required if x not in r.fieldnames]
    if missing:
        raise RuntimeError(
            "EXECUTION FILE COLUMN ERROR: " + ",".join(missing)
        )

    for row in r:
        execution_status[(row["DATE"], row["CODE"])] = row["EXECUTION_STATUS"]


with open(RISK, "r", encoding="utf-8-sig", newline="") as f:
    r = csv.DictReader(f)

    required = [
        "DATE",
        "CODE",
        "RISK_STATUS",
    ]

    missing = [x for x in required if x not in r.fieldnames]
    if missing:
        raise RuntimeError(
            "RISK FILE COLUMN ERROR: " + ",".join(missing)
        )

    for row in r:
        risk_status[(row["DATE"], row["CODE"])] = row["RISK_STATUS"]

# ============================================================
# Thesis / Entry Reconstruction
# ============================================================

with open(FEATURE, "r", encoding="utf-8-sig", newline="") as fin, \
     open(OUT, "w", encoding="utf-8", newline="") as fout:

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

    fields = [
        "DATE",
        "CODE",
        "NAME",
        "DECISION_TIME",

        "FEATURE_STATUS",
        "QUALITY_STATUS",

        "PREV_CLOSE",
        "PREV_HIGH",
        "PREV_LOW",
        "CURRENT_OPEN",
        "GAP",
        "GAP_PCT",
        "OPEN_ABOVE_PREV_HIGH",
        "OPEN_BELOW_PREV_LOW",

        "CATALYST_SOURCE",
        "CATALYST_STATUS",
        "CATALYST_DIRECTION",
        "CATALYST_FRESHNESS",
        "CATALYST_MATERIALITY",
        "PRICED_IN_STATUS",

        "PRICE_OBSERVATION_STATUS",
        "ENTRY_SIGNAL_STATUS",

        "TIME_BOUNDARY_STATUS",
        "EXECUTION_STATUS",
        "RISK_STATUS",

        "THESIS_STATUS",
        "ENTRY_STATUS",
        "NO_TRADE_REASON",

        "THESIS_ENTRY_AUDIT",
    ]

    w = csv.DictWriter(fout, fieldnames=fields)
    w.writeheader()

    for row in r:
        total += 1

        key = (row["DATE"], row["CODE"])

        date = row["DATE"]
        code = row["CODE"]
        name = row["NAME"]
        decision_time = row["DECISION_TIME"].strip()

        feature_status = row["FEATURE_STATUS"].strip()
        quality_status = row["QUALITY_STATUS"].strip()

        tb = time_status.get(key, "UNKNOWN")
        ex = execution_status.get(key, "UNKNOWN")
        rk = risk_status.get(key, "UNKNOWN")

        failures = []
        reasons = []

        # ----------------------------------------------------
        # Hard integrity checks
        # ----------------------------------------------------

        if decision_time != "09:10":
            failures.append("DECISION_TIME_NOT_09_10")

        if tb == "FAIL":
            failures.append("TIME_BOUNDARY_FAIL")

        if ex == "FAIL":
            failures.append("EXECUTION_AUDIT_FAIL")

        if rk == "FAIL":
            failures.append("RISK_AUDIT_FAIL")

        # ----------------------------------------------------
        # Source limitations
        #
        # Catalyst/news/IR is NOT contained in current JPX
        # monthly price dataset.
        # ----------------------------------------------------

        catalyst_source = "NOT_AVAILABLE"
        catalyst_status = "UNKNOWN"
        catalyst_direction = "UNKNOWN"
        catalyst_freshness = "UNKNOWN"
        catalyst_materiality = "UNKNOWN"
        priced_in_status = "UNKNOWN"

        # ----------------------------------------------------
        # Price observation
        #
        # We can observe the relationship between previous
        # session and current open, but this is NOT sufficient
        # to assert a valid entry thesis.
        # ----------------------------------------------------

        if feature_status in ("UNAVAILABLE", "PARTIAL_NO_OPEN"):
            price_observation = "LIMITED"
        else:
            price_observation = "OBSERVABLE"

        # ----------------------------------------------------
        # Entry signal
        #
        # No invented signal.
        # A gap or prior-high relationship alone does not
        # constitute the complete strategy entry condition.
        # ----------------------------------------------------

        entry_signal = "UNVERIFIABLE"

        # ----------------------------------------------------
        # Final classification
        # ----------------------------------------------------

        if failures:
            thesis_status = "FAIL"
            entry_status = "FAIL"
            no_trade_reason = "|".join(failures)
            audit = "FAIL"
            fail += 1

        elif feature_status in ("UNAVAILABLE", "PARTIAL_NO_OPEN"):
            thesis_status = "LIMITED"
            entry_status = "NO_TRADE_PREFERENCE"
            no_trade_reason = "REQUIRED_PRICE_OBSERVATION_UNAVAILABLE"
            audit = "PASS"
            conditional += 1
            no_trade += 1
            add_reason(no_trade_reason)

        else:
            # The price structure is observable.
            # However, catalyst and complete entry conditions
            # are not reconstructable from the current source.
            thesis_status = "UNVERIFIABLE"
            entry_status = "UNVERIFIABLE"
            no_trade_reason = (
                "CATALYST_DATA_UNAVAILABLE|"
                "MARKET_CONTEXT_NOT_RECONSTRUCTED|"
                "ENTRY_SIGNAL_NOT_FULLY_RECONSTRUCTABLE"
            )
            audit = "PASS"

            observable += 1
            unverifiable += 1
            add_reason(no_trade_reason)

        w.writerow({
            "DATE": date,
            "CODE": code,
            "NAME": name,
            "DECISION_TIME": decision_time,

            "FEATURE_STATUS": feature_status,
            "QUALITY_STATUS": quality_status,

            "PREV_CLOSE": row["PREV_CLOSE"],
            "PREV_HIGH": row["PREV_HIGH"],
            "PREV_LOW": row["PREV_LOW"],
            "CURRENT_OPEN": row["CURRENT_OPEN"],
            "GAP": row["GAP"],
            "GAP_PCT": row["GAP_PCT"],
            "OPEN_ABOVE_PREV_HIGH": row["OPEN_ABOVE_PREV_HIGH"],
            "OPEN_BELOW_PREV_LOW": row["OPEN_BELOW_PREV_LOW"],

            "CATALYST_SOURCE": catalyst_source,
            "CATALYST_STATUS": catalyst_status,
            "CATALYST_DIRECTION": catalyst_direction,
            "CATALYST_FRESHNESS": catalyst_freshness,
            "CATALYST_MATERIALITY": catalyst_materiality,
            "PRICED_IN_STATUS": priced_in_status,

            "PRICE_OBSERVATION_STATUS": price_observation,
            "ENTRY_SIGNAL_STATUS": entry_signal,

            "TIME_BOUNDARY_STATUS": tb,
            "EXECUTION_STATUS": ex,
            "RISK_STATUS": rk,

            "THESIS_STATUS": thesis_status,
            "ENTRY_STATUS": entry_status,
            "NO_TRADE_REASON": no_trade_reason,

            "THESIS_ENTRY_AUDIT": audit,
        })

# ============================================================
# Summary
# ============================================================

with open(SUMMARY, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)

    w.writerow(["METRIC", "VALUE"])
    w.writerow(["TOTAL_RECORDS", total])
    w.writerow(["PRICE_OBSERVABLE", observable])
    w.writerow(["CONDITIONAL_LIMITED", conditional])
    w.writerow(["THESIS_UNVERIFIABLE", unverifiable])
    w.writerow(["NO_TRADE_PREFERENCE", no_trade])
    w.writerow(["FAIL", fail])

    if total:
        w.writerow([
            "PRICE_OBSERVABLE_PCT",
            f"{observable / total * 100:.4f}"
        ])
        w.writerow([
            "THESIS_UNVERIFIABLE_PCT",
            f"{unverifiable / total * 100:.4f}"
        ])
        w.writerow([
            "NO_TRADE_PREFERENCE_PCT",
            f"{no_trade / total * 100:.4f}"
        ])
        w.writerow([
            "FAIL_PCT",
            f"{fail / total * 100:.4f}"
        ])

    w.writerow([])
    w.writerow(["DATA_COMPONENT", "STATUS"])
    w.writerow(["PREVIOUS_SESSION_PRICE", "AVAILABLE"])
    w.writerow(["CURRENT_OPEN", "AVAILABLE_WHEN_PRESENT"])
    w.writerow(["CATALYST_NEWS_IR", "NOT_AVAILABLE"])
    w.writerow(["MARKET_CONTEXT", "NOT_RECONSTRUCTED"])
    w.writerow(["09_10_EXACT_PRICE", "NOT_AVAILABLE"])
    w.writerow(["ORDER_BOOK", "NOT_AVAILABLE"])
    w.writerow(["INTRADAY_VOLUME", "NOT_AVAILABLE"])
    w.writerow(["INTRADAY_VWAP", "NOT_AVAILABLE"])

    w.writerow([])
    w.writerow(["RULE", "RESULT"])
    w.writerow(["NO_CATALYST_INVENTION", "ENFORCED"])
    w.writerow(["NO_MARKET_CONTEXT_INVENTION", "ENFORCED"])
    w.writerow(["NO_ENTRY_SIGNAL_INVENTION", "ENFORCED"])
    w.writerow(["GAP_IS_NOT_AUTOMATIC_ENTRY", "ENFORCED"])
    w.writerow(["PREV_HIGH_BREAK_IS_NOT_AUTOMATIC_ENTRY", "ENFORCED"])
    w.writerow(["UNVERIFIABLE_IS_NOT_RULE_FAILURE", "ENFORCED"])
    w.writerow(["INCOMPLETE_THESIS=NO_TRADE_PREFERENCE", "ENFORCED"])
    w.writerow(["POINT_IN_TIME=09:10", "ENFORCED"])

print("")
print("==============================================")
print(" THESIS / ENTRY RECONSTRUCTION ENGINE")
print("==============================================")
print(f"TOTAL RECORDS          : {total:,}")
print(f"PRICE OBSERVABLE      : {observable:,}")
print(f"CONDITIONAL LIMITED   : {conditional:,}")
print(f"THESIS UNVERIFIABLE   : {unverifiable:,}")
print(f"NO_TRADE PREFERENCE    : {no_trade:,}")
print(f"FAIL                   : {fail:,}")
print("----------------------------------------------")
print("CATALYST DATA          : NOT AVAILABLE")
print("MARKET CONTEXT         : NOT RECONSTRUCTED")
print("09:10 EXACT PRICE      : NOT AVAILABLE")
print("----------------------------------------------")
print("OUTPUT:")
print(OUT)
print(SUMMARY)
print("----------------------------------------------")

if fail == 0:
    print("THESIS_ENTRY_RECONSTRUCTION_AUDIT = PASS")
else:
    print("THESIS_ENTRY_RECONSTRUCTION_AUDIT = FAIL")

print("==============================================")
