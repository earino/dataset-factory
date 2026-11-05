# Watch-trigger re-checks for the 2026-11-05 South & SE Asia discovery tick.
# Anonymous, read-only, bounded reads. Prints measured evidence only.
import urllib.request, urllib.error, time, subprocess, socket

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TIMEOUT = 20

def probe(name, url, read_n=4096):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(read_n)
            print(f"[{name}] {url}")
            print(f"  -> HTTP {r.status}, {len(body)} B (bounded head-read), {time.time()-t0:.2f}s, final_url={r.geturl()[:120]}")
            return r.status, body
    except urllib.error.HTTPError as e:
        print(f"[{name}] {url}")
        print(f"  -> HTTP {e.code} {e.reason} in {time.time()-t0:.2f}s")
        return e.code, b""
    except Exception as e:
        print(f"[{name}] {url}")
        print(f"  -> FAIL {type(e).__name__}: {str(e)[:180]} ({time.time()-t0:.2f}s)")
        return None, b""

# 1. IMD free-data watch trigger (recorded in imd-station-observation-series):
#    reopen only if a station-level product appears in the free list.
st, body = probe("imd-free-data", "https://dsp.imdpune.gov.in/home_freedataaccess.php", read_n=200_000)
if body:
    txt = body.decode("latin-1", "replace")
    low = txt.lower()
    print("  free-list keywords: station=%s gridded=%s temperature=%s rainfall=%s cyclonic=%s"
          % ("station" in low, "gridded" in low, "temperature" in low, "rainfall" in low, "cyclonic" in low))

# 2. BMKG quarterly watch trigger (bmkg-earthquake-felt):
#    reopen if an anonymous bulk historical channel appears.
probe("bmkg-eventcatalog", "https://repogempa.bmkg.go.id/eventcatalog")
probe("bmkg-data-portal", "https://data.bmkg.go.id")

# 3. data.gov.vn DNS watch (vietnam-nso-publications): relaunch or new host?
for host in ("data.gov.vn", "www.data.gov.vn"):
    try:
        r = subprocess.run(["getent", "hosts", host], capture_output=True, text=True, timeout=15)
        print(f"[dns {host}] rc={r.returncode} out={r.stdout.strip()[:120]!r}")
    except Exception as e:
        print(f"[dns {host}] FAIL {type(e).__name__}: {e}")

# 4. data.gov.in reachability re-measure (india-datagovin-portal; recorded
#    blocked from coordinator + hel1 on 2026-11-04).
probe("datagovin-www", "https://www.data.gov.in/")
probe("datagovin-api", "https://api.data.gov.in/")

print("done")
