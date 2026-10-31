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

Our contribution - the s78_core eligibility frame (planning-permission-family
casework with a binary Allowed/Dismissed decision), the counted exclusions
(non-binary decisions, cross-file composite duplicates, decided-before-validation
rows), the derived binary label from the publisher's Decision field, the derived
date/calendar features, the site-descriptor and designation flags, the LPA
prior-outcome history features computed strictly from decisions earlier than the
row's validation instant, the validation-instant temporal partition, and the
packaging - is dedicated to the public domain under CC0-1.0 (see
`LICENSE-CC0-1.0.txt`). The dedication covers only our contribution.

## The source's own terms - Open Government Licence v3.0 (Planning Inspectorate)

The underlying data are the UK Planning Inspectorate's Casework Database
(`Casework_Database_-_2610.xlsx` and `Older_Casework_Data_-_2610.xlsx`, the
2026-10-22 edition), published on GOV.UK under the Open Government Licence v3.0.
OGL-UK v3.0 permits copying, publication, distribution, transmission, adaptation and
commercial exploitation with attribution, and applies the same-licence condition to
adapted versions of the information. OGL-UK exempts personal data, third-party
rights and official symbols from its grant; the shipped columns were chosen with
that in mind: the publisher's inspector-name field is excluded by design
(post-instant, and corrected for data errors by the publisher in 2025), no free-text
applicant or site-occupier identity ships, and the LPA identity, casework type,
procedure, development type, appeal reason fields, site descriptors and designation
flags are redistributed exactly as published.

**Attribution (required by OGL-UK v3.0, in every copy):**

> Contains public sector information licensed under the Open Government Licence
> v3.0. Source: Planning Inspectorate Casework Database (Planning Inspectorate),
> Casework_Database_-_2610.xlsx and Older_Casework_Data_-_2610.xlsx, 2026-10-22
> edition.

**Suggested citation:**

> Planning Inspectorate. Planning Inspectorate Casework Database (bulk extract,
> 2026-10-22 edition).
> https://www.gov.uk/government/publications/planning-inspectorate-appeals-database .
> Licensed under the Open Government Licence v3.0. Derived dataset: UK
> planning-appeal outcome prediction task (not a Planning Inspectorate product).

**The publisher's own data caveats carry through unchanged:** some categorisation of
appeals can be subjective; the data can change between different publications of
this dataset; the extract covers decided cases only (in progress, withdrawn and
turned away cases are not included); Local Plans Examinations rows were removed by
the publisher from the current Casework Database; TPO valid dates were removed by
the publisher after a data-entry issue; and "The Planning Inspectorate will not
entertain a challenge to the appointment of any Decision Maker on the basis of this
data."

**No implied endorsement:** neither the licence nor this derived dataset suggests
the Planning Inspectorate endorses this task or its use. This dataset is a derived
research dataset - a row selection, counted exclusions, a derived binary label,
derived features and a partition. It is **not** the Planning Inspectorate's product,
and the Planning Inspectorate has not reviewed or endorsed it.

The publisher's own designation, attribution statement, suggested citation and
caveats are preserved verbatim in `MANIFEST.json` (`licenses` block); the
per-dataset decision lives in the factory repository at
`candidates/pins-planning-appeal-outcome/license.json`.
