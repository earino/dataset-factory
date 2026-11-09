# Development window close - handoff record

Recorded 2026-11-09T21:17:20.069484+00:00. Dev accounting window closed by root at 2026-11-09T21:12:00Z
(closure commit c93981e93baca767d851f2f0d92d1428257215e9, exact CI 42700515978
green, 33 focused accounting tests pass). Pulled onto the live runtime
preserving in-flight work - config/docs only, no engine code, so no
model/worker interruption or code-deployment pause was needed.

- CFPB source-18 (cfpb-bank-account-monetary-relief): evaluate-2 clean accept
  (verdict accept, 0 findings, 9 limitations; 21:00:03-21:05:39Z, raw bytes in
  ../cfpb-evaluate2/). publish-1 done 21:12:19Z "Published and anonymously
  verified on GitHub and Hugging Face": staging release 439649721, worker
  241.3 s exit 0, server 175360897 created 21:06:04 / collected 21:12:04 /
  deleted 21:12:17, reservation EUR 0.24. Root independently verified both
  public tagged manifests byte-for-byte (SHA cb478312...) against accepted
  build-4 and saved receipt/manifests; not duplicated here.
- Worker/provider reconciliation: every jobs/*.json record status=deleted;
  provider live-server readback: []. No worker reset performed.
- Schedule state (cron readback 21:14:20Z): tick 07d6f8be3783 enabled, last
  run 21:12:19Z ok; cleanup sweep e80975eddd4a enabled, last 21:10:01Z ok.
  Old launchers disabled: scout-research-session 69a5bc676d10,
  scout-discovery-session 86fe52e55ef9, scout-worker-watch 98b45d983280
  (paused since 2026-11-08). Dec-1 allowance reset proof: dec1-reset-proof.json
  (cron ca002a2e360e enabled, one-shot 2026-12-01T00:00Z, never run; script
  copy sha256 225066278e475ac4...; monthly_budget_eur 45 now, extra allowance stays usable
  through November, reset 45->20 only if still 45).
- Budget close readback: [raw decision JSON](budget-decision-readback.json),
  explicit tracked config, observed 2026-11-09T21:23:21Z: allowed=true,
  development_token_exemption_active=false, normal-operation tokens=32,553,209
  against weekly_token_budget=40,000,000; development_tokens=10,478,967 remain
  excluded. Earlier prose mixed total research tokens with normal-operation
  tokens and read the exemption from the wrong JSON level; this raw decision
  supersedes those values. No cap, exclusion or lock was changed.
  The recorded development window remains 2026-11-08T19:58:14Z through
  2026-11-09T21:12:00Z; later sessions use normal admission.

- Window usage refreshed through 21:12:00Z:
  ../681deb7-deploy/dev-window-usage.json (unknown elapsed stays unknown).
- Normal operation continues: eia860 source-19 build-4 and nhtsa source-20
  build-2 proceed under the normal tick; no orchestration changes.
