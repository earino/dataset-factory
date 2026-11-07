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

## Seoul Open Data Plaza probe (2026-11-04, East Asia tick)

Different publisher from the two national portals above; all anonymous, commands retained in
probe_kr_seoul_2026_11_04.py (this dir), full text in
record.measurements.seoul_portal_probe_2026_11_04.

| Probe | Result |
|---|---|
| GET data.seoul.go.kr/ | HTTP 200, server-rendered (99,650 B) - anonymous browsing works |
| GET /dataList/OA-23105/S/1/datasetView.do | HTTP 200, 75,723 B; full metadata block server-rendered |
| Licence instrument (on the dataset's own page) | 이용허락범위: "공공누리 0유형 : 자유이용 (출처미표기)" (Public Nuri Type 0: free use, attribution NOT required) and "이용제한없음 : 자유이용" - class A equivalent; copyright holder 서울특별시, third-party rights 없음. Re-read per dataset when one is taken forward. |
| Catalog list (datasetList.do, datasetSearchList.do) | AJAX shell to plain clients: 83,378 B with 0 datasetView links (a variant render carried homepage recommendation links only); enumeration needs the supported browser |
| File download (nio_download.do POST infId/infSeq/seq) | JS-mediated; naive parameterised POST (with Referer+cookie) rejected: alert "잘못된 접근입니다. 파일 목록에서 다시 선택하세요" (one changed retry, same result) - bulk download goes through the browser; on-page sheet preview exposes <=1,000 rows; Open API needs an 인증키 |

Access consequence: Korea file data is NOT uniformly account-walled - the KOSIS/KMA park
stands, but a Seoul candidate needs no operator credential. The remaining gate for a Seoul
candidate is task-family crowding (see record.next_action): the catalog must be enumerated
for an event-grain register outside the bench's existing families before any candidate opens.

## Seoul catalog browser sweep (2026-11-04, same tick)

Supported browser (plain GET is a shell). Catalog: 6,537 public-data datasets. Keyword
sweeps measured on-page:

| Search | Result |
|---|---|
| 출동 (dispatch) | 9 results; FILE items are AGGREGATE monthly dispatch counts per 법정동 (구조/구급/화재 출동 현황) - aggregate-series family, operator decision; no per-incident dispatch register |
| 행정처분 (dispositions) | 122 results; strongest event-grain find: OA-23122 식품행정처분 (FSI food administrative dispositions) - per-business register, 18 documented columns incl. 처분유형/처분확정일/처분종료일/위반법령/위반내용, DAILY refresh, licence field "이용허락범위 제한 없음", preview rows carry 경기도 addresses (national coverage); bulk CSV/JSON download offered but not fetched on the coordinator |
| newest-items browse | aggregate monthly series and family-mapped registers |

OA-23122 is an enforcement/inspection-outcome family member (chicago-food-inspections,
msha citations published; cqc packaged) - opening it needs the operator family decision
(air4thai/hk-datagov-portal precedent). Recorded as option (a) in record.next_action,
not opened as a candidate.

## Seoul catalog sweep, 25 family keywords (2026-11-07, East Asia tick)

Executed option (b) of the recorded next_action. The catalog's search POST is
server-rendered, so the sweep ran from a plain client (recipe:
probe_kr_seoul_sweep_2026_11_07.py, this dir):

| Keyword family | Hits | Grain of every hit |
|---|---|---|
| 사고 (accident) | 67 (34 공공데이터) | aggregate traffic-accident/fire/electric-shock statistics (all 33 public-data cards paginated and read: 통계 tables by district/age/time) |
| 재난, 응급, 화재, 감염, 식중독 | 6-8 each | aggregate by-district/by-month statistics |
| 민원, 신고, 단속, 누수, 지하수, 도시가스, 항공, 교량, 가로수 | 1-8 each | aggregate counts/rates; no per-complaint or per-incident register |
| 리콜, 적발, 지연, 엘리베이터, 전력 사고, 도로 노면, 공사 지연, 시설물 안전, 자동차부품, 결함 | 0 | no such dataset family in the catalog |
| 붕괴 | 1 | improvement-district aggregate |

Verdict recorded in record.json (measurements.seoul_catalog_sweep_2026_11_07):
**no event-grain register outside the bench's existing families exists in the
Seoul catalog's search surface**; the only event-grain find remains OA-23122
(식품행정처분, enforcement family) behind the recorded operator family decision.
The Seoul gate collapses to that single decision (option (a)); option (b) is
closed by this measurement. KOSIS/KMA park unchanged.
