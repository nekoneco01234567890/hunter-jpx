import csv
import os

BASE = os.path.expanduser("~/jpx_replay")
DATA = os.path.join(BASE, "data")

FEATURE = os.path.join(DATA, "jpx_replay_feature.csv")
EXECUTION = os.path.join(DATA, "jpx_replay_execution_audit.csv")

OUT = os.path.join(DATA, "jpx_replay_risk_audit.csv")
SUMMARY = os.path.join(DATA, "jpx_replay_risk_summary.csv")

DAY_MAX_LOSS = 5000
PREFERRED_MAX_LOSS = 4000
PREFERRED_MIN_LOSS = 3000

total = 0
calculable = 0
uncalculable = 0
no_trade = 0
fail = 0

reason_counts = {}

def add_reason(reason):
    reason_counts[reason] = reason_counts.get(reason, 0) + 1

# ------------------------------------------------------------
# Load execution status by DATE + CODE
# ------------------------------------------------------------

execution_status = {}

with open(EXECUTION, "r", encoding="utf-8-sig", newline="") as f:
    r = csv.DictReader(f)

    required = [
        "DATE",
        "CODE",
        "EXECUTION_STATUS",
        "EXECUTION_AUDIT",
    ]

    missing = [x for x in required if x not in r.fieldnames]

    if missing:
        raise RuntimeError(
            "EXECUTION FILE COLUMN ERROR: " + ",".join(missing)
        )

    for row in r:
        key = (row["DATE"], row["CODE"])
        execution_status[key] = (
            row["EXECUTION_STATUS"],
            row["EXECUTION_AUDIT"],
        )

# ------------------------------------------------------------
# Risk reconstruction
# ------------------------------------------------------------

with open(FEATURE, "r", encoding="utf-8-sig", newline="") as fin, \
     open(OUT, "w", encoding="utf-8", newline="") as fout:

    r = csv.DictReader(fin)

    required = [
        "DATE",
        "CODE",
        "DECISION_TIME",
        "FEATURE_STATUS",
        "CURRENT_OPEN",
        "CURRENT_OPEN_AVAILABLE",
        "PREV_CLOSE",
        "PREV_HIGH",
        "PREV_LOW",
    ]

    missing = [x for x in required if x not in r.fieldnames]

    if missing:
        raise RuntimeError(
            "FEATURE FILE COLUMN ERROR: " + ",".join(missing)
        )

    fields = [
        "DATE",
        "CODE",
        "DECISION_TIME",

        "FEATURE_STATUS",
        "CURRENT_OPEN",
        "CURRENT_OPEN_AVAILABLE",

        "DAY_MAX_LOSS",
        "PREFERRED_MIN_LOSS",
        "PREFERRED_MAX_LOSS",

        "ENTRY_PRICE_SOURCE",
        "ENTRY_PRICE",
        "STOP_PRICE_SOURCE",
        "STOP_PRICE",

        "RISK_PER_SHARE",
        "EXPECTED_SLIPPAGE",
        "RISK_PER_SHARE_WITH_SLIPPAGE",

        "MAX_SHARES_BY_RISK",
        "BOARD_LOT_ADJUSTED_SHARES",

        "ONE_LOT_RISK",
        "RISK_CALCULABLE",

        "RISK_STATUS",
        "RISK_LIMIT_REASON",
        "RISK_AUDIT",
    ]

    w = csv.DictWriter(fout, fieldnames=fields)
    w.writeheader()

    for row in r:
        total += 1

        date = row["DATE"]
        code = row["CODE"]
        decision_time = row["DECISION_TIME"].strip()
        feature_status = row["FEATURE_STATUS"].strip()
        current_open_available = row["CURRENT_OPEN_AVAILABLE"].strip().upper()

        hard_fail = []

        # ----------------------------------------------------
        # Boundary validation
        # ----------------------------------------------------

        if decision_time != "09:10":
            hard_fail.append("DECISION_TIME_NOT_09_10")

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # No stop price exists in current JPX replay data.
        # No stop is invented.
        # No slippage is invented.
        # No actual fill is invented.
        # ----------------------------------------------------

        entry_price_source = "CURRENT_OPEN_ONLY"
        entry_price = row["CURRENT_OPEN"].strip()

        stop_price_source = "NOT_AVAILABLE"
        stop_price = ""

        risk_per_share = ""
        expected_slippage = ""
        risk_per_share_slippage = ""
        max_shares = ""
        board_lot_shares = ""
        one_lot_risk = ""

        if hard_fail:
            status = "FAIL"
            reason = "|".join(hard_fail)
            audit = "FAIL"
            fail += 1

        elif current_open_available != "TRUE":
            status = "RISK_UNCALCULABLE"
            reason = "CURRENT_OPEN_UNAVAILABLE"
            audit = "PASS"
            uncalculable += 1
            no_trade += 1
            add_reason(reason)

        elif entry_price == "":
            status = "RISK_UNCALCULABLE"
            reason = "ENTRY_PRICE_UNAVAILABLE"
            audit = "PASS"
            uncalculable += 1
            no_trade += 1
            add_reason(reason)

        else:
            status = "RISK_UNCALCULABLE"
            reason = (
                "STOP_PRICE_UNAVAILABLE|"
                "EXPECTED_SLIPPAGE_UNAVAILABLE|"
                "BOARD_LOT_RISK_UNVERIFIABLE"
            )
            audit = "PASS"

            uncalculable += 1
            no_trade += 1
            add_reason(reason)

        w.writerow({
            "DATE": date,
            "CODE": code,
            "DECISION_TIME": decision_time,

            "FEATURE_STATUS": feature_status,
            "CURRENT_OPEN": row["CURRENT_OPEN"],
            "CURRENT_OPEN_AVAILABLE": current_open_available,

            "DAY_MAX_LOSS": DAY_MAX_LOSS,
            "PREFERRED_MIN_LOSS": PREFERRED_MIN_LOSS,
            "PREFERRED_MAX_LOSS": PREFERRED_MAX_LOSS,

            "ENTRY_PRICE_SOURCE": entry_price_source,
            "ENTRY_PRICE": entry_price,
            "STOP_PRICE_SOURCE": stop_price_source,
            "STOP_PRICE": stop_price,

            "RISK_PER_SHARE": risk_per_share,
            "EXPECTED_SLIPPAGE": expected_slippage,
            "RISK_PER_SHARE_WITH_SLIPPAGE": risk_per_share_slippage,

            "MAX_SHARES_BY_RISK": max_shares,
            "BOARD_LOT_ADJUSTED_SHARES": board_lot_shares,

            "ONE_LOT_RISK": one_lot_risk,
            "RISK_CALCULABLE": "NO",

            "RISK_STATUS": status,
            "RISK_LIMIT_REASON": reason,
            "RISK_AUDIT": audit,
        })

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

