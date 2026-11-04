import json, urllib.request
UA={'User-Agent':'scout-discovery/1.0'}
def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())
d = get('https://data.gov.au/data/api/3/action/resource_show?id=c79b3af6-3720-44ac-9e39-6a68f5635924')
r = d['result']
for k in ['name','format','url','url_type','mimetype','size','created','last_modified','state','license_type','datastore_active']:
    print(k, ':', r.get(k))
print('--- dictionary resource ---')
d2 = get('https://data.gov.au/data/api/3/action/resource_show?id=f4750acd-decc-4b7b-99c9-4ed1c3c43441')
r2 = d2['result']
for k in ['name','format','url','url_type','size','last_modified','state']:
    print(k, ':', r2.get(k))
