#!/usr/bin/env python3
"""Discovery worker probe afdb-panel-probe-001 (2026-11-05): the afdb-project-cancellation
record's next_action steps (2)+(3) in one bounded pass - worker-side reachability of the
57 afdb.org IATI XML URLs plus the full-panel aggregate counts the split-capacity contract
needs. Read-only source measurement: counts only, no labelled rows, no CSVs, no task
construction. Stdlib only. No credentials in the container.

Outputs: one JSON line per step to stdout (container.log) and /output/summary.json.

Bounds: <= 130 HTTP requests, <= 400 MB total download, 45 s per request, 12-minute hard
deadline inside a 15-minute job. Exits 0 when the summary was written, even if targets
failed (a blocked channel is a measurement, not a crash).
"""
import gzip
import hashlib
import json
import statistics
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from collections import Counter, defaultdict
from pathlib import Path

START = time.time()
DEADLINE = START + 12 * 60
BUDGET_REQUESTS = 130
BUDGET_BYTES = 400 * 1024 * 1024
PER_REQ_TIMEOUT = 45
WORK = Path("/work")
OUT = Path("/output")

state = {"requests": 0, "bytes": 0}
summary = {
    "job": "afdb-panel-probe-001",
    "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "bounds": {"requests": BUDGET_REQUESTS, "bytes_total": BUDGET_BYTES,
               "per_request_s": PER_REQ_TIMEOUT, "deadline_s": 12 * 60},
    "complete": False,
    "steps": [],
}


def log(step):
    summary["steps"].append(step)
    print(json.dumps(step, ensure_ascii=False)[:3500], flush=True)


