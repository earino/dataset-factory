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
