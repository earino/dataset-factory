# Probe 4: (a) verify regional-plan country-slice grain; (b) GHO December
# cross-check of origRequirements as the launch-time value; (c) funding
# slice sum vs plan API total for a regional plan.
import csv, json, time, urllib.request

rows = []
with open('/opt/data/cache/scratch/fts/reqfund_global.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        rows.append(r)
elig = [r for r in rows if r['id'] and r['requirements']]

from collections import defaultdict
g = defaultdict(list)
for r in elig:
    g[(r['id'], r['year'])].append(r)

# (a) show all rows for two (id, year) groups that have >1 row
shown = 0
for k in sorted(g):
    if len(g[k]) > 1:
        rs = g[k]
        print(f'group {k}: {len(rs)} rows, name={rs[0]["name"][:50]}')
        for r in rs:
            print(f'   cc={r["countryCode"]} type={r["typeName"]} req={r["requirements"]} fund={r["funding"]} pct={r["percentFunded"]}')
        print(f'   -> sums: req={sum(float(r["requirements"]) for r in rs):.0f} fund={sum(float(r["funding"] or 0) for r in rs):.0f}')
        shown += 1
        if shown >= 3:
            break

def fetch(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'scout-discovery-probe/1.0'})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)

# (b) Afghanistan 2023: find plan ids for AFG 2023 and print orig/revised
afg = sorted({r['id'] for r in elig if r['countryCode'] == 'AFG' and r['year'] == '2023'})
print('\nAFG 2023 plan ids:', afg)
for pid in afg:
    d = fetch(f'https://api.hpc.tools/v2/public/plan/{pid}')['data']
    pv = d['planVersion']
    print(' ', pid, pv['name'], '| orig:', d.get('origRequirements'), '| revised:', d.get('revisedRequirements'))

# (c) regional plan funding cross-check: use one multi-row group's plan id
reg_pid = None
for k in sorted(g):
    if len(g[k]) > 1:
        reg_pid = k[0]
        break
if reg_pid:
    yr = [k[1] for k in g if k[0] == reg_pid][0]
    d = fetch(f'https://api.hpc.tools/v1/public/fts/flow?planId={reg_pid}&year={yr}')['data']
    api_total = d['incoming']['fundingTotal']
    csv_total = sum(float(r['funding'] or 0) for r in g[(reg_pid, yr)])
    print(f'\nregional plan {reg_pid} {yr}: API incoming total {api_total} vs CSV slice sum {csv_total:.0f} (ratio {csv_total/max(api_total,1):.2f})')
