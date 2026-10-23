# gh-opendata-coverage — notes

Country-coverage record for Ghana: the Ghana Open Data Initiative portal (data.gov.gh)
was unreachable from this coordinator during the 2026-10-23 Africa discovery tick, so
no licence or content claim could be measured first-hand. Status kept as investigating
because access failure is not a scientific rejection. All probes anonymous.

## Probes (2026-10-23)

- `https://data.gov.gh/api/3/action/package_list` and
  `https://data.gov.gh/data/api/3/action/package_list` — **connection refused** on both
  CKAN action API paths.
- Real-browser load of `https://data.gov.gh/` — ERR_SOCKS_CONNECTION_FAILED (network
  level, not a rendering/JS issue). Search engines still index live group/dataset pages
  (e.g. `/group/datagovgh`, "Displaying 1 - 8 of 8 datasets"), so the portal is likely
  intermittently reachable from other networks — recorded as attribution, not fact.

## Third-party evidence (attribution, not publisher instruments)

- Data Landscapers Ghana maturity assessment (corpus.data-landscapers.io/maturity/
  countries/gha/, read 2026-10-23): "Government data was published for download on the
  Ghana Open Data Initiative portal (data.gov.gh) in 2026; **no open licence is on
  record**"; portal rebuilt 2018-2019 under NITA; cites the World Bank eTransform
  completion report: 315 datasets uploaded since 2020, count not growing for 3 years,
  portal down at the time of that writing.
- Search-indexed catalogue pages show dated static CSVs: 2008 presidential election
  run-off results, regional fire outbreaks 2007-2012, defilement cases 2015-2017,
  airport departures 1997-2015 — snapshots, not ongoing series.

## Verdict (2026-10-23)

INVESTIGATING, parked-in-practice on access: the portal never answered from this
coordinator (API refused; browser SOCKS failure), so licence, content and currency are
all unmeasured. The third-party evidence makes a usable task unlikely (static
catalogue, no licence on record), but that hypothesis needs the publisher's own pages.
Next probe (record.json next_action): one bounded re-probe from a reachable network
(worker-side, alongside the ZA DWS access test); if the CKAN API answers, read
package_show licence fields on 2-3 datasets and count recently-updated resources; if
per-dataset open licences exist AND any ongoing dated series exists, open a real
candidate — otherwise close Ghana under the class C standing policy with the licence
absence as the decisive fact. Do not retry from this coordinator; the failure is
network-level.

## Reproducing the probes

`probe_access.py` in this directory re-runs the two CKAN action-API probes and prints
the refusal evidence. The browser failure is reproducible by loading
https://data.gov.gh/ in any browser on this network.
