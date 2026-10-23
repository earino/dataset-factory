# Licence

This is a derived research dataset built from the New Zealand Electricity
Authority's published data. It is **not** the Electricity Authority's official
product, and the Authority has not reviewed or endorsed it.

## The source data - CC BY 4.0 (terms preserved, never relicensed)

The underlying values come from the Electricity Authority (Te Mana Hiko) EMI
datasets "Final energy prices" (Real-time dispatch and pricing) and "Network
supply points table". The Authority's EMI LegalInformation states:

> "Unless indicated otherwise for specific items or collections of content
> (either below or within specific items or collections of content), this
> copyright material is licensed for re-use under the Creative Commons
> Attribution (CC-BY) 4.0 international licence. In essence, you are free to
> copy, store, distribute and adapt the material, as long as you attribute it
> to the Electricity Authority... and abide by the other licence terms."

Restricted-material carve-outs (emblems/trademarks, EMI tools and models,
third-party works, section-46 request responses) do not cover these datasets.
The same CC BY 4.0 statement is carried on the Authority's successor Data &
insights hub, so the announced EMI platform retirement does not change the
licence posture.

**Required attribution, in every copy of the data:**

> www.emi.ea.govt.nz provided by the Electricity Authority (New Zealand) -
> EMI datasets "Final energy prices" (Real-time dispatch and pricing) and
> "Network supply points table". Licensed under CC BY 4.0.

**Suggested citation:**

> Electricity Authority (Te Mana Hiko). EMI dataset: Final energy prices
> (Real-time dispatch and pricing).
> https://www.ea.govt.nz/data-and-insights/datasets/wholesale/dispatch-and-pricing/final-energy-prices/
> Licensed under CC BY 4.0. Derived dataset: NZ wholesale price exceedance
> prediction task (not the Electricity Authority's official product).

**Changes are indicated:** this dataset ships a row selection (island/anchor
days), a derived binary label at a fixed NZD 100/MWh threshold and derived
window features - it is not the Authority's own product, and the source's
attribution and terms carry through to every copy unchanged.

## Our rights in the derived compilation - CC0-1.0

To the extent we hold rights in the derived compilation - the row selection,
the derived label, the feature derivations, the temporal partition and the
packaging - we dedicate them to the public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) (text in
`LICENSE-CC0-1.0.txt`). This dedication covers only our contribution; the
source's CC BY 4.0 terms are unaffected and continue to apply to the
underlying data in every copy.

## Our code and documentation - MIT

The construction, qualification and packaging code and these documents are
MIT-licensed (text in `LICENSE-MIT.txt`). `baseline/train.py`,
`baseline/validate.py` and `baseline/validate.sh` are the harness benchmark's
own runner files, shipped verbatim and unmodified under their MIT terms with
the benchmark project's credits preserved; permission to distribute them covers
these distributed copies only.

## Take-down

This dataset redistributes derived values from a public CC BY 4.0 source with
attribution. If you believe any content here infringes a right you hold,
open an issue on this repository and the content will be reviewed and, if
warranted, removed.
