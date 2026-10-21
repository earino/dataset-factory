"""CER honest-feature AUC probe (2026-10-21 session).

Run: python3 candidates/cer-pipeline-incident-significant/probe_honest_auc.py
(after probe_download_measure.py has cached pipeline-incidents-data.csv in /tmp/cer_probe)

In-sample single-categorical AUC of each report-time (and label-adjacent) column
against 'Significant'. Levels with >=5 rows. In-sample on purpose: the question
is how much signal survives the timing exclusions, not generalisation.
"""
import bisect
import csv

P = "/tmp/cer_probe/pipeline-incidents-data.csv"
with open(P, newline="", encoding="cp1252") as f:
    rows = list(csv.DictReader(f))


def col_auc(col):
    levels = {}
    for r in rows:
        lev = (r.get(col) or "?").strip() or "?"
        y = 1 if (r.get("Significant") or "").strip().lower() in ("yes", "y", "true") else 0
        levels.setdefault(lev, [0, 0])
        levels[lev][y] += 1
    kept = {lev: c[1] / (c[0] + c[1]) for lev, c in levels.items() if c[0] + c[1] >= 5}
    pos, neg = [], []
    for r in rows:
        lev = (r.get(col) or "?").strip() or "?"
        if lev not in kept:
            continue
        y = 1 if (r.get("Significant") or "").strip().lower() in ("yes", "y", "true") else 0
        (pos if y else neg).append(kept[lev])
    if not pos or not neg:
        return None, len(kept)
    neg_sorted = sorted(neg)
    greater = ties = 0
    for v in pos:
        greater += bisect.bisect_left(neg_sorted, v)
        ties += bisect.bisect_right(neg_sorted, v) - bisect.bisect_left(neg_sorted, v)
    return (greater + 0.5 * ties) / (len(pos) * len(neg)), len(kept)


for col in ["Substance", "Province", "Company", "Year", "Release Type", "Incident Types"]:
    auc, n = col_auc(col)
    print(f"  {col}: AUC={auc} ({n} levels)")
