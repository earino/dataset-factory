source-15 build-2 saved-repair outcome (2026-11-08T21:00Z; raw
response + usage exported verbatim). Read-only export; no state edits.

Build-2 (rw-b702d47ad634-build-2): 2 calls, 16,159 in / 21,179 out,
tool_results 0, 99.3 s. VALIDATION OUTCOME: FAILED the same rule as
build-1 - "Feature descriptions may only name distinct existing source
features" (factory/construction.py:64). Its quality.task.features now
name the twelve CONCRETE build columns (state_code, deck_rating,
superstructure_rating, substructure_rating, culvert_rating,
channel_rating, lowest_component_rating, year_built, bridge_age_years,
months_since_inspection, numeric_component_count, culvert_applicable) -
none of which are the canonical TASK feature names (component_ratings,
material_and_design, age, size, traffic_exposure, network_role,
load_capacity, geometry, deck_system, waterway_and_scour, ownership,
inspection_cycle).

REPAIR-LOOP HAZARD FLAG for the operator: two consecutive attempts
(build-1 named 5 canonical + 1 invented; build-2 renamed all 12 to
concrete columns) have now failed the same prose rule from opposite
directions. The rule requires descriptions to name the task's declared
features; the model instead describes the columns it actually builds.
Without either (a) the construction prompt stating the exact canonical
names descriptions must use, or (b) an explicit versioned task-feature
change, build-3 risks the third identical burn. Paid build-2 output
retained on disk and here; tick ordering keeps publication first, so
no build-3 launches before the UCMR release completes.
