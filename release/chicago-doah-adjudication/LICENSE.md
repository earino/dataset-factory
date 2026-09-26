# Licence

Three layers of terms apply to this package, and they are not the same. Only the **code** is under
a standard open licence; the **data** is not.

## 1. Code and documentation — MIT

Everything written for this package is under the MIT licence in
[`LICENSE-MIT.txt`](LICENSE-MIT.txt): `build.py`, `qualify_dataset.py`, `materialize.py`,
`measurements`/manifest tooling, `get_dataset.py`, the documentation, and the site/build plumbing.

Three files under `baseline/` — `train.py`, `validate.py`, `validate.sh` — are bundled **verbatim**
from `earino/harness_benchmark` (the benchmark's `task_template/`) so that the recorded baseline is
reproducible against the runner's own contract. They are MIT too, and are shipped **unmodified**;
their SHA-256 digests are recorded in `MANIFEST.json` under
`licenses.code.third_party` and under `baseline.runner_files`, and both must agree with the bytes
on disk. Nothing in this package was changed to make this dataset score better.

## 2. Our contribution to the data — no separate dedication

The row selection, the case-level aggregation, the derived binary label, the temporal partition and
the packaging are our work. We do **not** dedicate them under CC0 or any other standard open
licence, because the terms that govern the City's data carry through to a derived compilation of
it. The terms this package is distributed under, and the source's own terms beneath them, are
recorded in [`LICENSE-CITY-OF-CHICAGO-TERMS-OF-USE.md`](LICENSE-CITY-OF-CHICAGO-TERMS-OF-USE.md).

## 3. The City's data — the City's terms, unchanged

The source data is published by the City of Chicago under its own Terms of Use. Those terms are
**preserved unchanged and not relicensed here** — the attribution, the "as is" disclaimer and the
derived-work labelling all carry through, and are repeated in `meta.json`, `quality.json`,
`MANIFEST.json` and the source record in [`LICENSE-CITY-OF-CHICAGO-TERMS-OF-USE.md`](LICENSE-CITY-OF-CHICAGO-TERMS-OF-USE.md).

**Required disclaimer** (from the City's Terms of Use, reproduced in full in every copy of
`meta.json` and `quality.json` in this release):

> This site provides applications using data that has been modified for use from its original
> source, www.cityofchicago.org, the official website of the City of Chicago. The City of Chicago
> makes no claims as to the content, accuracy, timeliness, or completeness of any of the data
> provided at this site. The data provided at this site is subject to change at any time. It is
> understood that the data provided at this site is being used at one's own risk.

This dataset is **derived** and is **not** an official City of Chicago product, and is not endorsed
by or affiliated with the City.

## Attribution

City of Chicago, Department of Administrative Hearings, Ordinance Violations. City of Chicago Open
Data Portal, dataset `6br9-quuz`, <https://data.cityofchicago.org/d/6br9-quuz>, accessed
2026-09-26. Used under the City of Chicago Data Terms of Use. Derived dataset:
`chicago-doah-adjudication`, version 2026.09.

## How the terms were decided, and the rule they follow

The terms are declared per dataset in `candidates/chicago-doah-adjudication/license.json` and read
from there into `MANIFEST.json` by the manifest tool, so the manifest cannot drift from the
decision. The policy they follow (`config/licensing-policy.json`) is:

- Code and documentation are MIT by default.
- Otherwise, each dataset must use terms **compatible with its sources**. A default dedication is
  not a blanket override of upstream terms: attribution, share-alike and non-commercial
  requirements from a source are carried through unchanged.
- The source's own terms are preserved and never relicensed; any dedication covers only our
  contribution to the compilation.
- A source whose terms cannot be read is not published at all.

The City's terms were read from the City's own published Terms of Use and confirmed against the
portal's dataset metadata; the evidence is recorded in the manifest's `licenses.source_data` block
and in `license.json`.

## If you believe this package misstates your rights

The terms above are recorded in good faith from the City's published Terms of Use. If the City (or
any rights holder) believes this release misstates the terms, says the data may not be
redistributed in this form, or objects to the derived labelling, contact the maintainer
(<https://github.com/earino>) and the package will be corrected or withdrawn. The takedown
commitment and contact route are also recorded in
[`LICENSE-CITY-OF-CHICAGO-TERMS-OF-USE.md`](LICENSE-CITY-OF-CHICAGO-TERMS-OF-USE.md).
