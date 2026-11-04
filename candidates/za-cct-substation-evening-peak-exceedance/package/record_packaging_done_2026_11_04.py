#!/usr/bin/env python3
"""Record packaging steps (iii)/(iv) DONE for za-cct-substation-evening-peak-exceedance.

Rewrites record.next_action: the package is assembled, manifest generated and
check-package green; what remains is private staging per the cqc precedent
(publish worker job, hf jobs, consumer job) and then the record flip to
packaged. Nothing else in the record changes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REC = ROOT / "candidates" / "za-cct-substation-evening-peak-exceedance" / "record.json"

record = json.loads(REC.read_text())

NEW = """OPERATOR DECISION (a) RECORDED 2026-11-04: package as an agent-headroom benchmark, with the comparison leading every package document - stock-runner baseline 0.5107 quoted beside the pre-registered headroom reference morning_ratio 0.7340 on the identical 14,965 eval rows, in every document, README first; no figure may be quoted without that comparison (full binding requirements and the ocha-fts agent-headroom framing are in the decision text below, unchanged). PACKAGING PIPELINE status: (i) DONE 2026-11-04 suitability record (artifact 9f2e10ce..., planned tag v2026.11, validated clean); (ii) DONE 2026-11-04 license.json + release.json; (iii) DONE 2026-11-04 packaging session: release/za-cct-substation-evening-peak-exceedance/ assembled by package/build_release_2026_11_04.py from digest-verified recorded bytes ONLY (construction commit c57e371 build.py/run.sh/score.py digests re-verified before copy; byte-pinned meta.json/quality.json equal to the accepted artifact's digests; qualification.json = the gate report sha256 0f1bb6a9...; canonical gate qualify_dataset.py 1.5.0 4fab8a34...; benchmark runner files verbatim from the read-only clone, bundled sha256 equal runner_files.json; measurements.json generated from the record + za-cct-001 gate reports + za-cct-baseline-001 result, nothing retyped); (iv) DONE 2026-11-04: record.construction_output.splits added from the gate-report values cross-checked against meta.json; release-manifest.py wrote MANIFEST.json + SHA256SUMS (artifact_version 9f2e10ce..., baseline present); check-package.py -> OK. publish-dataset.py dry-run rc=0 (plans v2026.11, 5 assets, 8.4 MB, streamed from staging 432591871, artifact from commit c57e371) - NOTE its plan text says 'public repository' because --execute is the OLD direct-publication path that also demands --confirm-publication: do NOT use --execute for private staging. REMAINING, in order: (v) private staging per the cqc precedent (watcher-recorded 59cb956): jobs/za-cct-publish-001 modeled on candidates/cqc-care-home-deregistration/publish/job.json (release: true worker job; create the PRIVATE repo earino/za-cct-substation-evening-peak-exceedance via the publish credential host-side outside every mount, then transfer the five accepted assets from staging release 432591871 into its v2026.11 release under the flat asset names, digest verified on arrival and server-side; resolve asset ids by digest match through publish-dataset.py --stream-test, never hand-copied), then hf-publish.py --create --upload-small + the hf_publish worker job, then the fresh-consumer worker job (download, checksums, gate re-run, --accept, baseline reproduce on the published bytes); (vi) DESTINATIONS.json both blocks (github verified at tag v2026.11; hub block names the tag step until --tag runs), record -> packaged (packaged_at, awaiting_operator FALSE until the pre-flip audit prompt is generated), check-candidate --all, suite. The pre-flip adversarial audit prompt (generated programmatically from the frozen manifest per skills/dataset-release/templates/pre-flip-audit-prompt.md, the cqc generate_pre_flip_audit_prompt.py pattern) and the flip itself remain the operator's single approval. Prior triad evidence stands as recorded: model 0.5107 vs morning_ratio 0.7340 (gap 0.2233), persistence 0.6502, calendar_identity 0.6504, identity_only 0.5134 on the same 14,965 eval rows; prevalence shift 11.20% -> 8.39% recorded; diagnosis candidates (a)-(d) in measurements.baseline_triad_2026_11_03_za_cct_baseline_001."""

assert record["status"] == "qualified"
old = record["next_action"]
assert "OPERATOR DECISION (a) RECORDED 2026-11-04" in old
record["next_action"] = NEW
record["updated_at"] = "2026-11-04T18:20:00+00:00"
REC.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("next_action rewritten:", len(NEW), "chars (was", len(old), "chars)")
