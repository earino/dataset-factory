# Licence and terms — `chicago-doah-adjudication`

This release has **three** layers of terms. They are not the same, and only one of them is an
open licence. Read this before you redistribute anything here.

## 1. Our code and documentation — MIT

`code/`, `baseline/`, `get_dataset.py`, and the prose in this repository are released under the
MIT licence. The full text is in `LICENSE-MIT.txt`.

## 2. Our compilation — **not** an open dedication

SPDX: `LicenseRef-CityOfChicago-DataTermsOfUse`.

There is **no separate dedication** of our contribution in the tabular data. The City of Chicago
Data Terms of Use regulate distribution and secondary or derivative use of the source rows; they
do not grant us a right to sublicense those rows on our own terms. We therefore distribute the
compilation under the City's Terms, and we make no claim of an irrevocable right to redistribute.

**Nothing in this release may be described as CC0, CC-BY, public domain, or any other standard
open licence.** The source does not support it. If you see such a claim attached to this dataset
anywhere, it is wrong.

## 3. The source data — City of Chicago Data Terms of Use

Dataset: *Ordinance Violations*, Department of Administrative Hearings, City of Chicago Data
Portal, dataset id `6br9-quuz`, <https://data.cityofchicago.org/d/6br9-quuz>.

The Socrata metadata for this dataset carries `licenseId: SEE_TERMS_OF_USE` and
`attribution: City of Chicago`. There is no standard SPDX licence. The clauses below were read
from the City's Data Terms of Use on 2026-09-26 and are reproduced as the basis of the decision
recorded in `candidates/chicago-doah-adjudication/license.json`:

> "The City may require a user of this data to terminate any and all display, distribution or
> other use of any or all of the data provided at this website for any reason…"

> "Any user of this website providing any software application, or other secondary or derivative
> application using data supplied at this website shall do the following…"

> "These Terms of Use do not grant anyone any title or right to any patent, copyright, trademark
> or other intellectual property rights that the City may have…"

Distribution and derivative use are expressly contemplated and **regulated**, not granted in
affirmative licence form. The operator accepted the Terms' indemnity and defence obligation, and
the City's right to require termination of use for any reason, before this release was prepared.

## Mandatory disclaimer — reproduced verbatim

The City prescribes a disclaimer for secondary or derivative applications using its data. It is
reproduced here verbatim and unaltered, as the Terms require:

> This site provides applications using data that has been modified for use from its original
> source, www.cityofchicago.org, the official website of the City of Chicago. The City of Chicago
> makes no claims as to the content, accuracy, timeliness, or completeness of any of the data
> provided at this site. The data provided at this site is subject to change at any time. It is
> understood that the data provided at this site is being used at one's own risk.

The same text is carried in `README.md`, in the task's `meta.json`, and in
`DATA_DICTIONARY.md`, so that it travels with the data wherever the dataset is obtained.

## Attribution

City of Chicago, Department of Administrative Hearings, *Ordinance Violations*, dataset
`6br9-quuz`, <https://data.cityofchicago.org/d/6br9-quuz>, accessed 2026-09-26.

This dataset is **derived** work. It is not an official City of Chicago product, and the City has
not endorsed it. Downstream users must preserve the attribution above and the disclaimer in the
previous section.

## Takedown

A request from the City to terminate display, distribution or other use of this data will be
honoured. To make that possible, this repository records exactly where the data came from
(`RELEASE_NOTES.md`, `MANIFEST.json` → `source`) and how to rebuild the extract from the original
(`REPRODUCE.md`). A takedown means removing the released assets, not repairing them.
