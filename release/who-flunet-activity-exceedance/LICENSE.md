# Terms for this dataset

## 1. No licence is asserted over the data

We could not establish a licence for this data, and we are not going to claim one.

The source is WHO FluNet. WHO's **general publishing policy** names CC BY-NC-SA 3.0 IGO for
WHO *publications*. FluNet is a *dataset*, and the FluNet page links a separate **Data policy**
whose terms for WHO data compilations, aggregations, evaluations and analyses say:

- use and distribution are permitted "for public health purposes" (clause 01);
- **"Any other alteration or modification of the Datasets (including abbreviations, additions, or
  deletions) may be made only with the prior written authorization of WHO"** (clause 04);
- **"You will not sell or otherwise transfer the Datasets and/or data contained therein to any
  third party, except within the Licensed Use"** (clause 05).

This release is a substantial alteration of the source: we re-grain it to country-weeks, derive a
binary label, select rows and partition the data in time. We hold no written authorisation from WHO
for that, and FluNet states no dataset-specific licence — there is no licence field in its metadata
CSV or in the API response.

CC BY-NC-SA 3.0 IGO also cannot be applied by us in any case: WHO's own copyright page notes that
licence "can only be used by organizations established by a treaty or other instrument governed by
international law". We are not such an organisation.

**So: no open licence is granted over the source rows or over this compilation.** Do not assume one
exists, and do not treat this dataset as CC-licensed, public domain, or freely redistributable. If
you need a definitive answer, or any commercial use, ask WHO: <gisrs-whohq@who.int>.

This does not affect our code, which is MIT (see below), or the fact that the compilation is our
work. It means we are not in a position to grant you rights we do not hold.

## 2. What we ask of you

- **Attribute** WHO and the contributing countries. Suggested citation:
  > World Health Organization. FluNet. Geneva: World Health Organization; 2026.
  > Derived dataset: WHO FluNet influenza-positivity exceedance prediction task.
- **Non-commercial research use only**, unless you have cleared rights with WHO yourself.
- **Do not use the WHO name or emblem**, and do not imply that WHO endorses this dataset or that it
  is an official WHO product. It is not.
- **Do not redistribute** this dataset as though it were openly licensed. If you pass it on, pass on
  this file with it.

## 3. Takedown

If WHO asks for this dataset to be withdrawn, it will be withdrawn. Contact the maintainer through
the repository's issue tracker or <https://github.com/earino>.

## 4. The code

`code/`, `baseline/train.py` (the unmodified benchmark runner), `get_dataset.py`, `baseline/*.sh` and
the scripts we wrote are MIT licensed: see `LICENSE-MIT.txt`. The runner files under `baseline/` are
shipped verbatim from the harness benchmark under the same MIT terms.

## 5. What this is not

A derived research dataset. It is not an official WHO publication, has not been reviewed,
authorised or endorsed by WHO, and must not be presented as WHO's own data product. The label is
ours: WHO publishes laboratory counts, not this exceedance target.
