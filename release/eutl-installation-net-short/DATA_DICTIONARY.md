# Data dictionary

One row per (registry, installation, compliance year t). Target: `net_short`.
Id column: `row_id`. Every shipped quantity is a Union Registry
`operators_yearly_activity` value or a derivation of one; column semantics are the
publisher's own (documented on the Union Registry Public Website data-download page,
fetched by the build), and units are tonnes CO2-equivalent (1 allowance = 1 tCO2e).

## Shipped columns

| Column | Role | Unit | Documented meaning and reference frame | Available at the instant (30 April of year t)? |
|---|---|---|---|---|
| `row_id` | id | composite `registry@installation@year` | Unique per row. Installations recur across split windows by construction of a panel - a declared property, not split leakage (the composite id is unique across all splits). | yes (row identity) |
| `registry_code` | feature | Union Registry country code | The installation's registry (country) identity: EU Member State, EEA-EFTA member, or XI = Northern Ireland electricity. 32 registries measured on the 2026-10-22 snapshot. | yes |
| `period_year` | feature (time column) | calendar year (integer) | Compliance year t, the year whose net-short status is predicted; the split time column. | yes (row identity) |
| `ve_l1` | feature | verified emissions, tCO2e | `VERIFIED_EMISSIONS` of year t-1: reported to the registry by 31 March of year t and settled at the instant. Current-snapshot vintage - the registry can correct entries after the fact and only the current daily extract is available, so values are stated as current-vintage with the cutoff a documented assumption. | yes |
| `alloc_l1` | feature | free allocation, allowances | `ALLOCATION` of year t-1 as recorded in the registry at the instant. | yes |
| `alloc_t` | feature | free allocation, allowances | `ALLOCATION` of year t, fixed in advance by the phase-4 national implementation measures and published before the instant (measured: the extract carries allocation rows through 2030). One side of the label comparison, but fully known at the instant and does not determine the label on its own. | yes |
| `alloc_change` | feature | allowances (difference) | `alloc_t - alloc_l1`: the announced allocation change between the last settled year and the target year. | yes |
| `margin_l1` | feature | allowances (net position) | `ve_l1 - alloc_l1`: the installation's net position at t-1. The persistence analogue the task must beat. | yes |
| `margin_t` | feature | allowances (net position) | `ve_l1 - alloc_t`: last verified emissions against the announced year-t allocation. The natural one-line solver rule (alone: 0.8988 eval rank AUC). | yes |
| `net_short_l1` | feature | binary indicator | 1 iff `ve_l1 > alloc_l1` - the status persistence rule (measured on eligible rows: P(short at t \| short at t-1) = 0.857, P(short at t \| long at t-1) = 0.176). | yes |
| `age_years` | feature | years | (t-1) minus the first year with numeric verified emissions in the extract. Installations operating before 2005 have the age understated by the 2005 left edge - a documented left-truncation property. | yes |
| `installation_key` | carry column | composite `REGISTRY_CODE@INSTALLATION_IDENTIFIER` | The installation identity across years; the event key, because an installation's net-short status is autocorrelated year to year. Declared high-cardinality, not a leak. | yes (identity) |
| `net_short` | target | binary indicator | 1 iff `VERIFIED_EMISSIONS(t) > ALLOCATION(t)`; exact ties are 0 and counted (4,224 measured). | no - the label |

## Excluded by construction (never shipped)

The label source columns and every post-hoc registry field are excluded from all
shipped files, and their absence is asserted in-build against every written header:

- `VERIFIED_EMISSIONS(period t)` and `ALLOCATION(period t)` - the label source.
- `CH_VERIFIED_EMISSIONS(period t)`, `CH_ALLOCATION`, `CH_EXCLUDED` - the registry's
  change-tracking fields for year t, written when year t is corrected (post-hoc).
- `SURR_ALL(period t)` and the other year-t surrender columns - surrender of year t
  happens after the instant.
- `EXCLUDED(period t)` - the registry's year-t exclusion flag, an outcome-period
  property (its t-1 value is the eligibility frame, not a feature; 81 of 204,914
  in-frame rows carry `EXCLUDED(t)=YES`, kept with the mix recorded).
- `SNAPSHOT_DATE` - the extract vintage, not a property of the installation.
- `REGISTRY_NAME`, `INSTALLATION_NAME` - free-text names; identity is carried by
  `registry_code` and `installation_key`.
- `SURR_ALL(t-1)` was probed as a surrender-history feature and **dropped**: missing
  on 10,647 of 188,205 eligible rows (measured), and a partially-defined column cannot
  ship. The verified-emissions and allocation history carry the signal.

## Units and reference frames

Both sides of the label and every emissions/allocation feature are in the same unit
(tonnes CO2-equivalent; 1 allowance = 1 tCO2e), so the comparison `>` is
frame-consistent by construction. The threshold is a row-relative one (each
installation against its own allocation), not an external datum, so no external
reference frame applies; the known-event fixtures (installation 1 sample rows and the
phase-3 allocation cut) are asserted in-build on the shipped rows.

## Timing (prediction instant)

30 April of compliance year t - the surrender deadline that closes year t-1's
compliance cycle. Year t's verified emissions are reported by 31 March of year t+1
and are absent from the registry at the instant (measured: no numeric verified
emissions for years after 2025 in the daily extract). The extract refreshes daily, so
a monthly refresh of this task is honest. See `quality.json`'s `timing` block for the
full declaration.
