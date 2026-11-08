Hermes output-redaction false positive corrupts benign dataset field names
(2026-11-08, source-000009 build-2 evidence, per operator request; no
credentials exported, no redaction disabled, no model probes).

1. GROUND TRUTH COMPARISON: the stored session assistant message
(local-b9ea0db93867151147581546..., 27,962 chars) and the adapter-captured
quiet stdout (response.txt, 27,962 chars) are BYTE-IDENTICAL, and BOTH
already contain "PWS_TYPE_CODE=***". The stored assistant line is NOT
intact - redaction is applied to assistant content BEFORE storage, so
state.db cannot distinguish and the original is unrecoverable.

2. THE REDACTION BOUNDARY (installed code, hash-bound): agent/chat_completion_helpers.py
lines 1580-1586 - assistant message content is passed through
redact_sensitive_text(content) (no code_file flag, obeys security.redact_secrets).

3. THE TRIGGER (agent/redact.py:249-250):
   _SECRET_ENV_NAMES = r"(?:API_?KEY|KEY|TOKEN|SECRET|PASSWORD|PASSWD|PASS|PW|CREDENTIAL|AUTH)"
   _ENV_ASSIGN_RE  = r"([A-Z0-9_]{0,50}<secretname>[A-Z0-9_]{0,50})\s*=\s*(['\"]?)(\S+)\2"
PWS_TYPE_CODE (Public Water System) matches the bare PW suffix at a word
boundary; the greedy (\S+) with the quote backreference swallows the value's
CLOSING QUOTE, so the mask leaves an unquoted *** inside the Python string
literal -> "unterminated string literal" SyntaxError at line 166 col 63.

4. DETERMINISTIC REPRODUCTION on the installed code (pure local function
call, no model, no config change):
   redact_sensitive_text("PWS_TYPE_CODE='CWS'")  -> "PWS_TYPE_CODE='***'"
   redact_sensitive_text("PWS_TYPE_CODE=\"CWS\"") -> 'PWS_TYPE_CODE="***"'
   redact_sensitive_text("pws_type_code == 'CWS'") -> unchanged
   re.search(_SECRET_ENV_NAMES, "PWS_TYPE_CODE") -> True
The same false positive appears twice in the stored response (build_py line
166 and construction_notes), consistent with redaction, not model shorthand.

5. IMPLICATION: every construction/review response whose code or prose
contains an uppercase NAME=value assignment whose name merely CONTAINS
PW/KEY/PASS/TOKEN/AUTH/SECRET (e.g. PWS_TYPE_CODE) is silently corrupted
BEFORE the adapter parses it. The runtime already ships the scoped
mechanism - redact_sensitive_text(..., code_file=True) skips the ENV/JSON
assignment passes for source code (used for file reads) - but the
assistant-content boundary does not pass it. Fix scoping is the owner's
call; no global disable performed. Source-9's parse failure is fully
explained by this mechanism.
