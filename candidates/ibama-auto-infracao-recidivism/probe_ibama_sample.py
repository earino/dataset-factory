#!/usr/bin/env python3
# Bounded IBAMA sample: Range-request the head of the plain AIE_MOB CSVs on blob storage
# and HEAD the aux table sizes. No bulk download: max 96 KB read per file.
import urllib.request, ssl

ctx = ssl.create_default_context()
BASE = "https://stibamadadosabertosprd.blob.core.windows.net/dados-abertos/dados"
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}

def ranged(url, n=65536):
    req = urllib.request.Request(url, headers={**H, "Range": f"bytes=0-{n-1}"})
    with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
        return r.read(), dict(r.headers)

def head(url):
    req = urllib.request.Request(url, headers=H, method="HEAD")
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return dict(r.headers)

# 1. AIe Mob enquadramento CSV (plain, Range-able) - shows AIe-era schema
for url in [f"{BASE}/AIE_MOB/auto_infracao/aie_enquadramento.csv",
            f"{BASE}/AIE_MOB/auto_infracao/aie_enquadramentocomp.csv"]:
    try:
        b, hd = ranged(url, 32768)
        s = b.decode("utf-8", "replace")
        print("== SAMPLE", url.split("/")[-1], "==")
        print("total length hdr:", hd.get("Content-Length"), "| content-range:", hd.get("Content-Range"))
        lines = s.splitlines()
        print("header:", lines[0][:500])
        for ln in lines[1:4]:
            print("row:", ln[:400])
        print()
    except Exception as e:
        print("FAILED", url, repr(e))

# 2. Sizes of the aux tables (plan cost) + confirm the two bulk zips
for url in [f"{BASE}/SIFISC/auto_infracao/especime/especime.csv",
            f"{BASE}/SIFISC/auto_infracao/coordenada/coordenada.csv",
            f"{BASE}/SIFISC/auto_infracao/bioma/bioma.csv",
            f"{BASE}/SIFISC/auto_infracao/auto_infracao/auto_infracao_csv.zip",
            f"{BASE}/SIFISC/auto_infracao/auto_infracao/auto_infracao_json.zip"]:
    try:
        hd = head(url)
        print("HEAD", url.split("/")[-1], "->", hd.get("Content-Length"), "bytes")
    except Exception as e:
        print("HEAD FAILED", url.split("/")[-1], repr(e))

# 3. Small aux table full read (bioma - likely tiny) to see served schema quality
try:
    b, hd = ranged(f"{BASE}/SIFISC/auto_infracao/bioma/bioma.csv", 65536)
    print("\n== bioma.csv (bounded 64KB) ==")
    print(b.decode("utf-8", "replace")[:800])
except Exception as e:
    print("bioma read failed:", repr(e))
