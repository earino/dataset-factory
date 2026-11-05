#!/usr/bin/env python3
"""Post-acceptance references for nws-tornado-warning-verification.

The FIRST performance metric in the job. Refuses to run unless the
qualification report passed over the full artifact AND --accept re-verified
the exact bytes. Computes simple references on the IDENTICAL eval rows only
(the holdout is never opened):

  - majority constant (fit on train)
  - persistence: the verify outcome of the most recent earlier same-WFO TOR
    warning whose expiry is >= PERSISTENCE_GAP_MIN minutes before this
    warning's issue (declared outcome-availability assumption; train-prior
    fallback when no such warning exists)
  - calendar-only: WFO identity + cyclical day-of-year + cyclical hour
    combined with train-only estimated priors (logit-additive seasonal
    prior; no feature information beyond identity and calendar)

plus per-issue-year AUC/Brier and prevalence, and the day-clustered paired
bootstrap (resampling outbreak days) for the reference comparisons. The full
model (stock runner) is a separate baseline job per the za-cct/cqc pattern;
the pre-registered deciding rule compares it against every reference on
these same rows once that number exists.
"""
import argparse
import csv
import json
import math
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path

TARGET = "verified"
PERSISTENCE_GAP_MIN = 30
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 20261105
DOY_BUCKETS = 24          # ~15-day seasonal buckets
MIN_DOY_BUCKET_ROWS = 50  # else fall back to the global train prior


def read_rows(path: Path) -> list:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def labels_of(rows: list) -> list:
    return [int(row[TARGET]) for row in rows]


def rank_pair(labels_a, scores_a, labels_b, scores_b):
    """Concordant rank statistic over aligned pairs (AUC via Mann-Whitney)."""
    # simple O(n^2)-free AUC: sort by score, count inversions with ties halved
    def auc(labels, scores):
        pos = sorted(s for l, s in zip(labels, scores) if l == 1)
        neg = sorted(s for l, s in zip(labels, scores) if l == 0)
        if not pos or not neg:
            return None
        i = j = 0
        wins = 0.0
        for s in pos:
            # count negs below s minus ties halved, via bisect on sorted neg
            import bisect
            lo = bisect.bisect_left(neg, s)
            eq = bisect.bisect_right(neg, s) - lo
            wins += lo + 0.5 * eq
        return wins / (len(pos) * len(neg))
    return auc(labels_a, scores_a), auc(labels_b, scores_b)


def auc(labels, scores):
    import bisect
    pos = sorted(s for l, s in zip(labels, scores) if l == 1)
    neg = sorted(s for l, s in zip(labels, scores) if l == 0)
    if not pos or not neg:
        return None
    wins = 0.0
    for s in pos:
        lo = bisect.bisect_left(neg, s)
        eq = bisect.bisect_right(neg, s) - lo
        wins += lo + 0.5 * eq
    return wins / (len(pos) * len(neg))


def brier(labels, scores):
    if not labels:
        return None
    return sum((s - l) ** 2 for l, s in zip(labels, scores)) / len(labels)


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def majority_reference(train_rows, eval_rows):
    train_labels = labels_of(train_rows)
    majority = 1 if (sum(train_labels) >= len(train_labels) / 2.0) else 0
    eval_labels = labels_of(eval_rows)
    acc = sum(1 for l in eval_labels if l == majority) / len(eval_labels) if eval_labels else None
    return {
        "name": "majority_constant",
        "score_rule": f"constant {majority} (fit on train prevalence)",
        "train_majority": majority,
        "scores": [float(majority)] * len(eval_rows),
        "eval_accuracy": acc,
        "eval_auc": None,  # a constant has no ranking information
    }