def fetch(url, max_bytes=64 * 1024 * 1024, to_path=None, timeout=PER_REQ_TIMEOUT):
    """GET with redirects; returns dict with status/body-or-path/bytes/elapsed/sha256."""
    state["requests"] += 1
    step = {"url": url, "t0": time.time()}
    req = urllib.request.Request(url, headers={"User-Agent": "dataset-factory-discovery/1.0",
                                               "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data_len = 0
            h = hashlib.sha256()
            chunks = []
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                data_len += len(chunk)
                state["bytes"] += len(chunk)
                h.update(chunk)
                if to_path is None:
                    chunks.append(chunk)
                else:
                    with open(to_path, "ab") as fh:
                        fh.write(chunk)
                if data_len > max_bytes:
                    step["error"] = "over single-file byte cap"
                    break
            body = b"".join(chunks) if to_path is None else None
            enc = (resp.headers.get("Content-Encoding") or "").lower()
            if body is not None and enc == "gzip":
                body = gzip.decompress(body)
            elif body is not None and enc == "deflate":
                body = zlib.decompress(body)
            step.update({"status": resp.status,
                         "content_type": resp.headers.get("Content-Type"),
                         "content_encoding": enc or None,
                         "content_length_header": resp.headers.get("Content-Length"),
                         "last_modified": resp.headers.get("Last-Modified"),
                         "bytes": data_len, "sha256": h.hexdigest(),
                         "elapsed_s": round(time.time() - step["t0"], 2)})
            if body is not None:
                step["body"] = body.decode("utf-8", "replace") if len(body) < 3_000_000 else None
                step["body_bytes"] = len(body)
            if to_path is not None and data_len and enc in ("gzip", "deflate"):
                raw = open(to_path, "rb").read()
                dec = gzip.decompress(raw) if enc == "gzip" else zlib.decompress(raw)
                open(to_path, "wb").write(dec)
                step["decompressed_bytes"] = len(dec)
    except urllib.error.HTTPError as e:
        step.update({"status": e.code, "error": f"HTTP {e.code}",
                     "elapsed_s": round(time.time() - step["t0"], 2),
                     "body_head": e.read()[:300].decode("utf-8", "replace")})
    except Exception as e:  # timeout, DNS, TLS: a blocked channel is a measurement
        step.update({"status": None, "error": f"{type(e).__name__}: {e}",
                     "elapsed_s": round(time.time() - step["t0"], 2)})
    return step


def budget_ok():
    return (state["requests"] < BUDGET_REQUESTS and state["bytes"] < BUDGET_BYTES
            and time.time() < DEADLINE)


WORK.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

# --- step 1: egress context ---------------------------------------------------------------
ip_step = fetch("https://api.ipify.org", timeout=15)
log({"step": "egress_ip", "ip": ip_step.get("body"), "status": ip_step.get("status")})

# --- step 2: IATI registry inventory (fresh, from the worker) --------------------------------
reg = fetch("https://iatiregistry.org/api/3/action/package_search?fq=organization:afdb&rows=100",
            to_path=WORK / "registry.json")
pkgs = []
licence_ids = Counter()
urls = []
try:
    payload = json.loads((WORK / "registry.json").read_text())
    for r in payload.get("result", {}).get("results", []):
        licence_ids[r.get("license_id")] += 1
        for res in r.get("resources", []):
            if res.get("format") == "IATI-XML" or res.get("url", "").endswith(".xml"):
                urls.append({"dataset": r.get("name"), "url": res.get("url")})
    pkgs = [r.get("name") for r in payload.get("result", {}).get("results", [])]
except Exception as e:
    log({"step": "registry_parse_error", "error": str(e)})
log({"step": "registry_inventory", "http": reg.get("status"),
     "datasets": len(pkgs), "xml_urls": len(urls),
     "license_ids": dict(licence_ids),
     "first_last": [pkgs[:2], pkgs[-2:]] if pkgs else None})

# --- step 3: IATI activity-status codelist (corroborative; not Cloudflare-gated) -------------
codelist = {}
for cl_url in ("https://raw.githubusercontent.com/IATI/codelists/master/xml/ActivityStatus.xml",
               "https://iatistandard.org/en/iati-standard/203/codelists/activitystatus/"):
    if not budget_ok():
        break
    st = fetch(cl_url, timeout=30)
    codelist[cl_url.rsplit("/", 2)[-2] if "raw.github" in cl_url else "iatistandard_html"] = {
        "status": st.get("status"), "bytes": st.get("bytes"),
        "head": (st.get("body") or "")[:400]}
    if st.get("status") == 200 and "raw.github" in cl_url:
        # pull the code/name pairs out of the codelist XML
        try:
            root = ET.fromstring((st.get("body") or "").encode())
            pairs = [(c.get("code"), (c.findtext("name") or "").strip())
                     for c in root.iter("codelist-item")]
            codelist["ActivityStatus"] = pairs
        except Exception as e:
            codelist["parse_error"] = str(e)
        break
log({"step": "iati_codelist", "result": codelist})

# --- step 4: fetch all afdb.org IATI XML files (reachability + extraction cost) ---------------
files = []
failures = 0
for i, u in enumerate(urls):
    if not budget_ok():
        log({"step": "fetch_budget_stop", "i": i, "requests": state["requests"],
             "bytes": state["bytes"], "deadline_s_left": round(DEADLINE - time.time(), 1)})
        break
    name = u["dataset"]
    path = WORK / f"{name}.xml"
    path.unlink(missing_ok=True)
    st = fetch(u["url"], to_path=path)
    st.update({"dataset": name, "index": i})
    if st.get("status") != 200:
        # one bounded retry on a clean file, then record and move on
        if budget_ok():
            path.unlink(missing_ok=True)
            st2 = fetch(u["url"], to_path=path)
            st2.update({"dataset": name, "index": i, "attempt": 2})
            st2.setdefault("status", None)
            files.append(st2)
            if st2.get("status") != 200:
                failures += 1
        else:
            files.append(st)
            failures += 1
    else:
        files.append(st)
        # over-write path cleanly on success is already done; on retry the .ab append
        # could stack bodies - guard: refetch wrote with 'ab'; delete before retry above
    if failures > 28:
        log({"step": "fetch_aborted_majority_blocked", "failures": failures,
             "fetched_ok": sum(1 for f in files if f.get("status") == 200)})
        break
ok_files = [f for f in files if f.get("status") == 200]
log({"step": "fetch_summary", "urls_attempted": len(files), "ok": len(ok_files),
     "failed": failures,
     "total_bytes": sum(f.get("bytes", 0) for f in ok_files),
     "fetch_wallclock_s": round(sum(f.get("elapsed_s", 0) for f in files), 1),
     "per_file": [{"d": f["dataset"], "b": f.get("bytes"), "s": f.get("status"),
                   "sha256": f.get("sha256", "")[:16], "t": f.get("elapsed_s")}
                  for f in files]})

# --- step 5: parse + aggregate (no labelled rows; counts only) -------------------------------
acts = []
for f in ok_files:
    path = WORK / f"{f['dataset']}.xml"
    try:
        for _, el in ET.iterparse(str(path), events=("end",)):
            if el.tag == "iati-activity":
                ident = el.findtext("iati-identifier") or ""
                status = (el.find("activity-status").get("code")
                          if el.find("activity-status") is not None else None)
                dates = {}
                for d in el.findall("activity-date"):
                    dates[d.get("type")] = d.get("iso-date")
                countries = [c.get("code") for c in el.findall("recipient-country")]
                sectors = [s.get("code") for s in el.findall("sector")
                           if s.get("vocabulary") == "1"]
                fin = el.find("default-finance-type")
                acts.append({
                    "id": ident, "status": status, "dates": dates,
                    "ctry": countries[0] if countries else None,
                    "multi": len(countries) > 1, "n_ctry": len(countries),
                    "sect": sectors[0] if sectors else None,
                    "fin": fin.get("code") if fin is not None else None,
                    "src": f["dataset"],
                })
                el.clear()
    except Exception as e:
        log({"step": "parse_error", "dataset": f["dataset"], "error": str(e)})

n_ids = Counter(a["id"] for a in acts)
status_hist = Counter(a["status"] for a in acts)


def year(iso):
    try:
        return int(iso[:4])
    except (TypeError, ValueError):
        return None


def days_between(a, b):
    try:
        from datetime import date
        d1 = date(*[int(x) for x in a.split("-")])
        d2 = date(*[int(x) for x in b.split("-")])
        return (d2 - d1).days
    except Exception:
        return None


term = [a for a in acts if a["status"] in ("3", "5")]
pos = [a for a in acts if a["status"] == "5"]
neg = [a for a in acts if a["status"] == "3"]
cens = [a for a in acts if a["status"] in ("1", "2")]

per_year = defaultdict(lambda: {"term": 0, "pos": 0, "neg": 0, "cens": 0})
for bucket, rows in (("term", term), ("pos", pos), ("neg", neg), ("cens", cens)):
    for a in rows:
        y = year(a["dates"].get("1"))
        key = y if y is not None else "missing_type1"
        per_year[key][bucket] += 1
per_year = {str(k): v for k, v in sorted(per_year.items(), key=lambda kv: str(kv[0]))}

WINDOWS = {"train": (None, 2000), "eval": (2001, 2010), "holdout": (2011, 2023),
           "recent": (2024, None)}


def window_stats(lo, hi):
    sel = [a for a in acts if a["status"] in ("3", "5")
           and (y := year(a["dates"].get("1"))) is not None
           and (lo is None or y >= lo) and (hi is None or y <= hi)]
    p = [a for a in sel if a["status"] == "5"]
    cells = Counter((a["ctry"], year(a["dates"]["1"])) for a in p)
    ctry_hist = Counter(a["ctry"] for a in p)
    return {
        "rows": len(sel), "positives": len(p), "negatives": len(sel) - len(p),
        "positive_rate": round(len(p) / len(sel), 4) if sel else None,
        "distinct_countries_terminal": len({a["ctry"] for a in sel}),
        "distinct_countries_with_positives": len(ctry_hist),
        "positive_country_year_cells": len(cells),
        "positives_in_cells_with_ge2": sum(c for c in cells.values() if c >= 2),
        "top_clusters": [[f"{k[0]}|{k[1]}", c] for k, c in cells.most_common(12)],
        "top_positive_countries": ctry_hist.most_common(10),
    }


windows = {name: window_stats(lo, hi) for name, (lo, hi) in WINDOWS.items()}

offsets = [d for d in (days_between(a["dates"]["1"], a["dates"]["2"])
                       for a in acts if a["dates"].get("1") and a["dates"].get("2"))
           if d is not None]
pos_offsets = [d for d in (days_between(a["dates"]["1"], a["dates"]["2"])
                           for a in pos if a["dates"].get("1") and a["dates"].get("2"))
               if d is not None]

cens_end = [year(a["dates"].get("3")) for a in cens]
summary_counts = {
    "activities_total": len(acts),
    "duplicate_identifiers": sum(c - 1 for c in n_ids.values() if c > 1),
    "status_histogram": dict(status_hist),
    "status_outside_1235": {k: v for k, v in status_hist.items() if k not in ("1", "2", "3", "5")},
    "terminal_missing_type1": sum(1 for a in term if not a["dates"].get("1")),
    "terminal_missing_type3": sum(1 for a in term if not a["dates"].get("3")),
    "completed_with_actual_end": sum(1 for a in neg if a["dates"].get("4")),
    "completed_without_actual_end": sum(1 for a in neg if not a["dates"].get("4")),
    "cancelled_with_actual_end": sum(1 for a in pos if a["dates"].get("4")),
    "cancelled_without_actual_end": sum(1 for a in pos if not a["dates"].get("4")),
    "type2_type1_offset_days": {
        "n": len(offsets),
        "median": statistics.median(offsets) if offsets else None,
        "min": min(offsets) if offsets else None, "max": max(offsets) if offsets else None,
        "negatives": sum(1 for d in offsets if d < 0),
    } if offsets else None,
    "type2_type1_offset_days_cancelled": {
        "n": len(pos_offsets), "median": statistics.median(pos_offsets) if pos_offsets else None,
    } if pos_offsets else None,
    "censored": {
        "n": len(cens),
        "planned_end_le_2015": sum(1 for y in cens_end if y is not None and y <= 2015),
        "planned_end_le_2020": sum(1 for y in cens_end if y is not None and y <= 2020),
        "planned_end_le_2026": sum(1 for y in cens_end if y is not None and y <= 2026),
        "planned_end_missing": sum(1 for y in cens_end if y is None),
        "min_type1_year": min((y for y in (year(a["dates"].get("1")) for a in cens)
                               if y is not None), default=None),
    },
    "distinct_sectors_vocab1": len({a["sect"] for a in acts if a["sect"]}),
    "multinational_rows": sum(1 for a in acts if a["multi"]),
    "per_approval_year": per_year,
    "windows": windows,
}

# --- step 6: MapAfrica control fetch (expect the Cloudflare challenge; no browser here) -------
ma = fetch("https://mapafrica.afdb.org/api/v15/stats?currency=xdr", timeout=20)
log({"step": "mapafrica_plain_client_control", "status": ma.get("status"),
     "error": ma.get("error"), "body_head": (ma.get("body_head") or "")[:150]})

# --- write outputs ---------------------------------------------------------------------------
summary["complete"] = bool(ok_files) and len(ok_files) == len(urls) and state["bytes"] < BUDGET_BYTES
summary["requests_used"] = state["requests"]
summary["bytes_downloaded"] = state["bytes"]
summary["wallclock_s"] = round(time.time() - START, 1)
summary["registry"] = {"http": reg.get("status"), "datasets": len(pkgs),
                       "xml_urls": len(urls), "license_ids": dict(licence_ids)}
summary["fetches"] = files
summary["counts"] = summary_counts
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
print(json.dumps({"step": "done", "summary_bytes": len(json.dumps(summary)),
                  "complete": summary["complete"], "ok_files": len(ok_files),
                  "activities": len(acts), "wallclock_s": summary["wallclock_s"]}))
