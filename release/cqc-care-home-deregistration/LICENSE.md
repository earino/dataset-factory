# Licensing

This package carries two grants from us plus the source's own terms, which we
never relicense. Full machine-readable decision:
`candidates/cqc-care-home-deregistration/license.json` in the factory
repository; the standing policy is `config/licensing-policy.json`
(policy_version 2026-09-19). The `MANIFEST.json` licenses block is generated
from that declaration.

## Our code and documentation: MIT

Everything we authored in this package (`code/build.py`, `code/run.sh`,
`code/score.py`, `code/materialize.py`, the docs, `get_dataset.py`, the
baseline scripts) is MIT - see `LICENSE-MIT.txt`. `baseline/train.py`,
`baseline/validate.py` and `baseline/validate.sh` are the harness benchmark's
own runner files, shipped verbatim and unmodified (bundled sha256 equal the
benchmark clone's hashes); permission to distribute verbatim copies covers
the distributed copies only.

## Our rights in the derived compilation: CC0-1.0

To the extent we hold rights in the derived compilation - the row selection
(care-home rows of the January vintages), the derived binary register-event
label, the per-instant pseudonymised identity, the at-T feature derivation,
the temporal partition and the packaging - we dedicate that contribution to
the public domain under CC0-1.0 (see `LICENSE-CC0-1.0.txt`). The dedication
covers **only our contribution**.

## The source: Open Government Licence v3.0, preserved

The Care Quality Commission's register bulk files are public sector
information. Contains public sector information licensed under the Open
Government Licence v3.0. Source: Care Quality Commission (CQC), HSCA Active
Locations (monthly vintages, January 2018-2025) and Deactivated Locations
(2026-11-02 edition) bulk files. https://www.cqc.org.uk/about-us/transparency/using-cqc-data

- The OGL v3.0 attribution condition carries through to every copy of the
  derived data: acknowledge CQC as the data source.
- The derived dataset is labelled as derived throughout and is **not a CQC
  product**; CQC has not reviewed or endorsed it.
- CQC's in-sheet disclaimer carries through unchanged: CQC does not hold
  responsibility for subsequent analysis done from raw data provided, as
  this is seen as creating new information; CQC should not be quoted as the
  source of the analysis or interpretation.
- Suggested citation: Care Quality Commission. CQC care directory bulk
  files: HSCA Active Locations and Deactivated Locations.
  https://www.cqc.org.uk/about-us/transparency/using-cqc-data . Licensed
  under the Open Government Licence v3.0. Derived dataset: CQC care-home
  12-month deregistration prediction task (not a CQC product).

Changes from the source are indicated: row selection, the derived
register-event label, pseudonymised identity (no name, address, postcode,
provider identifier, Companies House or charity number ships), derived
at-T features, and the temporal partition.
