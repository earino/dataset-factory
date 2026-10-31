# oecd-global-recalls-propagation

Record dated evidence, decisions, and failed approaches here.

## 2026-10-31 — coverage and licence triage (international-organisations tick)

Lead: cross-jurisdiction recall propagation on the OECD GlobalRecalls compilation.
Aggregate coverage measurement closed the lead on the target contract; the licence posture
(class C, no dataset-level open licence, third-party rows) closed publishability.

Exact commands (read-only, from the coordinator, 2026-10-31):

    # 1. The SPA shell is 586 B; the bundle names the anonymous MarkLogic ws endpoints:
    curl -sS -m 25 -o home.html -w "%{http_code} %{size_download}B\n" https://globalrecalls.oecd.org/
    # home.html -> 200 586B; only script: main.b95c2851e3e9cc7b2275.js
    curl -sS -m 40 -o main.js https://globalrecalls.oecd.org/main.b95c2851e3e9cc7b2275.js
    # -> 200 4,989,645 B. grep of the bundle finds /ws/{search.xqy, getrecall.xqy,
    #    mainDashboards.xqy, getproductstaxonomy.xqy, rss.xqy, import.xqy (apikey),
    #    export.xqy (admin area)} and the contributor GitHub link cis-itn-oecd/global-recalls.

    # 2. The two GETs the public UI itself issues on load (aggregate only, no bulk transfer):
    curl -sS -m 30 -o dash.json \
      "https://globalrecalls.oecd.org/ws/mainDashboards.xqy?q=&lang=en"
    # -> 200, 16,806 B
    curl -sS -m 30 -o search.json \
      "https://globalrecalls.oecd.org/ws/search.xqy?q=&start=1&end=5&lang=en&uiLang=en"
    # -> 200, 246,490 B (4 sample rows + the full facet lists)

    # 3. Terms:
    web_extract https://www.oecd.org/en/about/terms-conditions.html   # HTTP 200, Data section quoted
    web_search "OECD GlobalRecalls portal terms API bulk download"    # 2020 enhancements report + Statistics and Data Outputs 2024

Reproduction recipe retained at probe/probe_aggregates.py (same two GETs, prints total,
jurisdiction mix and sample-record fields).

Observed (2026-10-31):

- total = 57,807 recall notices; country facet = 50 jurisdictions.
- Measured mix (count per jurisdiction): EEA 15,002 / US 8,421 / AU 6,620 / CA 5,759 /
  DE 4,507 / IT 3,403 / GB 3,245 / KR 2,976 / HU 2,754 / FR 2,585 / CZ 1,363 / PL 1,350 /
  ES 1,230 / CY 1,076 / JP 1,063 / SE 1,060 / FI 1,054 / BG 993 / LT 863 / NL 767 / CO 699 /
  SK 640 / IE 510 / DK 494 / RO 473 / BE 442 / PT 416 / AT 355 / AE 289 / ASEAN 275 /
  LV 274 / GR 268 / MT 257 / LU 255 / HR 214 / EE 211 / NO 172 / SI 167 / VN 89 / PH 82 /
  SG 70 / IS 69 / ID 67 / CR 54 / TW 47 / TH 33 / BN 31 / IL 19 / MY 19 / LI 1.
  Top-5 channels = 40,309 (69.7%); 12 of the 50 jurisdictions hold fewer than 100
  lifetime notices (reproduced by probe/probe_aggregates.py).
- Sample rows (start=1 end=5, orderby date-asc; 4 returned) fields: countryId,
  countryName, date, extUrl, id, imageUri, index, language, languageId, manufacturer.country,
  product.name, tags, uri, url (detail link pointing at an INTERNAL OECD hostname,
  dmz-ml-2.main.oecd.org:8120). No GTIN/model/product-identity field. 2 of the 4 sample
  rows carry date 1900-01-01 — a missing/unparsed date sentinel in a timing-critical field.
- Facet keys: country-were-recalled, country-were-made, gs1-gpc-brick, gs1-gpc-class,
  gs1-gpc-family, gs1-gpc-segment, concepts-from-query, best-tags, related-concepts.
- The search response embeds: "© OECD. All rights reserved - http://www.oecd.org/termsandconditions".
- OECD ToU Data section (updated 1 July 2024): reuse of OECD-owned Data permitted with
  attribution, but "Data may be subject to restrictions ... because specific terms apply to
  those Data or because third parties may have ownership interests. It is the user's
  responsibility to verify ... and to contact the owner of the Data before incorporating it
  in your work in order to secure the necessary permissions." No dataset-level open licence
  found on the portal.
- Publisher's own scope caveat (OECD Statistics and Data Outputs 2024): "The scope of the
  recalls depends on the mandate of the particular government authority providing the
  information."

Decision: dropped. The propagation target's negative class is censoring-dominated at the
measured coverage mix (no recorded second-jurisdiction recall cannot be read as absence for
the ~20 jurisdictions with <100 lifetime notices), the public payload carries no
product-identity field to link the same product across jurisdictions, and the licence is
class C (compilation over ~50 national owners; OECD's grant excludes third-party data).
No full-schema, year-distribution, split or cost probes were run — deliberately; further
probing would spend budget on a closed lead.

Reopen triggers are recorded in record.json next_action.
