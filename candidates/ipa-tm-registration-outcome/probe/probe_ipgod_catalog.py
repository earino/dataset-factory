import json, urllib.request
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent':'scout-discovery/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())
d = get('https://data.gov.au/data/api/3/action/package_search?q=IPGOD&rows=16')
print('count', d['result']['count'])
for p in d['result']['results']:
    org = (p.get('organization') or {}).get('title')
    print('---')
    print(p['title'], '|', p.get('name'))
    print('  org:', org, '| license_id:', p.get('license_id'), '| license_title:', p.get('license_title'))
    print('  notes:', (p.get('notes') or '')[:180].replace('\n',' '))
    for r in p.get('resources', [])[:8]:
        print('   res:', (r.get('name') or '')[:70], '|', r.get('format'), '|', (r.get('url') or '')[:120])
