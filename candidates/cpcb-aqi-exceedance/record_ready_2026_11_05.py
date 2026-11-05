# Record the 2026-11-05 discovery session into candidates/cpcb-aqi-exceedance:
# channel measurements, OpenAQ enumeration, threshold binding + fixture, the
# measured full-panel counts, and the evidence-based split re-cut (2025 gap).
# Every value is asserted against the measured outputs before writing.
import json

COUNTS = "candidates/cpcb-aqi-exceedance/probe/out/xkdr_daily_counts_2019_2025_2026_11_05.json"
RECORD = "candidates/cpcb-aqi-exceedance/record.json"
NOW = "2026-11-05T21:45:00+00:00"

counts = json.load(open(COUNTS))
w = counts["windows"]["recut_2026_11_05"]
tr, ev, ho = w["train_2019_2022"], w["eval_2023"], w["holdout_2024"]
tail = w["excluded_tail_2025_04_to_09"]

assert counts["truncated_any"] is False
for name, win in (("train", tr), ("eval", ev), ("holdout", ho)):
    assert win["station_days"] > 0 and win["pos_n18"] > 0, f"{name}: needs both classes"
    assert win["station_days"] - win["pos_n18"] > 0, f"{name}: no negatives"
assert ev["pos_n18"] >= 30 and ho["pos_n18"] >= 30
assert ev["distinct_positive_days_n18"] >= 20 and ho["distinct_positive_days_n18"] >= 20
assert counts["rows_total"] >= 700000, counts["rows_total"]
print("assertions passed")
print("train:", tr["station_days"], tr["pos_n18"], tr["rate_n18"])
print("eval:", ev["station_days"], ev["pos_n18"], ev["rate_n18"])
print("holdout:", ho["station_days"], ho["pos_n18"], ho["rate_n18"])
print("tail:", tail["station_days"], tail["pos_n18"])

rec = json.load(open(RECORD))
assert rec["status"] == "investigating", rec["status"]
assert rec["novelty_check"]["verdict"] == "differentiated"
assert rec["licence_class"] == "A"

rec["sources"][0]["api"] = (
    "GET /v1/meta, /v1/stations, /v1/parameters, /v1/measurements (json|csv|parquet; "
    "filters station/city/state/source/parameter + agg raw|hourly|daily|monthly), "
    "/v1/files (list), /v1/files/<key> (monthly parquet, Range honoured). Demo tier "
    "(front-page key): 10,000 rows/query, 30 s timeout. MEASURED 2026-11-05: the demo "
    "tier's '2024 bulk files only' restriction is enforced on /v1/files (Range GET of "
    "year=2019 data.parquet -> HTTP 403; year=2024 -> HTTP 206) but NOT on /v1/measurements "
    "(2019-01 monthly -> HTTP 200, x-tier: demo; the full 2019-2025 daily-aggregate "
    "measurement ran on it). Full-history bulk therefore needs the free signup key; "
    "full-history QUERY access is anonymous at the demo tier."
)
rec["sources"][0]["access"] = (
    "anonymous with the published demo key for /v1/measurements (all years, measured "
    "2026-11-05); /v1/files bulk beyond 2024 needs a free signup key whose form requires "
    "an EMAIL + NAME (Cloudflare Turnstile) - no project email identity exists, recorded "
    "as MISSING ACCESS 2026-11-05: the operator either supplies/authorizes an email for "
    "the signup, provides a full key directly, or construction uses the anonymous "
    "measurements-API batching path. Transient origin incidents occur (a 401 window "
    "20:33-20:44Z 2026-11-05 with the same key 200 before and after; Cloudflare bans the "
    "literal 'Python-urllib' UA with 403 error 1010 - use a custom or curl UA)."
)
rec["sources"][1]["api"] = (
    "https://openaq-data-archive.s3.amazonaws.com/records/csv.gz/locationid=<id>/year=YYYY/"
    "month=MM/location-<id>-YYYYMMDD.csv.gz - anonymous S3, no account. Row schema "
    "measured 2026-11-05: location_id,sensors_id,location,datetime(+offset),lat,lon,"
    "parameter,units,value (no provider column). Indian locationids enumerated anonymously "
    "via Wayback capture 20230425092626 of api.openaq.org/v2/locations?limit=10000&country=IN "
    "(3,459,137 B, 1,765 locations; meta license CC BY 4.0d): 978 government CPCB-sourced, "
    "937 with pm25 (ids 13..363603). S3 year-dir enumeration of all 937: 447 have any "
    "archive; per-year location counts 2019:203 2020:270 2021:324 2022:365 2023:0 2024:0 "
    "2025:332 2026:327; 316 show a 2022->(gap)->2025 pattern and ZERO have any 2023/2024 "
    "files - OpenAQ's India ingestion stopped ~Oct 2022 and resumed 2025. OpenAQ therefore "
    "CANNOT carry the eval year 2023 or holdout 2024 under the re-cut windows (and no 2023 "
    "exists there at all); it is only a fallback for re-cut windows on 2019-2022 with a "
    "mid-task pipeline discontinuity that no overlap period can cross-validate. XKDR is "
    "the channel that carries all three windows."
)

