import json, struct, urllib.request
UA={'User-Agent':'scout-discovery/1.0'}
URL='https://data.gov.au/data/dataset/423000b8-5735-4447-bcb9-792644bcd7ea/resource/c79b3af6-3720-44ac-9e39-6a68f5635924/download/iprapid.zip'
TOTAL=1350841716
req = urllib.request.Request(URL, headers={**UA,'Range':f'bytes={TOTAL-65536}-{TOTAL-1}'})
with urllib.request.urlopen(req, timeout=90) as r:
    tail = r.read()
print('tail bytes:', len(tail), 'status 206 expected')
i = tail.rfind(b'PK\x05\x06')
assert i>=0, 'EOCD not found'
(eocd_disk, eocd_cd_disk, n_disk, n_total, cd_size, cd_off, clen) = struct.unpack('<HHHHIIH', tail[i+4:i+22])
print(f'EOCD: entries={n_total} cd_size={cd_size} cd_offset={cd_off}')
# central directory may start before our window; re-fetch enough
start = cd_off
need = cd_size
req2 = urllib.request.Request(URL, headers={**UA,'Range':f'bytes={start}-{start+need-1}'})
with urllib.request.urlopen(req2, timeout=90) as r2:
    cd = r2.read()
print('cd bytes:', len(cd))
members=[]
p=0
while p+46 <= len(cd):
    sig, vmade, vneed, flags, method, mtime, mdate, crc, csize, usize, nlen, elen, clen2, disk, iattr, eattr, lho = struct.unpack('<IHHHHHHIIIHHHHHII', cd[p:p+46])
    if sig != 0x02014b50: break
    name = cd[p+46:p+46+nlen].decode('utf-8', 'replace')
    members.append((name, csize, usize, method))
    p += 46+nlen+elen+clen2
print('members parsed:', len(members))
for name, csize, usize, method in members:
    print(f'{usize:>12,}  {csize:>12,}  m{method}  {name}')
