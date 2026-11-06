# PlanSA register browser-probe recipe (reproduces notes.md s2, 2026-11-06)

plan.sa.gov.au answers 403 to plain curl. Every step below runs in the
supported browser session (browser_exec). Re-running this file's steps
reproduces the measurements in notes.md; nothing downloads bulk data.

1. Open the register:
   goto https://plan.sa.gov.au/development_application_register
   - Footer licence line: "This work is licensed under a Creative Commons
     Attribution 3.0 Australia Licence" (this is the licence instrument).
2. Click `a[href="#showall"]` ("Search all applications"), wait ~6 s.
   Read the count: body text "We've found N development applications".
   (Observed 2026-11-06: N = 299,858; rows include same-day-old lodgements,
   so the register is current through yesterday.)
3. Status counts: set `select[name="Status"]` to one of
   Under Assessment / Decision Made / Lapsed / Withdrawn / Cancelled,
   then `closest('form').requestSubmit()`; wait 3-8 s; read the count.
   (Observed: 27,083 / 260,174 / 338 / 10,538 / 1,725.)
4. Date-window count: set `input[name="LodgedDateStart"]` / `LodgedDateEnd`
   (dd/mm/yyyy) and Status='' (empty option value is "" for All), submit,
   wait 30-90 s and verify the form echoes the window before trusting the
   count. Direct GET with only date params renders the landing page - the
   search must go through the form. (Observed 2026: 17,733.)
5. Detail view: click the first row's anchor `a[href^="#view-"]`
   (rows are tr[data-index] with data-action="#view-<ID>-DAP"). Wait ~8 s.
   Tabs: Overview / Assessment / Documents / Building Information.
   Application summary carries: Application ID, Lodged, Application number,
   Applicants, Assessment Pathway, Elements, Council area, Title/parcel,
   Public Notification. The Assessment tab carries per-consent decisions
   (e.g. "Development Approval - Planning, Building - Granted").
6. Status vocabulary + CSV recipe: fetch
   https://plan.sa.gov.au/__data/assets/js_file_folder/0019/607321/public-register.min.js?v=0.15.5
   from page context and read `PRstatusObj` (all statuses and their
   publisher-written descriptions) and the `daregisterCSV` payload builder
   (ActionType "csv", Config "public_register", DataObject
   "PublicRegisterCSV", Params = serialized form fields minus
   SortBy/perpage/resultspagenumb/givehoney/ActionType, btoa'd into the
   query string).

Known-failure notes (do not re-derive):
- Synthetic payload fetch to the CSV endpoint from page context:
  "TypeError: Failed to fetch" - the page's own click handler builds the
  request; replicate it exactly (encoding/padding unverified) or use the
  click path.
- tr[data-id] does not exist on form-submitted result sets; use the
  `a[href^="#view-"]` anchors inside tr[data-index] rows.
- Rows render after the count text on form-submitted searches; wait for the
  anchors before reading.
