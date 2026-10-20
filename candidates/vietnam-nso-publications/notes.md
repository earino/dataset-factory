# notes — vietnam-nso-publications (opened 2026-10-20)

Verdict: PARK. Publication-archive publisher; no machine-readable channel found; the
national open-data portal is dark in DNS. (Per the tick brief, a PDF-only publisher is
a park, not a go.)

## DNS measurements (2026-10-20)

Local resolution (getent): "Name or service not known" for gso.gov.vn, data.gov.vn,
www.gso.gov.vn. No dig on the host; used Google DoH to separate resolver gaps from
authoritative answers:

```
https://dns.google/resolve?name=gso.gov.vn&type=A        -> Status 3 NXDOMAIN (SOA from gov.vn zone)
https://dns.google/resolve?name=www.gso.gov.vn&type=A     -> Status 3 NXDOMAIN
https://dns.google/resolve?name=opendata.gov.vn&type=A    -> Status 3 NXDOMAIN
https://dns.google/resolve?name=data.gov.vn&type=A        -> Status 0, no Answer (zone alive, NS ns1.zonedns.vn)
https://dns.google/resolve?name=www.data.gov.vn&type=A    -> Status 3 NXDOMAIN under data.gov.vn
https://dns.google/resolve?name=nso.gov.vn&type=A         -> Status 0, Answer 160.25.148.3
```

The General Statistics Office was renamed the National Statistics Office (Ministry of
Finance Decision 384/QD-BTC, 26 Feb 2025) and its host is now nso.gov.vn — the old
gso.gov.vn names no longer exist in authoritative DNS. Recorded so the next session
does not re-diagnose the NXDOMAINs as a resolver fault.

## HTTP probes (2026-10-20)

```
curl https://www.nso.gov.vn/en/            -> HTTP 200 -> /en/homepage/, 107,925 B, Avada WordPress
curl https://www.nso.gov.vn/en/statistics-data/ -> HTTP 404 "Page not found"
curl https://www.nso.gov.vn/en/publication/ -> curl: (6) Could not resolve host (minutes after the 200 above)
```

The site is a publication archive (yearbooks, summary books); no API found; a repeat
probe minutes later failed local DNS while public DoH still resolved the host — .vn
resolution from the coordinator is intermittent. Two effects (dark portal +
intermittent resolution) both measured; neither is a judgement about the data.

## Licence

Not read (publication-listing pages only). Stays open with the park.

## Unpark question

Is there a current machine-readable NSO channel (XLSX monthly tables or a relaunched
open-data portal), reachable from a worker, with event-level or series grain?
