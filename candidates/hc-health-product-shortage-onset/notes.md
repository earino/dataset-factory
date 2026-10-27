# hc-health-product-shortage-onset

Record dated evidence, decisions, and failed approaches here.

## Access and licence probes (2026-10-22)

Closed at triage, before any task probing, per the standing order (licence first; a source we
must register with or ask permission is a source we do not use). No account was created and no
gated API call was made.

### 1. Portal access, plain client

    curl -s -L -o dsc_home.html -w "home %{http_code} %{size_download}\n" "https://drugshortagescanada.ca/"
    -> home 403 5277
    curl -s -L -o dsc_api.html -w "api %{http_code} %{size_download}\n" "https://drugshortagescanada.ca/api"
    -> api 403 5286

### 2. Portal access, real browser

Per the licence-posture rule (never record silence from a plain-client 403 without re-reading
in a real browser), loaded https://drugshortagescanada.ca/ in a browser session:
- landed at https://healthproductshortages.ca/ (portal relaunched; HC's licensing bulletin
  "New website for health product shortages" confirms the move and an "updated API to make it
  easier to extract data").
- page title "🐴 Just a moment..."; body: "Performing security verification / This website uses
  a security service to protect against malicious bots. This page is displayed while the website
  verifies you are not a bot." (Cloudflare; Ray ID a4eb304a9dcd2fef).
- the terms/licence page is therefore not readable anonymously from a real browser either.

### 3. The API's own contract (from Health Canada's published example, not a gated call)

HC's "Public web API examples" (drugshortagescanada.ca/blog/61, surfaced by web search):
- "Before any calls to the API can be made, it is necessary to retrieve an access token linked to
  your account" - POST /api/v1/login with {'email': ..., 'password': ...}, then auth-token header.
- "If the goal is to retrieve the entire report database for custom analysis, it is recommended
  that the monthly data extract be used instead" - an extract exists; nothing published says it
  is reachable without an account.
- Reports date to 2017-03-10 per the PMPRB/HC analytical study citing the database (search result).

### 4. Any anonymous bulk extract on the federal portal?

    curl -s -o ckan_drugshortage.json -w "dsc_ckan %{http_code} %{size_download}\n" \
      "https://open.canada.ca/data/en/api/3/action/package_search?q=drug+shortage&rows=10"
    -> dsc_ckan 200 56297

Parsed: 29 packages, ALL Health Canada informational HTML pages ("Information on Drug Shortages",
"Causes of Drug Shortages in Canada", reporting guidance, multi-stakeholder committee...).
No CSV/JSON/API resource for the report database.

### 5. Verdict input

- licence_class C: no licence instrument readable on any anonymous channel (bot wall measured in
  both a plain client and a real browser; account required before anything on the portal).
- access: registration-gated API (account email+password per HC's own examples).
- Per the 2026-10-21 standing rule (licence cannot be established -> closed, not parked;
  precedents cpcb-aqi-exceedance, melbourne-pedestrian-counts) and the StatCan park's
  registration-gated precedent: REJECT.
- Task-type note for future ticks: drug-shortage ONSET (transition into actual-shortage state) is
  unrepresented on the bench; the door reopens on a publisher-side change (anonymous machine-
  readable extract + licence readable without registration), not on an enquiry from us.

### Cleanup

Scratch files dsc_home.html / dsc_api.html / ckan_drugshortage.json under
/opt/data/cache/scratch (auto-pruned). Measurement script (.factory/ckan_scan.py) deleted
after use.

## 2026-10-27 discovery session (tick region: Canada) - reopen condition re-checked; still closed

The recorded reopen evidence ("publisher-side change: anonymous machine-readable extract
+ licence readable without registration") was re-checked via the open.canada.ca CKAN
(anonymous package_search q='drug shortage', rows=25, full records - no fl parameter, so
resource lists are complete):

- All 25 returned packages are Health Canada informational/HTML pages and old
  guidance records (newest created 2023-02-28: 'Guide to reporting drug shortages
  and discontinuations'); none carries any CSV, API, JSON, XLSX or ZIP resource.
- No package for the healthproductshortages.ca report database or its monthly
  extract appeared on the federal portal.

The registration-gated API and bot-wall posture of healthproductshortages.ca were not
re-probed (they were measured 2026-10-22 in a real browser; nothing announced since).
Reopen condition still not met; the drop stands.

