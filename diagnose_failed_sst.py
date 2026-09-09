import struct
import os

from build_jpx_weekly_investor_flow import ole_stream, records


FILES = [
    "/sdcard/Download/stock_val_1_250204.xls",
    "/sdcard/Download/stock_val_1_250705.xls",
    "/sdcard/Download/stock_val_1_250804.xls",
    "/sdcard/Download/stock_val_1_250901.xls",
    "/sdcard/Download/stock_val_1_250902.xls",
    "/sdcard/Download/stock_val_1_250903.xls",
    "/sdcard/Download/stock_val_1_251201.xls",
    "/sdcard/Download/stock_val_1_251204.xls",
]


for path in FILES:

    print()
    print("=" * 72)
    print(os.path.basename(path))
    print("=" * 72)

    wb = ole_stream(path)
    recs = list(records(wb))

    sst_index = None

    for i, (rid, payload, pos) in enumerate(recs):
        if rid == 0x00FC:
            sst_index = i

            total = struct.unpack_from("<I", payload, 0)[0]
            unique = struct.unpack_from("<I", payload, 4)[0]

            print("SST_INDEX =", i)
            print("TOTAL     =", total)
            print("UNIQUE    =", unique)
            print("SST_LEN   =", len(payload))

            j = i + 1
            cont = 0

            while j < len(recs) and recs[j][0] == 0x003C:
                p = recs[j][1]

                print(
                    "CONTINUE",
                    cont + 1,
                    "INDEX=", j,
                    "LEN=", len(p),
                    "HEAD=", p[:20].hex(" ")
                )

                cont += 1
                j += 1

            print("CONTINUE_COUNT =", cont)
            break

    if sst_index is None:
        print("NO_SST")
        continue

    # Show the first few record boundaries after SST.
    print()
    print("POST_SST_RECORDS")

    for i in range(sst_index, min(sst_index + 8, len(recs))):
        rid, payload, pos = recs[i]

        print(
            "INDEX=", i,
            "RID=", hex(rid),
            "LEN=", len(payload),
            "POS=", pos
        )

    print()
    print("DONE")
