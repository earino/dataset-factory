# License

## Our code and documentation: MIT

See `LICENSE-MIT.txt`. Construction, packaging and reproduction code in `code/`,
`baseline/` and `get_dataset.py` are Copyright (c) 2026 E. Arino de la Rubia (earino).

`baseline/train.py`, `baseline/validate.py` and `baseline/validate.sh` are the harness
benchmark's own runner files, shipped verbatim and unmodified under their MIT terms;
permission to distribute verbatim copies covers the distributed copies only.

## Our rights in the derived compilation: CC0-1.0

See `LICENSE-CC0-1.0.txt`. Our contribution - the installation-year row selection and
eligibility frame, the derived net-short label, the settlement-lagged feature
derivations, the temporal partition, and the packaging - is dedicated to the public
domain. The dedication covers **only our contribution**.

## The source data: CC BY 4.0 - European Commission reuse policy (preserved)

The underlying data are European Commission (DG CLIMA) Union Registry public extracts
(EUTL), published on the
[Union Registry Public Website](https://union-registry-data.ec.europa.eu/report/eu-registry-data-download).
The Commission's
[legal notice](https://commission.europa.eu/legal-notice_en) states its reuse policy:
"Unless otherwise indicated (e.g. in individual copyright notices), content owned by the
EU on this website is licensed under the Creative Commons Attribution 4.0 International
(CC BY 4.0) licence. This means that reuse is allowed, provided appropriate credit is
given and changes are indicated." The EEA's own metadata for its Union Registry-derived
EU ETS product independently states "License CC-BY 4.0", copyright holder "European
Commission, European Environment Agency (EEA)". CC BY 4.0 permits sharing and adapting
the material for any purpose, commercially, **with attribution and indication of
changes**. Those conditions carry through unchanged to every copy of this derived dataset:

> Source: European Commission, Directorate-General for Climate Action - Union Registry
> public extracts (EUTL), operators_yearly_activity daily extract
> (https://union-registry-data.ec.europa.eu/report/eu-registry-data-download), vintage of
> 2026-10-22. Contains Commission-owned content licensed under CC BY 4.0.

Changes from the source are indicated: this dataset ships a row selection
(in-frame installation-years with a numeric t-1 year), a derived binary label
(`net_short`) and derived features - not the Commission's own product.

Suggested citation for the derived dataset: *European Commission, Directorate-General
for Climate Action. Union Registry Public Website, EUTL public extracts: operators' yearly
activity data (daily extract), vintage of 2026-10-22. Licensed under CC BY 4.0
(Commission reuse policy). Derived dataset: EU ETS installation net-short prediction
task (not a Commission official product).*

This dataset is **derived** and is not the European Commission's official product; the
Commission has not reviewed or endorsed it, and nothing here may imply endorsement. The
publisher's own designation, attribution and suggested citation are preserved verbatim.
CC0 is not a blanket override of upstream terms: the CC BY 4.0 attribution and
indicate-changes conditions apply to every copy of the data regardless of our dedication
of the compilation.
