import sys
import openpyxl
from datetime import time

FILE = "N225f_2026.xlsx"

if len(sys.argv) != 2:
    print("使い方: python jpx_replay.py YYYY-MM-DD")
    sys.exit(1)

target = sys.argv[1]

# =========================
# LOAD DATA
# =========================

wb = openpyxl.load_workbook(FILE, read_only=True, data_only=True)
ws = wb["1min"]

rows = []

for row in ws.iter_rows(min_row=2, values_only=True):
    d, t, o, h, l, c, v = row

    if d is None or t is None:
        continue

    if d.strftime("%Y-%m-%d") != target:
        continue

    if time(8, 45) <= t <= time(15, 45):
        rows.append({
            "time": t,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        })

wb.close()

if not rows:
    print(f"{target}: 日中データなし")
    sys.exit(0)


# =========================
# BASIC HELPERS
# =========================

def show_bar(index):
    r = rows[index]

    print(
        f"[{index + 1}/{len(rows)}] "
        f"{r['time'].strftime('%H:%M')} "
        f"O:{r['open']} "
        f"H:{r['high']} "
        f"L:{r['low']} "
        f"C:{r['close']} "
        f"V:{r['volume']}"
    )


def find_index(target_time):
    for i, r in enumerate(rows):
        if r["time"] >= target_time:
            return i
    return len(rows) - 1


# =========================
# OBSERVATION SNAPSHOT
# =========================

def observation_0845():
    r = rows[0]

    print()
    print("========================================")
    print("  08:45 OBSERVATION")
    print("========================================")
    print(f"日時       : {target} 08:45")
    print(f"始値       : {r['open']}")
    print(f"高値       : {r['high']}")
    print(f"安値       : {r['low']}")
    print(f"終値       : {r['close']}")
    print(f"出来高     : {r['volume']}")
    print()
    print("※ 08:45時点で確定している1分足のみ")
    print("※ 09:00以降のデータは表示・参照しない")
    print("========================================")
    print()


def observation_0910():
    index = find_index(time(9, 10))
    r = rows[index]

    visible = rows[:index + 1]

    high = max(x["high"] for x in visible)
    low = min(x["low"] for x in visible)
    volume = sum(x["volume"] for x in visible)

    print()
    print("========================================")
    print("  09:10 OBSERVATION")
    print("========================================")
    print(f"日時       : {target} {r['time'].strftime('%H:%M')}")
    print(f"現在値     : {r['close']}")
    print(f"08:45始値  : {rows[0]['open']}")
    print(f"08:45以降高値: {high}")
    print(f"08:45以降安値: {low}")
    print(f"累積出来高 : {volume}")
    print()
    print("※ 09:10までに確定したデータのみ")
    print("※ 09:11以降のデータは参照しない")
    print("========================================")
    print()


def observation_0920():
    index = find_index(time(9, 20))
    r = rows[index]

    visible = rows[:index + 1]

    high = max(x["high"] for x in visible)
    low = min(x["low"] for x in visible)
    volume = sum(x["volume"] for x in visible)

    print()
    print("========================================")
    print("  09:20 EXECUTION OBSERVATION")
    print("========================================")
    print(f"日時       : {target} {r['time'].strftime('%H:%M')}")
    print(f"現在値     : {r['close']}")
    print(f"08:45始値  : {rows[0]['open']}")
    print(f"08:45-09:20高値: {high}")
    print(f"08:45-09:20安値: {low}")
    print(f"累積出来高 : {volume}")
    print()
    print("※ 09:20までに確定したデータのみ")
    print("※ 09:21以降のデータは判定に使用しない")
    print("========================================")
    print()


# =========================
# START
# =========================

print(f"=== JPX REPLAY {target} ===")
print(f"データ件数: {len(rows)}")
print()

print("コマンド:")
print("  n = 次の1分")
print("  a = 09:10へ")
print("  e = 09:20へ")
print("  o = 08:45観測")
print("  s = 09:10観測")
print("  x = 09:20観測")
print("  q = 終了")
print()

index = 0

while index < len(rows):

    show_bar(index)

    cmd = input("> ").strip().lower()

    if cmd == "q":
        break

    elif cmd == "n":
        if index < len(rows) - 1:
            index += 1

    elif cmd == "a":
        index = find_index(time(9, 10))

    elif cmd == "e":
        index = find_index(time(9, 20))

    elif cmd == "o":
        observation_0845()

    elif cmd == "s":
        observation_0910()

    elif cmd == "x":
        observation_0920()

    else:
        print("n / a / e / o / s / x / q を入力してください")

print()
print("=== REPLAY END ===")
