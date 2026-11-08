source-000012 discover-2 non-JSON diagnosis (2026-11-08 16:41Z, read-only).
The retained 16,313-byte stdout is the COMPLETE, substantively valid
discovery JSON wrapped in markdown code fences: it begins with a ``` line,
then the full {"verdict": "ready", ...} object (CMS Provider Data Catalog
nursing-home inspections), then a closing ``` line. The parse error
"Expecting value at line 1, column 1" is caused solely by the leading fence
line. Not incomplete, not substantively invalid - an ordinary wrapper
problem. The retry (discover-3) re-researched the identical source and
succeeded without the fence (16,305 bytes), advancing the candidate; the
fenced attempt wasted 11 calls / 149,751 in / 28,609 out (304.4 s). A
strip-fences pre-parse would have saved the duplicate research.

Snapshot at export: deployed head e2441dfbf39a277e10d08bd9819f9bfeedf1c8d0
(e520032 on main is evidence/docs only - not deployed, no pause). Queue:
sources 1-4,6,9 deferred at limits; 5,7,8,10 rejected on terms merits;
source-11 (RCRA) at build with its repair worker running; source-12 at
build after the successful CMS discovery. Worker budget: 81 reservations,
EUR 9.98 of 20.00 (EUR 10.02 remaining).
