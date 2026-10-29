# Probe 2: per-window class balance at 50% coverage, plan-id grain uniqueness,
# and requirements cross-check fields for dated fixtures.
import csv, json, urllib.request
from collections import Counter, defaultdict

rows = []
with open('/opt/data/cache/scratch/fts/reqfund_global.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        rows.append(r)

elig = [r for r in rows if r['id'] and r['requirements']]

# grain: is (plan id, year) unique?
c = Counter((r['id'], r['year']) for r in elig)
print('(id,year) pairs:', len(c), 'of', len(elig), 'rows -> duplicates:', len(elig)-len(c))
dupes = [k for k, v in c.items() if v > 1][:5]
print('example dupes:', dupes)
plan_ids = set(r['id'] for r in elig)
print('distinct plan ids:', len(plan_ids))

# per-window class balance at 50% of requirements
for lo, hi in [('2000','2014'), ('2015','2019'), ('2020','2022'), ('2023','2026')]:
    pos = neg = 0
    for r in elig:
        if not (lo <= r['year'] <= hi):
            continue
        req = float(r['requirements'] or 0)
        fund = float(r['funding'] or 0)
        if req <= 0:
            continue
        if fund / req >= 0.5:
            pos += 1
        else:
            neg += 1
    print(f'window {lo}-{hi}: rows {pos+neg}, pos {pos}, neg {neg} (rate {pos/(pos+neg):.1%})')

# countries per window (clustering)
cc = defaultdict(set)
for r in elig:
    cc[r['year']].add(r['countryCode'])
for lo, hi in [('2000','2014'), ('2015','2019'), ('2020','2022'), ('2023','2026')]:
    countries = set()
    for y, s in cc.items():
        if lo <= y <= hi:
            countries |= s
    print(f'window {lo}-{hi}: {len(countries)} distinct countries')

# requirements cross-check: fetch orig/revised requirements for a few known plans
def fetch(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'scout-discovery-probe/1.0'})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)

print('\nplan requirements detail (orig vs revised, current vintage):')
for pid in (1116,):  # Yemen HRP 2023
    d = fetch(f'https://api.hpc.tools/v2/public/plan/{pid}')['data']
    print(' ', pid, d['planVersion']['name'], '| orig:', d.get('origRequirements'), '| revised:', d.get('revisedRequirements'),
          '| revisionState:', d.get('revisionState'))

# cross-check aggregate vs publisher's GHO summary product for 2023
tot_req_2023 = sum(float(r['requirements']) for r in elig if r['year'] == '2023')
tot_fund_2023 = sum(float(r['funding'] or 0) for r in elig if r['year'] == '2023')
print(f'\n2023 eligible aggregate: requirements {tot_req_2023/1e9:.1f}B, funding {tot_fund_2023/1e9:.1f}B, coverage {tot_fund_2023/tot_req_2023:.1%}')

# typeName for eligible rows (plan-type vocabulary)
print('\neligible typeName mix:', Counter(r['typeName'] for r in elig))
