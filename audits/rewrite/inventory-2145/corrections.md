EVIDENCE CORRECTIONS + new-window accounting split (21:52Z, read-only
from existing records; ordinary repair not interrupted).

CORRECTION 1 - build-6 wording: the build-6 worker stopped BEFORE
qualification (source access failed first: 2018 annual ZIP URL returned
HTML). There is NO qualification verdict for build-6; the earlier
export's "qualification outcome: FAILED" phrasing was wrong. Correct:
source-access failure, artifacts preserved, ordinary bounded repair
consumes the diagnostic.

CORRECTION 2 - development token split by SESSION START boundaries
(sessions table, source=oneshot = factory model tasks; the 6,951,316
figure is CUMULATIVE across BOTH windows):
- Old window (11:07-19:07Z): 66 sessions, 328 calls, 3,259,877 in /
  1,997,961 out = 5,257,838 tokens.
- Gap (19:07-19:58:14Z): 0 sessions, 0 tokens.
- NEW window (>= 19:58:14Z): 15 sessions, 92 calls, 1,228,331 in /
  435,160 out = 1,663,491 tokens.

NEW-WINDOW MODEL TASKS (calls/in/out/elapsed from task usage.json):
UCMR: build-9 2/26,890/26,824/132.5s; evaluate-4 5/82,945/64,485/382.6s;
evaluate-5 6/69,977/61,933/489.2s.
Bridge source-15: build-1 2/7,309/67,027/435.6s; build-2 2/16,159/
21,179/99.3s; build-3 2/18,818/30,402/184.0s; build-4 2/19,805/45,429/
231.5s; build-5 2/15,755/7,720/62.5s; build-6 REUSED (zero calls).
Discovery: bridge discover-1 7/125,168/18,907/198.9s; source-16
(ba904118ba27) discover-1 13/164,725/25,435/(in flight), discover-2
12/104,943/18,810/226.1s, discover-3 13/141,860/12,773/(in flight);
source-17 (f5c98eaf9558) discover-1/2/3 13 calls each
(139,797/218,666/80,437 in; 11,944/9,342/13,140 out; in flight).

NEW-WINDOW WORKERS (job ledger): ucmr build-8 worker 61.0s succeeded
(release 438502804); build-9 worker 63.7s succeeded (438490129);
publish-1 199.0s failed UploadError (438510985); publish-2 119.6s
failed UploadError (438514274); publish-3 143.4s SUCCEEDED
(438522894, release live); bridge build-6 32.8s failed at source
access (438540430).

RETRY REASONS (recorded): bridge build-1/2/3 "Feature descriptions may
only name distinct existing source features" (superseded rule);
build-4 "Model response is not JSON (Expecting ',' delimiter line 1
col 52783)"; build-5 "Model response is not JSON (Expecting value at
line 1, column 1)"; build-6 2018 ZIP URL returned HTML; publish-1/2
UploadError at the Hub step (create_tag keyword-only defect, fixed);
source-16 discover "Model invocation failed" and "Missing source
evidence: attribution"; source-17 discovery retries in flight.
