# v2026.10 - Australian short-term visitor arrivals, next-month direction

First release. 19,071 train / 4,140 eval / 3,920 holdout rows over 70 residence series.

The task asks a direction question at the moment the ABS publishes month M: will arrivals in the
unpublished month M+1 fall below the same month last year? Persistence is anti-correlated (0.3647),
so the task rewards mean-reversion and seasonal reasoning; the runner-contract baseline reaches
0.6219 and clears the calendar-only rule (0.5501) by 0.0718.

The pandemic window is excluded rather than allowed to dominate, and the exclusion is counted. The
holdout is labelled and ships by design.
