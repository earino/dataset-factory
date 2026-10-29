# Probe: enumerate FTS plans per year via HPC API v2, extract requirements/funding
# and launch dates. Bounded: one request per year, summary output only.
import json, time, urllib.request

BASE = "https://api.hpc.tools/v2/public/plan/year/{}"
YEARS = range(2000, 2027)

def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "scout-discovery-probe/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)

first_sample = None
rows = []
for y in YEARS:
    try:
        d = fetch(BASE.format(y))
    except Exception as e:
        print(f"{y}: FETCH-ERROR {e}")
        continue
    # discover shape once
    if first_sample is None and d:
        first_sample = d
    plans = d if isinstance(d, list) else d.get("data", d.get("plans", []))
    if isinstance(plans, dict):
        plans = plans.get("data", [])
    print(f"{y}: {len(plans)} plans")
    rows.append((y, plans))
    time.sleep(0.3)

# once: print the full field structure of one plan record
if rows:
    sample = rows[-1][1][0] if rows and rows[-1][1] else None
    if sample:
        print("\nSAMPLE PLAN RECORD (last year, first):")
        print(json.dumps(sample, indent=1)[:3500])

# compact per-plan lines for one recent year to see the vocabulary
print("\n2023 plans compact:")
for y, plans in rows:
    if y == 2023:
        for p in plans[:60]:
            pv = p.get("planVersion") or {}
            print(" ", p.get("id"), "|", (p.get("planType") or {}).get("name") if isinstance(p.get("planType"), dict) else p.get("planType"),
                  "|", p.get("name")[:60], "| GHO:", pv.get("isPartOfGHO"),
                  "| origReq:", pv.get("origRequirements"), "| revReq:", pv.get("revisedRequirements"),
                  "| funded:", pv.get("fundedTotal"))