m = rec.setdefault("measurements", {})
for k in ("xkdr_channel_access_2026_11_05", "openaq_archive_enumeration_2026_11_05",
          "threshold_fixture_2026_11_05", "window_counts_2026_11_05"):
    assert k not in m, k

m["xkdr_channel_access_2026_11_05"] = {
    "recorded_at": NOW,
    "facts": "401 window 20:33-20:44Z with same key 200 before/after (no rotation; no cookies; plain curl and browser both pass); Cloudflare 403 error 1010 on the literal Python-urllib UA only; /v1/files list 200 (207 monthly parquets, 409,568,028 B total, plus v1/stations.parquet 27,232 B and v1/parameters.parquet 1,366 B); /v1/files year=2019 Range GET 403 vs year=2024 206 (demo tier boundary measured); /v1/measurements serves all years at demo tier (2019-01 monthly 200, x-tier demo, x-truncated false); signup form fields measured in the supported browser: EMAIL (required), NAME (required), affiliation/purpose (optional), accept_terms credit-sources checkbox, Cloudflare Turnstile; no project email identity exists (himalaya not configured, no signup convention recorded) -> full-key bulk path recorded as MISSING ACCESS (operator).",
}
m["openaq_archive_enumeration_2026_11_05"] = {
    "recorded_at": NOW,
    "facts": "Wayback capture 20230425092626id_ of v2 locations country=IN: 1,765 locations, 989 government, 978 source 'Central Pollution Control Board' (312 also 'data.gov.in'), 937 pm25 (ids 13..363603); embassy monitors present as 'U.S. Department of State India - *' x5 + 'EPA AirNow DOS' x10 (corroborates the us_embassy exclusion). S3 year-dirs for all 937: 447 with any files; per-year 2019:203 2020:270 2021:324 2022:365 2023:0 2024:0 2025:332 2026:327; 316 follow 2022->gap->2025. Evidence: probe/out/openaq_in_locations_2023_04_25_compact.json, probe/out/openaq_cpcb_937_year_coverage_2026_11_05.json; scripts probe/probe_openaq_*_2026_11_05.py.",
}
m["threshold_fixture_2026_11_05"] = {
    "recorded_at": NOW,
    "threshold_binding": "CPCB 'About National Air Quality Index' PDF (cpcb.gov.in displaypdf id bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvQWJvdXRfQVFJLnBkZg==, fetched 2026-11-05, 298,817 B, retained probe/out/about_aqi.pdf): PM2.5 24-hourly breakpoints Moderately Polluted 101-200 = 61-90 ug/m3, Poor 201-300 = 91-120, Very Poor 121-250, Severe 250+; '24-hourly average values for PM10, PM2.5...'; 'The worst sub-index determines the overall AQI.' Corroborated by CPCB AQI-Calculator.xlsx (app.cpcbccr.com/ccr_docs/): band 61.0-90.0 -> index 101-200, band 91.0-120.0 -> 201-300. The 90 ug/m3 label edge is the publisher's own Poor-band lower edge; '>90' = Poor-or-worse.",
    "known_event_fixture": "CPCB Daily AQI Bulletin 2024-11-18 (cpcb.gov.in/upload/Downloads/AQI_Bulletin_20241118.pdf, 52,671 B, retained): 'Air Quality Index on Nov 18, 2024 @ 4 PM ... (Average of past 24 hours)' - Delhi Severe 494, prominent pollutant PM2.5, 36/39 stations; Bahadurgarh Severe 453; Bhiwadi 447; Dharuhera 447; Ghaziabad 438; Bhiwani 429; Churu 401; Faridabad Very Poor 367. MEASURED CONFIRMATION from the panel rows: 38 Delhi cpcb station-days on 2024-11-18, all 36 with n>=18h labeled TRUE (24-hr means 235.7-731.5 ug/m3); the 2 exceptions are incomplete days (n=11, n=9) - matching the bulletin's 36/39 participating stations. Caveat: the bulletin's window is 4PM-4PM and city AQI is the worst pollutant sub-index - a category-level cross-check, not a numeric reproduction. Bulletin 2024-11-17 also retained.",
}
m["window_counts_2026_11_05"] = {
    "recorded_at": NOW,
    "method": "probe/probe_cpcb_full_window_2026_11_05.py: 84 monthly windows x 2 station-batches (275+274) through /v1/measurements agg=daily parameter=PM2.5, cpcb_caaqm stream only (549 stations), 166 requests, rows streamed and aggregated; completeness rule n_hours>=18 primary. Coordinator-class host (4 vCPU), anonymous demo key.",
    "rows_total": counts["rows_total"], "truncated_any": counts["truncated_any"],
    "proposed_windows_2026_11_04": counts["windows"]["proposed_2026_11_04"],
    "recut_windows": w,
    "recut_reason": "The 2026-11-04 proposed holdout (2025) is not viable as a scored window: the export's cpcb pm25 stream has NO data for 2025-01..2025-03 or 2025-10..2025-12 (monthly all-station queries return 2-5 stray rows, the 5 us_embassy monitors; measured), a partial 2025-04..2025-08 (~320 stations), and a single day 2025-09-01 - a winter-free, 1.74%-prevalence tail. Re-cut ONCE before any score, with both cuts preserved in this entry and in probe/out/xkdr_daily_counts_2019_2025_2026_11_05.json: train 2019-2022 / eval 2023 / holdout 2024 (all full years, both classes, mild prevalence drift 18.8% -> 13.5% -> 11.0%); the 2025-04..09 partial tail (47,566 station-days / 829 positives / 329 stations) is EXCLUDED from scored windows and counted here. The 2026-11-04 'stream effectively ends 2025-12' reading was wrong in both directions: the stream effectively ends 2025-09-01 AND Jan-Mar 2025 is missing too.",
    "note": "one fetch defect fixed mid-session (hardcoded Feb-29 produced end=2019-02-29 -> HTTP 400 'end must be YYYY-MM-DD'; replaced with calendar.monthrange); the first 'transient 400' diagnosis was wrong - it was this bug.",
}

