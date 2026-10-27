#!/usr/bin/env python3
"""Vintage diff: issue-202608 ZIP export ('Release: 2026 08') vs Isibalo export
('Release: 2026 09'), both fetched 2026-10-27, within the restated basis.
Usage: python3 probe_vintage_diff.py <ascii_202608_file> <ascii_202609_file>
Prints overlapping values compared, differing count, and every differing
series/month with old -> new values."""
import re
import sys

def parse(path):
    blocks = []
    cur = {"values": []}
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
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
    return blocks

def mi(seq):
    y, m = divmod(seq, 12)
    return f"{2000 + y:04d}-{m + 1:02d}"

def main():
    v1, v2 = parse(sys.argv[1]), parse(sys.argv[2])
    n = d = 0
    for b1 in v1:
        b2 = next((x for x in v2 if x["H03"] == b1["H03"]), None)
        if not b2:
            continue
        for i in range(min(len(b1["values"]), len(b2["values"]))):
            n += 1
            if b1["values"][i] != b2["values"][i]:
                d += 1
                print(f"diff {b1['H03']} {b1['H07'] or b1['H05']}: {mi(i)} "
                      f"202608={b1['values'][i]} -> 202609={b2['values'][i]}")
    print(f"{n} overlapping values compared, {d} differ")

if __name__ == "__main__":
    main()
