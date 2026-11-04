#!/usr/bin/env python3
"""One-shot recording for the cqc private-staging follow-up (2026-11-04).

Watcher follow-up for three finished release jobs on cqc-care-home-deregistration
(cqc-publish-001, cqc-hf-001, cqc-consumer-001). Reads only collected evidence
(the job ledger files) plus this session's provider read-backs, then:

  1. appends the three job entries to candidates/cqc-care-home-deregistration/record.json,
  2. records the private staged release on artifacts[0] (tag/repo/release_url),
  3. moves the record to status=packaged with packaged_at (awaiting_operator
     stays false: the flip is NOT the sole remaining step - hf-publish.py
     --verify and --tag still stand),
  4. rewrites next_action to the remaining steps,
  5. writes release/cqc-care-home-deregistration/DESTINATIONS.json with both
     destination blocks (github verified at tag v2026.11; huggingface verified
     at pre-tag main fea98b695abd...).

No manifest, data byte, tag or destination is modified. DESTINATIONS.json is
deliberately not part of MANIFEST.json's package_files (a manifest cannot hash
the record of its own publication). Idempotence: refuses to run if any of the
three job ids is already recorded.
"""
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REC = ROOT / "candidates" / "cqc-care-home-deregistration" / "record.json"
DEST = ROOT / "release" / "cqc-care-home-deregistration" / "DESTINATIONS.json"
LEDGER = {jid: ROOT / "jobs" / f"{jid}.json" for jid in
          ("cqc-publish-001", "cqc-hf-001", "cqc-consumer-001")}

ARTIFACT = "afe9ee203f302f3ca41b9b01ad74a937e111d1b830590c7e662bb0b7b6df85d7"
NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
NOW_ISO = NOW.isoformat().replace("+00:00", "Z")


