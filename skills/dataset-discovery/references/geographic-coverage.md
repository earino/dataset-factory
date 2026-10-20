# Geographic coverage for dataset sourcing

A pipeline that is not pointed at the world converges on the country with the easiest open APIs.
Use this as the rotation and as a starting map; it is not a list of acceptable answers.

## Rotation

Nine regions, cycled so consecutive sessions never share one. Each entry names where to start and
what the licence usually looks like — verify the licence on the publisher's own page, always.

| Region | Start here | Typical licence / gotcha |
| --- | --- | --- |
| EU / EEA | data.europa.eu; Eurostat, EEA, ECDC, EFSA; national statistical offices | CC-BY 4.0 usually; agency-specific terms vary. Portal metadata often lags the live API. |
| United Kingdom | data.gov.uk; ONS, DVSA/DfT, Environment Agency, Companies House, NHS | Open Government Licence v3 (attribution). CKAN `package_show` states it per dataset — quote it. |
| Canada | open.canada.ca; Statistics Canada, ECCC, Health Canada | Open Government Licence – Canada; attribution wording differs from the UK's. |
| Latin America | dados.gov.br, INPE, DATASUS; datos.gob.mx; datos.gob.cl; Colombia, Argentina | Mixed: some CC-BY, some "consulta" only. Portuguese/Spanish docs are the norm; expect PDFs. |
| Africa | data.gov.za, Stats SA, SAPS; Kenya, Nigeria, Ghana, Morocco open portals; AfDB, UNECA | Highly variable; several portals are aggregated links rather than APIs. |
| South & South-East Asia | data.gov.in, IMD, CPCB; BPS Indonesia; PSA Philippines; Thailand, Vietnam, Malaysia | Mixed licences; government PDFs and Excel are common, APIs rarer. |
| East Asia | Japan e-Stat and JMA; Korea KOSIS and KMA; Taiwan, Hong Kong, Singapore | e-Stat needs an app id; KOSIS and JMA publish clean open APIs. |
| Oceania | data.gov.au, ABS, BoM; data.govt.nz, Stats NZ | Australian state licences differ from the federal one — check each state separately. |
| International organisations | World Bank, OECD, UNHCR/UNICEF/UNODC, WHO, IMF, ITU | Usually CC-BY; the publisher's own jurisdiction is what goes in the record, not "international". |

## Choosing within a region

Prefer, in order: (1) a documented anonymous API, (2) a bulk CSV with a stable URL, (3) a portal
record with a per-dataset licence. A PDF-only publisher is a `park` with that reason, not a `go`.

National statistical offices and sector regulators beat aggregator portals: the aggregator's schema
is a third party's guess, and its licence statement may not be the publisher's.

## Habits that keep coverage honest

- Probe the same task shape across regions rather than collecting one dataset per country for its
  own sake: the point is testing whether the pipeline generalises, and a per-country quota invites
  weak candidates.
- Record measured base rates and coverage windows per region, so a small panel or a suspended
  year (a monitoring pause, a reporting-holiday gap) is visible before construction budgets it.
- When a region's most obvious sources are mirrors of an existing task, record that as the verdict —
  a clear rejection with the prior art named is the useful output, not a pushed-through candidate.