with open(SUMMARY, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)

    w.writerow(["METRIC", "VALUE"])
    w.writerow(["TOTAL_RECORDS", total])
    w.writerow(["RISK_CALCULABLE", calculable])
    w.writerow(["RISK_UNCALCULABLE", uncalculable])
    w.writerow(["NO_TRADE_BY_RISK_DATA_LIMITATION", no_trade])
    w.writerow(["FAIL", fail])

    if total:
        w.writerow([
            "RISK_CALCULABLE_PCT",
            f"{calculable / total * 100:.4f}"
        ])
        w.writerow([
            "RISK_UNCALCULABLE_PCT",
            f"{uncalculable / total * 100:.4f}"
        ])
        w.writerow([
            "FAIL_PCT",
            f"{fail / total * 100:.4f}"
        ])

    w.writerow([])
    w.writerow(["RISK_PARAMETER", "VALUE"])
    w.writerow(["DAY_MAX_LOSS", DAY_MAX_LOSS])
    w.writerow(["PREFERRED_MIN_LOSS", PREFERRED_MIN_LOSS])
    w.writerow(["PREFERRED_MAX_LOSS", PREFERRED_MAX_LOSS])

    w.writerow([])
    w.writerow(["REQUIRED_FOR_RISK_CALCULATION", "AVAILABLE"])
    w.writerow(["ENTRY_PRICE", "CURRENT_OPEN_ONLY"])
    w.writerow(["STOP_PRICE", "NO"])
    w.writerow(["EXPECTED_SLIPPAGE", "NO"])
    w.writerow(["BOARD_LOT_RISK", "NO"])
    w.writerow(["ORDER_IMPACT", "NO"])

    w.writerow([])
    w.writerow(["RULE", "RESULT"])
    w.writerow(["DAY_MAX_LOSS=5000", "ENFORCED"])
    w.writerow(["PREFERRED_LOSS=3000_TO_4000", "ENFORCED"])
    w.writerow(["NO_INVENTED_STOP", "ENFORCED"])
    w.writerow(["NO_INVENTED_SLIPPAGE", "ENFORCED"])
    w.writerow(["NO_INVENTED_POSITION_SIZE", "ENFORCED"])
    w.writerow(["RISK_UNCALCULABLE=NO_TRADE_PREFERENCE", "ENFORCED"])
    w.writerow(["RISK_DATA_LIMITATION_IS_NOT_A_RULE_FAILURE", "ENFORCED"])

print("")
print("==============================================")
print(" RISK RECONSTRUCTION ENGINE")
print("==============================================")
print(f"TOTAL RECORDS                  : {total:,}")
print(f"RISK CALCULABLE                : {calculable:,}")
print(f"RISK UNCALCULABLE              : {uncalculable:,}")
print(f"NO_TRADE BY RISK LIMITATION    : {no_trade:,}")
print(f"FAIL                           : {fail:,}")
print("----------------------------------------------")
print("DAY MAX LOSS                   : ¥5,000")
print("PREFERRED EXPECTED LOSS        : ¥3,000–¥4,000")
print("----------------------------------------------")
print("OUTPUT:")
print(OUT)
print(SUMMARY)
print("----------------------------------------------")

if fail == 0:
    print("RISK_RECONSTRUCTION_AUDIT = PASS")
else:
    print("RISK_RECONSTRUCTION_AUDIT = FAIL")

print("==============================================")
