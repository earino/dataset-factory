# v2026.10 - Malaysian retail price increases, week ahead

First release. State-scoped to Johor: 397,982 train / 280,468 eval / 154,279 holdout rows.

The task is a week-ahead direction call on the modal retail price of an item at a premise, built
from Malaysia's daily PriceCatcher panel. Eligibility requires three observations in week W; pairs
whose following week is too sparse are counted as unobserved outcomes rather than dropped silently.

Baseline 0.7520 eval AUC against a 17.5% positive rate, clearing the strongest naive reference
(item prior, 0.5354) by more than twenty points. The holdout is labelled and ships by design.
