#!/usr/bin/env python3
"""Pre-launch persistence-ceiling measurement for ea-bathing-water-classification.

Reads the ten published season slices fetched by .factory/eab_fetch.py (2015-2025,
2020 suspended), builds the (bwspid, season) panel the candidate would ship, and
measures the two simple references on the candidate's declared split windows:

  * binary persistence  - last season's classification collapsed to below-Good
  * ordinal persistence - last season's classification on its published 4-level
                          scale (Poor < Sufficient < Good < Excellent)

AUC is computed rank-based with tie groups averaged, stdlib only. This is a
PRE-LAUNCH measurement on the publisher's own slices: it is not a qualification
report, no gate has run, and no model has been fitted. It exists to decide whether
a worker construction is worth launching at all.
"""
import gzip
import os
import json
import pathlib
from collections import Counter, defaultdict

DATA = pathlib.Path(os.environ.get("EAB_DATA", ".factory/eab-probe/data"))
SEASONS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025]
ORD = {"Poor": 1, "Sufficient": 2, "Good": 3, "Excellent": 4}
BELOW = {"Poor", "Sufficient"}


def load(season):
    raw = gzip.decompress((DATA / f"season-{season}.json.gz").read_bytes())
    doc = json.loads(raw)
    out = {}
    for obs in doc["result"]["primaryTopic"]["observation"]:
        wid = obs["bwq_bathingWater"]["_about"].rsplit("/", 1)[-1]
        out[wid] = obs["complianceClassification"]["name"]["_value"]
    return out


def auc(scores, labels):
    groups = defaultdict(list)
    for s, y in zip(scores, labels):
        groups[s].append(y)
    n = len(labels)
    pos = sum(labels)
    if pos == 0 or pos == n:
        return None
    rank_sum = 0.0
    idx = 1
    for score in sorted(groups):
        g = groups[score]
        poss = sum(g)
        rank_sum += poss * (idx + (len(g) - 1) / 2.0)
        idx += len(g)
    return (rank_sum - pos * (pos + 1) / 2.0) / (pos * (n - pos))


def r4(x):
    return None if x is None else round(x, 4)


def majority_accuracy(train_rows, eval_rows):
    rate = sum(r["y"] for r in train_rows) / len(train_rows)
    majority = int(rate >= 0.5)
    if not eval_rows:
        return None
    return sum(1 for r in eval_rows if r["y"] == majority) / len(eval_rows)


slices = {s: load(s) for s in SEASONS}
rows = []
for season in SEASONS:
    for wid, label in slices[season].items():
        if label == "Closed":
            continue
        prev = [slices.get(season - k, {}).get(wid) for k in (1, 2, 3)]
        if prev[0] in (None, "Closed"):
            continue  # no observation at the instant: out of frame, counted
        rows.append({
            "id": wid,
            "season": season,
            "y": 0 if label not in BELOW else 1,
            "l1": prev[0],
            "l2": prev[1],
            "l3": prev[2],
            "bg1": 0 if prev[0] not in BELOW else 1,
            "bg2": 0 if prev[1] not in BELOW else 1,
            "bg3": 0 if prev[2] not in BELOW else 1,
            "o1": ORD.get(prev[0], 0),
        })

WINDOWS = {"train": [2016, 2017, 2018, 2019], "eval": [2022, 2023],
           "holdout": [2024, 2025]}
train = [r for r in rows if r["season"] in WINDOWS["train"]]

report = {"measured_at": "2026-10-23", "source": "EA bwq compliance-rBWD season slices",
          "panel_rows": len(rows), "splits": {}}
for name, seasons in WINDOWS.items():
    sel = [r for r in rows if r["season"] in seasons]
    entry = {
        "rows": len(sel),
        "positives": sum(r["y"] for r in sel),
        "positive_rate": round(sum(r["y"] for r in sel) / len(sel), 4),
        "distinct_positive_waters": len({r["id"] for r in sel if r["y"] == 1}),
        "binary_persistence_auc": r4(auc([r["bg1"] for r in sel],
                                            [r["y"] for r in sel])),
        "ordinal_persistence_auc": r4(auc([-r["o1"] for r in sel],
                                             [r["y"] for r in sel])),
        "hist3_count_auc": r4(auc([3 * r["bg1"] + 2 * r["bg2"] + r["bg3"] for r in sel],
                                     [r["y"] for r in sel])),
        "majority_class_accuracy": r4(majority_accuracy(train, sel)),
        "per_season": {},
    }
    for season in seasons:
        s = [r for r in sel if r["season"] == season]
        if not s:
            continue
        entry["per_season"][str(season)] = {
            "rows": len(s), "positives": sum(r["y"] for r in s),
            "rate": round(sum(r["y"] for r in s) / len(s), 4),
            "ordinal_persistence_auc": r4(auc([-r["o1"] for r in s],
                                                 [r["y"] for r in s])),
        }
    report["splits"][name] = entry

trans = Counter((r["bg1"], r["y"]) for r in rows if r["season"] >= 2022)
report["transition_bg1_to_y_2022plus"] = {f"{a}->{b}": c for (a, b), c in sorted(trans.items())}
report["out_of_frame"] = {
    "closed_labels_excluded": sum(1 for s in SEASONS
                                 for v in slices[s].values() if v == "Closed"),
    "no_prior_observation": sum(1 for s in SEASONS for wid in slices[s]
                                if slices[s][wid] != "Closed"
                                and slices.get(s - 1, {}).get(wid) in (None, "Closed")),
}
pathlib.Path(".factory/eab-probe/ceiling.json").write_text(json.dumps(report, indent=1))
print(json.dumps(report, indent=1))
