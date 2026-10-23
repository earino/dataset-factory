# ng-nbs-state-price-exceedance — notes

State-level monthly price series from the Nigerian National Bureau of Statistics
(Selected Food / PMS / AGO / LPG Price Watch family), considered for a state-month
price-exceedance task and closed at the licence gate. Opened and dropped in the
2026-10-23 Africa discovery tick. All probes anonymous from the coordinator.

## Why this source was tempting (recorded so the licence veto is not read as a data judgement)

- Monthly, state-panel price tables (36 states + FCT), the most task-shaped Nigerian
  data found this tick: food-security-relevant, event-structured around the 2023
  fuel-subsidy removal, published on a stated monthly release calendar.
- Raw mirrors already exist on Hugging Face (org `electricsheepafrica`, e.g.
  `africa-nigeria-automotive-gas-oil-diesel-price-watch-...`, license_id `other-open`
  taken from the NADA catalog) — raw mirroring, not a task, but a signal that African
  indicator/price tables are a crowded space.

## Probes (2026-10-23)

- `https://nigerianstat.gov.ng/` — HTTP 200. Footer links found: "Terms Of Use" ->
  `/page/terms`; "Open Data Portal" -> https://nigeria.opendataforafrica.org/;
  https://www.nigeriafoodpricetracking.ng/ (not probed).
- `https://nigerianstat.gov.ng/page/terms` — HTTP 200. Exact clause in the page body
  (fetched, not a search snippet):

  > "The data and other materials provided by the National Bureau of Statistics will
  > not be redistributed or sold to other individuals, institutions, or organizations
  > with out the written agreement of the National Bureau of Statistics."

  Followed by "The data will be used for statistical and scientific research purposes
  only" and a citation requirement. Surrounding wording (re-identification prohibitions)
  is microdata-style boilerplate, but the clause is not limited to survey microdata.
  Read as written: no redistribution of derived tables without written agreement.
- `https://nigeria.opendataforafrica.org/` — not anonymously usable: one probe attempt
  failed at connection level, a second answered HTTP 403 Forbidden (2026-10-23). The
  NBS footer still links it; the Knoema/opendataforafrica platform behind it is in
  sunset per its re3data entry (attribution).
- `https://www.nigeriadata.gov.ng/` ("Integrated Data Sharing Portal", new MDA portal) —
  HTTP 200, React SPA. No licence statement in the page source; grepping the main JS
  bundle found only map/tile endpoints, no data API. Not probed further this tick.

## Verdict (2026-10-23)

DROP — class D licence veto, the cheapest decisive fact, probed before any schema or
split work. Novelty was never reached and is not claimed in either direction. Reopen
conditions in record.json next_action: (a) written agreement from NBS (operator-side;
no unsolicited permission email per standing policy), or (b) a different channel with
its own open terms (e.g. WFP VAM market prices for Nigeria — that channel needs its own
licence + novelty check and is NOT covered by this verdict).

## Reproducing the probes

`probe_terms.py` in this directory refetches the NBS homepage, extracts the
terms/ODP links, refetches `/page/terms` and prints the no-redistribution clause with
context. Run: `python3 probe_terms.py`.