rec["split_strategy"] = (
    "Temporal by day on the cpcb_caaqm stream only (5 us_embassy DS* stations excluded; "
    "one instrumentation stream). MEASURED 2026-11-05 over the full 2019-2025 panel "
    "(166 requests, 716,750 station-days, threshold 90 ug/m3, n>=18h primary) and RE-CUT "
    "once before any score because the 2025 holdout is a winter-free partial tail "
    "(2025-01..03 and 2025-10..12 have no cpcb pm25 rows in the export; measured): "
    "train 2019-2022 " + str(tr["station_days"]) + " station-days / " + str(tr["pos_n18"])
    + " positives (" + str(tr["rate_n18"]) + ") / " + str(tr["distinct_stations_reporting"])
    + " reporting stations / " + str(tr["positive_state_x_season_cells"]) + " state-x-season positive cells / "
    + str(tr["distinct_positive_days_n18"]) + " distinct positive days; "
    "eval 2023 " + str(ev["station_days"]) + " / " + str(ev["pos_n18"]) + " (" + str(ev["rate_n18"])
    + ") / " + str(ev["distinct_stations_reporting"]) + " / " + str(ev["positive_state_x_season_cells"])
    + " / " + str(ev["distinct_positive_days_n18"]) + "; "
    "holdout 2024 " + str(ho["station_days"]) + " / " + str(ho["pos_n18"]) + " ("
    + str(ho["rate_n18"]) + ") / " + str(ho["distinct_stations_reporting"]) + " / "
    + str(ho["positive_state_x_season_cells"]) + " / " + str(ho["distinct_positive_days_n18"]) + ". "
    "Excluded and counted: the 2025-04..09 partial tail (" + str(tail["station_days"])
    + " station-days / " + str(tail["pos_n18"]) + " positives / " + str(tail["distinct_stations_reporting"])
    + " stations). Positives are winter-clustered (monthly positive share Dec-Feb up to ~0.39, "
    "monsoon ~0.00-0.03) - construction evaluates with cluster-aware intervals "
    "(cluster = station and/or state x season). Both classes present in every window; "
    "eval/holdout clear the qualification gate's minimums with large margin."
)

