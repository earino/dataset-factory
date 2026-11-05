# Full-window DAILY class measurement for cpcb-aqi-exceedance (train 2019-2023,
# eval 2024, holdout 2025) via the XKDR demo-key measurements API.
# Streams daily aggregates to a scratch rows-file; markers enable resume;
# all counts computed from the rows-file at the end. Nothing bulk is stored.
import urllib.request, urllib.parse, csv, io, json, time, os, sys, collections

BASE = "https://airquality.xkdr.org"
DEMO_KEY = "aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe"  # published on XKDR's front page
HDRS = {"Authorization": "Bearer " + DEMO_KEY, "User-Agent": "Mozilla/5.0 (dataset-factory-discovery/1.0)"}
THRESH = 90.0
OUT = "/opt/data/dataset-factory/candidates/cpcb-aqi-exceedance/probe/out/xkdr_daily_counts_2019_2025_2026_11_05.json"
ROWS = "/opt/data/cache/scratch/sea-tick-2026-11-05/xkdr_daily_rows.txt"
MARK = "/opt/data/cache/scratch/sea-tick-2026-11-05/month_batches.jsonl"
STATIONS = "/opt/data/dataset-factory/candidates/cpcb-aqi-exceedance/probe/out/xkdr_stations_2026_11_04.json"

def api(path, params, timeout=90, tries=6):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), dict(r.headers), None
        except urllib.error.HTTPError as e:
            # 2026-11-05: the origin served intermittent 401 and 400 windows
            # tonight (identical requests succeed on retry) - all retryable.
            body = b""
            try:
                body = e.read()[:200]
            except Exception:
                pass
            if e.code in (400, 401, 429, 500, 502, 503, 504):
                wait = min(15 * (2 ** attempt), 120)
                print(f"    HTTP {e.code} attempt {attempt}: backoff {wait}s body={body[:120]}", flush=True)
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            print(f"    net {type(e).__name__} attempt {attempt}: {str(e)[:100]}", flush=True)
            time.sleep(min(10 * (2 ** attempt), 60))
    return None, None, "exhausted"

body, hdrs, err = api("/v1/meta", {})
assert body is not None, f"sanity /v1/meta failed: {err}"
meta = json.loads(body)
print("SANITY meta ok: tier=%s cap=%s" % (meta["your_tier"], meta["max_rows_per_query"]), flush=True)

st_data = json.load(open(STATIONS))["data"]
cpcb = [s for s in st_data if s["source"] == "cpcb_caaqm" and "PM2.5" in s["parameters"]]
st_meta = {s["station_id"]: s for s in cpcb}
print(f"cpcb pm25 stations: {len(cpcb)}", flush=True)
BATCH = 275
batches = [cpcb[i:i + BATCH] for i in range(0, len(cpcb), BATCH)]
months = [(y, m) for y in range(2019, 2026) for m in range(1, 13)]
import calendar
MDAYS = {m: calendar.monthrange(y, m)[1] for (y, m) in months}

done = set()
if os.path.exists(MARK):
    for line in open(MARK):
        r = json.loads(line)
        done.add((r["y"], r["m"], r["b"]))
    print(f"resume: {len(done)} month-batches done", flush=True)

t0 = time.time(); nreq = 0; truncated_any = False
rows_f = open(ROWS, "a")
for (y, m) in months:
    key = f"{y}-{m:02d}"
    last_day = f"{y}-{m:02d}-{MDAYS[m]:02d}"
    for bi, batch in enumerate(batches):
        if (y, m, bi) in done:
            continue
        q = [("parameter", "PM2.5"), ("agg", "daily"), ("start", f"{key}-01"),
             ("end", last_day), ("format", "csv")]
        for s in batch:
            q.append(("station", s["station_id"]))
        body, hdrs, err = api("/v1/measurements", q)
        if body is None:
            print(f"FATAL {key} b{bi}: {err} - rows preserved, re-run resumes", flush=True)
            rows_f.close(); sys.exit(1)
        nreq += 1
        if hdrs.get("X-Truncated", "").lower() == "true":
            truncated_any = True
            print(f"  TRUNCATED {key} b{bi} rows={hdrs.get('X-Row-Count')}", flush=True)
        n_write = 0
        for row in csv.DictReader(io.StringIO(body.decode("utf-8", "replace"))):
            try:
                mean = float(row["mean"]); n = int(row["n"])
            except (ValueError, TypeError):
                continue
            rows_f.write(f"{row['station_id']}|{row['period_start'][:10]}|{n}|{mean:.4f}\n")
            n_write += 1
        rows_f.flush(); os.fsync(rows_f.fileno())
        with open(MARK, "a") as f:
            f.write(json.dumps({"y": y, "m": m, "b": bi}) + "\n")
        time.sleep(0.8)
    print(f"{key} fetched (cum requests {nreq}, {time.time()-t0:.0f}s)", flush=True)
