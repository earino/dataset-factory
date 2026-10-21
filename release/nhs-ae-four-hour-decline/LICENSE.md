# Terms for this dataset

This package contains three things under three sets of terms.

## 1. The source data (NHS England, Crown copyright)

The underlying statistics are NHS England's A&E Attendances and Emergency Admissions monthly
provider-level CSVs, published under the **Open Government Licence v3.0** (stated in the
statistical work-area page footer). OGL v3 permits use, copying, publication, distribution and
adaptation - including commercially - under its conditions, which carry through unchanged to
this derived data:

- **Attribution** - identify the source and, where possible, provide a link to the OGL v3
  licence, in every copy:
  > NHS England, A&E Attendances and Emergency Admissions, statistical work area.
  > <https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/>
  > Contains public sector information licensed under the Open Government Licence v3.0.
  > Crown copyright.
- **No distortion** - do not distort the meaning of the original information.
- **No false endorsement** - nothing may imply that NHS England endorses this dataset. It is a
  derived research dataset, **not an official NHS England product**.

Licence text: <https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/>.

## 2. Our contribution to the derived compilation (CC0-1.0)

Our contribution - the row selection, the derived month-over-month decline label, the temporal
partition, the volume gate, the feature derivations and the packaging - is dedicated to the
worldwide public domain under **CC0 1.0 Universal** (`LICENSE-CC0-1.0.txt`). The dedication
covers only our contribution: it does not relicence the NHS England statistics, which keep their
own designation and remain subject to OGL v3, and it does not remove the attribution condition
above.

## 3. The code

`code/`, `get_dataset.py`, `baseline/*.sh`, `baseline/README.md` and the scripts we wrote are
MIT licensed: see `LICENSE-MIT.txt`. `baseline/train.py`, `baseline/validate.py` and
`baseline/validate.sh` are the harness benchmark's own runner files, shipped **verbatim and
unmodified** under the benchmark's MIT terms (their sha256 digests are recorded in
`VERIFICATION.md` and in the baseline job's report).

## What this is not

This is a derived research dataset. It is not an official NHS England publication, has not been
reviewed or endorsed by NHS England, and must not be presented as the source agency's official
product. The publisher's own designation, attribution and suggested citation are preserved
verbatim in these terms.
