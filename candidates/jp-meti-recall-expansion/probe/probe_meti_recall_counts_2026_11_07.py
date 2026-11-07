#!/usr/bin/env python3
"""Probe recipe: METI recall register structure - dated-token counts, per-year
distribution, update-marker inventory (East Asia tick 2026-11-07).

Reproduces the measurements in candidates/jp-meti-recall-expansion/record.json
(measurements.sample_page_structure_denki5, update_marker_inventory_denki5,
update_lag_examples) and writes probe/out_meti_denki5_2026_11_07.json.

Host behaviour measured 2026-11-07 (must be respected when re-running):
- METI's WAF serves EMPTY 200s to urllib-style clients even for pages curl serves
  normally, and after a ~10-request burst serves an HTTP 202 challenge interstitial.
- Spaced single fetches (>=3 s) with a browser-like UA via curl succeed.
- Pages are mixed/legacy-encoded: decode with shift_jis/replace (naive utf-8 decode
  destroys most content - 0 dates found vs 225).
- Hub pages (e.g. denki.html) 403 to plain clients; sub-pages (denki_5.html) serve 200.

Read-only, anonymous. Usage:
  python3 probe_meti_recall_counts_2026_11_07.py [--page denki_5] [--keep-html PATH]
"""
import argparse
import collections
import json
import pathlib
import re
import subprocess
import time

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
BASE = "https://www.meti.go.jp/product_safety/recall/{}.html"
DATE = re.compile(r"20[0-2][0-9]年[0-9]{1,2}月[0-9]{1,2}日")
# label-class (outcome) update markers
OUTCOME = ["（対象追加", "（対策内容", "（型番追加", "（品番追加"]
# cosmetic (excluded) update markers
COSMETIC = ["（問い合わせ先", "（電話番号更新", "（受付時間", "（事業者リコール情報URL", "（回収開始"]


def fetch(page, retries=2):
    last = b""
    for attempt in range(retries + 1):
        out = subprocess.run(
            ["curl", "-s", "-m", "40", "-A", UA, BASE.format(page)],
            capture_output=True, timeout=60)
        last = out.stdout
        if len(last) > 5000:
            return last
        time.sleep(5 * (attempt + 1))  # WAF pace: back off and retry slowly
    raise SystemExit(f"fetch of {page} returned {len(last)} bytes; "
                     "METI WAF is pacing this client - wait >=60 s and retry one page")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="denki_5")
    ap.add_argument("--keep-html", default=None)
    args = ap.parse_args()

    raw = fetch(args.page)
    if args.keep_html:
        pathlib.Path(args.keep_html).write_bytes(raw)
    t = raw.decode("shift_jis", errors="replace")
    tt = re.sub(r"<[^>]+>", " ", t)
    tt = re.sub(r"[\s　]+", " ", tt)

    dates = DATE.findall(tt)
    years = collections.Counter(d[:4] for d in dates)
    result = {
        "page": args.page,
        "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "bytes": len(raw),
        "dated_tokens": len(dates),
        "by_year": dict(sorted(years.items())),
        "markers": {
            "outcome_class": {m.strip("（"): tt.count(m) for m in OUTCOME if tt.count(m)},
            "cosmetic_class": {m.strip("（"): tt.count(m) for m in COSMETIC if tt.count(m)},
        },
        "major_accident_triggered_marker": tt.count("重大製品事故契機"),
        "two_date_update_entries": [
            {"first_date": m.group(1), "second_date": m.group(2), "marker": m.group(3)}
            for m in re.finditer(
                r"(20[0-2][0-9]年[0-9]{1,2}月[0-9]{1,2}日)\s+"
                r"(20[0-2][0-9]年[0-9]{1,2}月[0-9]{1,2}日)\s*（([^）]{2,14})）", tt)],
    }
    out_path = pathlib.Path(__file__).parent / "out_meti_denki5_2026_11_07.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:1500])
    print("written:", out_path)


if __name__ == "__main__":
    main()
