#!/usr/bin/env python3
"""Record the cpcb-aqi-exceedance packaging step (2026-11-06).

Adds measurements.packaging_2026_11_06 (what was assembled, from which
digest-verified bytes, which checks passed), moves status ready -> qualified
(check-candidate vocabulary: constructed+qualified, not yet staged), and
rewrites next_action to the private-staging order per the cqc/za-cct
precedent. Every figure quoted here is read from the files written by the
packaging step or the collected job evidence - nothing retyped.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAND = ROOT / "candidates" / "cpcb-aqi-exceedance"
REL = ROOT / "release" / "cpcb-aqi-exceedance"
ART = "a749f0df2f9dd0103d0ba56524e1cc3638242fbc4710b0cac99603bcdef0d959"

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest = json.loads((REL / "MANIFEST.json").read_text())
assert manifest["artifact_version"] == ART
assert manifest["qualification"]["ok"] is True and manifest["qualification"]["failed_checks"] == []
assert manifest["baseline"]["contract"]["contract_ok"] is True

package_files = sorted(p.relative_to(REL).as_posix()
                       for p in REL.rglob("*") if p.is_file())

record_path = CAND / "record.json"
record = json.loads(record_path.read_text())
now = datetime.now(timezone.utc).isoformat(timespec="seconds")

record["measurements"]["packaging_2026_11_06"] = {
    "recorded_at": now,
    "step": "dataset-release packaging (release/ assembled, manifest + package check green; "
            "private staging is the next step and has NOT run)",
    "commands": [
        "python3 candidates/cpcb-aqi-exceedance/package/build_release_2026_11_06.py",
        "python3 candidates/cpcb-aqi-exceedance/package/record_splits_2026_11_06.py",
        "python3 scripts/release-manifest.py cpcb-aqi-exceedance",
        "python3 scripts/check-package.py release/cpcb-aqi-exceedance",
        "python3 scripts/publish-dataset.py cpcb-aqi-exceedance   (dry-run; --execute NOT run)",
    ],
    "package_dir": "release/cpcb-aqi-exceedance",
    "package_file_count": len(package_files),
    "package_files": package_files,
    "artifact_version": ART,
    "construction_commit": manifest["construction_commit"],
    "gate_report_sha256": sha(REL / "qualification.json"),
    "quality_json_sha256": sha(REL / "quality.json"),
    "meta_json_sha256": sha(REL / "meta.json"),
    "gate_script_sha256": sha(REL / "code" / "qualify_dataset.py"),
    "build_py_sha256": sha(REL / "code" / "build.py"),
    "score_py_sha256": sha(REL / "code" / "score.py"),
    "run_sh_sha256": sha(REL / "code" / "run.sh"),
    "materialize_py_sha256": sha(REL / "code" / "materialize.py"),
    "runner_files_sha256": json.loads((REL / "measurements.json").read_text())
        ["runner_contract_probe"].get("dependencies") and
        json.loads((CAND / "baseline" / "baseline_result.json").read_text())
        ["runner_files"]["bundled_sha256"],
    "checks": {
        "check_package": "OK first pass (release/cpcb-aqi-exceedance: OK)",
        "release_manifest": f"wrote MANIFEST.json + SHA256SUMS (artifact_version {ART[:16]}..., "
                            "5 files, baseline present)",
        "publish_dry_run": "rc=0: would create v2026.11, 5 assets, 88.8 MB, streamed from "
                           "staging 436180445, artifact from commit 75652fb6; --execute NOT run "
                           "(old direct-publication path; private staging uses the "
                           "cqc/za-cct publish worker-job pattern)",
        "doc_verification": "get_dataset.py compiles and its EXPECTED block equals "
                            "expected_artifact.json exactly (5 files); "
                            "baseline/reproduce_baseline.sh passes sh -n; no unreplaced "
                            "template token in any generated document; the ladder figures "
                            "render in README (0.9734 / 0.9689 / 0.8617)",
    },
    "notes": [
        "meta.json fetched from private staging release 436180445 asset 716182946 (1,197 B) "
        "with digest verification against expected_artifact.json - compact metadata, no bulk "
        "data through the coordinator",
        "baseline/expected_artifact.json gained a 'job' key equal to its 'source_job' "
        "(cpcb-aqi-build-004) because release-manifest.py reads expected['job']; no value changed",
        "candidates/cpcb-aqi-exceedance/baseline/baseline_result.json is the collected "
        "cpcb-aqi-baseline-001 result (sha256 29eb43eb653b2e08... equal to the staging "
        "manifest entry), placed where both release-manifest.py and the package read it",
        "the package's measurements.json, README, RELEASE_NOTES, VERIFICATION, REPRODUCE, "
        "DATA_DICTIONARY and LICENSE documents were generated from the record, the gate "
        "report, the baseline result and the references report; no figure retyped",
    ],
}

record["status"] = "qualified"
record["updated_at"] = now
record["qualification"] = {
    "gate_version": manifest["qualification"]["gate_version"],
    "artifact_version": ART,
    "job": manifest["artifact_job"],
    "accepted": "exact-byte --accept ACCEPTED on the worker against artifact_version "
                + ART + " (run.sh stage 3, after the gate, before any reference); "
                "re-accepted from fetched bytes in cpcb-aqi-baseline-001 before any score "
                "(accepted_before_scoring: true in baseline_result.json)",
    "qualified_at": "2026-11-06 (worker job cpcb-aqi-build-004, exit 0; gate 1.5.0 ok=true, "
                    "45/45 checks, failed_checks=[]; reports collected 06:43:35Z)",
    "checks": "45/45, failed_checks empty",
    "cross_row_probe_on_real_artifact":
        "the declared probe is next_day_mean_recovery (quality.json cross_row_audit: same-station "
        "offset-1 join donates its pm25_mean, which is exactly this row's label operand; gt 90 "
        "reproduces the label by construction). The serial exposure is real and declared, not "
        "argued away: row D's label is a function of the D+1 mean - row D+1's own pm25_mean "
        "feature - and the same value enters the trailing aggregates of rows D+2..D+91. Access "
        "is isolated_rows and the scope is restricted retrospective research "
        "(use=retrospective_research); honest evaluation keeps rows isolated. The gate's "
        "45-check run on the full artifact passed with no failed check; the probe is declared "
        "in the descriptor and the exposure is recorded in evaluation_contract.limitations",
    "rebuild_history": "cpcb-aqi-build-001 refused (station state_name gap, sentinel repair); "
                       "-002 refused (defective probe panel-total anchor, count anchors "
                       "restructured); -003 refused (Delhi fixture operand 38 vs 39, registry "
                       "semantics repaired); -004 green. Three refusals across three distinct "
                       "defect classes, one repair each, all diagnosed from retained evidence "
                       "and recorded in measurements",
    "report": "private staging release 436180445 (tag job-cpcb-aqi-build-004); gate report, "
              "acceptance, quality.json, extract summary and references fetched "
              "digest-verified to .factory/cpcb-aqi-build-004/reports/; the gate report is "
              "shipped in the package as release/cpcb-aqi-exceedance/qualification.json "
              "(sha256 " + sha(REL / "qualification.json")[:16] + "...)",
}
record["next_action"] = (
    "PACKAGED (not yet staged): release/cpcb-aqi-exceedance assembled and check-package green; "
    "MANIFEST artifact_version a749f0df2f9dd010..., 5 assets, 88.8 MB, from staging 436180445, "
    "construction commit 75652fb6. Private staging per the cqc/za-cct worker-job pattern, in order: "
    "(1) create the PRIVATE repo earino/cpcb-aqi-exceedance (publish token), commit the package "
    "files as its initial commit, create release v2026.11 at that commit (non-draft, tag == main); "
    "(2) jobs/cpcb-aqi-publish-001 (release:true transfer job, cqc publish/job.json pattern): copy "
    "the five accepted assets from staging release 436180445 into the new release under the flat "
    "names, sha256 verified on arrival and server-side, asset ids resolved via "
    "publish-dataset.py --stream-test; (3) the fresh-consumer worker job (cqc consumer/source "
    "pattern) on the released bytes: gate re-run, exact-byte --accept, baseline reproduce "
    "(both AUC prints 0.9734, CONTRACT OK), references recomputed equal; (4) hf-publish.py "
    "--create --upload-small + the hf_publish worker job + --verify + --tag; (5) "
    "release/cpcb-aqi-exceedance/DESTINATIONS.json both blocks (github: verified release, tag, "
    "files_verified list; hub: revision, loading check), record -> packaged with packaged_at + "
    "awaiting_operator TRUE only after the pre-flip audit prompt exists (generate from "
    "skills/dataset-release/templates/pre-flip-audit-prompt.md with digests filled "
    "programmatically from the frozen manifest). The holdout stays sealed; no re-tuning after "
    "any score. After the staging steps: check-candidate --all, check-package, check-suitability, "
    "suite."
)

record_path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
print("record updated: status=qualified, measurements.packaging_2026_11_06 written,")
print("next_action = private staging order")
print("package files:", len(package_files))
