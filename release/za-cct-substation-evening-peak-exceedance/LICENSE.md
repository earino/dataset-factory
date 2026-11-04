# Licensing

This package carries two grants from us plus the source's own terms, which we
never relicense. Full machine-readable decision:
`candidates/za-cct-substation-evening-peak-exceedance/license.json` in the
factory repository; the standing policy is `config/licensing-policy.json`.
The `MANIFEST.json` licenses block is generated from that declaration.

## Our code and documentation: MIT

Everything we authored in this package (`code/build.py`, `code/run.sh`,
`code/score.py`, `code/materialize.py`, the docs, `get_dataset.py`, the
baseline scripts) is MIT - see `LICENSE-MIT.txt`. `baseline/train.py`,
`baseline/validate.py` and `baseline/validate.sh` are the harness benchmark's
own runner files, shipped verbatim and unmodified (bundled sha256 equal the
benchmark clone's hashes); permission to distribute verbatim copies covers
the distributed copies only.

## Our rights in the derived compilation: CC0-1.0

To the extent we hold rights in the derived compilation - the substation-day
eligibility frame (>= 30 prior evenings at the instant; burn-in counted, never
scored), the derived binary evening-peak-exceedance label (over the sealed
trailing-90-evening p95), the at-instant feature derivations, the sealed
evening label matrix kept outside every solver-visible frame, and the temporal
partition (train 2022 / eval 2023 / holdout 2024) - we dedicate that
contribution to the public domain under CC0-1.0 (see `LICENSE-CC0-1.0.txt`).
The dedication covers **only our contribution**.

## The source: City of Cape Town Open Data Terms of Use, preserved

No standard SPDX licence is declared; the operative instruments are the City of Cape Town Open Data Terms of Use (disclaimer-only: as-is, no warranty, no liability; no restriction on reuse, redistribution or derivatives for portal data) together with the Council-approved Open Data Policy 27781 ('freely used, shared and built-on by anyone, anywhere, for any purpose'), and the ArcGIS item's licenseInfo links the portal terms. The table is engineering telemetry (half-hourly apparent-power MVA readings per switching substation): no personal data, no third-party content, no official symbols. The redistributed fields are the publisher's own readings (timestamped MVA values and station identifiers) plus our derived binary label, at-instant aggregates, calendar fields and partition. The derived dataset is labelled as such throughout and is not a City of Cape Town product.

- Source: City of Cape Town Open Data Portal - Switching Substation Load Profile (ArcGIS item bebf20c25bfa4ffaa7fc07a1a94ba287), accessed 2026-11-01.
- The derived dataset is labelled as derived throughout and is **not a City of
  Cape Town product**; the City has not reviewed or endorsed it.
- The portal Terms of Use disclaimer (as-is, no warranty, no liability)
  carries through unchanged, and the publisher's data caveat carries through
  in every document: readings are indicative measured MVA, not corrected for
  temporary load shifts or load fluctuations due to load shedding.
- Suggested citation: City of Cape Town. Switching Substation Load Profile. City of Cape Town Open Data Portal, ArcGIS item bebf20c25bfa4ffaa7fc07a1a94ba287, Open Data Terms of Use. Derived dataset: Cape Town switching-substation evening-peak exceedance prediction task (not a City of Cape Town product).

Changes from the source are indicated: the substation-day row selection with
burn-in, the derived binary evening-peak-exceedance label over the sealed
trailing-evening p95, the at-instant feature derivations, the sealed evening
label matrix, and the temporal partition.
