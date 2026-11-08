source-000015 (National Bridge Inventory) build-1 evidence export,
2026-11-08T20:47Z. Read-only; no state edits, no extra model calls.

Title: "Will a Fair-condition U.S. highway bridge be rated Poor at its
next routine inspection? Forward condition deterioration from the
National Bridge Inventory."

DIAGNOSIS: source-feature NAMING MISMATCH, not an actual changed
feature. The canonical task features (12 names, identical between the
discovery proposal and the canonical source record) are:
component_ratings, material_and_design, age, size, traffic_exposure,
network_role, load_capacity, geometry, deck_system, waterway_and_scour,
ownership, inspection_cycle.

The saved build-1 construction (2 calls, 7,309 in / 67,027 out, 0 tools,
435.6 s) wrote quality.task.features descriptions naming only:
component_ratings, rating_applicability, age, inspection_cycle,
ownership. "rating_applicability" is NOT a declared task feature - it
is the single name that trips factory/construction.py:64 ("Feature
descriptions may only name distinct existing source features"; the rule
at lines 56-71 requires each clarified description to name a distinct
feature from the task's declared list). Eight declared features
(material_and_design, size, traffic_exposure, network_role,
load_capacity, geometry, deck_system, waterway_and_scour) lack
descriptions - not itself a rule failure, but incomplete coverage.

No underlying source feature changed. The concrete build columns the
model used (state_code, deck_rating, superstructure_rating,
substructure_rating, culvert_rating, channel_rating,
lowest_component_rating, year_built, bridge_age_years,
months_since_inspection, numeric_component_count, culvert_applicable)
all derive from declared task features. Existing bounded repair can
resolve it by rewriting descriptions against the canonical 12 names
(rating_applicability folded into component_ratings or added via the
explicit versioned task-change path). Paid proposal preserved; raw
discovery + construction + usage exported here.