rec["review"] = (
    "Five contracts reconciled 2026-11-05 against recorded evidence. "
    "(1) REDISTRIBUTION - supported, class A: CPCB's own publication is licensed GODL-India by the "
    "data.gov.in platform instrument (Wayback-read 2026-11-04, AIKosh-corroborated live; attribution "
    "template + non-endorsement to carry into LICENSE.md; no share-alike); the XKDR compilation is "
    "CC BY 4.0 (README, credit 'India Air Quality Database, XKDR Forum' + CPCB + US DoS); OpenAQ is "
    "CC BY 4.0 (docs + archived v2 meta 'CC BY 4.0d'). "
    "(2) PREDICTION TIMING - supported for a clearly-labelled retrospective-research scope with two "
    "declared, unverified assumptions: instant = 23:59 IST on day D; features = the station's own "
    "trailing PM2.5 history through day D (naive IST, calendar-day convention); label = calendar-day "
    "D+1 24-hr mean, entirely after the instant. Assumption (a) current-vintage: the archive is one "
    "export (2026-09-30), values 'as reported', 'no gap filling', 'preliminary and not fully "
    "validated' (XKDR README) - no operational as-of claim; revision behaviour unmeasured (a second "
    "export has never been observed). Assumption (b) day-D trailing hours are treated as complete at "
    "the instant: CPCB intraday latency is not measured (the publisher's own 4 PM bulletin averages "
    "the past 24 h and shows non-participating stations, e.g. Delhi 36/39 on 2024-11-18). "
    "(3) TARGET - supported: mechanical label (D+1 calendar-day mean > 90 ug/m3) from a published "
    "band edge of the publisher's own AQI instrument (Poor band lower edge 91; quote in "
    "measurements.threshold_fixture_2026_11_05); label-source series excluded from every shipped "
    "column; known-event fixture bound to the publisher's Daily AQI Bulletin (2024-11-18 Delhi "
    "Severe 494) AND confirmed in the measured panel (36/36 complete Delhi station-days TRUE); the "
    "bulletin is also the publisher-summary cross-check (category-level). "
    "(4) SPLIT CAPACITY - supported, measured on the full 2019-2025 panel and re-cut once with "
    "measured evidence before any score (see split_strategy): train 2019-2022 "
    + str(tr["pos_n18"]) + " positives, eval 2023 " + str(ev["pos_n18"]) + " positives over "
    + str(ev["distinct_positive_days_n18"]) + " distinct positive days, holdout 2024 "
    + str(ho["pos_n18"]) + " positives over " + str(ho["distinct_positive_days_n18"])
    + " days; both classes in all three windows; winter clustering recorded and cluster-aware "
    "evaluation required at construction. "
    "(5) NOT A MIRROR - supported: novelty_check verdict differentiated (2026-10-20): research papers "
    "fit CPCB forecasters with private splits (arXiv 2404.08702 22-station; Discover AI 2026), Kaggle "
    "raw-data mirrors (CC BY-SA), and open archives (OpenAQ/XKDR/Vayuayan) - none ships this task "
    "with fixed splits and a scored contract. "
    "RESIDUAL LIMITATIONS carried to construction: (i) the cross-row exposure - a scored day-D row's "
    "label operand (day D+1 mean) appears inside the trailing features of days D+2..D+91 - requires "
    "the za-cct-style bounded-exposure design (restricted trailing aggregates, isolated_rows "
    "declared, gate-1.5 reverse-history probes measuring eval/holdout coverage and mismatch); "
    "(ii) label-availability exclusions (station-days with <18 h on D+1) must be counted and "
    "declared, never silently dropped; (iii) the export's 2025 hole (Jan-Mar, Oct-Dec absent; the "
    "2025-04..09 tail excluded) and the OpenAQ 2023-2024 gap (zero files, measured) mean XKDR is "
    "the only channel that carries all three re-cut windows; the full-key bulk path stays behind "
    "the operator's email/key decision while the anonymous measurements-API batching path remains "
    "viable and measured."
)

