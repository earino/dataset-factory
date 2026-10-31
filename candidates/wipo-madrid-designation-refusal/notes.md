# wipo-madrid-designation-refusal

Record dated evidence, decisions, and failed approaches here.

## 2026-10-31 — licence triage (class D, session 2026-10-31 international-organisations tick)

Lead: designation-level provisional-refusal prediction on the WIPO Madrid System registry.
The shape was promising (treaty-documented censoring window, weekly official publication
carrying both the cohort and the outcome events, large volume, no known ML-ready precedent).
Order of work: licence first. Every free machine-readable channel died on the publisher's own
instrument, so no task probing was spent.

Commands used (all read-only, bounded, from the coordinator):

    # Madrid Monitor Terms of Use (July 2025) — the decisive instrument
    web_extract https://www3.wipo.int/madrid/monitor/en/terms.jsp      # HTTP 200, full text read
    # Gazette portal — confirms the Gazette is served inside the Madrid Monitor application
    web_extract https://www3.wipo.int/madrid/monitor/en/gazette.jsp   # HTTP 200
    # Global Brand Database Terms of Use (November 2022) — the other free channel incl. Madrid records
    web_extract https://www.wipo.int/en/web/global-brand-database/terms_and_conditions  # HTTP 200
    # WIPO general Terms of Use — confirms the site-wide CC BY 4.0 policy is conditional
    web_search "WIPO data licence \"CC BY\" terms of use Madrid Global Brand Database redistribution"
    # (read via the search tool's live-page extraction of https://www.wipo.int/en/web/terms-of-use)
    # Madrid Monitor help/FAQ — no public API, backfile for a fee
    web_search "WIPO Madrid System bulk data download registrations refusals API open data"

Observed (2026-10-31):

- terms.jsp §4(b)-(c): granted rights are "query the data", "view, download and store
  individual documents"; "Any use other than those specifically authorized above shall
  require the prior written consent of WIPO."
- terms.jsp §5(a)(i)-(ii): no right to "perform bulk acquisition, bulk downloads or bulk
  storing", no "bulk copying, bulk reformatting or bulk redistribution".
- terms.jsp §6: "the service is not designed for bulk downloads"; "more than 10 search
  related actions per minute" and "automated queries" are unfair use; "(c) Under no
  circumstances may the information made available through the Madrid Monitor database be
  made accessible or sublicensed in any way to another service provider host or publisher."
- gazette.jsp: weekly issues (No. 42 - 29/10/2026 back to No. 01 - 15/01/2026 for 2026;
  years 2009-2026 + All; 1997-2010 archive at wipo.int/madrid/en/madridgazette/year.html),
  with the label-event chapters measured: "Notifications of provisional refusals",
  "Final decisions", "Confirmations of total provisional refusal (Rule 18ter(3))",
  "Statements of grant of protection following a provisional refusal (Rule 18ter(2))",
  "Statements of grant of protection (Rule 18ter(1))",
  "Possible opposition beyond the 18-month time limit (Rule 16)", "Invalidations".
  Served at /madrid/monitor/en/ — inside the application whose ToU is terms.jsp.
- GBD ToU §2.1: user "is forbidden to ... perform automated queries; perform bulk
  acquisition, bulk downloading, and bulk storing of data; perform bulk copying, bulk
  reformatting, bulk sharing and bulk redistributing of data; perform web scraping";
  §2.2 no selling or sublicensing without permission; §3.2 "WIPO may also provide the
  entire collection of all international marks recorded under the Madrid system on request
  and payment of a fee."
- Madrid Monitor help/FAQ (live-page extraction 2026-10-31): "do you have a public API for
  direct search access? Not currently."; "The complete Madrid backfile is available for a
  fee"; downloads are per-page-of-results (PDF/CSV/XLSX/HTML/XML/ZIP).
- WIPO general ToU: "Unless service-specific terms of use apply ..." — the site-wide
  CC BY 4.0 policy is conditional, and Madrid Monitor's service terms apply here.

Decision: dropped, licence class D (bulk redistribution and automated access explicitly
prohibited; any other use requires prior written consent; bulk backfile is a paid service).
No schema, volume, base-rate, split or cost probes were run — deliberately, per the
licence-first order of work.

Reopen triggers are recorded in record.json next_action.
