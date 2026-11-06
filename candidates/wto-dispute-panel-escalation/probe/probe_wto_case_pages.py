#!/usr/bin/env python3
"""Discovery probe: WTO dispute case pages - cross-era schema sample.

Verifies, on a fixed sample of DS numbers spanning 1995-2025, that each
per-case gateway page (https://www.wto.org/english/tratop_e/dispu_e/cases_e/ds<N>_e.htm):
  - exists (HTTP 200),
  - names the complainant ("Complaint by ..."),
  - records the request-for-consultations event with its date,
  - cites the WTO agreements in dispute,
  - records the panel-establishment event where one occurred,
and measures fetch size and wall-clock per page (coordinator-class machine).

Read-only, anonymous. Run from anywhere:
    python3 probe_wto_case_pages.py [--out probe/out/case_pages_YYYY_MM_DD.json]
"""
import argparse
import datetime
import json
import re
import sys
import time
import urllib.request

BASE = "https://www.wto.org/english/tratop_e/dispu_e/cases_e/ds{}_e.htm"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}

# Era-spanning sample: early panel era, mid-era mega-disputes, recent, modern tail.
SAMPLE = [1, 26, 58, 90, 135, 184, 267, 316, 363, 406, 436, 461, 496, 536, 543, 561, 585, 598, 611, 620, 631]


def page_text(raw: bytes) -> str:
    h = raw.decode("windows-1252", errors="replace")
    t = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&mdash;", " - ").replace("&ndash;", " - ")
    return re.sub(r"\s+", " ", t)


def probe_one(ds: int):
    url = BASE.format(ds)
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            status = r.status
            raw = r.read()
    except Exception as e:  # noqa: BLE001 - probe records the failure
        return {"ds": ds, "url": url, "error": repr(e)[:200], "elapsed_s": round(time.time() - t0, 2)}
    elapsed = time.time() - t0
    t = page_text(raw)
    complainants = re.findall(r"Complaint by ((?:the )?[A-Z][A-Za-z ()\.]{2,60}?)(?:\s+On\s|\.\s)", t)
    consult = re.search(r"[Oo]n (\d{1,2} \w+ \d{4}), .{0,80}?requested consultations with", t)
    agreements = re.findall(r"\b(GATT 1994|GATT|GATS|TRIPS|SCM Agreement|Anti-Dumping|SPS Agreement|TBT Agreement|Agreement on Agriculture|Safeguards|Customs Valuation|TRIMS|Import Licensing|Pre-shipment Inspection|Rules of Origin|Subsidies)[\b,]", t)
    panel_est = re.search(r"DSB (?:established a panel|deferred the establishment)", t)
    req_panel = re.search(r"requested the establishment of a panel", t)
    return {
        "ds": ds,
        "url": url,
        "http": status,
        "bytes": len(raw),
        "elapsed_s": round(elapsed, 2),
        "complainants": sorted(set(complainants))[:4],
        "consultations_date_text": consult.group(1) if consult else None,
        "agreements_seen": sorted(set(agreements))[:6],
        "mentions_panel_request": bool(req_panel),
        "mentions_dsb_panel_establishment": bool(panel_est),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    results = [probe_one(ds) for ds in SAMPLE]
    ok = [r for r in results if r.get("http") == 200]
    have_comp = [r for r in ok if r.get("complainants")]
    have_consult = [r for r in ok if r.get("consultations_date_text")]
    have_agr = [r for r in ok if r.get("agreements_seen")]
    summary = {
        "probe": "wto_case_pages_sample",
        "date_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "sample_size": len(SAMPLE),
        "http_200": len(ok),
        "with_complainant_field": len(have_comp),
        "with_consultations_date": len(have_consult),
        "with_agreements_cited": len(have_agr),
        "mean_bytes": (sum(r["bytes"] for r in ok) // len(ok)) if ok else 0,
        "mean_elapsed_s": round(sum(r["elapsed_s"] for r in ok) / len(ok), 2) if ok else 0,
        "results": results,
    }
    print(json.dumps(summary, indent=1)[:4000])
    if args.out:
        with open(args.out, "w") as f:
            json.dump(summary, f, indent=1)
        print("written:", args.out)
    # fail loudly if the channel is not what the record claims
    if len(ok) < len(SAMPLE) * 0.8 or len(have_comp) < len(ok) * 0.8:
        print("PROBE FINDING: case-page channel unstable across the sample - investigate before ready")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
