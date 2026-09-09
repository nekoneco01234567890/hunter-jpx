import csv
import os

BASE = os.path.expanduser("~/jpx_replay")
DATA = os.path.join(BASE, "data")

FEATURE = os.path.join(DATA, "jpx_replay_feature.csv")
OUT = os.path.join(DATA, "jpx_replay_time_boundary_audit.csv")
SUMMARY = os.path.join(DATA, "jpx_replay_time_boundary_summary.csv")
MATRIX = os.path.join(DATA, "jpx_replay_time_boundary_matrix.csv")

# ============================================================
# TIME BOUNDARY MASTER
# ============================================================

BOUNDARY_RULES = {
    "PREV_DATE":      {"08:45": True,  "09:10": True,  "09:20": True,  "INTRADAY": True,  "DAY_END": True},
    "PREV_CLOSE":     {"08:45": True,  "09:10": True,  "09:20": True,  "INTRADAY": True,  "DAY_END": True},
    "PREV_HIGH":      {"08:45": True,  "09:10": True,  "09:20": True,  "INTRADAY": True,  "DAY_END": True},
    "PREV_LOW":       {"08:45": True,  "09:10": True,  "09:20": True,  "INTRADAY": True,  "DAY_END": True},
    "PREV_RANGE":     {"08:45": True,  "09:10": True,  "09:20": True,  "INTRADAY": True,  "DAY_END": True},

    "CURRENT_OPEN":   {"08:45": False, "09:10": True,  "09:20": True,  "INTRADAY": True,  "DAY_END": True},

    # Current-session fields become usable only after they actually exist.
    "AM_OPEN":        {"08:45": False, "09:10": True,  "09:20": True,  "INTRADAY": True,  "DAY_END": True},
    "AM_HIGH":        {"08:45": False, "09:10": False, "09:20": True,  "INTRADAY": True,  "DAY_END": True},
    "AM_LOW":         {"08:45": False, "09:10": False, "09:20": True,  "INTRADAY": True,  "DAY_END": True},
    "AM_CLOSE":       {"08:45": False, "09:10": False, "09:20": False, "INTRADAY": True,  "DAY_END": True},

    "PM_OPEN":        {"08:45": False, "09:10": False, "09:20": False, "INTRADAY": False, "DAY_END": True},
    "PM_HIGH":        {"08:45": False, "09:10": False, "09:20": False, "INTRADAY": False, "DAY_END": True},
    "PM_LOW":         {"08:45": False, "09:10": False, "09:20": False, "INTRADAY": False, "DAY_END": True},
    "PM_CLOSE":       {"08:45": False, "09:10": False, "09:20": False, "INTRADAY": False, "DAY_END": True},

    "SESSION_HIGH":   {"08:45": False, "09:10": False, "09:20": False, "INTRADAY": True,  "DAY_END": True},
    "SESSION_LOW":    {"08:45": False, "09:10": False, "09:20": False, "INTRADAY": True,  "DAY_END": True},
    "SESSION_CLOSE":  {"08:45": False, "09:10": False, "09:20": False, "INTRADAY": False, "DAY_END": True},

    "FUTURE_SESSION_FIELDS_USED": {
        "08:45": False, "09:10": False, "09:20": False, "INTRADAY": False, "DAY_END": False
    },
    "FUTURE_INTRADAY_FIELDS_USED": {
        "08:45": False, "09:10": False, "09:20": False, "INTRADAY": False, "DAY_END": False
    },
}

# ============================================================
# FIELD MATRIX
# ============================================================

