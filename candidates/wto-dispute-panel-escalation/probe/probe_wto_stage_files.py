#!/usr/bin/env python3
"""Discovery probe: WTO publisher aggregate files - stage counts, windows, lags.

Downloads (or reads cached copies of) the WTO's own aggregate artifacts:
  - numbers_of_disputes_by_stage_e.xlsx  (per-year stage counts, 1995-current)
  - dates_of_key_stages_e.xlsx           (per-DS dates of key stages; coverage ends DS543, Apr 2018)

and prints the measurements recorded in candidates/wto-dispute-panel-escalation:
  - per-year consultations requests and panels established (stage file)
  - cross-check: stage-file consultations 1995-2024 total vs the stats page's own "631"
  - proposed split windows from the dates file (rows / positives / distinct positive pairs)
  - consultations -> panel-establishment lag distribution (eligibility cutoff evidence)

Read-only, anonymous. Evidence copies of the xlsx files live in probe/out/ with sha256
recorded in notes.md; this script re-fetches them by default and falls back to the copies.
"""
import argparse
import datetime
import hashlib
import re
import sys
import urllib.request
from collections import Counter

import openpyxl

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
STAGE_URL = "https://www.wto.org/english/tratop_e/dispu_e/numbers_of_disputes_by_stage_e.xlsx"
DATES_URL = "https://www.wto.org/english/tratop_e/dispu_e/dates_of_key_stages_e.xlsx"


def get_bytes(url, cache_path):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            print(f"fetched {url}: {len(raw)} B, Last-Modified {r.headers.get('Last-Modified')}")
            return raw
    except Exception as e:  # noqa: BLE001 - fall back to the retained copy
        print(f"fetch failed ({e!r}); using retained copy {cache_path}")
        return open(cache_path, "rb").read()


def year_of(v):
    if v is None:
        return None
    if isinstance(v, datetime.datetime):
        return v.year
    s = str(v).strip()
    if not s:
        return None
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", s)
    if m:
        y = int(m.group(3))
        return y + 2000 if y < 50 else y + 1900
    m = re.match(r"(\d{4})", s)
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached", action="store_true", help="use retained copies in probe/out/ instead of re-fetching")
    args = ap.parse_args()
    here = __file__.rsplit("/", 1)[0]  # <candidate>/probe
    out = f"{here}/out"

    if args.cached:
        stage_b = open(f"{out}/numbers_of_disputes_by_stage_e.xlsx", "rb").read()
        dates_b = open(f"{out}/dates_of_key_stages_e.xlsx", "rb").read()
    else:
        stage_b = get_bytes(STAGE_URL, f"{out}/numbers_of_disputes_by_stage_e.xlsx")
        dates_b = get_bytes(DATES_URL, f"{out}/dates_of_key_stages_e.xlsx")
    for name, b in (("stage", stage_b), ("dates", dates_b)):
        print(f"{name} sha256: {hashlib.sha256(b).hexdigest()[:32]} size {len(b)}")

    # --- stage file: per-year counts + the publisher's own cross-check ---
    import io
    wb = openpyxl.load_workbook(io.BytesIO(stage_b), read_only=True)
    ws = wb["Original Panel and AB"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = req = est = mas = None
    for r in rows:
        c0 = str(r[0]).strip() if r[0] is not None else ""
        if c0 == "Action":
            hdr = r
        elif c0.startswith("Requests for consultations"):
            req = r
        elif c0.startswith("Panels established by DSB"):
            est = r
        elif c0.startswith("Mutually agreed"):
            mas = r
    assert hdr is not None and req is not None and est is not None, "stage-file layout changed: row anchors not found"
    tot = tot24 = te = tm = 0
    per_year = []
    for i in range(1, len(hdr)):
        y = hdr[i]
        if y is None or not str(y).strip().isdigit():
            continue
        y = int(str(y).strip())
        v = req[i] if isinstance(req[i], (int, float)) else 0
        e = est[i] if isinstance(est[i], (int, float)) else 0
        per_year.append((y, int(v), int(e)))
        tot += v
        tot24 += v if 1995 <= y <= 2024 else 0
        te += e
        if mas:
            tm += mas[i] if isinstance(mas[i], (int, float)) else 0
    print("\nstage file: consultations 1995-2024 =", tot24, "(stats page states 631); through latest year =", tot)
    print("stage file: panels established total =", te, "; MAS/lapse total =", tm)
    print("recent years (consult, estab):", [(y, c, e) for y, c, e in per_year if y >= 2019])

    # --- dates file: rows, windows, clustering, lags ---
    wb2 = openpyxl.load_workbook(io.BytesIO(dates_b), read_only=True)
    ws2 = wb2["Sheet1"]
    data = []
    tmb = 0
    for r in ws2.iter_rows(values_only=True):
        ds = r[59] if len(r) > 59 else None
        if ds and re.fullmatch(r"DS\d+", str(ds).strip()):
            if year_of(r[3]) is None:
                tmb += 1
            data.append(r)
    print("\ndates file: rows =", len(data), "(incl.", tmb, "TMB/non-consultation rows)")
    lags = []
    pairs = Counter()
    pairs_pos = Counter()

    def resp_from_title(t):
        if not t:
            return None
        m = re.match(r"\s*([A-Za-z ()\.]+?)\s*[\u2013\u2014-]\s*", str(t))
        return m.group(1).strip() if m else None

    for r in data:
        yc, ye = year_of(r[3]), year_of(r[5])
        if yc is None:
            continue
        k = (str(r[1]).strip(), resp_from_title(r[2]) or "?")
        pairs[k] += 1
        if ye:
            pairs_pos[k] += 1
            d1 = r[3]
            d2 = r[5]
            def pdate(v):
                if isinstance(v, datetime.datetime):
                    return v.date()
                m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", str(v))
                if m:
                    d, mo, y = m.groups()
                    y = int(y)
                    y = y + 2000 if y < 50 else y + 1900
                    try:
                        return datetime.date(y, int(mo), int(d))
                    except ValueError:
                        return None
                return None
            a, b = pdate(d1), pdate(d2)
            if a and b:
                lags.append((b - a).days)
    lags.sort()
    n = len(lags)
    print("lags consultations->establishment: n =", n, "median", lags[n // 2] if n else None,
          "p90", lags[9 * n // 10] if n else None,
          "| within 12m %.1f%% 18m %.1f%% 24m %.1f%%" % (
              100 * sum(1 for x in lags if x <= 365) / n,
              100 * sum(1 for x in lags if x <= 548) / n,
              100 * sum(1 for x in lags if x <= 730) / n) if n else "")
    print("malformed/negative lags present:", sum(1 for x in lags if x < 0), "negative;",
          sum(1 for x in lags if x > 3650), "absurd")
    for a, b in [(1995, 2008), (2009, 2014), (2015, 2018)]:
        w = [r for r in data if year_of(r[3]) and a <= year_of(r[3]) <= b]
        pos = [r for r in w if year_of(r[5])]
        pp = Counter((str(r[1]).strip(), resp_from_title(r[2]) or "?") for r in pos)
        print(f"window {a}-{b}: rows={len(w)} positives={len(pos)} ({len(pos)/max(len(w),1):.1%}) distinct positive pairs={len(pp)}")
    print("distinct complainant-respondent pairs overall:", len(pairs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
