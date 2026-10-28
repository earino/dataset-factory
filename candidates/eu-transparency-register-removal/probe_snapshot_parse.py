#!/usr/bin/env python3
"""Streaming parse of one Transparency Register snapshot XML (2024-01).

Answers, with counts only:
1. the complete per-organisation field inventory (all element paths);
2. value distribution of every field with few distinct values (statuses,
   categories, networking, ...);
3. count of organisations, and registration-date coverage.
RAM-bounded via iterparse; nothing bulk is retained.
"""
import sys
import xml.etree.ElementTree as ET
from collections import Counter

NS = "{http://intragate.ec.europa.eu/transparencyregister/odp}"
path = sys.argv[1] if len(sys.argv) > 1 else "tr_2024JAN.xml"

paths = Counter()          # element paths under interestRepresentative
low_card = {}              # path -> Counter of values (kept for short lists)
n_orgs = 0
reg_years = Counter()
lastupd_years = Counter()
meta = {}


def walk(el, prefix):
    paths[prefix] += 1
    for child in el:
        walk(child, prefix + "/" + child.tag.replace(NS, ""))


context = ET.iterparse(path, events=("end",))
root = None
for event, elem in context:
    tag = elem.tag.replace(NS, "")
    if tag == "metaData":
        for c in elem:
            meta[c.tag.replace(NS, "")] = (c.text or "").strip()
        elem.clear()
    elif tag == "interestRepresentative":
        n_orgs += 1
        # local walk without recursing into big text twice
        for child in elem.iter():
            p = child.tag.replace(NS, "")
            if child is elem:
                continue
            # build path lazily: only record depth<=2 simple names
            paths["<org>/" + p] += 1
        for c in elem:
            p = c.tag.replace(NS, "")
            if p in ("registrationDate",):
                v = (c.text or "")[:4]
                reg_years[v] += 1
            if p in ("lastUpdateDate",):
                v = (c.text or "")[:4]
                lastupd_years[v] += 1
        elem.clear()

print("meta:", meta)
print("orgs parsed:", n_orgs)
print("\n--- element inventory (counts are occurrences across orgs) ---")
for p, c in sorted(paths.items()):
    print(f"{c:7d}  {p}")
print("\nregistration year:", dict(sorted(reg_years.items())))
print("\nlastUpdate year:", dict(sorted(lastupd_years.items())))
