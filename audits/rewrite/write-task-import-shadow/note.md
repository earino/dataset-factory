Write-task adapter import crash (61b7da/05fab28 runtime, 2026-11-08 ~14:4xZ).
Both zero-tool construction tasks (source-000006 rw-69fd63106b72-build-3 and
source-000004 rw-17b5d37bd413-build-6) failed identically at IMPORT time,
zero model sessions, zero tokens: the child traceback ends
"ModuleNotFoundError: No module named 'http.client'; 'http' is not a package".
Demonstrated cause: factory/hermes_write_task.py runs as a script, so
sys.path[0] is /opt/data/dataset-factory/factory/, and the repo's own
factory/http.py (3,543 B) shadows the stdlib http package deep inside the
Hermes CLI import chain (cli.py:35 -> cli_commands_mixin -> ... ->
http.server -> urllib.request -> import http.client). The adapter's
sys.path.insert(0, hermes_root) does not help: /opt/hermes has no http
module, so resolution falls through to the script dir and finds the repo
module. Verified read-only: with /opt/hermes first, http resolves to the
real stdlib package; the factory/ script-dir entry is what shadows.
Candidate fix paths (owner's call): run the adapter with python3 -m
factory.hermes_write_task from the repo root (package-mode sys.path), or
drop the script dir from sys.path in the adapter before importing cli, or
rename the shadowing module. Both candidates exhausted their 3-attempt
startup-failure allowance on this crash and are deferred; no inference was
spent; no state was reset.
