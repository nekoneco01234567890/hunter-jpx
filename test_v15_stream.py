import csv
import os

DATA = os.path.expanduser("~/jpx_replay/data")

FILES = {
    "FEATURE": os.path.join(DATA, "jpx_replay_feature.csv"),
    "TIME": os.path.join(DATA, "jpx_replay_time_boundary_audit.csv"),
    "EXECUTION": os.path.join(DATA, "jpx_replay_execution_audit.csv"),
    "RISK": os.path.join(DATA, "jpx_replay_risk_audit.csv"),
    "THESIS": os.path.join(DATA, "jpx_replay_thesis_entry_audit.csv"),
}


def read_rows(path):
    f = open(path, "r", encoding="utf-8-sig", newline="")
    r = csv.reader(f)
    header = next(r)
    return f, r, header


streams = {}

try:
    for name, path in FILES.items():
        if not os.path.exists(path):
            raise RuntimeError(f"MISSING: {path}")

        f, r, header = read_rows(path)

        if "DATE" not in header or "CODE" not in header:
            raise RuntimeError(
                f"{name}: DATE/CODE column missing"
            )

        date_i = header.index("DATE")
        code_i = header.index("CODE")

        streams[name] = {
            "file": f,
            "reader": r,
            "date_i": date_i,
            "code_i": code_i,
        }

    print("V15 STREAM TEST")
    print("RAM MODE = ONE ROW ONLY")
    print()

    for i in range(10):
        rows = {}

        for name, s in streams.items():
            try:
                row = next(s["reader"])
            except StopIteration:
                raise RuntimeError(
                    f"{name}: ended before row {i + 1}"
                )

            rows[name] = row

        keys = {}

        for name, row in rows.items():
            key = (
                row[streams[name]["date_i"]],
                row[streams[name]["code_i"]],
            )
            keys[name] = key

        first_key = keys["FEATURE"]

        if not all(k == first_key for k in keys.values()):
            print("KEY MISMATCH")
            for name, key in keys.items():
                print(name, key)
            raise RuntimeError("STREAM ALIGNMENT FAILED")

        print(
            f"ROW {i + 1:02d} OK "
            f"DATE={first_key[0]} "
            f"CODE={first_key[1]}"
        )

    print()
    print("STREAM_TEST = PASS")
    print("NO DICTIONARY")
    print("NO FULL FILE LOAD")
    print("NO MASS MEMORY INDEX")

finally:
    for s in streams.values():
        s["file"].close()
