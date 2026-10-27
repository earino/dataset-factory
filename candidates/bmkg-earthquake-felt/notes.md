# bmkg-earthquake-felt - probe evidence (2026-10-20, all anonymous, no key)

    curl "https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json"   -> HTTP 200, 4,157 bytes
    curl "https://data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json" -> HTTP 200, 4,602 bytes
       - exactly 15 "Tanggal" items (the latest 15 FELT events; counted with grep)
       - item fields: Tanggal, Jam, DateTime (ISO), Coordinates, Lintang, Bujur, Magnitude,
         Kedalaman - instrumental features + felt designation in one record
    curl "https://data.bmkg.go.id/gempabumi/"                       -> HTTP 200, 24,466 bytes
       - enumerates only: DataMKG/TEWS/autogempa.{json,xml}, gempaterkini.{json,xml},
         gempadirasakan.{json,xml}; grep for catalog|katalog|historis|arsip|unduh|download|CSV
         -> no archive/bulk links
    curl "https://data.bmkg.go.id/DataMKG/TEWS/gempabumidirasmakan.json" -> 404 (spelling variant absent)

Terms measured on data.bmkg.go.id pages: attribution mandatory ("Wajib untuk mencantumkan BMKG
sebagai sumber data dan menampilkannya"), 60 requests/min per IP; no named formal licence.

Also probed (search reads, 2026-10-20): api.bmkg.gov.id/publik/prakiraan-cuaca - anonymous
3-day VILLAGE-level forecast API (no key) - forecasts, no observations, so no verification
label without another source; bmkg.go.id/alerts/nowcast - active CAP warnings only.
SATU PETA MKG API (gis.bmkg.go.id/portal/dataapi) NOT probed - named unpark step.

## 2026-10-28 session (regional tick: South & South-East Asia): the historical felt catalogue EXISTS - but behind an interactive captcha gate, with no redistribution licence

The recorded unpark question - does BMKG expose a historical earthquake catalogue with felt
annotations? - is now ANSWERED.

    curl -skL https://gis.bmkg.go.id/portal/dataapi -> "Satu Peta MKG" map portal (29,139 B);
       links out to https://inatews.bmkg.go.id/ and http://repogempa.bmkg.go.id/
    curl -skL https://inatews.bmkg.go.id/  -> links: repogempa.bmkg.go.id, /web/felt,
       /web/m5, /web/realtime, /web/tsunami, aeic.bmkg.go.id
    curl -skL https://inatews.bmkg.go.id/web/felt -> "30 Gempabumi Dirasakan Terakhir"
       (latest 30 felt only; feed, not archive)
    curl -skL https://repogempa.bmkg.go.id/ -> "EQ Repository | BMKG"; link /eventcatalog
    curl -skL https://repogempa.bmkg.go.id/eventcatalog -> 200, 38,372 B. "Earthquake
       Events Request" form with Event Type options: Preliminary Earthquake Catalog;
       Final Earthquakes Catalog (Relocated Event, Login required for arrival data);
       **Significant/Felt Earthquakes Catalog**; Destructive Earthquakes and Tsunami
       Catalog. Parameter Retrieval: Origin (Main Parameter) anonymous; Origin + Focal
       Mechanism; Origin + Arrival Phases (Login Required). Date Interval: Past 7 Days,
       Past 30 Days, **Custom (limited to 30 days)**. Submit requires e-mail,
       institution, and a CAPTCHA.

Decisive shape of the retrieval contract: a multi-year felt history would need one
captcha-protected request per 30-day window (e.g. ~220 requests for 18 years), each with
e-mail+institution. That is an interactive low-volume service, not an anonymous bulk
download; automating past the captcha is not a path we take. (How far back the catalog
reaches was not measured - the form's own presets and the 30-day cap make the extraction
cost prohibitive before that question matters.)

Licence posture measured this session:
    - repogempa.bmkg.go.id/eventcatalog footer: "Copyright (c) 2026 All rights reserved."
    - gis.bmkg.go.id/portal/hukum ("Landasan Hukum") lists the governing laws/regulations
      for the GIS portal - it is NOT a data licence; no redistribution terms.
    - (2026-10-20, unchanged) data.bmkg.go.id usage terms: attribution mandatory
      ("Wajib untuk mencantumkan BMKG ... sebagai sumber data"), no named licence.
    - dataonline.bmkg.go.id: registration-gated (login/register), weather/climate data focus.

## Decision 2026-10-28

Stays PARKED. The missing historical archive now exists and is nameable (the EQ Repository
Significant/Felt Earthquakes Catalog), which UPGRADES the lead's feasibility, but two
blockers remain, both requiring the operator, not a probe: (1) extraction - the catalog is
only obtainable through the captcha-gated 30-day-window form or a formal request to BMKG
(pusatdatabase@bmkg.go.id); a class-C permission enquiry is operator-authorized only;
(2) licence - no redistribution grant anywhere (all-rights-reserved footer + attribution
mandate, no named licence). The previously recorded option (c), a 12-month live-feed
collection loop, remains the only Scout-runnable path and still needs the licence answered
before publication.
