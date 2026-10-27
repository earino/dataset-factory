# Licensing

This release carries three grants with three scopes. Nothing here relicenses the
source: the publisher's own terms are preserved and carry through to every copy.

## Our code and documentation - MIT

The package's scripts (`get_dataset.py`, everything under `code/` and `baseline/`)
and its documents are MIT (see `LICENSE-MIT.txt`):
Copyright (c) 2026 E. Arino de la Rubia (earino).

`baseline/train.py`, `baseline/validate.py` and `baseline/validate.sh` are the
harness benchmark's own runner files, shipped verbatim and unmodified (their
sha256 digests, equal to the benchmark's declared hashes, are recorded in
`VERIFICATION.md`); the MIT grant covers the distributed copies.

## Our rights in the derived compilation - CC0-1.0

Our contribution - the notified-case eligibility frame, the derived Phase II
opener label, the notification-date feature derivations, the temporal partition,
and the packaging - is dedicated to the public domain under CC0-1.0
(see `LICENSE-CC0-1.0.txt`). The dedication covers only our contribution.

## The source's own terms - CC BY 4.0 (European Commission reuse notice)

The underlying data is the European Commission's machine-readable merger case
register (DG COMP), released as open data under the Commission reuse notice, i.e.
CC BY 4.0 unless otherwise indicated. DG COMP's release announcement states the
machine-readable data sets can be processed "in any way the users may wish, for
commercial or non-commercial purposes, provided that the source is acknowledged."

**Attribution (required by CC BY 4.0, in every copy):**

> European Commission, Directorate-General for Competition - EU Competition:
> Merger case publications (open data case register),
> https://data.europa.eu/data/datasets/cc7e224e-6569-40f0-8037-d3389aa0fae7,
> vintage of 2026-10-27. Contains Commission-owned content licensed under
> CC BY 4.0.

**Changes are indicated:** this dataset is a derived research dataset - a row
selection (notified merger cases), a derived binary label (whether the Commission
opened an in-depth Phase II investigation), and derived features. It is **not**
the European Commission's official product, and the Commission has not reviewed
or endorsed it.

The publisher's own designation, attribution statement and suggested citation are
preserved verbatim in `MANIFEST.json` (`licenses` block) and in the candidate
record; the per-dataset decision lives in the factory repository at
`candidates/ec-merger-phase2-opening/license.json`.
