# ea-flood-defence-asset-condition - discovery notes

Probed 2026-11-06 (UK-focus scheduled discovery session), from the repo root unless a URL
is given. Infrastructure-maintenance shape check: does the EA's open flood-defence asset
product carry per-asset condition grades and inspection dates, and can condition
transitions ever be labelled?

## Commands and results

1. Collections present in the bundle (OGC API, anonymous):

       curl -s "https://environment.data.gov.uk/spatialdata/aims-asset-bundle/ogc/features/v1/collections"

   12 collections; the relevant one is
   `AIMS_Spatial_Flood_Defences_Including_Standardised_Attributes`.

2. One feature (fields exist):

       curl -s ".../collections/AIMS_Spatial_Flood_Defences_Including_Standardised_Attributes/items?limit=1"

   37 property fields, including `current_condition`, `target_condition`,
   `last_inspection_date`, `next_inspection_date`, `asset_start_date`. The sampled feature
   had empty condition and None inspection dates - coverage needed measuring, see (3).

3. Coverage sample (500 items, default ordering - non-random):

       curl -s ".../items?limit=500"

   - numberMatched = 141,416 assets in the collection.
   - 83/500 carry a current_condition grade: {'3': 49, '2': 23, '4': 7, '5': 2, '1': 1,
     '0': 1, '': 417}.
   - 466/500 carry last_inspection_date.

4. Licence (publisher's own dataset record, read 2026-11-06):
   "Use of this data is subject to the licence identified." + "Licence: Open Government
   Licence" (v3) + use-limitation "There are no public access constraints to this data."
   Attribution: "© Environment Agency copyright and/or database right 2020. All rights
   reserved." This is NOT the Conditional Licence that governs EA permit-compliance
   products (the class-D veto on ea-permit-compliance-breach); class A.

5. Download size: direct
   `https://environment.data.gov.uk/dataset/019a8eaa-.../AIMS_Asset_Bundle.gpkg.zip` (and
   .shp/.geojson) answer 404 to plain HEAD; downloads route through the area-of-interest
   explorer. Publisher statement on the record: "depending on the chosen download format,
   it may take 7-8 minutes to download the full national dataset". Size unmeasured.

## Analysis and verdict

The task's fields are in the open product, the population is large (141,416 assets), and
the decision is real (EA capital-programme prioritisation between formal inspections).
But the bundle is a daily-updated current-state extract: no dated historical captures are
published (checked the EA platform and data.gov.uk; the separate decommissioned-assets
products carry lifecycle end dates, not condition histories). Condition-transition labels
therefore cannot be constructed for any past instant, and the observable transition rate
going forward is gated by the EA's multi-year per-asset inspection cycle.

Parked, not dropped: the blocker is structural but has a concrete, measurable reopen path
(a monthly capture schedule; the bundle's own inspection dates make the cycle distribution
measurable after a few captures). No construction before that measurement exists.
