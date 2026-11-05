# Fetch the archived OpenAQ v2 locations?country=IN capture (2023-04-25) and
# extract Indian locationids: names, coordinates, providers, sensor parameters.
import urllib.request, urllib.parse, json, time, collections

UA = {"User-Agent": "Mozilla/5.0 (dataset-factory-discovery/1.0)"}
TS = "20230425092626"
ORIG = "https://api.openaq.org/v2/locations?limit=10000&country=IN"
url = "http://web.archive.org/web/" + TS + "/" + ORIG
print("GET", url)
for attempt in range(3):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read()
        break
    except Exception as e:
        print("retry", attempt, type(e).__name__, str(e)[:150])
        time.sleep(5)
print("fetched", len(body), "B")
data = json.loads(body.decode("utf-8", "replace"))
res = data.get("results", [])
print("meta:", {k: data.get(k) for k in ("meta") if k in data})
print("num results:", len(res))
provs = collections.Counter()
params = collections.Counter()
pm25_locs = []
for r in res:
    provs[(r.get("providerName") or "?")] += 1
    plist = tuple(sorted({s.get("parameter", {}).get("name") if isinstance(s.get("parameter"), dict) else s.get("parameter") for s in (r.get("sensors") or [])}))
    params[plist] += 1
    names = {s.get("parameter", {}).get("name") if isinstance(s.get("parameter"), dict) else s.get("parameter") for s in (r.get("sensors") or [])}
    if "pm25" in names:
        pm25_locs.append(r)
print("providers:", provs.most_common())
print("coordinates present:", sum(1 for r in res if r.get("coordinates")))
print("pm25 locations:", len(pm25_locs))
if res:
    print("SAMPLE:", json.dumps(res[0], indent=1)[:1500])
if pm25_locs:
    print("PM25 SAMPLE:", json.dumps(pm25_locs[0], indent=1)[:1200])
# save compact: id, name, coords, provider, first/last datetime, sensor params
compact = []
for r in res:
    names = sorted({(s.get("parameter", {}) or {}).get("name") if isinstance(s.get("parameter"), dict) else s.get("parameter") for s in (r.get("sensors") or [])} - {None})
    compact.append({
        "id": r.get("id"), "name": r.get("name"), "provider": r.get("providerName"),
        "city": (r.get("city") or ""), "coords": r.get("coordinates"),
        "first": r.get("firstUpdated") or r.get("datetimeFirst") or (r.get("datetime") or [None, None])[0],
        "last": r.get("lastUpdated") or r.get("datetimeLast") or (r.get("datetime") or [None, None])[-1],
        "params": names,
    })
out = "/opt/data/cache/scratch/sea-tick-2026-11-05/openaq_in_locations_2023_04_25.json"
json.dump({"capture": TS, "n": len(compact), "locations": compact}, open(out, "w"), indent=1)
print("wrote", out)
# yearly coverage histogram by first-updated year for pm25 locations
years = collections.Counter()
for r in pm25_locs:
    f = r.get("firstUpdated") or (r.get("datetime") or [None])[0] or "?"
    years[str(f)[:4]] += 1
print("pm25 locations by first-updated year:", dict(sorted(years.items())))
