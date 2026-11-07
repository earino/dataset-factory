# PlanSA endpoint recipes (measured 2026-11-07; reproduces notes.md s6)
#
# plan.sa.gov.au and cdn.plan.sa.gov.au answer 403 to plain curl. Every recipe
# below must run from the supported browser's page context (browser_exec), as
# the page's own JS does. The payloads replicate public-register.min.js v0.15.5
# exactly (getSearchtoCSV / getSearchResults / getSingleResult); btoa them in
# the page, never in transit.
#
# 1) CSV export (GET) - columns: Unique ID, Development No, coarse Application
#    Status, Address, Description, Lodged (m/d/yyyy), Register Code.
#    NO decision date, NO outcome. Dates are m/d/yyyy (21/06/2021 returns 0
#    bytes). Truncates NON-DETERMINISTICALLY above ~789,151 bytes: use month-
#    scale windows and reconcile counts against the search TotalRecords.
#
#    const p = {ActionType:"csv", Config:"public_register",
#      DataObject:"PublicRegisterCSV",
#      Params:[{name:"Status",value:"Decision Made"},
#              {name:"LodgedDateStart",value:"09/01/2021"},   // m/d/yyyy
#              {name:"LodgedDateEnd",value:"09/30/2021"}],
#      SortExpression:"LodgedNew", RecordNumber:0};
#    const url = "https://plan.sa.gov.au/development_application_register/"
#      + "assets/daregisterCSV?payload=" + btoa(JSON.stringify(p));
#
# 2) Search (POST https://cdn.plan.sa.gov.au/prs/fFGE56_reg8R) - the response
#    Count field is unreliable; the authoritative total is the row's
#    TotalRecords column (field index from Fields.Fields[].FieldCode).
#
#    const l = {ActionType:"select", Config:"public_register",
#      DataObject:"PublicRegisterSearch",
#      Params:[...filters, {name:"Page",value:"1"}, {name:"PageSize",value:"1"}],
#      SortDirection:"", SortExpression:"LodgedNew", RecordNumber:0, MaxRecords:1};
#    // Status accepts ONLY the coarse five: Under Assessment / Decision Made /
#    // Lapsed / Withdrawn / Cancelled (Refused/Granted return no rows).
#
# 3) Per-application detail (POST same endpoint) - DecisionDetails child carries
#    per-consent [CT=decision type, DRT=decision, DD=decision date].
#    DataObject by the row's Register Code: DAP->DAPRegisterDetail,
#    LUA/LUC->LandUseRegisterDetail, LDE->LandDivisionRegisterDetail,
#    MD->MajorDevelopmentRegisterDetail; Base = the register code.
#
#    const l = {ActionType:"select", Config:"public_register",
#      DataObject:"DAPRegisterDetail",
#      Params:[{name:"AppId",value:"21001010"}, {name:"Base",value:"DAP"}],
#      SortDirection:"", SortCode:"desc", RecordNumber:1, MaxRecords:1};
#
#    KNOWN HAZARD (measured 2026-11-07): after ~100 detail POSTs the endpoint
#    starts returning hollow children (children present, FieldValues empty),
#    including for previously-verified IDs. Pace >= 1.5 s, re-fetch on hollow
#    reads, never read an empty DecisionDetails as "no decision". Verified
#    good read: app 6154 LUA -> "Development Approval / Granted / 30 Apr 2021".
#
# Environment notes: the browser harness recycles tabs every few minutes - do
# not rely on window.* background jobs; run foreground batches that fit the
# daemon's 5 s evaluation timeout (<= 6-7 detail POSTs per call), or poll small
# incremental background jobs early and often.
