"""Record the unhcr-corridor-002 outcome (HDX AWS-WAF fetch block, diagnosed)
and the -003 rebuild launch carrying the one fetch repair for that defect
class. Run from the repo root:  python3 candidates/unhcr-corridor-entry-surge/record_waf_repair_2026_11_05.py
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "candidates" / "unhcr-corridor-entry-surge" / "record.json"


def utc_now() -> str:
    out = subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True,
                         text=True, check=True)
    return out.stdout.strip()


def main() -> int:
    record = json.loads(RECORD.read_text())
    now = utc_now()
    jobs = record["jobs"]

    if not any(j["id"] == "unhcr-corridor-002" for j in jobs):
        jobs.append({
            "id": "unhcr-corridor-002",
            "attempted_at": "2026-11-05T02:02:38Z",
            "status": "collected-then-deleted (ledger jobs/unhcr-corridor-002.json; server 174547804 destroyed with provider 404 read-back)",
            "outcome": (
                "FAILED at the source fetch, 9.3 s into the container, exit 1. The build's "
                "single un-retried GET wrote a 0-byte file: HDX answered HTTP 202 with "
                "x-amzn-waf-action: challenge and a zero-length body. Reproduced and isolated "
                "from the coordinator 2026-11-05 (see measurements."
                "hdx_waf_ua_probe_2026_11_05): the AWS WAF in front of data.humdata.org "
                "(awselb/2.0) challenges unrecognised User-Agent strings - the build's former "
                "custom UA 'dataset-factory/unhcr-corridor-build' and a plain browser UA both "
                "get 202 + empty, while urllib's default UA and curl/wget/requests strings are "
                "served the file. Server-side policy change (the same custom UA fetched the "
                "8,669,567-byte pin successfully on 2026-11-04), not a worker, construction or "
                "provider defect. The construction itself never ran; no rows, labels or "
                "features were touched and no score exists."
            ),
            "evidence": (
                "staging release 434681365 (assets verified by collect: source.tar 256,000 B, "
                "container.log 713 B, manifest.json 5,157 B), local copy "
                ".factory/unhcr-corridor-002/result.json; container.log: 'panel sha256 "
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 (0 bytes)' + "
                "'panel CSV has no header'; worker 174547804 destroyed 2026-11-05T02:42:10Z, "
                "provider read-back 0 servers / 0 primary IPs"
            ),
            "reservation_eur": "0.04",
        })

    if not any(j["id"] == "unhcr-corridor-003" for j in jobs):
        jobs.append({
            "id": "unhcr-corridor-003",
            "attempted_at": "2026-11-05T02:42:43Z",
            "status": "running (launched; server 174550077)",
            "outcome": (
                "The ONE rebuild the source-fetch defect class is entitled to (stopping "
                "condition: one rebuild per structural defect class). fetch() repair only: "
                "send urllib's honest default UA (measured to pass the WAF), refuse a "
                "challenge / non-200 / zero-length body with the observed evidence, retry "
                "three times bounded, and move only a complete non-empty body into place via "
                "a .part sibling. No construction logic, threshold, label, split, feature or "
                "gate input changed. Pinned by three new red/green rehearsal tests "
                "(tests/test_unhcr_corridor_build.py 15/15 OK; all three seen failing on the "
                "pre-fix fetch). Worker order unchanged: construct -> gate 1.5.0 on the FULL "
                "artifact -> exact-byte --accept -> score.py references (first real "
                "execution)."
            ),
            "evidence": (
                "ledger jobs/unhcr-corridor-003.json; bundle .factory/jobs/unhcr-corridor-003 "
                "(build.py sha256 cabb1e65-> see ledger for the repaired bundle's hash); "
                "rehearsal suite 15/15; WAF probe evidence in measurements."
                "hdx_waf_ua_probe_2026_11_05"
            ),
            "reservation_eur": "0.04",
        })

    record["measurements"]["hdx_waf_ua_probe_2026_11_05"] = {
        "measured_at": now,
        "measured_from": "coordinator, anonymous, bounded (64-256 B ranged reads; no full dataset transferred)",
        "finding": (
            "data.humdata.org fronts downloads with AWS WAF (server: awselb/2.0). An "
            "unrecognised User-Agent receives HTTP 202, x-amzn-waf-action: challenge, "
            "content-length 0 - urllib treats 202 as success, which is how the -002 worker "
            "came to write an empty panel. Recognised tool UAs are served the file "
            "(content-length 8,669,567, the recorded pin size)."
        ),
        "user_agent_results": {
            "dataset-factory/unhcr-corridor-build": "202 challenge, empty",
            "Mozilla/5.0 (browser-shaped)": "202 challenge, empty",
            "dataset-factory/1.0 (research; mailto:...)": "202 challenge, empty",
            "Python-urllib/3.x (urllib default)": "200, 8,669,567 B",
            "curl/8.5.0": "200, 8,669,567 B",
            "Wget/1.21.4": "200, 8,669,567 B",
            "python-requests/2.32.3": "200, 8,669,567 B",
        },
        "note": (
            "The former custom UA fetched the same URL successfully on 2026-11-04, so the "
            "challenge began in the window between the two fetches; treat any future HDX "
            "fetch failure that returns 202 + empty as this same WAF action and re-probe "
            "with a recognised UA rather than retrying blindly."
        ),
    }

    record["next_action"] = (
        "unhcr-corridor-003 is RUNNING (launched 2026-11-05T02:42:43Z, server 174550077, "
        "EUR 0.04 reservation, 45-minute lifetime ending ~03:27:43Z). Next session: "
        "(1) `sh scripts/scout-factory worker collect unhcr-corridor-003`; if status "
        "running and now < expiry, wait and re-collect. (2) On a finished report verify, in "
        "order: gate ok=true failed_checks=[] on the FULL artifact, exact-byte --accept "
        "ACCEPTED, all six fixtures green, corridor-grain probe coverage 0, anchors "
        "363/127/106, 202/98/80, 159/72/64, and the fetched panel sha256 (expect the "
        "d5808616 pin; a different digest means the HDX vintage moved and the anchor "
        "asserts decide). (3) DESTROY the worker (provider 404 read-back + 0/0 inventory). "
        "(4) Record the full ladder beside the pre-registered deciding check "
        "(preflight_unhcr_corridor_001.deciding_check_preregistered) and APPLY it: "
        "headroom demonstrated (momentum_raw or momentum_bucket_rate beats "
        "identity_combined with a cluster-bootstrap 95% CI excluding zero) -> the "
        "runner-contract baseline job is next; identity dominates both -> DROP per the "
        "pre-registered rule with the negative finding preserved; inconclusive -> HOLD. "
        "(5) If -003 fails at the fetch again with 202/x-amzn-waf-action:challenge: the "
        "default UA has been newly challenged too - that is a second failure of the same "
        "defect class and a recorded blocker, never a blind retry; preserve evidence and "
        "report. No re-tuning of the 2x threshold or the 500 eligibility after scores."
    )

    record["updated_at"] = now
    RECORD.write_text(json.dumps(record, indent=2) + "\n")
    print("record updated at", now)
    print("jobs:", [j["id"] for j in jobs])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
