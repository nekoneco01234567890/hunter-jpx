import csv
import os

BASE = os.path.expanduser("~/jpx_replay")
DATA = os.path.join(BASE, "data")

FEATURE = os.path.join(DATA, "jpx_replay_feature.csv")
OUT = os.path.join(DATA, "jpx_replay_execution_audit.csv")
SUMMARY = os.path.join(DATA, "jpx_replay_execution_summary.csv")

total = 0
verifiable = 0
uncertain = 0
unverifiable = 0
limited = 0
fail = 0

reasons = {}

def count_reason(x):
    reasons[x] = reasons.get(x, 0) + 1

with open(FEATURE, "r", encoding="utf-8-sig", newline="") as fin, \
     open(OUT, "w", encoding="utf-8", newline="") as fout:

    r = csv.DictReader(fin)

    required = [
        "DATE",
        "CODE",
        "DECISION_TIME",
        "CURRENT_OPEN",
        "CURRENT_OPEN_AVAILABLE",
        "FEATURE_STATUS",
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

        "EXACT_0910_PRICE",
        "ORDER_BOOK",
        "SPREAD",
        "VISIBLE_DEPTH",
        "INTRADAY_VOLUME_PATH",
        "INTRADAY_VWAP_PATH",
        "EXACT_FILL",
        "SLIPPAGE",
        "EXIT_FEASIBILITY",

        "EXECUTION_STATUS",
        "EXECUTION_LIMIT_REASON",
        "EXECUTION_RECONSTRUCTION_LEVEL",
        "EXECUTION_AUDIT",
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

        # --------------------------------------------------
        # Boundary integrity
        # --------------------------------------------------

        if decision_time != "09:10":
            hard_fail.append("DECISION_TIME_NOT_09_10")

        # --------------------------------------------------
        # What the JPX monthly source actually contains
        # --------------------------------------------------

        exact_0910_price = "NO"
        order_book = "NO"
        spread = "NO"
        visible_depth = "NO"
        intraday_volume_path = "NO"
        intraday_vwap_path = "NO"
        exact_fill = "NO"
        slippage = "NO"

        # Exit feasibility cannot be reconstructed from this source
        # because no intraday execution path/order book exists.
        exit_feasibility = "UNVERIFIABLE"

        # --------------------------------------------------
        # Determine reconstruction level
        # --------------------------------------------------

        if hard_fail:
            status = "FAIL"
            reason = "|".join(hard_fail)
            level = "NONE"
            audit = "FAIL"
            fail += 1

        elif current_open_available not in ("TRUE", "FALSE"):
            status = "UNVERIFIABLE"
            reason = "CURRENT_OPEN_AVAILABILITY_UNKNOWN"
            level = "NONE"
            audit = "PASS"
            unverifiable += 1
            count_reason(reason)

        elif feature_status in (
            "UNAVAILABLE",
            "PARTIAL_NO_OPEN",
        ):
            status = "UNVERIFIABLE"
            reason = "REQUIRED_ENTRY_PRICE_UNAVAILABLE"
            level = "NONE"
            audit = "PASS"
            unverifiable += 1
            count_reason(reason)

        else:
            # Current dataset provides AM open but not 09:10 execution.
            #
            # Therefore:
            # - open price is known
            # - exact 09:10 price is unknown
            # - actual fill is unknown
            # - order book is unknown
            # - slippage is unknown
            #
            # This is not a failed audit.
            status = "EXECUTION_UNVERIFIABLE"
            reason = (
                "NO_EXACT_0910_PRICE|"
                "NO_ORDER_BOOK|"
                "NO_SPREAD|"
                "NO_VISIBLE_DEPTH|"
                "NO_INTRADAY_VOLUME_PATH|"
                "NO_INTRADAY_VWAP_PATH|"
                "NO_EXACT_FILL|"
                "NO_SLIPPAGE"
            )
            level = "SESSION_LEVEL_ONLY"
            audit = "PASS"
            unverifiable += 1
            count_reason(reason)

        w.writerow({
            "DATE": date,
            "CODE": code,
            "DECISION_TIME": decision_time,
            "FEATURE_STATUS": feature_status,
            "CURRENT_OPEN": row["CURRENT_OPEN"],
            "CURRENT_OPEN_AVAILABLE": current_open_available,

            "EXACT_0910_PRICE": exact_0910_price,
            "ORDER_BOOK": order_book,
            "SPREAD": spread,
            "VISIBLE_DEPTH": visible_depth,
            "INTRADAY_VOLUME_PATH": intraday_volume_path,
            "INTRADAY_VWAP_PATH": intraday_vwap_path,
            "EXACT_FILL": exact_fill,
            "SLIPPAGE": slippage,
            "EXIT_FEASIBILITY": exit_feasibility,

            "EXECUTION_STATUS": status,
            "EXECUTION_LIMIT_REASON": reason,
            "EXECUTION_RECONSTRUCTION_LEVEL": level,
            "EXECUTION_AUDIT": audit,
        })

# ----------------------------------------------------------
# Summary
# ----------------------------------------------------------

with open(SUMMARY, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)

    w.writerow(["METRIC", "VALUE"])
    w.writerow(["TOTAL_RECORDS", total])
    w.writerow(["EXECUTION_VERIFIABLE", verifiable])
    w.writerow(["EXECUTION_UNCERTAIN", uncertain])
    w.writerow(["EXECUTION_UNVERIFIABLE", unverifiable])
    w.writerow(["LIMITED", limited])
    w.writerow(["FAIL", fail])

    if total:
        w.writerow(["VERIFIABLE_PCT", f"{verifiable / total * 100:.4f}"])
        w.writerow(["UNCERTAIN_PCT", f"{uncertain / total * 100:.4f}"])
        w.writerow(["UNVERIFIABLE_PCT", f"{unverifiable / total * 100:.4f}"])
        w.writerow(["LIMITED_PCT", f"{limited / total * 100:.4f}"])
        w.writerow(["FAIL_PCT", f"{fail / total * 100:.4f}"])

    w.writerow([])
    w.writerow(["EXECUTION_DATA_FIELD", "AVAILABLE"])
    w.writerow(["EXACT_0910_PRICE", "NO"])
    w.writerow(["ORDER_BOOK", "NO"])
    w.writerow(["SPREAD", "NO"])
    w.writerow(["VISIBLE_DEPTH", "NO"])
    w.writerow(["INTRADAY_VOLUME_PATH", "NO"])
    w.writerow(["INTRADAY_VWAP_PATH", "NO"])
    w.writerow(["EXACT_FILL", "NO"])
    w.writerow(["SLIPPAGE", "NO"])
    w.writerow(["EXIT_FEASIBILITY", "UNVERIFIABLE"])

    w.writerow([])
    w.writerow(["RULE", "RESULT"])
    w.writerow(["NO_INVENTED_FILL", "ENFORCED"])
    w.writerow(["NO_INVENTED_SLIPPAGE", "ENFORCED"])
    w.writerow(["NO_INVENTED_ORDER_BOOK", "ENFORCED"])
    w.writerow(["NO_INVENTED_0910_PRICE", "ENFORCED"])
    w.writerow(["SESSION_LEVEL_DATA_ONLY", "ENFORCED"])
    w.writerow(["UNVERIFIABLE_IS_NOT_FAILURE", "ENFORCED"])

print("")
print("==============================================")
print(" EXECUTION RECONSTRUCTION ENGINE")
print("==============================================")
print(f"TOTAL RECORDS          : {total:,}")
print(f"EXECUTION VERIFIABLE  : {verifiable:,}")
print(f"EXECUTION UNCERTAIN   : {uncertain:,}")
print(f"EXECUTION UNVERIFIABLE: {unverifiable:,}")
print(f"LIMITED                : {limited:,}")
print(f"FAIL                   : {fail:,}")
print("----------------------------------------------")
print("OUTPUT:")
print(OUT)
print(SUMMARY)
print("----------------------------------------------")

if fail == 0:
    print("EXECUTION_RECONSTRUCTION_AUDIT = PASS")
else:
    print("EXECUTION_RECONSTRUCTION_AUDIT = FAIL")

print("==============================================")