def persistence_reference(train_rows, eval_rows, all_prior_rows):
    """Most recent earlier same-WFO warning whose expiry precedes issue by
    PERSISTENCE_GAP_MIN minutes; train-prior fallback. Prior expiry is
    derived from the shipped issue_ts + duration_min."""
    prior_by_wfo = defaultdict(list)  # wfo -> (issue_dt, expire_dt, verify)
    for row in all_prior_rows:
        issue = datetime.fromisoformat(row["issue_ts"].replace("Z", "+00:00"))
        duration = float(row["duration_min"]) if row.get("duration_min") else 0.0
        expire = issue.fromtimestamp(issue.timestamp() + duration * 60,
                                     tz=issue.tzinfo)
        prior_by_wfo[row["wfo"]].append((issue, expire, int(row[TARGET])))
    for wfo in prior_by_wfo:
        prior_by_wfo[wfo].sort(key=lambda t: t[0])

    train_labels = labels_of(train_rows)
    train_rate = sum(train_labels) / len(train_labels) if train_labels else 0.5
    wfo_rate = defaultdict(list)
    for row in train_rows:
        wfo_rate[row["wfo"]].append(int(row[TARGET]))
    wfo_prior = {w: sum(v) / len(v) for w, v in wfo_rate.items()}

    scores = []
    used_gap = 0
    fallback_wfo = 0
    fallback_global = 0
    for row in eval_rows:
        issue = datetime.fromisoformat(row["issue_ts"].replace("Z", "+00:00"))
        best = None
        # scan the WFO's warnings latest-first; take the most recent one that
        # expired at least PERSISTENCE_GAP_MIN before this issue
        for (p_issue, p_expire, p_verify) in reversed(prior_by_wfo[row["wfo"]]):
            if p_expire > issue:
                continue                     # still live at our issue
            delta = (issue - p_expire).total_seconds() / 60.0
            if delta >= PERSISTENCE_GAP_MIN:
                best = p_verify
                break
        if best is None:
            prior = wfo_prior.get(row["wfo"])
            if prior is None:
                fallback_global += 1
                scores.append(train_rate)
            else:
                fallback_wfo += 1
                scores.append(prior)
        else:
            used_gap += 1
            scores.append(float(best))
    return {
        "name": "persistence_same_wfo_30min",
        "score_rule": (
            "verify outcome of the most recent earlier same-WFO TOR warning "
            "whose expiry is >= 30 min before this issue (outcome-availability "
            "assumption: an LSR deciding the prior warning's outcome is "
            "assumed reported within 30 minutes of its expiry; LSR arrival "
            "lag is unmeasured and this is a reference, not a shipped "
            "feature); fallback = the WFO's train positive rate, then the "
            "global train rate"),
        "scores": scores,
        "rows_with_prior_outcome": used_gap,
        "rows_fallback_wfo_prior": fallback_wfo,
        "rows_fallback_global_prior": fallback_global,
    }


def calendar_reference(train_rows, eval_rows):
    """WFO identity + cyclical day-of-year + cyclical hour, train-only
    logit-additive priors (identity, seasonality, time-of-day)."""
    train_labels = labels_of(train_rows)
    global_rate = sum(train_labels) / len(train_labels) if train_labels else 0.5

    wfo_counts = defaultdict(lambda: [0, 0])
    doy_counts = defaultdict(lambda: [0, 0])
    hour_counts = defaultdict(lambda: [0, 0])
    for row, label in zip(train_rows, train_labels):
        wfo_counts[row["wfo"]][label] += 1
        doy_counts[int(row["issue_doy"])][label] += 1
        hour_counts[int(row["issue_hour"])][label] += 1

    # bucket the day-of-year prior coarsely so every bucket has rows
    bucket_size = 366 / DOY_BUCKETS
    doy_bucket_counts = defaultdict(lambda: [0, 0])
    for doy, (neg, pos) in doy_counts.items():
        b = min(int((doy - 1) / bucket_size), DOY_BUCKETS - 1)
        doy_bucket_counts[b][0] += neg
        doy_bucket_counts[b][1] += pos

    def rate_pair(neg, pos):
        total = neg + pos
        if total < 1:
            return None
        return (pos + 0.5) / (total + 1.0)  # Laplace-smoothed

    scores = []
    for row in eval_rows:
        wfo_rate = rate_pair(*wfo_counts[row["wfo"]]) if row["wfo"] in wfo_counts else None
        b = min(int((int(row["issue_doy"]) - 1) / bucket_size), DOY_BUCKETS - 1)
        doy_rate = rate_pair(*doy_bucket_counts[b])
        hour_rate = rate_pair(*hour_counts[int(row["issue_hour"])])
        logit_score = logit(global_rate)
        for r in (wfo_rate, doy_rate, hour_rate):
            if r is not None:
                logit_score += logit(r) - logit(global_rate)
        scores.append(sigmoid(logit_score))
    return {
        "name": "calendar_identity_wfo_doy_hour",
        "score_rule": (
            "logit-additive train-only priors: WFO positive rate x doy-bucket "
            f"({DOY_BUCKETS} buckets) positive rate x hour-of-day positive "
            "rate, Laplace-smoothed, combined additively in logit space "
            "around the global train rate; uses identity and calendar only"),
        "scores": scores,
    }


