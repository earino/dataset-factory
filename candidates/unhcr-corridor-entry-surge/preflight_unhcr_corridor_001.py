#!/usr/bin/env python3
"""Record the unhcr-corridor-001 preflight + the PRE-REGISTERED deciding
check into candidates/unhcr-corridor-entry-surge/record.json, before the
worker launch. No score existed when this ran: the local dry runs verified
counts, anchors, fixtures and gate diagnostics only (build.py computes no
performance metric; score.py has never run on real bytes).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

RECORD = Path(__file__).resolve().parent / "record.json"
record = json.loads(RECORD.read_text())

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

record["construction_script"] = "candidates/unhcr-corridor-entry-surge/source/build.py"
record["updated_at"] = now

record["preflight_unhcr_corridor_001"] = {
    "recorded_at": now,
    "design_decisions_before_any_score": {
        "population": (
            "momentum-eligible one-shot: one row per corridor at its FIRST "
            "year >= 500 G/P applications (entry year T0), requiring a "
            "published strictly positive T0-1 value (the parent task's own "
            "eligibility rule; capacity measured for exactly this variant "
            "in split_strategy - chosen now, before any score, and never "
            "re-tuned after one)"),
        "label": "cum2_2x: corridor total over T0+1..T0+2 >= 2 x T0 total",
        "splits": "entry years train 2000-2014 / eval 2015-2020 / holdout 2021-2023",
        "features": (
            "18 at-instant features: origin, asylum, entry_year, apps_t0, "
            "apps_t0m1, log_growth_into_entry, surged_into_entry, "
            "years_since_first_seen, prior_history_len, prior_max, "
            "host_apps_t0/t0m1/growth, origin_apps_t0/t0m1/growth, "
            "share_of_host_t0, share_of_origin_t0; carry entry_date "
            "(time column) + surge_cluster (origin|entry-year event key)"),
        "runner_layout": "public/train.csv, public/eval.csv, private/holdout.csv, meta.json, quality.json",
        "cross_row": (
            "corridor-grain exposure structurally removed (one row per "
            "corridor; the gate's corridor-grain probe must read coverage "
            "0). Origin/host aggregate features SHIP (the record's declared "
            "partial-information exposure): the build measures exactly "
            "whether any shipped aggregate equals another row's label "
            "operand, and the gate runs 4 declared probes (corridor grain; "
            "origin aggregate at +12/+24 months; host aggregate at +12 "
            "months). evaluation_contract.access = isolated_rows"),
        "exclusions_counted": (
            "missing_published_prior (left-censored T0=2000 + zero-valued "
            "prior cells), live_edge_outcome_beyond_vintage (entries >= "
            "2024), host_silent_outcome_year - all counted per split, "
            "never value-conditioned, never silently dropped"),
    },
    "local_dry_run_on_pinned_source": {
        "source": ("/opt/data/cache/scratch/unhcr-oneshot-2026-11-04/"
                   "asylum_applications_residing_world.csv, sha256 "
                   "d5808616c3d10d33925d4df5a3182a2028dd574d111e843cc207455ba45fe950 "
                   "= the record's pin, re-verified before the run"),
        "anchors_reproduced": {
            "train": "363 rows / 127 positives / 106 events",
            "eval": "202 rows / 98 positives / 80 events",
            "holdout": "159 rows / 72 positives / 64 events",
            "full_population_cross_check": "653/214/153, 230/103/83, 170/73/64 - all equal to the recorded design table",
        },
        "fixtures": "all six green (AFG->USA 2021 TRUE, VEN->COL 2017 TRUE, UKR->POL 2014 FALSE, SYR->DEU 2000 left-censored excluded, SSD->ETH 2025 live-edge excluded, UKR->POL 2021 no-re-entry)",
        "gate_local_preflight": (
            "gate 1.5.0 on the dry-run extract: ok=true, failed_checks=[] "
            "(one iteration needed: origin/asylum cross the rows/5 "
            "cardinality threshold in this smaller population and are now "
            "DECLARED high_cardinality - the gate caught it locally, "
            "exactly what the preflight is for); local --accept ACCEPTED "
            "(dry run; the worker's full-artifact gate + accept remain the "
            "authoritative run)"),
        "exact_label_operand_recovery_measured": (
            "ZERO built rows in any split have a shipped origin/host "
            "aggregate equal to another row's label operand (verified "
            "twice: the build's measurement and an independent "
            "re-implementation from the written CSVs; the panel's 497 "
            "single-corridor origin-years and 167 single-corridor "
            "host-years never coincide with a built row's outcome years "
            "plus a built donor). The residual aggregate exposure is "
            "sum-components only - partial information, declared, probed"),
        "gate_probe_diagnostics_local": {
            "corridor_grain": "covered 0/0/0 train/eval/holdout (the structural claim, gate-verified)",
            "origin_aggregate_12m": "covered 50/30/20, mismatches 31/14/7",
            "origin_aggregate_24m": "covered 39/27/9, mismatches 25/10/3",
            "host_aggregate_12m": "covered 36/20/4, mismatches 23/9/2",
        },
        "boundary_note": (
            "construct-only dry run, cqc vintage-probe precedent: counts, "
            "anchors, fixtures and gate diagnostics; NO reference, AUC or "
            "model figure was computed on real bytes - score.py's first "
            "real execution is inside the worker job, strictly after the "
            "worker's gate and exact-byte acceptance"),
    },
    "synthetic_rehearsal": (
        "tests/test_unhcr_corridor_build.py 12/12 OK: real build.py "
        "(--rehearsal skips only the real-data anchor/fixture asserts) "
        "over a synthetic HDX panel -> gate 0 failed checks -> accept -> "
        "score.py references (its first execution, synthetic bytes) -> "
        "one-row-per-corridor, label rule, exclusion machinery "
        "(left-censored, zero-valued prior cell, host-silent, live edge) "
        "-> byte-identical rebuild -> FIVE red/green refusals: eval row "
        "outside the declared window, timing block removed, stale report "
        "vs mutated bytes, a fully-declared label-determining "
        "outcome_ratio column caught by "
        "leakage.no_single_column_determines_the_target, duplicated row "
        "id"),
    "deciding_check_preregistered": {
        "registered_at": now,
        "registered_before": (
            "the unhcr-corridor-001 launch; no construction score existed "
            "at registration (the local dry run verified counts and gate "
            "diagnostics only)"),
        "rule": (
            "On the identical eval rows of the accepted artifact: "
            "reference-level headroom over identity-only priors is "
            "demonstrated ONLY if at least one pre-specified pair - (a) "
            "momentum_raw vs identity_combined, (b) "
            "momentum_bucket_rate_vs_identity_combined - has an observed "
            "AUC difference > 0 AND its cluster-aware paired bootstrap "
            "95% interval excluding zero in favor of the momentum "
            "reference. If identity_combined exceeds BOTH momentum "
            "references, the finding is identity_prior_dominates and the "
            "candidate is DROPPED for no headroom (the "
            "wb-loan-disbursement-completion precedent). Any other "
            "outcome (difference <= 0, or an interval containing zero) "
            "is recorded as no_demonstrated_headroom and the candidate "
            "is HELD: no packaging, no runner baseline job, the measured "
            "ladder preserved as the finding. An inconclusive interval is "
            "NOT parity. No re-tuning of the 2x threshold, the 500 "
            "eligibility, the label or the windows after any score; the "
            "measured fallback design (next1_g25) stays available only "
            "through a fresh operator decision, never a post-hoc switch"),
    },
}

record["next_action"] = (
    "IN FLIGHT (advancement session 2026-11-04/05): launch "
    "unhcr-corridor-001 (fresh attempt ID; assembled bundle "
    "candidates/unhcr-corridor-entry-surge/source/bundle.json via "
    "scripts/assemble-job.py, worker order construct -> gate 1.5.0 on the "
    "FULL artifact -> exact-byte --accept -> score.py references, run.sh "
    "fixed). HANDOFF on completion: collect the job, require gate ok=true "
    "with failed_checks EMPTY on the worker, --accept ACCEPTED, all six "
    "fixtures green, corridor-grain probe coverage 0, the recorded anchors "
    "363/127/106, 202/98/80, 159/72/64 reproduced, then DESTROY the worker "
    "(collect-then-delete, provider 404 read-back) and record: the "
    "reference ladder beside the pre-registered deciding check "
    "(preflight_unhcr_corridor_001.deciding_check_preregistered) - "
    "headroom demonstrated -> the runner-contract baseline job is next; "
    "no_demonstrated_headroom or identity_prior_dominates -> hold/drop "
    "per the pre-registered rule, negative finding preserved. ANY gate, "
    "fixture or anchor failure: collect diagnostics, diagnose, record - "
    "ONE rebuild per structural defect class, a second failure of the same "
    "class is a recorded blocker, never a blind retry.")

RECORD.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n")
print("record updated:", RECORD)
print("updated_at:", now)
