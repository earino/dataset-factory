# jma-typhoon-rapid-intensification - probes

East Asia discovery tick, 2026-10-20. All probes anonymous, from the coordinator.
Verdict: **reject** - the RI prediction task already ships as ML-ready, split, scored
benchmarks (TCRISI, TCBench). Access and licence measured clean; they are not the blocker.

## Probe 1 - old RSMC URL (moved)

    curl -sS -o bt2024.txt -w "%{http_code} %{size_download}B" \
      "https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp/pub-egt/bt2024.txt"
    -> 404 2203B
    curl ... ".../rsmc-hp/pub-egt/besttrack.html"
    -> 404 2203B

The pre-2026 path `rsmc-hp/pub-egt` is gone; a search for the format doc located the
section at `.../rsmc-hp-pub-eg/`.

## Probe 2 - RSMC pages (all 200, anonymous, no key)

    GET https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/RSMC_HP.htm       -> 200 9087B
    GET .../rsmc-hp-pub-eg/trackarchives.html                                         -> 200 6141B
    GET .../rsmc-hp-pub-eg/besttrack.html                                            -> 200 6536B
    GET .../rsmc-hp-pub-eg/Besttracks/e_format_bst.html                               -> 200 10438B

`besttrack.html` lists the data files: `Besttracks/bst2026.txt` (current season),
`Besttracks/bst_all.zip` (whole archive), `history_of_revision.csv`,
`history_of_revision_format.pdf`, and the format doc.

## Probe 3 - bulk archive size (HEAD, 1 request)

    curl -sS -I ".../rsmc-hp-pub-eg/Besttracks/bst_all.zip"
    -> HTTP/2 200, content-length: 744954, last-modified: Tue, 29 Sep 2026 05:25:31 GMT

The full 1951-present best-track record is a single ~0.75 MB anonymous download.
Cheapest bulk channel measured in this tick's region.

## Probe 4 - column documentation (e_format_bst.html)

Fixed-width ASCII, documented per column: one header line per storm (international
number ID, data-line count, storm name, revision date), then 6-hourly data lines:
time `yymmddhh` UTC; grade (2 TD / 3 TS / 4 STS / 5 TY / 6 extra-tropical);
0.1-degree latitude/longitude; central pressure (hPa); maximum sustained wind (kt);
direction + longest/shortest radius of 50kt and 30kt winds (nm); landfall indicator.
Every column has a stated meaning, position and unit - the schema contract holds.

## Probe 5 - licence (JMA Website Terms of Use)

    GET https://www.jma.go.jp/jma/en/copyright.html -> 200 13749B

Quote (extracted from the page text): "Information made available on the Japan
Meteorological Agency website (hereinafter referred to as \"Content\") may be used in
accordance with the terms and conditions of use stipulated in Public Data License
(Version 1.0), unless otherwise indicated by a specific rights notice." Source citation
required, examples given on the page; edited content must state it was edited, without
implying creation by the Government of Japan. Licence settled and permissive.

## Probe 6 - novelty (the decisive one)

Web search for ML-ready RI benchmarks (query recorded in record.json's novelty_check):

- **TCRISI** - csie.ntu.edu.tw/~htlin/program/TCRISI: "TCRISI serves as the dataset for
  benchmarking the performance of TC rapid intensification prediction models", derived
  from the TCIR dataset, training/validation/test splits published, official benchmark
  repository for loading tfrecords; benchmarked with attention-based deep models.
- **TCBench** (arXiv 2601.23268): IBTrACS-derived benchmark for TC track and intensity,
  storms divided by year to prevent leakage, named baselines.
- SHIPS-based RI studies with publicly downloadable predictor data and chronological
  train/test splits (Nat Hazards 2023: train 1982-2015, test 2016-2020, RI = DELV >= 30 kt).
- Data mirrors of the raw source: IBTrACS republishes RSMC Tokyo best track; Digital
  Typhoon archive; the `jmastats` R package parses best-track files directly.

Verdict: **mirror** - the task exists in usable, split, scored form; the record is
`dropped` so JMA is not re-opened blind. Unit caveat recorded anyway: the 30 kt/24 h RI
standard is a 1-minute-wind convention; JMA reports 10-minute sustained winds - any
future JMA-units task would need a threshold decision and a known-event fixture.

## Not measured this session

- Storm count, 6-hourly row count, RI positive counts from the archive itself
  (`bst_all.zip` not downloaded - wall clock ended at the verdict). Literature figures
  (~1,500-1,700 WNP named storms since 1951, multiple RI events per season) are labelled
  as estimates in record.json and were not used to justify anything.