rows_f.close()

# aggregate from the rows file
month_tot = collections.defaultdict(lambda: {"station_days": 0, "pos_n18": 0, "pos_n1": 0, "stations": set(), "days": set()})
state_month = collections.defaultdict(lambda: [0, 0, 0])
stmonth = collections.defaultdict(lambda: [0, 0])
day_pos = collections.defaultdict(lambda: [0, 0])
nrows = 0
seen = set()
for line in open(ROWS):
    sid, date, n, mean = line.rstrip("\n").split("|")
    n = int(n); mean = float(mean)
    k = (sid, date)
    if k in seen:
        continue
    seen.add(k)
    nrows += 1
    y, m = int(date[:4]), int(date[5:7])
    mt = month_tot[f"{y}-{m:02d}"]
    mt["station_days"] += 1; mt["stations"].add(sid); mt["days"].add(date)
    pos18 = (n >= 18 and mean > THRESH); pos1 = mean > THRESH
    if pos18: mt["pos_n18"] += 1
    if pos1: mt["pos_n1"] += 1
    sm = state_month[(st_meta.get(sid, {}).get("state_name", "unknown"), y, m)]
    sm[0] += 1
    if pos18: sm[1] += 1
    if pos1: sm[2] += 1
    sml = stmonth[(sid, y, m)]
    sml[0] += 1
    if pos18: sml[1] += 1
    d = day_pos[date]; d[0] += 1
    if pos18: d[1] += 1

SEASON = {12:"DJF",1:"DJF",2:"DJF",3:"MAM",4:"MAM",5:"MAM",6:"JJAS",7:"JJAS",8:"JJAS",9:"JJAS",10:"ON",11:"ON"}
def window(y0, y1):
    sd = p18 = p1 = 0
    stations = set(); posdays = set(); cells = set()
    for k, v in month_tot.items():
        y = int(k[:4])
        if y0 <= y <= y1:
            sd += v["station_days"]; p18 += v["pos_n18"]; p1 += v["pos_n1"]
    for (st, y, m), v in state_month.items():
        if y0 <= y <= y1 and v[1] > 0:
            cells.add((st, SEASON[m]))
    for (sid, y, m), v in stmonth.items():
        if y0 <= y <= y1 and v[0] > 0:
            stations.add(sid)
    for date, v in day_pos.items():
        y = int(date[:4])
        if y0 <= y <= y1 and v[1] > 0:
            posdays.add(date)
    return {"station_days": sd, "pos_n18": p18, "pos_n1": p1,
            "rate_n18": round(p18 / sd, 4) if sd else None,
            "distinct_stations_reporting": len(stations),
            "distinct_positive_days_n18": len(posdays),
            "positive_state_x_season_cells": len(cells)}

out = {
 "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
 "channel": "XKDR measurements API, demo tier (front-page key), agg=daily, parameter=PM2.5, source cpcb_caaqm only",
 "tier_note": "demo tier served 2019-2025 measurement queries this run (front-page prose 'can only read the 2024 bulk files' applies to /v1/files, not /v1/measurements)",
 "threshold_ug_m3": THRESH, "completeness_primary": "n_hours >= 18 of 24; pos_n1 = no completeness filter",
 "season_def": "DJF=Dec-Feb, MAM=Mar-May, JJAS=Jun-Sep, ON=Oct-Nov",
 "truncated_any": truncated_any,
 "per_month": {k: {"station_days": v["station_days"], "pos_n18": v["pos_n18"], "pos_n1": v["pos_n1"],
                   "stations": len(v["stations"]), "days": len(v["days"])} for k, v in sorted(month_tot.items())},
 "windows": {
    "proposed_2026_11_04": {"train_2019_2023": window(2019, 2023), "eval_2024": window(2024, 2024), "holdout_2025": window(2025, 2025)},
    "recut_2026_11_05": {"train_2019_2022": window(2019, 2022), "eval_2023": window(2023, 2023), "holdout_2024": window(2024, 2024), "excluded_tail_2025_04_to_09": window(2025, 2025)},
 },
 "state_month_triples": {f"{k[0]}|{k[1]}-{k[2]:02d}": v for k, v in sorted(state_month.items(), key=lambda kv: (str(kv[0][0]), kv[0][1], kv[0][2]))},
 "rows_total": nrows, "requests": nreq, "wall_seconds": round(time.time() - t0, 1),
}
json.dump(out, open(OUT, "w"), indent=1)
print("WINDOWS:", json.dumps(out["windows"], indent=1))
print("WROTE", OUT, "| rows:", nrows, "| requests:", nreq, "| wall:", out["wall_seconds"], "s")
