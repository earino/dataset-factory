# Africa tick 2026-11-04: batch 13 - registry totals + Sao Tome sample overrun/base-rate signals (from saved bytes)
import json, re
from collections import Counter

# A. sum activity_count over all 57 afdb datasets from the saved package_search response
d = json.loads(json.load(open("africa_tick_b12.json"))["pkg_search_afdb"]["text"])
rows = d["result"]["results"]
counts = {}
lic = Counter()
for r in rows:
    ex = {e["key"]: e["value"] for e in r.get("extras", [])}
    counts[r["name"]] = ex.get("activity_count")
    lic[r.get("license_id")] += 1
print("datasets:", len(rows))
print("license mix over ALL 57 datasets:", dict(lic))
tot = sum(int(v) for v in counts.values() if v)
missing = [k for k, v in counts.items() if not v]
print("sum activity_count:", tot, "datasets missing activity_count:", missing)
print("top files:", sorted(((int(v), k) for k, v in counts.items() if v), reverse=True)[:6])

# B. Sao Tome XML: pair dates correctly per activity, compute status/date stats + overrun rate
t = json.load(open("africa_tick_b12.json"))["xml_saotome"]["text"]
acts = re.findall(r"<iati-activity.*?</iati-activity>", t, re.S)
stats = Counter()
overrun = None
per = []
for a in acts:
    st = re.search(r'<activity-status code="(\d+)"', a)
    st = st.group(1) if st else "?"
    stats[st] += 1
    dates = {}
    for m in re.finditer(r"<activity-date([^>]*)/>", a):
        attrs = m.group(1)
        ty = re.search(r'type="(\d+)"', attrs)
        dt = re.search(r'iso-date="([^"]+)"', attrs)
        if ty and dt:
            dates[ty.group(1)] = dt.group(1)
    per.append((st, dates))
print("status mix:", dict(stats))
# type-4 presence by status
t4_by_status = Counter(st for st, dd in per if "4" in dd)
print("activities with actual end (type 4) by status:", dict(t4_by_status))
# overrun among completed: actual_end > planned_end
comp = [(st, dd) for st, dd in per if st == "3" and "4" in dd and "3" in dd]
over = sum(1 for st, dd in comp if dd["4"] > dd["3"])
print(f"Sao Tome completed with both dates: {len(comp)}; actual_end > planned_end: {over} ({over/len(comp)*100:.1f}% if comp else n/a)")
for st, dd in comp[:6]:
    print("   ", st, dd)
# planned vs actual start (approval timing)
both_start = [(st, dd) for st, dd in per if "1" in dd and "2" in dd]
same = sum(1 for st, dd in both_start if dd["1"] == dd["2"])
print(f"planned_start == actual_start on {same}/{len(both_start)} activities")
