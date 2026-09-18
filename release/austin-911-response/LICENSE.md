# Licence and attribution

## The data

**Public Domain.** The source catalogue entry for `e687-fx2y` reports the licence as
`Public Domain`:

- Socrata catalogue metadata for `e687-fx2y`, queried 2026-09-18.
- Re-confirmed 2026-09-18 from
  `GET https://datahub.austintexas.gov/api/views/e687-fx2y.json`, which returns
  `"license": {"name": "Public Domain"}` for the view *APD 911 Calls for Service 2023-2026*.

Redistribution of the source data is permitted on that basis. This dataset is a derived work:
row selection, a derived binary label, and a temporal partition. No row is edited, imputed,
reweighted or synthesised.

**Attribution.** City of Austin, *APD 911 Calls for Service 2023-2026*, Austin Open Data,
https://datahub.austintexas.gov/d/e687-fx2y, accessed 2026-09-18. Public Domain.

**Suggested citation text.**

> City of Austin. *APD 911 Calls for Service 2023-2026*. Austin Open Data. Public Domain.
> Accessed 2026-09-18. Derived dataset: Austin 911 response time prediction dataset,
> version 2026.09, artifact `e4598317e406984fa590aacc5e7aff675867578c51ae1a84ebf6279bc42c3328`.

## The construction code

The script that builds this dataset (`build.py`) is stdlib-only Python and is published with
the release so the dataset is reproducible independently of the private factory repository.

**Its licence has not been chosen yet.** The data's Public Domain status says nothing about the
code that derives it, so the code licence is left as an explicit open decision for the reviewer
rather than assumed. Until it is set, treat the script as *all rights reserved* and reproduce
the dataset by running it under the terms you are given, or contact the maintainer.

*(Decision needed: pick one — MIT, Apache-2.0, CC0, or "no licence published; reproduction
instructions only" — and state it here. This is flagged rather than silently defaulted because
it is a legal choice, not a technical one.)*

## The benchmark

The baseline number in this release was produced by running the **harness benchmark's own**
`train.py` and `validate.py` unmodified, from a pinned revision of that project. Those files
carry that project's licence and are **not** redistributed here; `REPRODUCE.md` records their
SHA-256 hashes so a run can be checked against the same revision. No part of that benchmark is
relicensed by its use here.