rec["next_action"] = (
    "READY - construction handoff, in order: (1) channel: default = anonymous demo-key "
    "measurements-API batching on the worker (measured 2026-11-05: daily aggregates = 2 batches x "
    "84 months; hourly raw pulls are larger but worker-feasible; use a non-Python-urllib UA and "
    "retry 400/401/5xx with backoff - the origin served a 401 window 2026-11-05 20:33-20:44Z). "
    "Operator option: a full free XKDR key (signup needs an EMAIL identity - MISSING ACCESS "
    "recorded 2026-11-05) enables one-parquet-per-month bulk fetch (/v1/files, 409,568,028 B total; "
    "demo tier reads only the 2024 files - measured 403 on 2019). (2) Build on a worker from the "
    "pinned XKDR export 2026-09-30 (re-verify any re-fetched artifact against the recorded anchors): "
    "station-day panel 2019-2024, cpcb_caaqm only (549 PM2.5 stations), eligibility n>=18h on day D, "
    "label = D+1 calendar-day 24-hr mean > 90 ug/m3 with n>=18h on D+1 (unlabelable excluded AND "
    "counted), splits train 2019-2022 / eval 2023 / holdout 2024 with the measured counts in "
    "split_strategy, the 2025-04..09 partial tail excluded and counted, features = trailing "
    "daily/hourly PM2.5 statistics + calendar only, label-source columns absent from every CSV, "
    "in-build fixtures: 2024-11-18 Delhi TRUE (bulletin-bound, measured 36/36 complete station-days) "
    "and one monsoon negative day; cross-row bounded-exposure design with gate-1.5 reverse-history "
    "probes and isolated_rows declared. (3) Standing order: full-artifact gate 1.5 on the worker -> "
    "exact-byte --accept -> reference triad on identical eval rows (station persistence, "
    "state-x-season climatology prior, majority) with station-clustered paired bootstrap and a "
    "pre-registered deciding rule written BEFORE any score -> reporting. Holdout never opened in "
    "development. No score, gate or acceptance exists yet - nothing is quotable."
)

rec["status"] = "ready"
rec["verdict"] = "ready"
rec["updated_at"] = NOW
json.dump(rec, open(RECORD, "w"), indent=1, ensure_ascii=False)
print("record updated: status=ready")
