#!/usr/bin/env python3
"""Close out the 2026-11-04/05 session: the unhcr-corridor-001 launch was
refused by the provider (HTTP 412 resource_unavailable on POST /servers).
Record the diagnosis and the ONE permitted changed-retry protocol into the
candidate record. No server was ever created (provider read-back 0 servers /
0 primary IPs, project and account); no artifact exists yet; no score of any
kind exists.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

RECORD = Path(__file__).resolve().parent / "record.json"
record = json.loads(RECORD.read_text())
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

record["updated_at"] = now
record["jobs"] = record.get("jobs") or []
entry = {
    "id": "unhcr-corridor-001",
    "attempted_at": "2026-11-04T22:36:50Z",
    "status": "creation-unresolved (ledger jobs/unhcr-corridor-001.json; the "
              "designed state for a creation that never resolved)",
    "outcome": (
        "launch REFUSED by the provider: API POST servers returned HTTP 412 "
        "before any server existed. Diagnosis (read-only probes, 2026-11-04 "
        "22:40-22:42Z): Hetzner's documented 412 = resource_unavailable - "
        "'the requested resource is currently unavailable (e.g. not "
        "available for order)'; known shapes are a server-type+location "
        "combination temporarily unavailable and, since 2025-07, primary-IP "
        "allocation unavailable (POST /servers with public_net.enable_ipv4 "
        "implicitly allocates a primary IPv4). Ruled out by direct "
        "measurement: SSH key 'scout-worker' present in the project; cx23 "
        "available and priced in hel1 (EUR 0.0106/h gross, fetched live); "
        "provider inventory 0 servers / 0 primary IPs in project AND "
        "account after the failure. INFRASTRUCTURE failure with a named "
        "source, not a scientific verdict and not a job defect - the same "
        "cx23/hel1 launches succeeded at 20:33-20:41Z the same day."),
    "evidence": (
        "ledger record created 2026-11-04T22:36:50Z, expires 23:21:50Z, "
        "server_id null; provider read-back 0/0; bundle assembled at "
        ".factory/jobs/unhcr-corridor-001 (159,156 B, source sha256 "
        "0791e722390804680177ca0cac3b31d60d2c2f42ded7bbc9b0cfbc6bbe5d20fb, "
        "gate 1.5.0 4fab8a34...); EUR 0.04 reservation retained by policy"),
    "reservation_eur": "0.04",
}
record["jobs"] = [entry] + [j for j in record["jobs"] if j.get("id") != "unhcr-corridor-001"]

record["next_action"] = (
    "RETRY PROTOCOL (the ONE changed retry this infrastructure failure is "
    "entitled to, per the recorded stopping condition - the named source is "
    "Hetzner 412 resource_unavailable; nothing about the job or its source "
    "changes, only the attempt ID): (1) at/after 2026-11-05T00:21:50Z (the "
    "-001 entry's expiry 23:21:50Z + 60-minute cleanup grace) run "
    "`sh scripts/scout-factory worker status unhcr-corridor-001` so "
    "reconcile closes it as deleted ('No server found after expiry and "
    "cleanup grace; reservation retained') - the launcher hard-refuses new "
    "jobs while any non-deleted ledger entry exists, and the ledger must "
    "never be hand-edited around that invariant; confirm 0 servers / 0 "
    "primary IPs again. (2) Edit "
    "candidates/unhcr-corridor-entry-surge/source/job.json id -> "
    "'unhcr-corridor-002' (a recorded attempt ID is never relaunched), "
    "re-assemble (python3 scripts/assemble-job.py "
    "unhcr-corridor-entry-surge), plan, launch. (3) The worker order is "
    "fixed in run.sh: construct -> gate 1.5.0 on the FULL artifact "
    "(fresh HDX fetch; sha compared to the d5808616 pin, anchors "
    "363/127/106, 202/98/80, 159/72/64 asserted) -> exact-byte --accept -> "
    "score.py references (its first real execution). (4) On completion: "
    "collect, verify gate ok=true failed_checks=[] + ACCEPTED + fixtures + "
    "corridor-grain probe coverage 0, DESTROY the worker (provider 404 "
    "read-back), record the ladder beside the pre-registered deciding check "
    "(preflight_unhcr_corridor_001.deciding_check_preregistered) and apply "
    "it: headroom demonstrated -> the runner-contract baseline job is next; "
    "no_demonstrated_headroom or identity_prior_dominates -> hold/drop per "
    "the pre-registered rule with the negative finding preserved. (5) If "
    "the -002 launch ALSO fails with 412 resource_unavailable: that is a "
    "recorded blocker - preserve the evidence, record it in STATE.md and "
    "this record, and report; never a blind retry loop. Local preflight "
    "state (all reusable, no score exists): the pinned-source dry run "
    "reproduced every anchor and passed gate 1.5.0 with zero failed checks "
    "(dry run; the worker's full-artifact run remains authoritative), the "
    "rehearsal suite tests/test_unhcr_corridor_build.py is 12/12 green, "
    "and the deciding check is pre-registered in "
    "preflight_unhcr_corridor_001.")

RECORD.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n")
print("record updated:", RECORD)
print("updated_at:", now)
