# Probe 5: class balance at >=50% of ORIGINAL (launch) requirements, bounded to
# single-country-attribution plans in cohorts 2016, 2019, 2023. Saves evidence.
import csv, json, time, urllib.request
from collections import defaultdict, Counter

rows = []
with open('/opt/data/cache/scratch/fts/reqfund_global.csv', newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        rows.append(r)
elig = [r for r in rows if r['id'] and r['requirements']]

g = defaultdict(list)
for r in elig:
    g[(r['id'], r['year'])].append(r)

def fetch(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'scout-discovery-probe/1.0'})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)

out = {}
for cohort in ('2016', '2019', '2023'):
    singles = [(k, v[0]) for k, v in g.items() if k[1] == cohort and len(v) == 1]
    n_pos = n_neg = n_req = 0
    detail = []
    for (pid, yr), r in singles:
        try:
            d = fetch(f'https://api.hpc.tools/v2/public/plan/{pid}')['data']
        except Exception as e:
            print('err', pid, e)
            continue
        o = d.get('origRequirements')
        fund = float(r['funding'] or 0)
        if not o or o <= 0:
            continue
        n_req += 1
        cov = fund / o
        lab = cov >= 0.5
        n_pos += lab
        n_neg += (not lab)
        detail.append({'plan': pid, 'year': yr, 'country': r['countryCode'], 'orig': o,
                       'funding': fund, 'coverage_of_orig': round(cov, 4), 'label_50': int(lab)})
        time.sleep(0.12)
    out[cohort] = {'single_country_plans': len(singles), 'with_orig_req': n_req,
                   'pos_ge50_of_orig': n_pos, 'neg': n_neg}
    print(f'cohort {cohort}: {n_req} plans with orig req; pos {n_pos} neg {n_neg} rate {n_pos/max(n_req,1):.1%}')
    time.sleep(0.3)

json.dump(out, open('/opt/data/cache/scratch/fts/orig_balance.json', 'w'), indent=1)
print('saved orig_balance.json')
