#!/usr/bin/env python3
"""Record the 2026-11-05 advancement-session launch of ibama-build-001.

Writes the preflight (source locations, stage boundaries, first-metric
location), the compact plan, and the PRE-REGISTERED deciding rule into the
candidate record BEFORE any construction score exists, and sets
construction_script. Run from the repository root.
"""
import json
from pathlib import Path

RECORD = Path("candidates/ibama-auto-infracao-recidivism/record.json")


def main() -> None:
    record = json.loads(RECORD.read_text())
    record["construction_script"] = "candidates/ibama-auto-infracao-recidivism/source/build.py"
    record["preflight_2026_11_05"] = {
        "session": "scheduled advancement 2026-11-05",
        "plan": {
            "candidate": "ibama-auto-infracao-recidivism",
            "next_decision": ("construct the pre-registered entity-instant panel on a "
                              "worker, qualify the FULL artifact with gate 1.5.0, "
                              "exact-byte accept, then compute the reference triad; "
                              "the runner-contract model baseline is the following job "
                              "and decides headroom against these references"),
            "required_evidence": [
                "pinned current-vintage zip sha256 + export stamp + per-window counts "
                "with drift vs the 2026-11-03 probe reference (recorded, not asserted)",
                "gate 1.5.0 passing report over the full artifact on the worker "
                "(failed_checks empty), including the two declared cross-row probes",
                "exact-byte --accept against that report",
                "reference triad on identical eval rows with cluster-aware paired "
                "bootstrap CIs by entity and per-eval-year structural reporting",
            ],
            "expected_artifact": ("extract public/train.csv, public/eval.csv, "
                                  "private/holdout.csv, meta.json, quality.json at "
                                  "/output/extract; reports qualification-, "
                                  "acceptance-, references-, summary-*.json uploaded "
                                  "to the private staging release"),
            "job": "ibama-build-001 (bundle ibama-build, cx23/hel1, 45 min timeout)",
            "stopping_condition": ("fixture/build/gate/acceptance failure -> collect "
                                   "diagnostics, diagnose, record; ONE rebuild per "
                                   "structural defect class; a reference-dominance "
                                   "measurement is a finding, not a retry trigger"),
        },
        "entrypoint_review": {
            "what_chooses_rows": ("build.py panel pass (flush_group): lavratura year in "
                                  "a scored window (window_of), normalized 11/14-digit "
                                  "entity key, and lavratura instant at or before the "
                                  "right-censoring cutoff (max observed lavratura minus "
                                  "365 days) so the label window is fully observed; "
                                  "excluded rows counted per bucket and the row ledger "
                                  "must reconcile to the deduped count"),
            "what_writes_the_artifact": ("build.py writes public/train.csv, "
                                         "public/eval.csv, private/holdout.csv "
                                         "streaming per entity group, then meta.json "
                                         "and quality.json from the same accumulated "
                                         "stats, then verifies the written files "
                                         "against the declarations"),
            "where_qualification_runs": ("run.sh stage 2: "
                                         "skills/dataset-qualification/scripts/"
                                         "qualify_dataset.py (gate 1.5.0, copied "
                                         "verbatim by assemble-job) over "
                                         "/output/extract on the worker, full rows"),
            "where_acceptance_runs": ("run.sh stage 3: qualify_dataset.py --accept "
                                      "against the just-written report; run.sh stops "
                                      "on any nonzero stage"),
            "first_performance_metric": ("run.sh stage 4: score.py, which re-checks "
                                         "the accepted report and on-disk digests "
                                         "before its first metric and never opens "
                                         "private/holdout.csv; build.py computes no "
                                         "AUC/accuracy/model (asserted by the "
                                         "synthetic fixture's output scan), and the "
                                         "fixture test runs on the worker BEFORE the "
                                         "live source is touched"),
            "row_filters_vs_timing": ("the timing declaration (event_time instant, "
                                       "administrative record, feature lag 0) is "
                                       "implemented by construction: shipped features "
                                       "are the auto's own issuance attributes plus "
                                       "strictly-prior autos only; every post-instant "
                                       "field (status, cancellation, alteration "
                                       "metadata, launch date, ciencia/process dates, "
                                       "names) is declared post_hoc and never "
                                       "written; the censor cutoff reads the pinned "
                                       "vintage's END, never a row's own outcome, "
                                       "and the selection kind is declared "
                                       "prediction_time with that evidence"),
            "contract_vs_source": ("the record's prediction_time feature list is "
                                   "implemented exactly (TIPO_AUTO, TIPO_MULTA, "
                                   "VAL_AUTO_INFRACAO, GRAVIDADE_INFRACAO, "
                                   "MOTIVACAO_CONDUTA, TIPO_INFRACAO/COD_INFRACAO, "
                                   "UF/COD_MUNICIPIO, DS_BIOMAS_ATINGIDOS, TIPO_ACAO, "
                                   "OPERACAO + prior-history features); entity keys "
                                   "normalized to bare digits before join/hash "
                                   "(punctuated variants merge, measured); dedupe on "
                                   "SEQ_AUTO_INFRACAO with conflict-refusal; "
                                   "Cancelado/Excluido/Substituido rows stay in the "
                                   "population with their status recorded per window "
                                   "in summary.json and never shipped; labels read "
                                   "the FULL table so excluded-window autos "
                                   "(2020-21 dip, censored tail) still label"),
            "cross_row_design": ("the entity-instant panel is structurally "
                                 "self-answering under row joins (a T+365d "
                                 "re-autuacao is a later row's prior-history feature "
                                 "and its own existence answers the earlier row's "
                                 "label), exactly as the record pre-registered; "
                                 "quality.json declares access=isolated_rows with "
                                 "two declared reverse-history probes the gate "
                                 "executes over the full artifact "
                                 "(next_auto_gap_recovery: days_since_prev_auto < "
                                 "365 addresses the entity's previous auto; "
                                 "prior_count_growth_365d: ABS-style window probe); "
                                 "both were shape-verified on the synthetic fixture "
                                 "(probe 0 covered 3/1/3 rows with the one "
                                 "documented 365-day boundary mismatch; probe 1 "
                                 "low-coverage as designed) and the enforced "
                                 "restricted protocol travels with the artifact"),
            "fixture_evidence": ("synthetic-zip fixture green locally and on-path in "
                                 "run.sh: labels at the 365/366-day boundaries, "
                                 "same-day successors, gap-window successors, "
                                 "punctuated-variant entity merging, censoring, "
                                 "ledger reconciliation, TP_PESSOA cross-check, "
                                 "meta/quality-vs-files; gate --selftest green "
                                 "(every broken fixture still rejected)"),
        },
        "pre_registered_deciding_rule": (
            "written BEFORE any construction score existed (this update precedes the "
            "ibama-build-001 launch): the full runner-contract model, trained by the "
            "separate baseline job on the identical eval rows under the artifact's "
            "isolated_rows protocol, must beat EVERY simple reference computed by "
            "score.py (persistence_recency, persistence_count_365d, "
            "persistence_count_rate, identity_entity_history, identity_count_history, "
            "calendar_month_rate, calendar_identity, global_rate, majority_class) "
            "for any headroom claim; if any reference matches or beats the model with "
            "a cluster-aware paired bootstrap 95% interval excluding zero on the "
            "deficit side, the verdict is 'no demonstrated headroom under this "
            "protocol' and the wb-loan-disbursement-completion / "
            "unhcr-corridor-entry-surge precedent applies (drop, negative finding "
            "preserved); an interval containing zero is an inconclusive difference, "
            "not parity; no re-tuning of the label window, population or splits after "
            "scores is permitted"),
    }
    record["next_action"] = (
        "LAUNCHED (advancement session 2026-11-05): job ibama-build-001 constructs the "
        "pre-registered entity-instant panel per preflight_2026_11_05 (construct -> "
        "full-artifact gate 1.5.0 on the worker -> exact-byte accept -> reference "
        "triad BEFORE any model figure). After collection: verify the gate report "
        "(failed_checks empty, both cross-row probes recorded), verify --accept, read "
        "the references with their CIs, record drift vs the 2026-11-03 probe vintage, "
        "then run the runner-contract baseline as the FOLLOWING job "
        "(ibama-baseline-001: fetch the accepted extract from staging, re-accept, "
        "materialize public train+eval only, run the benchmark's train.py/validate.sh "
        "unmodified) and apply the pre-registered deciding rule in "
        "preflight_2026_11_05.pre_registered_deciding_rule against the model's eval "
        "AUC on the identical rows."
    )
    RECORD.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print("record updated: preflight + pre-registered deciding rule written;")


if __name__ == "__main__":
    main()
