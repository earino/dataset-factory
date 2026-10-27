import json, time, urllib.request

TOK = "1|qPD6pk5OPGVIqNHAqMFtyfCDb0vnUDTFqgDkakfia33cbb7c"
STATES = ["Perlis","Kedah","Pulau Pinang","Perak","Selangor","Wilayah Persekutuan Kuala Lumpur",
          "Negeri Sembilan","Melaka","Johor","Pahang","Terengganu","Kelantan","Sarawak","Sabah",
          "Wilayah Persekutuan Labuan"]
tot_bytes, tot_stations, t0 = 0, 0, time.time()
per_state = {}
for s in STATES:
    body = json.dumps({"state": s, "district": "ALL", "station_name": "ALL", "parameter": "waterlevel"}).encode()
    req = urllib.request.Request("https://publicinfobanjir.water.gov.my/api/detailstation", data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + TOK,
                 "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/131.0"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = r.read()
            d = json.loads(data)
            n = len(d.get("data", d) if isinstance(d, dict) else d)
            tot_bytes += len(data); tot_stations += n
            per_state[s] = (n, len(data))
            print(f"{s:40s} stations={n:3d} bytes={len(data)}")
    except Exception as e:
        print(f"{s:40s} ERROR {e}")
        per_state[s] = None
el = time.time() - t0
print(f"\nTOTAL: {tot_stations} stations, {tot_bytes} bytes, {el:.1f}s for {len(STATES)} state requests")
json.dump(per_state, open("my_river_state_counts.json","w"), indent=1)
