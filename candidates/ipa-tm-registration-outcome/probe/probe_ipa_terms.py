import urllib.request, re
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) scout-discovery/1.0'}
def fetch(url, n=120000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(n)
for u in ['https://www.ipaustralia.gov.au/about-us/using-this-website/copyright',
          'https://www.ipaustralia.gov.au/tools-and-research/professional-resources/data-research-and-reports/open-ip-data']:
    try:
        b = fetch(u)
        txt = re.sub(rb'<[^>]+>', b' ', b)
        txt = re.sub(rb'\s+', b' ', txt).decode(errors='replace')
        print('=== ', u)
        # print windows around licence-ish keywords
        for kw in ['Creative Commons','licence','copyright','attribution','terms']:
            for m in re.finditer(kw, txt, re.I):
                s = max(0, m.start()-160); e = min(len(txt), m.end()+320)
                print(f'[{kw}] ...{txt[s:e]}...')
                break
    except Exception as e:
        print(u, 'ERR', e)
