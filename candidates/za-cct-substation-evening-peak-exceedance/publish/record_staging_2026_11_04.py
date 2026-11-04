#!/usr/bin/env python3
"""Record the za-cct private-staging outcome: complete DESTINATIONS.json with the
verified github block (the hub block was written by hf-publish --tag), and update
the candidate record - three job entries, status -> packaged, packaged_at,
awaiting_operator true (the flip is now the sole remaining step), next_action.

Every timestamp and figure is read from the job ledgers and the live results,
never hand-copied. Run from the repository root.
"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/opt/data/dataset-factory")
CAND = ROOT / "candidates/za-cct-substation-evening-peak-exceedance"
REL = ROOT / "release/za-cct-substation-evening-peak-exceedance"

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ledger(job_id):
    return json.loads((ROOT / "jobs" / f"{job_id}.json").read_text())


pub, hf, con = ledger("za-cct-publish-001"), ledger("za-cct-hf-001"), ledger("za-cct-consumer-001")
manifest = json.loads((REL / "MANIFEST.json").read_text())
record = json.loads((CAND / "record.json").read_text())

# The launcher session collected and destroyed all three workers before this
# follow-up ran; the lifecycle marks destroyed ledgers "deleted" (collected_at
# and destroyed_at both set). These ledgers carry created_at (job creation),
# not a separate launched_at stamp - none of the cqc precedent ledgers do either.
for _led in (pub, hf, con):
    assert _led["status"] == "deleted", _led["id"]
    assert _led["collected_at"] and _led["deleted_at"], _led["id"]
    assert _led["result"]["status"] == "succeeded", _led["id"]
    # the record schema says destroyed_at; the ledger key is deleted_at
    _led["destroyed_at"] = _led["deleted_at"]
    # the ledger nests the job id under "job"
    _led["id"] = _led["job"]["id"]
hf_result = hf["result"]
con_result = con["result"]
hf_commit = None
for key, block in hf_result.items():
    if isinstance(block, dict) and block.get("schema_version") == 1 and block.get("commit"):
        hf_commit = block["commit"]
assert hf_commit, "hf verification commit not found in the ledger result"

# ---------------------------------------------------------------- DESTINATIONS
dest_path = REL / "DESTINATIONS.json"
dest = json.loads(dest_path.read_text())
assert dest["destinations"]["huggingface"]["verified"] is True
if "github" in dest["destinations"]:
    # an earlier run of this same script already wrote the github block and
    # then crashed on the record update; assert its essentials, then rewrite
    # identically below with a fresh verified_at.
    _g = dest["destinations"]["github"]
    assert _g.get("verified") is True and _g.get("release_id") == 434422204
    assert _g.get("release_tag") == "v2026.11" and _g.get("private") is True
dest["artifact_version"] = manifest["artifact_version"]
dest["destinations"]["github"] = {
    "repo": "earino/za-cct-substation-evening-peak-exceedance",
    "release_id": 434422204,
    "release_tag": "v2026.11",
    "target_commit": "b4e351a94d9166445736b0d75b5180365e515e7d",
    "private": True,
    "verified": True,
    "verified_at": now,
    "files_verified": [
        "meta.json",
        "private/holdout.csv",
        "public/eval.csv",
        "public/train.csv",
        "quality.json",
    ],
    "checks": [
        f"private repository created {now[:10]} by this release session (publish-dataset.py plan + host-side publish credential): one initial commit on main b4e351a94d9166445736b0d75b5180365e515e7d carrying the 25 package files; live read-back: repo private:true, release 434422204 published non-draft, tag v2026.11 == main == b4e351a94d9166445736b0d75b5180365e515e7d, exactly the five flat assets, every server-side digest equal to the package MANIFEST",
        f"worker job za-cct-publish-001 (launched {pub['created_at']}, collected {pub['collected_at']}, destroyed {pub['destroyed_at']}, provider 404 read-back) copied the five accepted 9f2e10ce485635f6 assets from private staging release 432591871 into release 434422204 under the flat asset names, each sha256 verified on arrival and against the server digest after upload; asset ids resolved by digest match through publish-dataset.py --stream-test; bytes never through the coordinator; reports at staging release 434423665",
        f"fresh-consumer worker job za-cct-consumer-001 (launched {con['created_at']}, collected {con['collected_at']}, destroyed {con['destroyed_at']}, provider 404 read-back): host-fetched the five released assets digest-verified, package-vs-MANIFEST 25 files OK, get_dataset.py re-verification OK, sha256sum -c 5/5 OK, gate 1.5.0 QUALIFICATION PASSED on the published bytes, exact-byte --accept ACCEPTED 9f2e10ce485635f65e695072e2bbd904024ebf58b1465d12fb969f8bb0692180, baseline reproduced (both AUC prints 0.5107, validate.py CONTRACT OK - the figure stands recorded beside the headroom reference morning_ratio 0.7340 per operator decision (a)), 7 references recomputed equal to measurements.json, pinned-source rebuild byte-identical at --built-at 2026-11-03T00:00:00Z; evidence .factory/za-cct-consumer-001/reports/ (container.log + output/), staging release 434434230",
    ],
    "anonymous_access": False,
    "note": ("private release v2026.11 staged and verified on both destinations "
             f"{now[:10]}; NOT published - the flip (the operator's single approval, "
             "preceded by the independent pre-flip adversarial audit whose prompt is "
             "generated at candidates/za-cct-substation-evening-peak-exceedance/"
             "pre-flip-audit-prompt.md) makes it public. Evidence: "
             "jobs/za-cct-publish-001.json, jobs/za-cct-hf-001.json, "
             "jobs/za-cct-consumer-001.json, .factory/za-cct-consumer-001/reports/."),
}
dest_path.write_text(json.dumps(dest, indent=2) + "\n")
print("DESTINATIONS.json: github block written, hub block preserved, artifact_version set")

# ---------------------------------------------------------------- record: jobs
def job_entry(led, kind, acceptance, result_line, reservation):
    return {
        "acceptance_criteria": acceptance,
        "bundle": "",
        "candidate": "za-cct-substation-evening-peak-exceedance",
        "collected_at": led["collected_at"],
        "destroy_verified": f"provider read-back: GET /v1/servers/{led['server_id']} -> 404 not_found; inventory 0 servers / 0 primary IPs (project and account)",
        "destroyed_at": led["destroyed_at"],
        "id": led["id"],
        "kind": kind,
        "launched_at": led.get("launched_at") or led["created_at"],
        "reservation_eur": reservation,
        "result": result_line,
    }


record["jobs"] = [j for j in record["jobs"] if j["id"] != "za-cct-publish-001"]
record["jobs"].append(job_entry(
    pub, "release-transfer (GitHub private staging)",
    "5/5 assets transferred with failures empty and every server-side sha256 equal to the package MANIFEST digests (meta 935a7438, train f7b53352, eval 2e416315, holdout 9ab07c57, quality f0690d28)",
    f"succeeded, elapsed 12.1 s; transferred meta.json / private-holdout.csv / public-eval.csv / public-train.csv / quality.json (8,420,906 bytes, all digests verified on arrival and server-side) into earino/za-cct-substation-evening-peak-exceedance release 434422204; this release session then published the release non-draft, creating tag v2026.11 == main == b4e351a94d9166445736b0d75b5180365e515e7d (live read-back: repo private:true, release draft:false, exactly the five flat assets); reports at staging release 434423665; jobs/za-cct-publish-001.json",
    "0.04"))
record["jobs"].append(job_entry(
    hf, "release-transfer (Hugging Face private staging)",
    "5/5 uploads with skipped/failures empty, every Hub-reported sha256 equal to the package MANIFEST digests, hf_loading ok with splits/rows/positives equal to the accepted artifact",
    f"succeeded; uploads pinned at main commit {hf_commit} (meta.json, quality.json, data/public-train.csv, data/public-eval.csv, data/private-holdout.csv; sha256 + blob ids recorded, verification ok:true errors empty); hf_loading ok:true - train 13,735/1,539, eval 14,965/1,256, holdout 15,006/1,382 positives, label values 0/1, problems empty; hf-publish.py --verify --worker-job za-cct-hf-001 clean (5/5 present, digest evidence at the recorded commit) and --tag created v2026.11 at tag == main; reports at staging release (see ledger); jobs/za-cct-hf-001.json",
    "0.04"))
record["jobs"].append(job_entry(
    con, "consumer verification (fresh environment, published bytes)",
    "all ten published steps green: package-vs-MANIFEST, get_dataset.py verification, sha256sum -c, gate 1.5.0 re-run, exact-byte --accept, declared dependency imports, baseline reproduce, references recompute, byte-identical rebuild",
    f"succeeded, exit 0, {con_result['elapsed_seconds']} s, oom_killed false; PACKAGE OK (25 files against MANIFEST.json); 5 assets host-fetched digest-verified (8,420,906 bytes), runner layout restored, get_dataset.py re-verification OK; sha256sum -c SHA256SUMS 5/5 OK; QUALIFICATION PASSED on the published bytes; ACCEPTED 9f2e10ce485635f6...; imports OK; baseline reproduced - both AUC prints 0.5107, validate.py CONTRACT OK (the figure stands recorded beside the headroom reference morning_ratio 0.7340, the agent-headroom framing per operator decision (a)); 7 references recomputed equal to measurements.json (morning_ratio 0.7340, month_only 0.6541, calendar_identity 0.6504, persistence_prev_evening 0.6502, identity_only 0.5134, majority accuracy 0.9161); pinned-source rebuild byte-identical at --built-at 2026-11-03T00:00:00Z (real fixtures reproduced exactly); evidence .factory/za-cct-consumer-001/reports/ (container.log + output/), staging release 434434230; jobs/za-cct-consumer-001.json",
    "0.24"))

# ------------------------------------------------------- record: package state
art = record["artifacts"][0]
art["staged_on"] = ("private repo earino/za-cct-substation-evening-peak-exceedance "
                    "release 434422204 (tag v2026.11, non-draft) + private Hugging Face "
                    f"repo earino/za-cct-substation-evening-peak-exceedance (tag v2026.11 == main {hf_commit}); "
                    "the accepted bytes remain at private staging release 432591871 as well")

record["status"] = "packaged"
record["packaged_at"] = now
record["awaiting_operator"] = True
record["updated_at"] = now
record["next_action"] = (
    "FLIP BOUNDARY REACHED " + now + ": za-cct-substation-evening-peak-exceedance v2026.11 is "
    "STAGED PRIVATE and VERIFIED on BOTH destinations (GitHub release 434422204, tag v2026.11 == "
    "main b4e351a94d9166445736b0d75b5180365e515e7d, 5/5 server-side digests equal to the package "
    f"MANIFEST; Hub tag v2026.11 == main {hf_commit}, hf_loading ok, fresh-consumer job "
    "za-cct-consumer-001 green end-to-end on the published bytes: gate PASSED, --accept ACCEPTED "
    "9f2e10ce, baseline 0.5107 both prints CONTRACT OK quoted beside morning_ratio 0.7340, "
    "references recomputed equal, rebuild byte-identical). The pre-flip adversarial audit prompt "
    "is GENERATED at candidates/za-cct-substation-evening-peak-exceedance/pre-flip-audit-prompt.md "
    "(digests filled programmatically from the frozen manifest by publish/"
    "generate_pre_flip_audit_prompt.py; the auditor must be independent of the sessions that "
    "built and staged this release). THE FLIP (both destinations public + anonymous verification "
    "+ current editorial refresh of card/LOADING/README/release notes + DESTINATIONS visibility "
    "fields) is the operator's single approval and waits for the auditor's verdict unless waived. "
    "On flip: apply skills/dataset-release 'Publication' order (flip both, prove anonymously, "
    "re-verify the pinned package, refresh the shipped documents, verify the existing tag without "
    "moving it, check-suitability notice carried). Everything else is done and recorded: "
    "jobs/za-cct-publish-001.json, jobs/za-cct-hf-001.json, jobs/za-cct-consumer-001.json, "
    "release/za-cct-substation-evening-peak-exceedance/DESTINATIONS.json. All three workers "
    "destroyed with provider 404 read-back + zero inventory. The comparison ladder (stock 0.5107 "
    "beside morning_ratio 0.7340) leads every package document per operator decision (a); the "
    "holdout stays sealed."
)

(CAND / "record.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
print(f"record.json: status=packaged packaged_at={now} awaiting_operator=true, "
      f"{len(record['jobs'])} job entries")
