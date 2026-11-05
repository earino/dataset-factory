# Re-analyze the archived OpenAQ v2 country=IN capture with the correct v2 schema
# (entity / sources / parameters), isolating government CPCB pm25 locations.
import json, collections

data = json.loads(open("openaq_in_capture_id_.json", "rb").read().decode("utf-8", "replace"))
res = data["results"]
print("meta.license:", data["meta"].get("license"), "| found:", data["meta"].get("found"))

ents = collections.Counter(r.get("entity") or "?" for r in res)
print("entities:", ents.most_common())
src_names = collections.Counter()
for r in res:
    for s in (r.get("sources") or []):
        src_names[s.get("name")] += 1
print("source names (top 20):", src_names.most_common(20))

gov = [r for r in res if (r.get("entity") == "government")]
print("government locations:", len(gov))
gov_src = collections.Counter()
for r in gov:
    for s in (r.get("sources") or []):
        gov_src[s.get("name")] += 1
print("government source names:", gov_src.most_common(15))

def has_pm25(r):
    return any((p.get("parameter") == "pm25") for p in (r.get("parameters") or []))

cpcbish = [r for r in gov if any("cpcb" in (s.get("name") or "").lower() or "cpcb" in (s.get("organization") or "").lower() for s in (r.get("sources") or []))]
print("government locations with a CPCB-named source:", len(cpcbish), "of which pm25:", sum(1 for r in cpcbish if has_pm25(r)))
if cpcbish:
    r0 = cpcbish[0]
    print("CPCB SAMPLE:", json.dumps({k: r0.get(k) for k in ("id", "name", "city", "coordinates", "entity", "sensorType", "firstUpdated", "lastUpdated", "isMobile", "isAnalysis")}, indent=1))
    p0 = [p for p in r0["parameters"] if p.get("parameter") == "pm25"][0]
    print("  pm25 param:", json.dumps(p0))
    ids = sorted(r["id"] for r in cpcbish)
    print("  id range:", ids[0], "..", ids[-1], "n=", len(ids))
    yrs = collections.Counter(str(r.get("firstUpdated"))[:4] for r in cpcbish)
    print("  firstUpdated years:", dict(sorted(yrs.items())))
    yrs2 = collections.Counter(str(r.get("lastUpdated"))[:4] for r in cpcbish)
    print("  lastUpdated years:", dict(sorted(yrs2.items())))

compact = []
for r in res:
    names = sorted({p.get("parameter") for p in (r.get("parameters") or [])} - {None})
    compact.append({
        "id": r.get("id"), "name": r.get("name"), "entity": r.get("entity"),
        "sources": [s.get("name") for s in (r.get("sources") or [])],
        "city": r.get("city") or "", "coords": r.get("coordinates"),
        "first": r.get("firstUpdated"), "last": r.get("lastUpdated"),
        "sensorType": r.get("sensorType"), "isMobile": r.get("isMobile"),
        "params": names,
    })
out = "openaq_in_locations_2023_04_25_compact.json"
json.dump({"capture": "20230425092626", "meta_license": data["meta"].get("license"),
           "n": len(compact), "locations": compact}, open(out, "w"), indent=1)
print("wrote", out)