with open(MATRIX, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "FIELD",
        "AVAILABLE_FROM",
        "08:45_ALLOWED",
        "09:10_ALLOWED",
        "09:20_ALLOWED",
        "INTRADAY_ALLOWED",
        "DAY_END_ALLOWED"
    ])

    available_from = {
        "PREV_DATE": "PREVIOUS_SESSION",
        "PREV_CLOSE": "PREVIOUS_SESSION",
        "PREV_HIGH": "PREVIOUS_SESSION",
        "PREV_LOW": "PREVIOUS_SESSION",
        "PREV_RANGE": "PREVIOUS_SESSION",
        "CURRENT_OPEN": "09:00_OPEN",
        "AM_OPEN": "09:00_OPEN",
        "AM_HIGH": "09:20_OR_LATER",
        "AM_LOW": "09:20_OR_LATER",
        "AM_CLOSE": "AFTER_MORNING_SESSION",
        "PM_OPEN": "AFTER_LUNCH",
        "PM_HIGH": "AFTER_LUNCH",
        "PM_LOW": "AFTER_LUNCH",
        "PM_CLOSE": "AFTER_PM_SESSION",
        "SESSION_HIGH": "INTRADAY_AFTER_HIGH_EXISTS",
        "SESSION_LOW": "INTRADAY_AFTER_LOW_EXISTS",
        "SESSION_CLOSE": "DAY_END",
        "FUTURE_SESSION_FIELDS_USED": "NEVER",
        "FUTURE_INTRADAY_FIELDS_USED": "NEVER",
    }

    for field, rules in BOUNDARY_RULES.items():
        w.writerow([
            field,
            available_from.get(field, "UNKNOWN"),
            "YES" if rules["08:45"] else "NO",
            "YES" if rules["09:10"] else "NO",
            "YES" if rules["09:20"] else "NO",
            "YES" if rules["INTRADAY"] else "NO",
            "YES" if rules["DAY_END"] else "NO",
        ])

# ============================================================
# REPLAY FEATURE AUDIT
# ============================================================

total = 0
pass_count = 0
limited_count = 0
fail_count = 0

reason_counts = {}

with open(FEATURE, "r", encoding="utf-8-sig", newline="") as fin, \
     open(OUT, "w", encoding="utf-8", newline="") as fout:

    r = csv.DictReader(fin)

    required_columns = [
        "DATE",
        "CODE",
        "DECISION_TIME",
        "QUALITY_STATUS",
        "FEATURE_STATUS",
        "PREV_CLOSE",
        "PREV_HIGH",
        "PREV_LOW",
        "CURRENT_OPEN",
        "FUTURE_SESSION_FIELDS_USED",
        "FUTURE_INTRADAY_FIELDS_USED",
    ]

    missing_columns = [x for x in required_columns if x not in r.fieldnames]

    if missing_columns:
        raise RuntimeError(
            "FEATURE FILE COLUMN ERROR: " + ",".join(missing_columns)
        )

    fields = [
        "DATE",
        "CODE",
        "DECISION_TIME",
        "FEATURE_STATUS",
        "QUALITY_STATUS",
        "TIME_BOUNDARY_STATUS",
        "LIMIT_REASON",
        "FUTURE_SESSION_FIELDS_USED",
        "FUTURE_INTRADAY_FIELDS_USED",
        "BOUNDARY_CHECK",
    ]

    w = csv.DictWriter(fout, fieldnames=fields)
    w.writeheader()

    for row in r:
        total += 1

        decision_time = row["DECISION_TIME"].strip()
        feature_status = row["FEATURE_STATUS"].strip()
        quality_status = row["QUALITY_STATUS"].strip()

        future_session = row["FUTURE_SESSION_FIELDS_USED"].strip().upper()
        future_intraday = row["FUTURE_INTRADAY_FIELDS_USED"].strip().upper()

        failures = []
        limited_reasons = []

        # --------------------------------------------
        # HARD FAIL: malformed decision boundary
        # --------------------------------------------

        if decision_time != "09:10":
            failures.append("DECISION_TIME_NOT_09_10")

        # --------------------------------------------
        # HARD FAIL: explicit future information usage
        # --------------------------------------------

        if future_session not in ("", "FALSE", "NO", "0", "NONE"):
            failures.append("FUTURE_SESSION_FIELD_USED")

        if future_intraday not in ("", "FALSE", "NO", "0", "NONE"):
            failures.append("FUTURE_INTRADAY_FIELD_USED")

        # --------------------------------------------
        # LIMITED: insufficient historical/current data
        # --------------------------------------------

        if feature_status == "PARTIAL_NO_OPEN":
            limited_reasons.append("CURRENT_OPEN_UNAVAILABLE")

        if feature_status == "PARTIAL_NO_PREV":
            limited_reasons.append("PREVIOUS_SESSION_DATA_UNAVAILABLE")

        if feature_status == "UNAVAILABLE":
            limited_reasons.append("FEATURE_UNAVAILABLE")

        if quality_status in ("NO_PRICE_DATA", "PARTIAL"):
            limited_reasons.append("SOURCE_PRICE_DATA_LIMITED")

        # --------------------------------------------
        # FINAL STATUS
        # --------------------------------------------

        if failures:
            status = "FAIL"
            reason = "|".join(failures)
            fail_count += 1

        elif limited_reasons:
            status = "LIMITED"
            reason = "|".join(sorted(set(limited_reasons)))
            limited_count += 1

        else:
            status = "PASS"
            reason = ""
            pass_count += 1

        reason_counts[reason if reason else "PASS"] = \
            reason_counts.get(reason if reason else "PASS", 0) + 1

        w.writerow({
            "DATE": row["DATE"],
            "CODE": row["CODE"],
            "DECISION_TIME": decision_time,
            "FEATURE_STATUS": feature_status,
            "QUALITY_STATUS": quality_status,
            "TIME_BOUNDARY_STATUS": status,
            "LIMIT_REASON": reason,
            "FUTURE_SESSION_FIELDS_USED": future_session,
            "FUTURE_INTRADAY_FIELDS_USED": future_intraday,
            "BOUNDARY_CHECK": "PASS" if not failures else "FAIL",
        })

