# Probe: full-file aggregate pass over the IPO trade mark domestic snapshot.
# ONE anonymous GET (63,238,846 B) streamed through zlib + UTF-16LE; nothing is
# written to disk except this aggregate JSON; no labelled rows are emitted
# (construction belongs on a worker). Reproduces every number in notes.md's
# aggregate table and record.json splits. Run 2026-10-27, wall 5.1 s on the
# coordinator (1.9 GiB / 4 vCPU).
import urllib.request, zlib, time, json
from collections import defaultdict

URL = "https://assets.publishing.service.gov.uk/media/5a82e5f4e5274a2e87dc387d/opendatadomestic.zip"
OUT = "ipo_tm_aggregates.json"

POS_LAPSED = {"Dead", "Removed", "Expired", "Cancelled", "Surrendered", "Registered", "Merged"}
NEG = {"Refused", "Withdrawn"}

t0 = time.time()
req = urllib.request.Request(URL, headers={"User-Agent": "scout-probe"})
resp = urllib.request.urlopen(req, timeout=180)
http_len = int(resp.headers.get("Content-Length", 0))
dec = zlib.decompressobj(-15)
pre = resp.read(30)
nlen, elen = pre[26] | (pre[27] << 8), pre[28] | (pre[29] << 8)
resp.read(nlen + elen)

rows = 0
field_counts = defaultdict(int)
per_year = defaultdict(lambda: {"n": 0, "pos": 0, "neg": 0, "cens": 0,
                                "status": defaultdict(int), "shift": 0})
years_all = defaultdict(int)
sorted_violations, last_mark_int = 0, -1
owner_dup, blank_filed, bad_short, neg_with_regdate = 0, 0, 0, 0
shift_rows_total, bad_examples = 0, []
seen = set()

def handle_row(fields):
    global rows, sorted_violations, last_mark_int
    global owner_dup, blank_filed, bad_short, neg_with_regdate, shift_rows_total
    rows += 1
    field_counts[len(fields)] += 1
    if len(fields) < 15:
        bad_short += 1
        return
    tm, status, filed, regd = fields[0].strip(), fields[7].strip(), fields[12].strip(), fields[14].strip()
    if len(fields) != 62:
        shift_rows_total += 1
        if len(bad_examples) < 8:
            bad_examples.append([f[:20] for f in fields[:10]])
    try:
        tm_int = int(tm.replace("UK", "").replace(" ", "").lstrip("0") or "0")
    except ValueError:
        tm_int = -1
    if tm_int >= 0:
        if tm_int <= last_mark_int - 5 and last_mark_int >= 0:
            sorted_violations += 1
        last_mark_int = tm_int
    if not filed or not filed[:4].isdigit():
        blank_filed += 1
        return
    years_all[filed[:4]] += 1
    if tm_int >= 0:
        if tm_int in seen:
            owner_dup += 1
            return
        seen.add(tm_int)
    y = filed[:4]
    if y >= "2010":
        d = per_year[y]
        d["n"] += 1
        d["status"][status] += 1
        if regd:
            d["pos"] += 1
            if status not in POS_LAPSED:
                d["shift"] += 1
        elif status in NEG:
            d["neg"] += 1
        else:
            d["cens"] += 1
        if regd and status in NEG:
            neg_with_regdate += 1

tail, bytebuf = "", b""
while True:
    raw = resp.read(1 << 18)
    text_part = dec.decompress(raw, 0) if raw else dec.flush()
    if text_part:
        bytebuf += text_part
        usable = len(bytebuf) - (len(bytebuf) % 2)
        tail += bytebuf[:usable].decode("utf-16-le", "replace")
        bytebuf = bytebuf[usable:]
        lines = tail.split("\r")
        tail = lines[-1]
        for ln in lines[:-1]:
            ln = ln.strip("\n")
            if ln.strip():
                handle_row(ln.split("|"))
    if not raw:
        break

res = {
    "url": URL, "http_bytes": http_len, "wall_s": round(time.time() - t0, 1),
    "rows_seen": rows, "distinct_marks_total": len(seen),
    "field_count_distribution": dict(sorted(field_counts.items())),
    "rows_with_field_count_ne_62": shift_rows_total, "bad_examples": bad_examples,
    "bad_short_rows": bad_short, "owner_dup_rows": owner_dup,
    "blank_or_bad_filed": blank_filed, "sortedness_violations": sorted_violations,
    "neg_with_regdate": neg_with_regdate,
    "years_all": dict(sorted(years_all.items())),
    "per_year_2010plus": {y: {"n": d["n"], "pos": d["pos"], "neg": d["neg"], "cens": d["cens"],
                              "pos_status_outside_lapsed_set": d["shift"],
                              "status": dict(sorted(d["status"].items(), key=lambda kv: -kv[1]))}
                          for y, d in sorted(per_year.items())},
}
with open(OUT, "w") as f:
    json.dump(res, f, indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("years_all", "per_year_2010plus", "bad_examples")}, indent=1))