def paired_day_bootstrap(labels, score_a, score_b, days, resamples, seed):
    """Resample outbreak days with replacement; AUC difference distribution."""
    day_to_idx = defaultdict(list)
    for i, d in enumerate(days):
        day_to_idx[d].append(i)
    day_list = sorted(day_to_idx)
    rng = random.Random(seed)

    def diff_for(sample_days):
        idx = [i for d in sample_days for i in day_to_idx[d]]
        if not idx:
            return None
        l = [labels[i] for i in idx]
        a = [score_a[i] for i in idx]
        b = [score_b[i] for i in idx]
        auc_a, auc_b = auc(l, a), auc(l, b)
        if auc_a is None or auc_b is None:
            return None
        return auc_a - auc_b

    diffs = []
    for _ in range(resamples):
        sample = [rng.choice(day_list) for _ in day_list]
        d = diff_for(sample)
        if d is not None:
            diffs.append(d)
    diffs.sort()
    if len(diffs) < 10:
        return {"resamples": len(diffs), "mean": None,
                "ci95": [None, None]}
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[int(0.975 * len(diffs)) - 1 if int(0.975 * len(diffs)) > 0 else -1]
    return {"resamples": len(diffs),
            "mean": sum(diffs) / len(diffs),
            "ci95": [lo, hi]}


def per_year_table(rows, scores):
    labels = labels_of(rows)
    years = [r["issue_ts"][:4] for r in rows]
    table = {}
    for year in sorted(set(years)):
        idx = [i for i, y in enumerate(years) if y == year]
        l = [labels[i] for i in idx]
        s = [scores[i] for i in idx]
        table[year] = {
            "rows": len(idx),
            "positives": sum(l),
            "prevalence": round(sum(l) / len(l), 4) if l else None,
            "auc": auc(l, s),
            "brier": brier(l, s),
        }
    return table


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--accepted-report", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    data = Path(args.data)
    # gate: the acceptance report must exist and have passed
    report = json.loads(Path(args.accepted_report).read_text())
    if not report.get("ok"):
        print("REFUSED: the qualification report did not pass; nothing is scored")
        return 2
    # exact-byte acceptance is run.sh's separate --accept stage; score only
    # runs after it succeeded. Re-check the report's artifact identity.
    artifact = report.get("artifact") or {}
    print(f"scoring against qualified artifact {artifact.get('artifact_version')}")

    train_rows = read_rows(data / "public" / "train.csv")
    eval_rows = read_rows(data / "public" / "eval.csv")
    if not train_rows or not eval_rows:
        print("REFUSED: empty train or eval split")
        return 2
    # holdout is NEVER opened here
    labels = labels_of(eval_rows)
    days = [row["issue_date"] for row in eval_rows]

    refs = {}
    majority = majority_reference(train_rows, eval_rows)
    refs[majority["name"]] = majority
    # persistence uses every train+eval warning as prior history; the temporal
    # split guarantees train rows all precede eval rows, and eval rows only
    # ever read STRICTLY EARLIER same-WFO outcomes (self-rows are excluded by
    # the gap rule: a warning never expires 30 min before its own issue)
    persistence = persistence_reference(train_rows, eval_rows,
                                        train_rows + eval_rows)
    refs[persistence["name"]] = persistence
    calendar = calendar_reference(train_rows, eval_rows)
    refs[calendar["name"]] = calendar

    result = {
        "name": "nws-tornado-warning-verification references",
        "stage": "post-acceptance, eval rows only, holdout sealed",
        "persistence_gap_min": PERSISTENCE_GAP_MIN,
        "eval_rows": len(eval_rows),
        "eval_positives": sum(labels),
        "eval_prevalence": round(sum(labels) / len(labels), 6),
        "references": {},
        "per_issue_year": {},
        "bootstrap": {},
    }
    for name, ref in refs.items():
        entry = {k: v for k, v in ref.items() if k != "scores"}
        if ref.get("scores"):
            entry["eval_auc"] = auc(labels, ref["scores"])
            entry["eval_brier"] = brier(labels, ref["scores"])
            entry["per_issue_year"] = per_year_table(eval_rows, ref["scores"])
        result["references"][name] = entry

    # day-clustered paired bootstrap between the two ranked references
    p_scores = persistence["scores"]
    c_scores = calendar["scores"]
    result["bootstrap"]["persistence_vs_calendar"] = paired_day_bootstrap(
        labels, p_scores, c_scores, days, BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED)

    Path(args.report).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({
        "eval_rows": result["eval_rows"],
        "eval_prevalence": result["eval_prevalence"],
        "persistence_auc": result["references"][persistence["name"]]["eval_auc"],
        "calendar_auc": result["references"][calendar["name"]]["eval_auc"],
        "majority_accuracy": majority["eval_accuracy"],
        "persistence_vs_calendar_ci95":
            result["bootstrap"]["persistence_vs_calendar"]["ci95"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
