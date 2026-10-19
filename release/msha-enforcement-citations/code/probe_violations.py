#!/usr/bin/env python3
"""Probe the MSHA Violations data set (streamed, two passes, nothing extracted to disk).

Pass 1: row count, grain, date range, distinct mines/events, label space, density.
Pass 2: co-occurrence among the labels that survive a 1% floor.

Usage: python3 probe_violations.py <Violations.zip> [--top N]
"""
import argparse, collections, csv, io, statistics, sys, zipfile

def rows(zf):
    name = [n for n in zf.namelist() if n.lower().endswith((".txt", ".csv"))][0]
    with zf.open(name) as fh:
        text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace", newline="")
        reader = csv.DictReader(text, delimiter="|")
        yield name, reader

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip_path"); ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    zf = zipfile.ZipFile(a.zip_path)
    print("members:", [(i.filename, i.file_size) for i in zf.infolist()][:5])

    n = 0
    events = set(); mines = set(); labels = collections.Counter()
    per_event = collections.Counter(); null_label = 0
    d_min = None; d_max = None; coal = collections.Counter()
    member = None
    for member, reader in rows(zf):
        for row in reader:
            n += 1
            e = (row.get("EVENT_NO") or "").strip()
            lab = (row.get("PART_SECTION") or "").strip()
            events.add(e); mines.add((row.get("MINE_ID") or "").strip())
            if lab:
                labels[lab] += 1; per_event[e] += 1
            else:
                null_label += 1
            d = (row.get("INSPECTION_BEGIN_DT") or "").strip()
            if d:
                if d_min is None or d < d_min: d_min = d
                if d_max is None or d > d_max: d_max = d
            coal[(row.get("COAL_METAL_IND") or "").strip()] += 1
    print(f"\nfile: {member}")
    print(f"rows (citations): {n:,}")
    print(f"distinct EVENT_NO (inspections): {len(events):,}")
    print(f"distinct MINE_ID: {len(mines):,}")
    print(f"rows with empty PART_SECTION: {null_label:,} ({100*null_label/max(n,1):.2f}%)")
    print(f"distinct PART_SECTION labels: {len(labels):,}")
    print(f"inspection_begin_dt range: {d_min} .. {d_max}")
    print("coal/metal:", dict(coal))
    dense = [per_event[e] for e in events if per_event[e]]
    print(f"events with >=1 label: {len(dense):,}")
    print(f"labels per inspection: mean {statistics.mean(dense):.2f}, median {statistics.median(dense)}, max {max(dense)}")
    for thr in (0.01, 0.005, 0.001):
        c = sum(1 for v in labels.values() if v >= thr * len(dense))
        print(f"labels in >= {thr*100:.1f}% of inspections: {c}")
    print("\ntop labels:")
    for lab, v in labels.most_common(a.top):
        print(f"  {lab}  {v:,}")

    # pass 2: co-occurrence among labels above the 1% floor, counted per inspection
    floor = sorted(lab for lab, v in labels.items() if v >= 0.01 * len(dense))
    bit = {lab: 1 << i for i, lab in enumerate(floor)}
    masks = {}
    for _, reader in rows(zf):
        for row in reader:
            lab = (row.get("PART_SECTION") or "").strip()
            if lab in bit:
                e = (row.get("EVENT_NO") or "").strip()
                masks[e] = masks.get(e, 0) | bit[lab]
    pair = collections.Counter()
    for m in masks.values():
        idx = [i for i in range(len(floor)) if m >> i & 1]
        for i in range(len(idx)):
            for j in range(i + 1, len(idx)):
                pair[(floor[idx[i]], floor[idx[j]])] += 1
    print(f"\nlabels above the 1% floor: {len(floor)}")
    print("top co-occurring pairs (label, label, inspections):")
    for (x, y), v in pair.most_common(15):
        print(f"  ({x}, {y})  {v:,}")

if __name__ == "__main__":
    main()
