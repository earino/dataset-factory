# Data dictionary transcript - Alberta historical wildfire data 2006-2025

Verbatim field definitions transcribed 2026-11-06 from the publisher's data
dictionary PDF (fp-historical-wildfire-data-dictionary-2006-2025.pdf,
sha256 bfff81c0d0e4b5cb0684180a53ddab4da54ddb5dd63f0c0f9497fa67f2334cdf,
16 pages, no text layer - rendered at 150 dpi and read visually; pages cited).
Only fields used by, or excluded from, the task are transcribed. The
numbering is the dictionary's own.

## Fields documenting the prediction instant (assessment)

**24. assessment_datetime** (p11)
"The date and time the wildfire was originally assessed by Alberta Wildfire
employees."
Related (#23 assessment_resource, p11): "the name (first and last) of the
Alberta Wildfire person who first assessed the wildfire. This assessment could
be a quick assessment or the full assessment on the FP41." (In the published
CSV this column carries 5 position categories - IA Forces / AAO / Wildfire
Assessor / Other / blank - not names; measured, see notes.md.)

**25. assessment_hectares** (p12)
"The size of the wildfire at the time of assessment is recorded to the nearest
hectare or hundredth (0.01) of a hectare."

**26. fire_spread_rate** (p12)
"The rate of spread of the wildfire at the time of initial assessment, capture
in metres per minute."

**27. fire_type** (p12)
"This is the predominant fire behaviour that was observed when the fire was
originally assessed." (Ground Fire / Surface Fire / Crown Fire.)

**28. fire_position_on_slope** (p12)
"The position of the wildfire relative to the slope it is travelling on at the
time of initial assessment." (Bottom Flat / Lower 1/3 / Middle 1/3 / Upper 1/3.)

**29. weather_conditions_over_fire** (p12)
"Description of the weather conditions over the wildfire at the time of initial
assessment." (CB dry / CB wet / Clear / Cloudy / Rain showers.)

**30. temperature** (p12)
"The temperature at the wildfire site at the time of initial assessment,
captured in degrees Celsius."

**31. relative_humidity** (p12)
"The relative humidity at the wildfire site at the time of initial assessment."

**32. wind_direction** (p12)
"The wind direction at the wildfire site at the time of initial assessment."

**33. wind_speed** (p12)
"The wind speed at the wildfire site at the time of initial assessment,
captured in kilometers per hour."

**34. fuel_type** (p12)
"The predominant fuel type (vegetation cover) in which the wildfire is burning,
at the time of initial assessment." (Canadian FBP codes: C-1/C-2/C-3/C-4,
M-1/M-2, D-1, O-1a/O-1b, S-1/S-2, Grass, Mixed wood, Other.)

**6/7. latitude / longitude** (p6)
"Location of the ignition area of the wildfire recorded as a GPS (recorded as
decimal degrees (DD). The location is originally captured during the assessment
but may be further investigated as the wildfire progresses. The final location
is the confirmed ignition area of the wildfire."

## Fields available before the instant

**14. fire_start_date** (p10)
"The time and date the wildfire started. If the exact time and date is
unknown, an estimate is made of the wildfire start time. Actual start time can
be obtained by storm tracking, a witness or statement from the responsible
party. Start time for lightning-caused wildfires can be estimated from
lightning map data."

**15/16. det_agent_type / det_agent** (p10)
"The general type of detection agent responsible for discovering the wildfire."
(LKT lookout / AIR air patrol / GRP ground patrol / UNP unplanned / CAM
camera) and the specific agent.

**17. discovered_date** (p10)
"The time the detection agent first discovered the wildfire."

**18. discovered_size** (p11)
"The size of wildfire when first discovered by the detection agent." (Filled
0.5% - "mandatory for all detection agents except unplanned, and therefore may
be blank on those wildfires.")

**19. reported_date** (p11)
"The time and date the wildfire was first reported to Alberta Wildfire. This
is generally the time the discovery agent calls the Alberta Wildfire Area
dispatch. The report time can be the same as the discovery time."

**20-22. dispatched_resource / dispatch_date / start_for_fire_date** (p11)
"The first Alberta Wildfire resource that started for the wildfire." /
"The date and time the first Alberta Wildfire resource was dispatched" /
"The time and date that the first Alberta Wildfire resource started for the
wildfire." (Measured: dispatch_date is after assessment_datetime for 670/27,813
fires (2.4%) - excluded from the feature set rather than shipped on mixed
ordering evidence.)

## Label source fields (post-instant; never shipped as features)

**4. current_size** (p6)
"This is the final area burned of the wildfire. This size will not necessarily
match the sizes from the fire status fields. If an updated size is determined
after a wildfire has already been extinguished, the revised size is recorded in
the Area Burned field of FIRES and the extinguished size recorded on the fire
status line will not change. Wildfires that have had aerial photography flown
will generally not have the area burned updated until the following spring when
the interpretation is complete. This interpretation includes removal of
waterbodies, unburnt islands and man-made infrastructure."

**5. size_class** (p6)
"This is a grouping of wildfires into classes based on final area burned. Size
class can change as the wildfire grows until the final area burned is
determined after extinguishment." A >= 0 to 0.1 ha; B > 0.1 to 4.0; C > 4.0 to
40.0; D > 40.0 to 200; E > 200.

**43/44. first_bh_date / first_bh_size** (p14)
"The date and time the Incident Commander (IC) determined the wildfire to be at
the fire status of being held (BH). A wildfire is being held when it is not
expected to grow beyond its existing boundaries, given current weather
conditions and resources. A wildfire is not required to have a being held
status..."

**45/46. first_uc_date / first_uc_size** (p14)
"The date and time the Incident Commander determined the wildfire to be at the
fire status of under control (UC). A wildfire is under control when it has
received sufficient suppression action to ensure no further spread." / size at
that status change.

**47/48. first_to_date / first_to_size** (p14/15)
Turned-over status: "responsibility for the extinguishment of the wildfire has
been returned to another agency or individual."

**49/50. first_ex_date / first_ex_size_perimeter** (p15)
"This is the date and time the Incident Commander determined the wildfire to be
completely extinguished (EX)."

## Fields excluded as post-hoc (cause investigation)

**9. general_cause** (p7)
"Classification of the wildfire cause according to the general group,
individual industry, or ignition source (for lightning) that started the
wildfire. For wildfires that are currently being investigated, the temporary
general cause of 'under investigation' is used." Values include Lightning,
Resident, Recreation, Incendiary, Power Line Industry, Oil and Gas Industry,
Forest Industry, Agriculture Industry, Railroad, Government, Other Industry,
Prescribed Fire (2012-2016), Restart (until 2012), Undetermined ("a wildfire
that has been investigated but the cause cannot be determined. Upon further
evidence or new information, the final cause may be determined and this cause
may be updated").

**13. true_cause** (p9)
"Identifies the specific reason why the wildfire started." (Post-investigation;
52.5% filled in the CSV vs 100% for general_cause.)

**10-12. industry_identifier / responsible_group / activity_class**
Cause-adjacent classification fields of the same investigation (measured
mixes in notes.md; excluded with the cause family).
