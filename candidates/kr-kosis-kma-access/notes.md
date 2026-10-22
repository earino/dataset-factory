# kr-kosis-kma-access

**Verdict: park (2026-10-22) - access walls; licences are clean.**

## Probe evidence (2026-10-22; commands in probe_kr_access.py)

| Probe | Result |
|---|---|
| GET kosis.kr/openapi/ | 200; primary actions: OPEN API 인증키 신청, 활용신청, 회원가입 -> personal key required |
| KOSIS 이용지침 (serviceInfo/useGuide.do) | redistribution allowed (commercial + non-commercial) with 출처명시; international/NK stats excluded |
| GET data.kma.go.kr (3 paths) | JS shell, 1,872 bytes each |
| KMA membership guide PDF (their own doc) | 회원가입 collects e-mail, name, phone number; licence = 출처 표시 ('기상청 제공') |
| data.go.kr | robots noindex/nofollow; also membership-gated for most datasets |

## Decision

No task probing beyond the access triage - the standing preference is anonymous,
documented APIs, and a scheduled session cannot create personal accounts. The unpark
condition is explicit: an operator-registered KOSIS key stored under /opt/data/.secrets.
