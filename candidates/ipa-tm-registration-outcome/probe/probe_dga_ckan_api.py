import json, urllib.request
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent':'scout-discovery/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()
url = 'https://data.gov.au/api/3/action/package_search?q=IPGOD&rows=10'
st, body = get(url)
d = json.loads(body)
print('status', st, 'success', d.get('success'), 'count', d['result']['count'])
for p in d['result']['results']:
    print('---')
    print(p.get('title'))
    print('org:', (p.get('organization') or {}).get('title'))
    print('license_id:', p.get('license_id'), '| license_title:', p.get('license_title'))
    print('num_resources:', len(p.get('resources', [])))
    for r in p.get('resources', [])[:6]:
        print('   res:', (r.get('name') or r.get('description') or '?')[:80], '|', r.get('format'), '|', r.get('license_type'), '|', r.get('url')[:110] if r.get('url') else None)
