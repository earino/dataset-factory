# Terms for this dataset

This package contains two things under two sets of terms.

## 1. The data (our derived compilation)

The source is WHO FluNet. WHO issues its materials under the **Creative Commons
Attribution-NonCommercial-ShareAlike 3.0 Intergovernmental Organization (CC BY-NC-SA 3.0 IGO)**
licence. Because the source is NonCommercial and ShareAlike, no separate dedication (and in
particular no CC0 dedication) is made over the derived compilation: it is distributed under the
same CC BY-NC-SA 3.0 IGO terms, and those terms carry through unchanged.

You may copy, reproduce, distribute, translate and adapt this derived data for **non-commercial**
purposes, provided that:

- **Attribution** - WHO is acknowledged as the source, with the licence named:
  > World Health Organization. FluNet. Geneva: World Health Organization; 2026.
  > Licence: CC BY-NC-SA 3.0 IGO.
- **NonCommercial** - you do not use the material for commercial purposes.
- **ShareAlike** - if you remix, transform or build upon the material, you distribute your
  contributions under the same licence as the original.
- **No endorsement** - you do not use the WHO name or emblem, and nothing implies that WHO
  endorses this dataset. It is not an official WHO product.

Licence text: <https://creativecommons.org/licenses/by-nc-sa/3.0/igo/>. The WHO copyright policy
that states this posture is <https://www.who.int/about/policies/publishing/copyright>.

Our contribution - row selection, the derived binary label, the temporal partition, the gating
rules and the packaging - is distributed under the same terms. Nothing in this release grants a
commercial right or an irrevocable redistribution right beyond the source's own licence.

## 2. The code

`code/`, `baseline/train.py` (unchanged benchmark runner), `get_dataset.py`, `baseline/*.sh` and
the scripts we wrote are MIT licensed: see `LICENSE-MIT.txt`. The runner files under
`baseline/` are shipped verbatim from the harness benchmark with the same MIT terms.

## 3. What this is not

This is a derived research dataset. It is not an official WHO publication, has not been reviewed
by WHO, and must not be presented as WHO's own data product. The label is ours: WHO publishes
laboratory counts, not this exceedance target.