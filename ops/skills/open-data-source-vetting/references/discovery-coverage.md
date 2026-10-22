# Measuring discovery coverage

A discovery routine picks the source that is cheapest to open, and cheapest is nearly always the
home country's federal or national API. Coverage therefore has to be a recorded property of the
bench, counted from the records, not a quality claimed in a report.

## The jurisdiction block

Every candidate record carries, beside its identity fields:

```json
"jurisdiction": {"country": "GB", "region": "Europe", "publisher": "Office for National Statistics"}
```

- `country` is an ISO code for the **publisher's** jurisdiction. Data describing Brazil, published by
a US agency, is US.
- `publisher` names the body that issues the data, as it names itself - not the portal that
  mirrors it.
- Add the field to the candidate checker's required identity list in the same change, and never
  default it: a record without it reports `unknown` and fails.

## The coverage report

A small read-only script over `candidates/*/record.json`:

1. skip non-sources - smoke tests, scratch or infrastructure candidates, by an explicit name set;
2. group by `country` and by `region`, counting **live** candidates (anything not rejected);
3. report the distribution and the share of live candidates outside the home country;
4. `--json` for machine use; exit non-zero when any record lacks a jurisdiction.

The number that matters is the live share, not the historical count: rejected candidates inflate a
country's total without proving any current reach. Print both so the report cannot be read as
progress it is not.

Pin the arithmetic with a test that patches the candidate directory to a temp tree: a fixture with
one missing jurisdiction, one rejected foreign source and one live domestic source, asserting the
count, the share and the non-zero exit. Then prove the guard fails against the pre-change checker
before accepting it.

## Deterministic regional rotation

Keep the regions as an ordered tuple and index it by the tick's hour, so consecutive ticks differ and
a report reproduces from its timestamp:

| Region | Catalogue / portals worth probing first |
|---|---|
| Europe (EU/EEA) | data.europa.eu, Eurostat, EEA, ECDC, EFSA |
| United Kingdom | data.gov.uk, ONS, NHS Digital, Defra, Environment Agency, Companies House (OGL) |
| Canada | open.canada.ca (Open Government Licence) |
| Latin America | datos.gob.mx, dados.gov.br, datos.gov.co |
| Africa | openAFRICA, national statistics offices |
| South & SE Asia | data.gov.in, data.gov.sg, BPS Indonesia |
| East Asia | data.gov.tw, data.go.kr, e-Stat Japan |
| Oceania | data.gov.au, ABS |
| International bodies | World Bank, OECD, UN agencies, WHO |

Append the region's name and its portals to the session brief under their own heading, and say there
that an empty regional result is a recorded outcome rather than a cue to substitute a domestic
source.

## Order of work

1. Backfill `jurisdiction` on existing records from their own metadata - never from the URL - and
   read each one back before committing.
2. Make the field required and run the checker over every candidate.
3. Add the coverage report and its test.
4. Only then change the brief and the rotation, so the first rotated tick is measured against a
   baseline rather than a guess.
5. Report the before/after distribution with the commit that made the change.

Budget interaction: raising cadence to several ticks a day is only honest if the spend gate is
measured in a unit the runtime actually records (see `agent-spend-budgeting`); an allowance that is
estimated at zero cannot bind, and the tick count that the token budget admits is the real ceiling.
