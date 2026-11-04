import urllib.request, re
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) scout-discovery/1.0'}
def fetch(url, n=150000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(n)
b = fetch('https://www.ipaustralia.gov.au/')
links = re.findall(rb'href="([^"]+)"', b)
for x in links:
    s = x.decode(errors='replace')
    if any(k in s.lower() for k in ['copyright','terms','legal','privacy']):
        print(s)
