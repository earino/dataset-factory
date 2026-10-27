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

Our contribution - the corridor-year eligibility frame, the derived doubling label,
the published-year feature derivations, the temporal partition, and the packaging -
is dedicated to the public domain under CC0-1.0 (see `LICENSE-CC0-1.0.txt`).
The dedication covers only our contribution.

## The source's own terms - CC BY 3.0 IGO (UNHCR via HDX)

The underlying statistics are UNHCR's asylum-applications data (applications
residing in each country of origin, annual), distributed through the Humanitarian
Data Exchange under a Creative Commons Attribution 3.0 IGO licence recorded on the
dataset page. CC BY 3.0 IGO permits any use, redistribution and adaptation with
attribution.

**Attribution (required by CC BY 3.0 IGO, in every copy):**

> UNHCR, The UN Refugee Agency - asylum applications residing in each country of
> origin (annual), via the Humanitarian Data Exchange (HDX),
> https://data.humdata.org/dataset/74cdbe77-0a0b-441b-9535-bacc263be2a8,
> vintage of 2026-08-20. Licensed under CC BY 3.0 IGO.

**No implied endorsement:** neither the licence nor this derived dataset suggests
UNHCR endorses this task or its use. This dataset is a derived research dataset -
a row selection (eligible corridors), a derived binary label (whether applications
double year-over-year), and derived features. It is **not** UNHCR's product, and
UNHCR has not reviewed or endorsed it.

The publisher's own designation, attribution statement and suggested citation are
preserved verbatim in `MANIFEST.json` (`licenses` block) and in the candidate
record; the per-dataset decision lives in the factory repository at
`candidates/unhcr-refugee-data-finder/license.json`.
