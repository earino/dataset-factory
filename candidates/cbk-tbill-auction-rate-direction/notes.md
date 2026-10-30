# cbk-tbill-auction-rate-direction

## 2026-10-30 (Africa discovery tick)

Lead origin: the kenya-opendata-knbs record's next-action step 3 named regulator probes
(CBK/KRA/NTSA); the 2026-10-23 tick recorded CBK "unreachable from the coordinator, not
probed, not negative". This tick resolved that.

### Access (the 10-23 blocker, resolved)

- Coordinator resolver: NXDOMAIN for www.centralbank.go.ke (and meteo.go.ke).
- dns.google resolves www.centralbank.go.ke -> 192.124.249.9 (Sucuri edge).
- All fetches below used `curl --resolve www.centralbank.go.ke:443:192.124.249.9` and
  returned HTTP 200 to a plain client. The 10-23 "unreachable" was a coordinator DNS
  artifact, not a server-side refusal.

    # re-resolve before reuse:
    curl -sS 'https://dns.google/resolve?name=www.centralbank.go.ke'
    curl -sS -L --resolve www.centralbank.go.ke:443:192.124.249.9 \
      -A "Mozilla/5.0" https://www.centralbank.go.ke/bills-bonds/treasury-bills/ \
      -o tbills.html -w "HTTP %{http_code} bytes %{size_download} time %{time_total}s\n"
    # -> HTTP 200 bytes 1945083 time 0.027592s (2026-10-30 16:19Z)

### Archive measurements (from tbills.html, 1,945,083 bytes)

- 2,134 distinct .pdf hrefs on the page.
- 601 unique dates parseable from filenames; earliest 2013-04-07, latest 2026-11-02
  (mixed dd-mm-yyyy / dd.mm.yyyy formats; the 2026-11-02 file is unexplained - possibly
  pre-dated or tap-related; low stakes, recorded not resolved).
- Auction numbers in filenames run ~1900s .. 2705; 2705 is DATED 26-10-2026 (latest).
  Weekly Monday-auction cadence per CBK's own Auction Rules Guidelines (linked on page).
- Layout: /uploads/{91,182,364}_day_historical_treasury_bill_results/ (one PDF per
  auction, same PDF listed in all three tenor dirs) + older /images/docs/tbillsresults/YYYY/.

### Auction PDF schema (auction 2705, fetched verbatim via --resolve; 220,389 bytes)

`1455927531_RESULTS 2705-091 2679-182 2634-364 DATED 26-10-2026.xlsx.pdf` - despite the
double extension the bytes are a real PDF (not a zip). One page. Per tenor (91/182/364):
ISIN, Due Date, Amount Offered, Bids Received, Performance Rate %, Total Accepted,
Competitive bids, Non-competitive bids, Bid-to-Cover, Rollover/Redemptions,
New Borrowing/Net Repayment, Market Weighted Average Rate, Weighted Average Rate of
accepted bids, Price per 100; plus a comparative block vs the previous auction.
Reproduce the extraction with probe_cbk.py.

### Licence channels read (all 2026-10-30; every live channel silent on data terms)

1. tbills page HTML + footer: no licence metadata; footer = `© 2017 Central Bank of Kenya`.
2. /privacypolicy/ (HTTP 200): `Copyright 2016 © Copyright Central Bank of Kenya.
   All rights reserved.` then monitoring/cookie/privacy text only; its "terms" consent
   sentence is about monitoring, not data redistribution.
3. Terms-path sweep all 404: /terms /terms-of-use /disclaimer /privacy-policy /legal
   /access-to-information /about-us /sitemap.xml /sitemap_index.xml. Nav 'Metadata'
   link (/?page_id=889) also 404.
4. robots.txt: only wp-admin/author disallows; no sitemap.
5. Auction 2705 PDF text: no notice of any kind.
6. No CKAN/API metadata channel (WordPress uploads archive).
7. No live Kenyan national harvest catalogue (open.data.go.ke NXDOMAIN, kenya record).
8. Web search for a CBK data-licence statement: only /privacypolicy/ surfaces.
9. Wayback CDX for historical terms pages: "Temporarily Offline" twice (~16:10-16:20Z);
   channel not consultable this tick - recorded as attempted, not as absence.

Classification: **C** (unstated - no grant, no prohibition of data reuse; the NBS-Nigeria
prohibition clause is absent here, so not D). Standing policy (2026-10-21): new unresolved
class C leads are closed. Verdict: dropped; reopen conditions in record.json next_action.

### Kenya Met (meteo.go.ke), same tick - recorded here, no separate record opened

- Also NXDOMAIN from the coordinator; dns.google -> 196.202.217.199; fetches 200 via
  --resolve. Site publishes forecast products (5-day/7-day/county/flood bulletins);
  no anonymous observation archive found on /Services/climate-data-management/ (services
  menu page). Rights statement: bare `© Kenya Meteorological Department`. Same class C
  publisher-silence posture as CBK; no data channel + no terms means a KMD lead would
  close at the same gate - not opened this tick.

### Reproduce

    python3 probe_cbk.py            # access + terms-path sweep + link census + PDF schema
