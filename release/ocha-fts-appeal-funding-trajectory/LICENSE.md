# Licence - ocha-fts-appeal-funding-trajectory

This is a **derived research dataset**, not an OCHA or FTS product. OCHA and the
Financial Tracking Service have not reviewed or endorsed it.

## Three grants, three scopes

| Scope | Licence | File |
| --- | --- | --- |
| Our code and documentation (construction, qualification, packaging, docs) | MIT | `LICENSE-MIT.txt` |
| Our rights in the derived compilation (row selection, counted exclusions, derived label, appeal-recency feature, temporal partition, packaging) | CC0-1.0 | `LICENSE-CC0-1.0.txt` |
| The source data (FTS/HPC records; HDX bulk CSV) | **Preserved, never relicensed**: FTS use-and-republish terms + CC BY-IGO (HDX record) | see below |

The CC0 dedication covers **only our contribution**. The underlying source data
keeps its own terms, which carry through unchanged to every copy of the derived
data. CC0 is not presented as the source's licence.

## The source's terms

1. **FTS use-and-republish terms** ("About FTS / Using FTS data",
   https://fts.unocha.org/content/about-fts-using-fts-data, read 2026-10-29):
   FTS permits use and republication of data published on the FTS website/API,
   including amended and derived data, with a citation request. For data that is
   amended or combined, FTS suggests citing your organisation as the author,
   "based on Financial Tracking Service (FTS) data, [DATE], [URL]".
2. **CC BY-IGO** (HDX record for "Global - Requirements and Funding Data",
   https://data.humdata.org/dataset/global-requirements-and-funding-data, read
   2026-10-29): Creative Commons Attribution for Intergovernmental
   Organisations - reproduction, distribution and derivative works permitted
   with attribution; the no-endorsement condition carries through.

## Required attribution (carry into every copy)

> Derived dataset based on Financial Tracking Service (FTS) data, OCHA HPC API
> records harvested 2026-10-30 and the HDX "Global - Requirements and Funding
> Data" bulk CSV (downloaded 2026-10-29),
> https://fts.unocha.org and
> https://data.humdata.org/dataset/global-requirements-and-funding-data .
> Contains OCHA Financial Tracking Service data licensed under CC BY-IGO.
> Not an OCHA or FTS product.

## Suggested citation

> United Nations OCHA. Financial Tracking Service: Global Requirements and
> Funding Data (HDX bulk distribution, downloaded 2026-10-29) and HPC API
> plan/flow records (harvested 2026-10-30). https://fts.unocha.org . CC BY-IGO.
> Derived dataset: humanitarian-appeal funding-trajectory prediction task
> (not an OCHA product).

## Changes from the source (indicated, per CC BY-IGO)

Row selection (single-country appeals with positive launch asks, plan years
2000-2025); counted exclusions (multi-country regional groups, no-orig groups,
pre-window and live-edge unobserved targets); a derived binary label (year-end
funding >= 50% of launch-vintage original requirements); an appeal-recency
feature reading only prior appeal YEARS; a launch-instant temporal partition;
packaging and documentation. No funding value ships in the data files.

## Third-party files

`baseline/train.py`, `baseline/validate.py` and `baseline/validate.sh` are the
harness benchmark's own runner files, MIT-licensed by that project, shipped
verbatim and unmodified; permission to distribute verbatim copies covers the
distributed copies only.

## Takedown

If you are the rights holder and believe any content here is used outside its
terms, open an issue in this repository's tracker and it will be removed or
corrected.
