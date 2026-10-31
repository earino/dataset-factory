# Licensing

This release carries three grants with three scopes. Nothing here relicenses the
source: the publisher's own terms are preserved and carry through to every copy.

## Our code and documentation - MIT

The package's scripts (`get_dataset.py`, everything under `code/` and `baseline/`)
and its documents are MIT (see `LICENSE-MIT.txt`):
Copyright (c) 2026 E. Ariño de la Rubia (earino).

`baseline/train.py`, `baseline/validate.py` and `baseline/validate.sh` are the
harness benchmark's own runner files, shipped verbatim and unmodified (their sha256
digests, equal to the benchmark's declared hashes, are recorded in
`VERIFICATION.md`); the MIT grant covers the distributed copies.

## Our rights in the derived compilation - CC0-1.0

Our contribution - the eligibility frame (domestic applications with parseable
filing dates in 2010-2016), the registered-by-snapshot label with per-cohort
censoring, the right-anchored recovery of embedded-pipe rows and stripped-string-key
deduplication, the derived feature columns, the filed-year cohort partition with
boundary exclusions, and the packaging - is dedicated to the public domain under
CC0-1.0 (see `LICENSE-CC0-1.0.txt`). The dedication covers only our contribution.

## The source's own terms - Open Government Licence v3.0 (UK IPO)

The underlying trade mark data are the UK Intellectual Property Office's trade mark
open data (`opendatadomestic.zip`, the frozen 2018-02-13 snapshot), published under
the Open Government Licence v3.0. OGL-UK v3.0 permits copying, publication,
distribution, transmission, adaptation and commercial exploitation with attribution,
and applies the same-licence condition to adapted versions of the information.
OGL-UK exempts personal data, third-party rights and official symbols from its grant;
the shipped columns were chosen with that in mind: owner name and the hyperlink
column are excluded by design, while the owner country / region / postcode-area
fields and the mark text are redistributed exactly as published.

**Attribution (required by OGL-UK v3.0, in every copy):**

> Contains public sector information licensed under the Open Government Licence
> v3.0. Source: UK trade mark applications open data (Intellectual Property Office),
> opendatadomestic.zip snapshot of 2018-02-13.

**Suggested citation:**

> Intellectual Property Office. UK trade mark applications open data
> (opendatadomestic.zip, snapshot of 2018-02-13).
> https://www.gov.uk/government/publications/ipo-trade-mark-data-release .
> Licensed under the Open Government Licence v3.0. Derived dataset: UK trade mark
> application registration-outcome prediction task (not an Intellectual Property
> Office product).

**No implied endorsement:** neither the licence nor this derived dataset suggests
the Intellectual Property Office endorses this task or its use. This dataset is a
derived research dataset - a row selection, a derived binary label, derived features
and a partition. It is **not** the Intellectual Property Office's product, and the
IPO has not reviewed or endorsed it.

The publisher's own designation, attribution statement and suggested citation are
preserved verbatim in `MANIFEST.json` (`licenses` block); the per-dataset decision
lives in the factory repository at
`candidates/ipo-trademark-registration-outcome/license.json`.
