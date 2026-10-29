# za-capetown-odp-coverage — notes

Portal coverage record for the City of Cape Town Open Data Portal, Africa tick
2026-10-29. All measurements via the anonymous DCAT-US feed and ArcGIS REST
queries from this coordinator; commands preserved in
`candidates/za-cct-c3-service-request-surge/probe_c3.py` (--mask reproduces the
billing-mask probe on the water service; the census scripts are described below).

## Commands behind the measurements (2026-10-29)

- DCAT census: `curl -sS https://odp-cctegis.opendata.arcgis.com/api/feed/dcat-us/1.1.json`
  → 265 datasets; per-dataset license property points at the City's Open Data
  terms of use; keyword filter run over the feed for task-shaped series.
- Billing schema + panel: ArcGIS REST on
  `.../Suburb_Level_Water_Billing_2021_to_March_2026/FeatureServer/0`
  (count 219,184; min/max Date 2020-12-31..2026-09-30 in the service frame =
  69 monthly tags; 787 distinct Suburb values; 6 Billing_Class values:
  Commercial 35,460 / Departmental 38,208 / Domestic 49,947 / Industrial 12,622 /
  Not assigned 35,997 / Other 46,950; ~3,157 rows/month). Electricity sibling:
  102,809 rows, same classes plus 'Unmetered' 1,277.
- Mask-by-month (water Domestic, full class, 2 fields, 27.2 s measured):
  `python3 candidates/za-cct-c3-service-request-surge/probe_c3.py --mask`
  → ~98% masked every month 2020-12..2026-02, 0% masked 2026-04..2026-09,
  2026-03 absent (63+6 = 69 monthly groups). Electricity Domestic: 100% masked
  before 2026-04. Water non-Domestic spot checks: 92.7-100% masked in 2023-06,
  0% in 2026-09.
- Quantity semantics (resolved before the veto): 2026-09 Domestic city slice —
  sum(Quantity) 6,506,832,249 over sum(Number_of_Records) 2,345,019 →
  2,774.7 units/record; sum(Amount) 286,426,095 ZAR → 0.044 ZAR/unit ≈ R44/kl,
  the CCT domestic tariff band → Quantity = litres, Amount = ZAR billed.
  2026-01 Domestic: 98.2% masked (the masking is a temporal regime, not
  small-cell suppression: same suburbs, same classes, unmasked after 2026-04).
- Live pages: https://www.capetown.gov.za/general/city-of-cape-town-open-data-terms-of-use/
  (disclaimer-only); Open Data Policy PDF at
  https://www.capetown.gov.za/media/vg2plaql/open_data_policy.pdf (read in full).
  Old ASPX portal web1.capetown.gov.za/web1/opendataportal → 302 to an error page.

## What this session carried forward

- za-cct-c3-service-request-surge (ready): the portal's live, unit-grain,
  daily-updated C3 notification table → weekly surge exceedance task.
- Everything else: parked per record.json rejection_reason, with the reopen
  conditions stated there (billing needs ~18+ unmasked months, i.e. from ~2027-10).
