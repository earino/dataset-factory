#!/usr/bin/env python3
"""Record the 2026-11-05 pre-launch pins for nws-tornado-warning-verification.

All values below are measured (probe outputs retained under probe/out/) or
quoted from the fetched paper; nothing is retyped from memory. This update
happens BEFORE the nws-tornado-build-001 launch, per the pre-registered plan
("pin the exact per-warning list into the record BEFORE launch").
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent  # candidates/<id>/
RECORD = HERE / "record.json"
r = json.loads(RECORD.read_text())

r["measurements"]["preflight_2026_11_05"] = {
    "anchors_reverified_exact": (
        "2026-11-05 coordinator pulls: 2013 = 19,590,053 B -> 1,832 raw "
        "features / 441 verified / 94 WFOs / 170 active days / 100 verified "
        "days / FAR[1] 0.7593; 2023 = 28,383,984 B -> 2,531 / 656 / 96 / 201 "
        "/ 115 / 0.7408. BOTH anchors reproduce EXACTLY (the record-pinned "
        "2026-10-19 counts are identical; the 2023 file changed bytes "
        "28,389,049 -> 28,383,984 while the counts held: live recomputation, "
        "stable counts - the current-vintage basis for quality.json). "
        "cow response shape: events.features (not top-level features), "
        "stats.events_total/events_verified agree with the raw feature "
        "counts in both anchor years."),
    "duplicate_feature_structure_measured": (
        "cow emits byte-identical duplicate features: 2013 FWD #33 x2 (zero "
        "differing properties), Joplin day file 2011-05-22 SGF #28 and #30 "
        "each x2; 2023 has none. cow's own stats count the duplicates "
        "(stats.events_total 1832 = 1831 distinct + 1 dup). Build rule "
        "pinned: drop byte-identical duplicates; same-key with DISAGREEING "
        "verify refuses the build; same-key agreeing verify keeps the "
        "earliest product_id. Raw feature counts are the anchor unit; row "
        "counts post-dedupe."),
    "product_text_sample_decision_excluded_v1": (
        "500-warning deterministic spread sample from the 2023 year file "
        "(probe/preflight_2026_11_05.py sample mode): 500/500 fetched OK, 0 "
        "failures, bytes p50 1,598 (min 1,278 / max 2,595), latency p50 458 "
        "ms, wall 49.2 s at 5 workers -> implied ~40,000 warnings = 305 min "
        "serial / 61 min at 5 workers, over the 60-min worker lifetime on "
        "fetches alone plus load/politeness risk on one public service. "
        "DECISION: v1 ships cow per-event fields only; product_text/IBW "
        "fetch EXCLUDED. A v2 wanting the tornado-tag category should probe "
        "IEM's bulk AFOS archive channel, not per-warning fetches."),
    "arkansas_fixture_correction_before_launch": (
        "The record's original fixture expectation ('the 2022-04-16 storm's "
        "warnings must read verify=false') was WRONG and is corrected BEFORE "
        "launch on measured evidence: (1) the paper at arXiv 2510.25011 is "
        "Wolff, Goodnight, Blind-Doskocil, Conklin, Gustafson, "
        "Trujillo-Falcon 2025, 'Reflecting on a Decade of Formalized Tornado "
        "Emergencies' - the record's 'Keylon 2025' attribution was a citation "
        "slip (Keylon 2025 is the performance.commerce.gov storm-based FAR "
        "KPI the same paper cites for the 0.69 all-warnings FAR). (2) The "
        "paper's own words: '3 tornado emergency false alarms, all of which "
        "were issued for the same nontornadic thunderstorm in northern "
        "Arkansas on 16 April 2022', 'false real-time reports of tornado "
        "damage' (Navarro 2022). (3) The IEM tornado-emergency archive the "
        "paper used (api/1/nws/emergencies.json) identifies the three 2022-04-16 "
        "UTC storm warnings: LZK #49 (00:09Z), LZK #50 (00:45Z), MEG #40 "
        "(01:05Z, states=AR) - one storm crossing the LZK/MEG boundary. "
        "(4) MEASURED cow verdicts on 2026-11-05: LZK #49 verify=TRUE, LZK "
        "#50 verify=TRUE, MEG #40 verify=FALSE - the false real-time tornado "
        "LSrs that later surveys reclassified as straight-line wind remain "
        "in the LSR archive and verify two of the three. CONSEQUENCE: the "
        "task label is REPORT-based (LSR archive), the paper's 0.03 "
        "emergency FAR is SURVEY-based (NCEI tracks); the 89-emergency "
        "0.03-FAR cross-check is NOT expected to reproduce under the LSR "
        "label and is reframed as the documented semantics caveat. The "
        "pinned per-warning fixture asserts the MEASURED cow verdicts "
        "(1/1/0) plus the Joplin known-positive event."),
    "joplin_known_positive_fixture": (
        "2011-05-22 SGF TOR warnings (national day pull 2026-11-05): #28 "
        "21:25Z verify=FALSE (x2 identical duplicate features), #29 21:51Z "
        "FALSE, #30 22:09Z FALSE (x2), #31 22:17Z TRUE, #32 22:48Z TRUE. "
        "Asserted as the known-positive event: #31 and #32 (in effect over "
        "Jasper/Newton/Lawrence MO as the EF-5 crossed Joplin) MUST read "
        "verify=1; #28/#29/#30 recorded as measured context, not asserted "
        "(their FALSE values are LSR-timing/polygon facts, not externally "
        "documented certainties)."),
    "local_dry_run_construct_only": (
        "build.py --dry-run over the cached 2013+2023 anchor files "
        "(construct only, no performance metric, no gate): 2013 -> 1,831 "
        "rows / 441 positives / 100 positive days (1 byte-identical "
        "duplicate dropped), 2023 -> 2,531 / 656 / 115, stats cross-checks "
        "and anchor asserts green, CSVs + quality.json + meta.json written. "
        "score.py's first execution was the synthetic smoke test "
        "(test_score_smoke.py): references, gap rule, bootstrap and report "
        "all exercised; no real-data figure exists anywhere on this host."),
}

r["construction_script"] = "source/build.py"
r["jobs"] = r.get("jobs", [])

r["next_action"] = (
    "EXECUTING the pre-registered plan (SESSION DECISION 2026-11-05): "
    "preflight done 2026-11-05 (measurements.preflight_2026_11_05: anchors "
    "re-verified EXACT, fixture corrected to measured per-warning verdicts "
    "BEFORE launch, product_text fetch EXCLUDED on the 500-warning sample, "
    "duplicate-structure rule pinned, local construct-only dry run green, "
    "score.py smoke green). Construction source written: source/build.py "
    "(construct only: 17 year-pulls, dedupe rule, anchor+fixture asserts, "
    "row ledger), source/run.sh (fixed order construct -> full-artifact "
    "gate -> exact-byte --accept -> score.py), source/score.py (references "
    "on identical eval rows only: majority, persistence with the declared "
    "30-min outcome-availability assumption, calendar/identity train-only "
    "priors; per-issue-year AUC/Brier/prevalence; day-clustered paired "
    "bootstrap), source/job.json + bundle.json (nws-tornado-build-001, "
    "cx23/hel1, lifetime 60 min, EUR ~0.10 reservation). LAUNCH ORDER: "
    "assemble -> plan -> launch -> collect on success -> destroy with "
    "provider read-back. The FULL MODEL (stock runner) is a separate "
    "baseline job per the za-cct/cqc pattern (documented deviation from a "
    "single-job triad: the deciding rule is applied in the record once the "
    "runner number exists alongside these references). PRE-REGISTERED "
    "deciding rule (unchanged, written before any score): headroom only if "
    "the full model beats EVERY simple reference on identical eval rows "
    "with the day-clustered paired bootstrap 95% CI excluding zero in the "
    "model's favour; reference dominance with CI excluding zero on the "
    "deficit side -> DROP (wb-loan/unhcr precedent); inconclusive -> HOLD "
    "with the negative finding preserved; NO re-tuning of splits, "
    "population, features or label after any score. Stopping condition: "
    "anchor/fixture/duplicate/gate failure or empty/one-class eval -> "
    "collect diagnostics, diagnose, record; ONE rebuild per structural "
    "defect class; a second failure of the same class is a recorded "
    "blocker. If the session ends with the worker running: the running job "
    "is the handoff (expected reports = summary.json, "
    "qualification-*.json, acceptance-*.txt, references-*.json; next "
    "acceptance check = gate ok:true + ACCEPTED + the fixture list).")

RECORD.write_text(json.dumps(r, indent=1) + "\n")
print("record updated; status:", r["status"])
