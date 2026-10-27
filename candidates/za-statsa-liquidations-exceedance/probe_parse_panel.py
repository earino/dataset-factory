#!/usr/bin/env python3
"""Parse StatsSA Isibalo P0043.1 liquidations ASCII export (Release 2026 09).

Blocks: H01..H25 header lines, then one integer per month (monthly, start 2000-01).
Outputs: parsed panel (TSV), series inventory, month coverage, JSON-vs-ASCII vintage diff.
"""
import json
import re
import sys

SCRATCH = "/opt/data/cache/scratch/statsa-liq"

def parse_ascii(path):
    blocks = []
    cur = None
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n").lstrip()
        if line.startswith("H0") or line.startswith("H1") or line.startswith("H2"):
            m = re.match(r"(H\d+):\s*(.*)", line)
            if m:
                cur = cur or {}
                cur[m.group(1)] = m.group(2).strip()
        elif line and cur is not None and re.match(r"^\d+$", line):
            cur.setdefault("values", []).append(int(line))
        elif line.strip() == "" and cur and "values" in cur:
            pass
    # block boundaries: a new block starts when we see H01 again
    blocks = []
    cur = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n").lstrip()
        if line.startswith("H01:"):
            if cur.get("values"):
                blocks.append(cur)
            cur = {"values": []}
        m = re.match(r"(H\d+):\s*(.*)", line)
        if m:
            cur[m.group(1)] = m.group(2).strip()
        elif re.match(r"^\d+$", line) and cur is not None:
            cur["values"].append(int(line))
        elif re.match(r"^\d+\.\d+$", line) and cur is not None:
            cur["values"].append(float(line))
    if cur.get("values"):
        blocks.append(cur)
    return blocks

def month_index(seq):
    """0 -> 2000-01."""
    y, m = divmod(seq, 12)
    return f"{2000 + y:04d}-{m + 1:02d}"

def main():
    blocks = parse_ascii(f"{SCRATCH}/ASCII_Liquidations.txt")
    print(f"blocks parsed: {len(blocks)}")
    lens = sorted({len(b["values"]) for b in blocks})
    print(f"value counts per block: {lens}")
    n = lens[-1]
    print(f"coverage: {month_index(0)} .. {month_index(n - 1)} ({n} months)")
    for b in blocks:
        print(" ", b["H03"], "|", b["H05"], "|", b["H06"], "|", b["H07"],
              "| vals:", len(b["values"]), "| release:", b.get("H23", "?"))

    # panel TSV
    with open(f"{SCRATCH}/panel.tsv", "w") as f:
        f.write("series\tentity\tprocedure\tindustry\tmonth\tvalue\n")
        for b in blocks:
            for i, v in enumerate(b["values"]):
                f.write(f"{b['H03']}\t{b['H05']}\t{b['H06']}\t{b['H07']}\t{month_index(i)}\t{v}\n")

    # vintage diff vs the JSON export (fetched same day; months through 2025-12)
    data = json.load(open(f"{SCRATCH}/P0043_1p.json"))
    jrows = {r["H03"]: r for r in data["SASTableData+P0043_1"]}
    diffs = 0
    checked = 0
    examples = []
    for b in blocks:
        code = b["H03"]
        jr = jrows.get(code)
        if not jr:
            continue
        for i in range(min(len(b["values"]), 312)):  # 2000-01..2025-12
            jv = jr.get(f"MO{i % 12 + 1:02d}{2000 + i // 12:04d}")
            if jv is None:
                continue
            checked += 1
            if int(jv) != b["values"][i]:
                diffs += 1
                if len(examples) < 10:
                    examples.append((code, month_index(i), jv, b["values"][i]))
    print(f"vintage diff 2000-01..2025-12: {checked} overlapping values checked, {diffs} differ")
    for e in examples:
        print("  revised:", e)

if __name__ == "__main__":
    main()
