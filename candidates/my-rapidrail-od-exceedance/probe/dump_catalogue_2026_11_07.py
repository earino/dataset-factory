#!/usr/bin/env python3
"""Dump full data.gov.my catalogue inventory (ids, titles, descriptions, sizes) 2026-11-07."""
import json

data = json.load(open("/opt/data/cache/scratch/my_catalogue_nextdata.json"))
coll = data["props"]["pageProps"]["collection"]

rows = []
for cat, sub in coll.items():
    for subname, items in sub.items():
        for it in items:
            rows.append((cat, subname, it))

print(f"total datasets: {len(rows)}")
print()
for cat, subname, it in sorted(rows, key=lambda r: (r[0], r[1], r[2]["title"])):
    desc = (it.get("description") or "").replace("\n", " ")
    print(f"[{cat} / {subname}] {it['title']}  |id={it['id']} |as_of={it.get('data_as_of')} |csv={it.get('size_csv')}")
    if desc:
        print(f"    {desc[:220]}")
