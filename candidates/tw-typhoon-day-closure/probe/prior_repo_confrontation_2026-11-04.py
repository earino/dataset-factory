#!/usr/bin/env python3
"""Prior-art confrontation probe (2026-11-04): kxykxyou/TyphoonDayoffPrediction.

Reproduces the measurements behind the 2026-11-04 novelty re-verdict
(differentiated) from the actual bytes the prior repository ships.
The 2026-11-04 session fetched the files listed in URLS with curl into
/opt/data/cache/scratch/tyoff/ (scratch, not committed); this script takes the
same filenames as arguments so any fresh run can re-derive every number quoted
in notes.md section "Prior-art confrontation (2026-11-04)".

Usage:
  curl -s -o station_dayoff_neat.csv \
    https://media.githubusercontent.com/media/kxykxyou/TyphoonDayoffPrediction/master/data/neat_data/station_dayoff_neat.csv
  python3 probe/prior_repo_confrontation_2026-11-04.py station_dayoff_neat.csv
"""
import csv
import sys
from collections import Counter

URLS = {
    "station_dayoff_neat.csv":
        "https://media.githubusercontent.com/media/kxykxyou/TyphoonDayoffPrediction/"
        "master/data/neat_data/station_dayoff_neat.csv",
    "dayoff_info_utf-8.csv":
        "https://media.githubusercontent.com/media/kxykxyou/TyphoonDayoffPrediction/"
        "master/data/dayoff/dayoff_info_utf-8.csv",
    "data_ver2_transform.R":
        "https://raw.githubusercontent.com/kxykxyou/TyphoonDayoffPrediction/"
        "master/data_ver2_transform.R",
    "DCT_model_training.ipynb":
        "https://raw.githubusercontent.com/kxykxyou/TyphoonDayoffPrediction/"
        "master/DCT_model_training.ipynb",
}


def main(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8", newline="")))
    print(f"rows: {len(rows)}")
    dates = sorted({r["alert_dates"] for r in rows})
    print(f"distinct dates: {len(dates)} | first: {dates[0]} | last: {dates[-1]}")
    pos_per_date = Counter()
    for r in rows:
        pos_per_date[r["alert_dates"]] += int(r["day_off"])
    zero = [d for d in dates if pos_per_date[d] == 0]
    print(f"dates with zero positives (all-counties-open): {len(zero)} -> "
          f"{'OUTCOME-CONDITIONED day population' if not zero else 'mixed'}")
    cd = {}
    for r in rows:
        cd[(r["County"], r["alert_dates"])] = r["day_off"]
    print(f"county-date pairs: {len(cd)} | positives: {sum(int(v) for v in cd.values())} "
          f"({100.0 * sum(int(v) for v in cd.values()) / len(cd):.1f}%)")
    hl = [r for r in rows if r["County"] == "\u82b1\u84ee\u7e23" and r["alert_dates"] == "2021-10-14"]
    print(f"\u82b1\u84ee\u7e23 2021-10-14 (known district-qualified closure day) rows in panel: {len(hl)}")
    yrs = Counter(d[:4] for d in dates)
    print("dates per year:", dict(sorted(yrs.items())))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        for name, url in URLS.items():
            print(f"  {url}")
        sys.exit(2)
    main(sys.argv[1])