def main() -> int:
    record = json.loads(REC.read_text())
    known = {j.get("id") for j in record.get("jobs") or []}
    for jid in LEDGER:
        if jid in known:
            print(f"REFUSED: {jid} already recorded", file=sys.stderr)
            return 1
        entry = json.loads(LEDGER[jid].read_text())
        if entry.get("status") != "deleted":
            print(f"REFUSED: {jid} ledger status is {entry.get('status')!r}, not deleted",
                  file=sys.stderr)
            return 1
        res = entry.get("result") or {}
        if res.get("status") != "succeeded":
            print(f"REFUSED: {jid} result status is {res.get('status')!r}", file=sys.stderr)
            return 1

    art = record["artifacts"][0]
    assert art["artifact_version"] == ARTIFACT, art["artifact_version"]

    jobs_entries = [
        {
            "id": "cqc-publish-001",
            "candidate": "cqc-care-home-deregistration",
            "kind": "release-transfer (GitHub private staging)",
            "launched_at": "2026-11-04T10:09:38Z",
            "collected_at": "2026-11-04T10:18:22Z",
            "destroyed_at": "2026-11-04T10:19:08Z",
            "destroy_verified": "provider read-back 2026-11-04T10:46Z: GET /v1/servers/174456485 -> 404 not_found",
            "reservation_eur": "0.04",
            "bundle": "release-flagged transfer job (cx23/hel1): fetch the five accepted assets from private staging release 433536764, verify each sha256 on arrival, upload into the private repo release under the flat asset names, verify the server-side digest after upload; asset ids resolved by digest match through publish-dataset.py --stream-test",
            "acceptance_criteria": "5/5 assets transferred with failures empty and every server-side sha256 equal to the package MANIFEST digests (meta 3b350af6, train 6138dd92, eval 2078146f, holdout 880a36d4, quality 4e07a858)",
            "result": "succeeded, elapsed 21.1 s; transferred meta.json / private-holdout.csv / public-eval.csv / public-train.csv / quality.json (13,155,319 bytes, all digests verified on arrival and server-side) into earino/cqc-care-home-deregistration release 433767120; the owning release session then published the release non-draft, creating tag v2026.11 == main == 8bc008af97f60fd798bd8d453108c37fc0404d3a (live read-back 2026-11-04T10:47Z: repo private:true, release draft:false, tag v2026.11, exactly the five flat assets); reports at staging release 433770072; jobs/cqc-publish-001.json",
        },
        {
            "id": "cqc-hf-001",
            "candidate": "cqc-care-home-deregistration",
            "kind": "release-transfer (Hugging Face private staging)",
            "launched_at": "2026-11-04T10:33:16Z",
            "collected_at": "2026-11-04T10:37:02Z",
            "destroyed_at": "2026-11-04T10:49:15Z",
            "destroy_verified": "destroyed by the 2026-11-04 watcher follow-up after verified collection; provider read-back: GET /v1/servers/174459641 -> 404 not_found, provider inventory 0 servers / 0 primary IPs (project and account)",
            "reservation_eur": "0.04",
            "bundle": "hf_publish worker job (cx23/hel1): fetch the five released files from the private GitHub release 433767120 at recorded asset ids, verify each sha256 on arrival, upload each with the Hub-reported digest verified after upload, delete the local copy, run the documented load_dataset path against the uploaded bytes",
            "acceptance_criteria": "5/5 uploads with skipped/failures empty, every Hub-reported sha256 equal to the package MANIFEST digests, hf_loading ok with splits/rows/positives equal to the accepted artifact",
            "result": "succeeded, elapsed 100.4 s; uploads pinned at main commit fea98b695abd7804e78377c65782585af4e126e7 (meta.json, quality.json, data/public-train.csv, data/public-eval.csv, data/private-holdout.csv; sha256 + blob ids recorded, verification ok:true errors empty); hf_loading ok:true - train 78,138/4,418, eval 14,765/757, holdout 14,749/761 positives, label values 0/1, problems empty; anonymous Hub API read-back 2026-11-04: 401 (private); reports at staging release 433788369; jobs/cqc-hf-001.json",
        },
        {
            "id": "cqc-consumer-001",
            "candidate": "cqc-care-home-deregistration",
            "kind": "consumer verification (fresh environment, published bytes)",
            "launched_at": "2026-11-04T10:22:16Z",
            "collected_at": "2026-11-04T10:32:02Z",
            "destroyed_at": "2026-11-04T10:33:11Z",
            "destroy_verified": "provider read-back 2026-11-04T10:46Z: GET /v1/servers/174458029 -> 404 not_found",
            "reservation_eur": "0.24",
            "bundle": "cpx32/hel1 container job (python:3.13-slim): the worker host fetches the five released assets from the private release 433767120 with digest verification (the container holds no credential), then the container runs every published REPRODUCE.md step against the released bytes",
            "acceptance_criteria": "all ten published steps green: package-vs-MANIFEST, get_dataset.py verification, sha256sum -c, gate 1.5.0 re-run, exact-byte --accept, declared dependency imports, baseline reproduce, references recompute, byte-identical rebuild",
            "result": "succeeded, exit 0, 383.7 s, oom_killed false; PACKAGE OK (24 files against MANIFEST.json); 5 assets host-fetched digest-verified (13,155,319 bytes), runner layout restored, get_dataset.py re-verification OK; sha256sum -c SHA256SUMS 5/5 OK; QUALIFICATION PASSED on the published bytes; ACCEPTED afe9ee203f302f3c...; imports OK; baseline reproduced - both AUC prints 0.5659, validate.py CONTRACT OK (the figure stands recorded beside headroom reference rating_x_beds_rate 0.5871, the recorded stock-runner defect); 7 references recomputed equal to measurements.json; CQC-source rebuild byte-identical to the release at --built-at 2026-11-04T00:00:00Z (real fixtures reproduced exactly); evidence .factory/cqc-consumer-001/reports/ (container.log + output/), staging release 433783951; jobs/cqc-consumer-001.json",
        },
    ]
    record["jobs"].extend(jobs_entries)

    art["tag"] = "v2026.11"
    art["repo"] = "earino/cqc-care-home-deregistration (private)"
    art["release_url"] = "https://github.com/earino/cqc-care-home-deregistration/releases/tag/v2026.11"
    art["hub_repo"] = ("earino/cqc-care-home-deregistration (private Hugging Face dataset, "
                       "main commit fea98b695abd7804e78377c65782585af4e126e7, pre-tag)")

    record["status"] = "packaged"
    record["packaged_at"] = NOW_ISO
    record["awaiting_operator"] = False
    record["updated_at"] = NOW_ISO
    record["next_action"] = (
        "STAGED PRIVATE on BOTH destinations (v2026.11, NOT published): the accepted artifact "
        "afe9ee203f302f3c sits at the package MANIFEST digests on the private GitHub repo "
        "earino/cqc-care-home-deregistration release 433767120 (published non-draft, tag "
        "v2026.11 == main == 8bc008af, 5 flat assets, server-side digests verified by "
        "cqc-publish-001, fresh-consumer green end-to-end by cqc-consumer-001) and on the "
        "private Hub repo earino/cqc-care-home-deregistration at main commit fea98b695abd... "
        "(5 uploads digest-verified with blob ids, load_dataset check ok by cqc-hf-001; "
        "anonymous Hub API 401). release/cqc-care-home-deregistration/DESTINATIONS.json records "
        "both blocks. REMAINING, in order, before the flip: (1) python3 scripts/hf-publish.py "
        "--verify (files vs the manifest; also confirms the --create --upload-small small files "
        "including the card); (2) python3 scripts/hf-publish.py --tag (tag the commit that has "
        "the data) and update the hub DESTINATIONS block to revision v2026.11; (3) re-run "
        "python3 scripts/check-package.py release/cqc-care-home-deregistration; (4) the "
        "independent pre-flip adversarial audit using "
        "candidates/cqc-care-home-deregistration/pre-flip-audit-prompt.md (generated 2026-11-04, "
        "digests filled programmatically from the frozen manifest) - the flip waits for the "
        "auditor verdict unless the operator waives it; (5) set awaiting_operator true once the "
        "flip is the sole remaining step. The flip itself - both destinations, anonymous "
        "verification, DESTINATIONS visibility fields, current editorial refresh of card / "
        "LOADING / README / release notes, check-suitability notice carried - is the operator's "
        "single approval. Nothing public; the holdout stays sealed on both destinations."
    )

    raw = REC.read_text()
    indent = 1
    for line in raw.splitlines()[1:]:
        if line.startswith(" "):
            indent = len(line) - len(line.lstrip())
            break
    REC.write_text(json.dumps(record, indent=indent, ensure_ascii=False) + "\n")

    destinations = {
        "release_tag": "v2026.11",
        "destinations": {
            "github": {
                "repo": "earino/cqc-care-home-deregistration",
                "release_id": 433767120,
                "release_tag": "v2026.11",
                "target_commit": "8bc008af97f60fd798bd8d453108c37fc0404d3a",
                "private": True,
                "verified": True,
                "verified_at": NOW_ISO,
                "files_verified": [
                    "meta.json",
                    "private/holdout.csv",
                    "public/eval.csv",
                    "public/train.csv",
                    "quality.json",
                ],
                "checks": [
                    "private repository created 2026-11-04 by the release session (publish-dataset.py) with the package documents on main; live read-back 2026-11-04T10:47Z: repo private:true, release 433767120 published non-draft, tag v2026.11 == main == 8bc008af97f60fd798bd8d453108c37fc0404d3a, exactly the five flat assets",
                    "worker job cqc-publish-001 (collected 2026-11-04T10:18:22Z, destroyed 10:19:08Z, provider 404 read-back) copied the five accepted afe9ee203f302f3c assets from private staging release 433536764 into release 433767120 under the flat asset names, each sha256 verified on arrival and against the server digest after upload; bytes never through the coordinator",
                    "fresh-consumer worker job cqc-consumer-001 (collected 2026-11-04T10:32:02Z, destroyed 10:33:11Z, provider 404 read-back): host-fetched the five released assets digest-verified, package-vs-MANIFEST 24 files OK, get_dataset.py re-verification OK, sha256sum -c 5/5 OK, gate 1.5.0 PASSED on the published bytes, exact-byte --accept ACCEPTED afe9ee203f302f3c, baseline reproduced (both AUC prints 0.5659, CONTRACT OK), 7 references recomputed equal, CQC-source rebuild byte-identical at --built-at 2026-11-04T00:00:00Z",
                ],
                "anonymous_access": False,
                "note": (
                    "private release v2026.11 staged and verified 2026-11-04; NOT published - "
                    "the flip (the operator's single approval, preceded by the independent "
                    "pre-flip audit) makes it public. Evidence: jobs/cqc-publish-001.json, "
                    "jobs/cqc-consumer-001.json, .factory/cqc-consumer-001/reports/."
                ),
            },
            "huggingface": {
                "repo": "earino/cqc-care-home-deregistration",
                "commit": "fea98b695abd7804e78377c65782585af4e126e7",
                "private": True,
                "verified": True,
                "verified_at": NOW_ISO,
                "files_verified": [
                    "data/private-holdout.csv",
                    "data/public-eval.csv",
                    "data/public-train.csv",
                    "meta.json",
                    "quality.json",
                ],
                "missing": [],
                "size_mismatch": [],
                "digest_unverified": [],
                "loading_check": (
                    "verified by collected worker job cqc-hf-001: load_dataset path green - "
                    "train 78,138 rows / 4,418 positives, eval 14,765 / 757, holdout 14,749 / 761, "
                    "label values 0/1, problems empty, ok true"
                ),
                "worker_job": "cqc-hf-001",
                "note": (
                    "uploads verified at pre-tag main commit fea98b695abd7804e78377c65782585af4e126e7 "
                    "by worker job cqc-hf-001 (collected 2026-11-04T10:37:02Z, destroyed 10:49:15Z "
                    "by the watcher follow-up, provider 404 read-back): each file's Hub-reported "
                    "sha256 and blob id recorded and equal to the package MANIFEST digests; bytes "
                    "never through the coordinator. hf-publish.py --verify and --tag still to run; "
                    "when tagged, update this entry to revision v2026.11. Anonymous Hub API "
                    "read-back 2026-11-04: 401 (private). Private until the operator's flip."
                ),
            },
        },
    }
    DEST.write_text(json.dumps(destinations, indent=2, ensure_ascii=False) + "\n")

    print("record: status=%s packaged_at=%s awaiting_operator=%s jobs=%d"
          % (record["status"], record["packaged_at"], record["awaiting_operator"],
             len(record["jobs"])))
    print("DESTINATIONS.json written: %s (%d bytes)" % (DEST, DEST.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
