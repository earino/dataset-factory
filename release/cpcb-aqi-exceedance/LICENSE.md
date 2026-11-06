# Licensing

Three grants with three scopes. Nothing here relicenses anyone else's data.

## Our code and documentation: MIT

See `LICENSE-MIT.txt`. Covers the construction, qualification, references
and helper scripts and this documentation. The `baseline/` runner files
(train.py, validate.py, validate.sh) are the harness benchmark's own MIT
files, shipped verbatim and unmodified at the sha256 recorded in
`measurements.json`.

## Our rights in the derived compilation: CC0-1.0

See `LICENSE-CC0-1.0.txt`. The dedication covers **our contribution only**:
the station-day eligibility frame, the derived binary next-day exceedance
label at the publisher's own band edge, the at-instant trailing-history
features, the UNKNOWN_STATE sentinel, the excluded-and-counted accounting,
and the temporal partition. It does not cover the source measurements.

## The sources' own terms, preserved

Two preserved upstream instruments, neither relicensed. CPCB CAAQM PM2.5 measurements: Government Open Data License - India (GODL-India v1.0) via the data.gov.in platform instrument, with its attribution template, non-endorsement, no-warranty and continuity conditions. The XKDR Forum Air-Quality-Database compilation carrying those measurements: Creative Commons Attribution 4.0, with the README's own requested credit. The redistributed fields are the publisher's own station identifiers, timestamps and hourly PM2.5 measurements (aggregated by us to daily statistics) plus our derived label, features and partition. The derived dataset is labelled as such throughout and is neither a CPCB product nor an XKDR Forum product.

Attribution (carries in every copy):

> Source: Central Pollution Control Board (CAAQM network) via the India Air Quality Database, XKDR Forum (data.xkdr.org), licensed under the Government Open Data License - India (CPCB measurements) and CC BY 4.0 (XKDR compilation). Credit: India Air Quality Database, XKDR Forum; Central Pollution Control Board (CAAQM network); US Department of State via AirNow. Export accessed 2026-09-30 (pinned; construction verifies exported_at and row count).

Suggested citation:

> Central Pollution Control Board. Real Time Air Quality Index from Various Locations (CAAQM network). Government Open Data License - India, via data.gov.in. Republished as India Air Quality Database by XKDR Forum (CC BY 4.0), data.xkdr.org. Derived dataset: India CPCB station-day next-day PM2.5 exceedance prediction task (not a CPCB or XKDR Forum product).

Conditions that carry through unchanged: the requested credits above;
GODL-India's non-endorsement condition (this is a derived research dataset,
not a CPCB, Government of India, or XKDR Forum product); and the XKDR
compilation's own data-quality caveat (values "as reported", "no gap
filling", "preliminary and not fully validated"). The full evidence trail
for both licence readings is recorded in the candidate's
`license_evidence` and reproduced in `LICENSE.md`'s generating source
(`candidates/cpcb-aqi-exceedance/license.json`).