# ============================================================
# SUMMARY
# ============================================================

with open(SUMMARY, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)

    w.writerow(["METRIC", "VALUE"])
    w.writerow(["TOTAL_RECORDS", total])
    w.writerow(["PASS", pass_count])
    w.writerow(["LIMITED", limited_count])
    w.writerow(["FAIL", fail_count])

    if total:
        w.writerow(["PASS_PCT", f"{pass_count / total * 100:.4f}"])
        w.writerow(["LIMITED_PCT", f"{limited_count / total * 100:.4f}"])
        w.writerow(["FAIL_PCT", f"{fail_count / total * 100:.4f}"])

    w.writerow([])
    w.writerow(["RULE", "RESULT"])
    w.writerow(["DECISION_TIME=09:10", "ENFORCED"])
    w.writerow(["NO_FUTURE_SESSION_FIELDS", "ENFORCED"])
    w.writerow(["NO_FUTURE_INTRADAY_FIELDS", "ENFORCED"])
    w.writerow(["MISSING_DATA=LIMITED", "ENFORCED"])
    w.writerow(["FAIL_ONLY_FOR_BOUNDARY_VIOLATION", "ENFORCED"])
    w.writerow(["REPLAY_FEATURE_SOURCE", "jpx_replay_feature.csv"])

print("")
print("==============================================")
print(" TIME BOUNDARY ENGINE")
print("==============================================")
print(f"TOTAL RECORDS : {total:,}")
print(f"PASS          : {pass_count:,}")
print(f"LIMITED       : {limited_count:,}")
print(f"FAIL          : {fail_count:,}")
print("----------------------------------------------")
print("OUTPUT:")
print(OUT)
print(SUMMARY)
print(MATRIX)
print("----------------------------------------------")

if fail_count == 0:
    print("TIME_BOUNDARY_AUDIT = PASS")
else:
    print("TIME_BOUNDARY_AUDIT = FAIL")

print("==============================================")
