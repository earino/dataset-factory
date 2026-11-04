#!/usr/bin/env python3
"""Record the operator's packaging decision for za-cct-substation (2026-11-04).

The record pre-registered: "the OPERATOR records one decision among (a) package as an
agent-headroom benchmark with the comparison leading every package document - stock
baseline 0.5107 quoted beside morning_ratio 0.7340, on the ocha-fts precedent ...
(b) re-scope the task instance, or (c) drop. Scout does not package until (a) is
recorded."

The operator's 2026-11-04 scheduler brief (this session's task list) names this
candidate as actionable at stage "(package)" - selecting (a) among the three recorded
options. This script records that decision with its basis, plus the packaging
requirements the option carries, and leaves the pipeline steps for the packaging
session (documents, descriptors, manifest, staging, consumer verification).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECORD = ROOT / "candidates" / "za-cct-substation-evening-peak-exceedance" / "record.json"

NOW_ISO = "2026-11-04T14:22:00Z"

NEXT_ACTION = (
    "OPERATOR DECISION (a) RECORDED 2026-11-04: package as an agent-headroom benchmark, "
    "with the comparison leading every package document. Basis: the operator's 2026-11-04 "
    "scheduler brief lists this candidate as actionable at stage '(package)' - among the "
    "three recorded options ((a) package as agent-headroom benchmark, (b) re-scope, "
    "(c) drop) that selection is (a), exactly as Scout recommended. The decision carries "
    "these binding requirements from the recorded option: (1) the stock-runner baseline "
    "0.5107 (za-cct-baseline-001, both runner implementations agree, on the accepted "
    "artifact 9f2e10ce after --accept) is quoted BESIDE morning_ratio 0.7340 (the "
    "pre-registered headroom reference, fair same-information comparison - both read only "
    "shipped at-instant columns) in every package document, README first, and no figure "
    "may be quoted without that comparison; (2) the ocha-fts precedent governs the "
    "framing: the consumer is an agent that edits train.py and can compute the ratio in "
    "one line, so the reference ladder is the target to beat - this is an "
    "agent-headroom benchmark, NOT a demonstrated-model-headroom claim; (3) the holdout "
    "stays sealed and everything stays private until the operator's flip; (4) the "
    "retrospective_research evaluation contract (publisher released 2022-01-01.."
    "2024-12-31 as one closed table, hasStaticData since 2026-03) and the "
    "information-asymmetry note for persistence (recomputed scorer-side from strictly "
    "earlier same-station rows) are carried in every document. PACKAGING PIPELINE, in "
    "order, each step checkable by a fresh session: (i) suitability record "
    "suitability/za-cct-substation-evening-peak-exceedance.json written this session for "
    "artifact 9f2e10ce485635f65e695072e2bbd904024ebf58b1465d12fb969f8bb0692180 with "
    "planned release_tag v2026.11 (update it in the same change if the tag differs); "
    "(ii) candidates/za-cct-substation-evening-peak-exceedance/license.json (class A, "
    "City of Cape Town Open Data portal terms + Open Data Policy 27781, evidence already "
    "in record.license_evidence; follow the cqc license.json shape) and release.json "
    "(construction commit + build/script digests from the za-cct-001 bundle-owner "
    "record at .factory/za-cct-001/, staging release 432591871; commands gate/baseline/"
    "get_dataset; layout public/train.csv, public/eval.csv, private/holdout.csv, "
    "meta.json, quality.json); (iii) package documents (README, RELEASE_NOTES, "
    "VERIFICATION, REPRODUCE, DATA_DICTIONARY, measurements.json, get_dataset.py, code/, "
    "baseline/) with the comparison leading; (iv) python3 scripts/release-manifest.py "
    "<package-dir> then scripts/check-package.py green; (v) stage private: "
    "publish-dataset.py --execute (GitHub repo earino/"
    "za-cct-substation-evening-peak-exceedance), worker transfer job for the five "
    "assets, hf-publish.py --create --upload-small + hf_publish worker job, "
    "fresh-consumer worker job (download, checksums, gate re-run, --accept, baseline "
    "reproduce); (vi) DESTINATIONS.json both blocks, record -> packaged (packaged_at, "
    "awaiting_operator false until the pre-flip audit prompt is generated), "
    "check-candidate --all, suite. The pre-flip adversarial audit prompt (generated "
    "programmatically from the frozen manifest) and the flip remain the operator's. "
    "Prior triad evidence stands as recorded: model 0.5107 vs morning_ratio 0.7340 "
    "(gap 0.2233), persistence 0.6502, calendar_identity 0.6504, identity_only 0.5134 "
    "on the same 14,965 eval rows; prevalence shift 11.20% -> 8.39% recorded; "
    "concrete diagnosis candidates (a)-(d) recorded in "
    "measurements.baseline_triad_2026_11_03_za_cct_baseline_001."
)


def main() -> int:
    record = json.loads(RECORD.read_text())
    assert record["status"] == "qualified", record["status"]
    assert "Scout does not package until (a) is recorded" in record["next_action"]
    record["next_action"] = NEXT_ACTION
    record["updated_at"] = NOW_ISO
    RECORD.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print("record: status=%s updated_at=%s" % (record["status"], record["updated_at"]))
    print("next_action head:", record["next_action"][:120])
    return 0


if __name__ == "__main__":
    sys.exit(main())
