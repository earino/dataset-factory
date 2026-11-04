import urllib.request
UA={'User-Agent':'scout-discovery/1.0'}
def fetch(url, method='GET', hdrs=None, out=None):
    req = urllib.request.Request(url, method=method, headers={**UA, **(hdrs or {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        if out:
            with open(out,'wb') as f:
                while True:
                    chunk = r.read(1<<16)
                    if not chunk: break
                    f.write(chunk)
            return r.status, dict(r.headers)
        return r.status, dict(r.headers), r.read(256)
st, h, b = fetch('https://data.gov.au/data/dataset/423000b8-5735-4447-bcb9-792644bcd7ea/resource/c79b3af6-3720-44ac-9e39-6a68f5635924/download/iprapid.zip', method='HEAD')
print('ZIP HEAD status', st, 'content-length', h.get('Content-Length'), 'last-modified', h.get('Last-Modified'))
st2, h2 = fetch('https://data.gov.au/data/dataset/423000b8-5735-4447-bcb9-792644bcd7ea/resource/f4750acd-decc-4b7b-99c9-4ed1c3c43441/download/ip-rapid-data-dictionary.pdf', out='iprapid-data-dictionary.pdf')
print('dictionary saved', st2, h2.get('Content-Length'))
import hashlib
print('sha256', hashlib.sha256(open('iprapid-data-dictionary.pdf','rb').read()).hexdigest()[:32])
