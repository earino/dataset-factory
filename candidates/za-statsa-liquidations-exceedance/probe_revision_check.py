#!/usr/bin/env python3
"""Revision check: values as published in past P0043.1 issues vs the current
Isibalo Release-2026-09 vintage, for the national-total series (LIQ00000).

Source tables read from the Wayback-snapshotted release PDFs:
- Feb 2026 issue (embargoed 25 Mar 2026), Table 2: monthly totals 2020-01..2026-02
- Sep 2023 issue (embargoed 25 Oct 2023 per its cover), Table 2: monthly totals 2017..2023-09
"""
import re

SCRATCH = "/opt/data/cache/scratch/statsa-liq"

# --- current vintage panel: LIQ00000 totals ---
blocks = []
cur = {"values": []}
for line in open(f"{SCRATCH}/ASCII_Liquidations.txt", encoding="utf-8", errors="replace"):
    line = line.rstrip("\n").lstrip()
    if line.startswith("H01:"):
        if cur.get("values"):
            blocks.append(cur)
        cur = {"values": []}
    m = re.match(r"(H\d+):\s*(.*)", line)
    if m:
        cur[m.group(1)] = m.group(2).strip()
    elif re.match(r"^\d+$", line):
        cur["values"].append(int(line))
if cur.get("values"):
    blocks.append(cur)
tot = next(b for b in blocks if b["H03"] == "LIQ00000")["values"]

def cur_value(year, month):
    return tot[(year - 2000) * 12 + month - 1]

# --- Feb 2026 issue, Table 2 (read from PDF text extraction, transcribed) ---
feb26_table2 = {  # year -> {month: value}
    2020: {1:125,2:164,3:145,4:0,5:195,6:134,7:193,8:228,9:211,10:215,11:272,12:153},
    2021: {1:122,2:178,3:216,4:158,5:191,6:132,7:165,8:165,9:152,10:172,11:159,12:122},
    2022: {1:120,2:160,3:182,4:138,5:188,6:145,7:165,8:157,9:170,10:157,11:166,12:159},
    2023: {1:81,2:162,3:168,4:112,5:151,6:128,7:140,8:142,9:156,10:136,11:144,12:137},
    2024: {1:109,2:138,3:138,4:128,5:125,6:121,7:133,8:128,9:117,10:196,11:128,12:90},
    2025: {1:106,2:140,3:127,4:109,5:141,6:130,7:155,8:127,9:145,10:128,11:126,12:100},
    2026: {1:96,2:135},
}

print("== Feb 2026 issue (published 25 Mar 2026) vs current Release 2026 09 ==")
n = diff = 0
diffs = []
for y, months in sorted(feb26_table2.items()):
    for m, v in sorted(months.items()):
        c = cur_value(y, m)
        n += 1
        if c != v:
            diff += 1
            diffs.append((y, m, v, c))
print(f"  months compared: {n}, differing: {diff}")
for d in diffs:
    print("   REVISION:", d)
# spot-check two known events
print("  known events in current vintage: Apr 2020 =", cur_value(2020, 4),
      "(expected 0, lockdown); Nov 2020 =", cur_value(2020, 11), "(expected 272, backlog surge)")
