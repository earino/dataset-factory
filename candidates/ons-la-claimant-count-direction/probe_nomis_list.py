#!/usr/bin/env python3
"""Probe: list nomis datasets mentioning 'claimant' with id, name, status."""
import json

with open("/opt/data/cache/scratch/nomis_all.json", encoding="utf-8", errors="replace") as f:
    text = f.read()

# the JSON contains escaped chars; parse properly
data = json.loads(text)
kfs = data["structure"]["keyfamilies"]["keyfamily"]
if isinstance(kfs, dict):
    kfs = [kfs]
print(f"total keyfamilies: {len(kfs)}")
for kf in kfs:
    name = (kf.get("name") or {}).get("value", "")
    if "claimant" in name.lower():
        ann = {a.get("annotationtitle"): a.get("annotationtext")
               for a in (kf.get("annotations") or {}).get("annotation", [])}
        print(f'{kf.get("id")}: "{name}"')
        print(f'    status={ann.get("Status")!r} units={ann.get("Units")!r}')
        print(f'    description={(kf.get("description") or {}).get("value", "")[:140]}')
