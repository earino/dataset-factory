# Africa tick 2026-11-04: batch 14 - XML field inventory for the record (approval date? finance types?)
import json, re

t = json.load(open("africa_tick_b12.json"))["xml_saotome"]["text"]
for pat in ["afdb:", "approval", "recipient-country", "default-finance-type", "default-aid-type",
            "default-flow-type", "default-tied-status", "policy-marker", "conditions", "budget",
            "planned-disbursement", "transaction", "sector", "hierarchy", "aggregation-status"]:
    hits = re.findall(r"<" + pat + r"[^>]{0,120}>", t)
    uniq = list(dict.fromkeys(hits))[:4]
    print(f"{pat!r}: {len(hits)} total, uniq sample: {uniq}")

acts = re.findall(r"<iati-activity.*?</iati-activity>", t, re.S)
spans = []
for a in acts:
    dd = {}
    for m in re.finditer(r"<activity-date([^>]*)/>", a):
        at = m.group(1)
        ty = re.search(r'type="(\d+)"', at)
        dt = re.search(r'iso-date="([^"]+)"', at)
        if ty and dt:
            dd[ty.group(1)] = dt.group(1)
    if "1" in dd and "3" in dd:
        spans.append((dd["1"], dd["3"]))
print("\nplanned_start -> planned_end spans (first 8):", spans[:8])
