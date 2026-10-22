# Query recipes for public data portals

Anonymous, key-free endpoints unless noted. Send a `User-Agent`; some portals reject the default
Python one. All of these return bounded JSON, which is the point: they answer vetting questions
without moving data.

Save probe output to a file and read that file back. These scripts make a dozen calls, and a
failure on call nine is invisible if the terminal only showed the tail of the transcript.

## Socrata (api.us.socrata.com + `<domain>/resource/<id>.json`)

**Cross-domain catalog search** — discovery plus license in one request:

```
https://api.us.socrata.com/api/catalog/v1?q=<url-encoded term>&limit=10
https://api.us.socrata.com/api/catalog/v1?domains=<domain>&q=<term>&limit=10
```

Read `results[].resource.id` (the dataset id), `.resource.name`, `.metadata.license`,
`.metadata.domain`. A quoted phrase works and is the fastest way to sweep many portals for one
mechanism.

**Schema and license** — `https://<domain>/api/views/<id>.json`:

- `columns[].fieldName` / `.dataTypeName` — the API field names, which differ from the display labels.
- `columns[].description` — the column documentation, and the single most valuable field here. It
  is where a label's start instant, a flag's timing and a field's unit are settled.
- `license.name` — the string to record verbatim; `null` means unstated, not unrestricted.
- `view.rowsUpdatedAt` — freshness of the view.

**Reconcile the schema from two sources before quoting a column count.** Fetch
`/api/views/<id>.json` for the declared columns and `/resource/<id>.json?$limit=1` for the keys a
real row returns, then diff the two sets. They should agree exactly; when they do not, the narrower
one is what your queries can actually use. A column count taken from a page, a summary or an
earlier session is a claim, not a measurement — say "N columns" only after this check.

**Aggregates** — `https://<domain>/resource/<id>.json?<params>`, URL-encoded:

| Question | Params |
|---|---|
| How many rows? | `$select=count(*)` |
| How recent, how far back? | `$select=min(<date_field>),max(<date_field>)` |
| Rows per year | `$select=date_trunc_y(<date_field>) AS y, count(*) AS n&$group=y&$order=y DESC` |
| Class balance | `$select=<label>, count(*) AS n&$group=<label>&$order=n DESC` |
| Rows with a usable label | `$select=count(*)&$where=<label> IS NULL` |
| Recent activity | `$select=date_trunc_ym(<date_field>) AS m, count(*) AS n&$group=m&$order=m DESC&$limit=10` |
| Base rate at a threshold | `$select=count(*)&$where=<label> > <value> AND <time_field> < '<train end>'` |

**Grouped queries need the grouping column in `$select` too.** `$select=count(*)&$group=<field>`
returns rows with no `<field>` key at all, and the caller then fails on a missing key rather than on
a bad query. Always write
`$select=<field>, count(*) AS n&$group=<field>&$order=n DESC`, and the rows come back keyed.

**Uniqueness and a total ordering, before you page.** Offset paging is only correct over a *total*
order. `$order=<col>&$offset=<n>` where `<col>` repeats leaves the tied rows in whatever order the
backend prefers, and that preference is not promised to be stable between requests — so a page
boundary can repeat or skip rows, and it does so silently. Two cheap aggregates settle whether the
key is usable, and one tiebreaker fixes it if it is not:

```
# rows against distinct values: 1,049,636 vs 1,049,612 -> 24 values carry two rows each
$select=count(*) AS n, count(DISTINCT <col>) AS n_distinct

# which values repeat, and how often
$select=<col>,count(*) AS n&$group=<col>&$having=count(*)>1&$limit=10

# is `:id` (Socrata's per-row identifier) unique? 1,049,636 vs 1,049,636 -> usable tiebreaker
$select=count(*) AS n, count(DISTINCT :id) AS n_ids
```

Then prove the order is total *and* deterministic by fetching the same page twice and comparing:
`$select=<col>,:id&$order=<col>,:id&$where=<col>='<a repeated value>'&$limit=4`. Identical JSON on
both calls is the evidence; "the key looked unique enough" is not.

Reconcile the result against the built file: if the extract's duplicated set is exactly the source's
duplicated set, the paging is clean; if the file has more, the paging repeated rows. That comparison
is what separates a source-grain property from a retrieval bug, and the two look identical in the
data.

**Bounded sample** — always name the fields, so the response stays small and the output stays
interpretable: `?$limit=2&$select=id,<time_field>,<label>`.

Query parameters must be percent-encoded (`$select`, `$group`, `$where` are literal dollar-sign
params); passing them from a script, use a URL-encoder rather than hand-building the string.

A dataset listed as a Socrata *view* may be community-created: the page usually links the asset it
was built from. Prefer the official asset for a long-lived task.

### Portal quirks that look like absence

- **A 403 is often a bot wall, not a missing dataset.** Cloudflare-fronted Socrata hosts answer
  `403` with a `<title>Just a moment...</title>` interstitial on a first or bursty attempt, then
  serve normally. Retry with backoff (three or four attempts is plenty) and treat the HTML title as
  the tell. Recording a dataset as unavailable on one 403 is the mistake this prevents.
- **Successor datasets rename their columns.** A "new for <year>" replacement frequently calls the
  date field something else than its predecessor (`start_date` versus `date_discovered`). The
  failure mode is an error that reads like the dataset is empty:
  `query.soql.no-such-column: No such column: <field>`. Re-read the columns endpoint before
  querying the successor, and when a series looks empty, suspect the field name before the data.
- **`rowsUpdatedAt` is an epoch second.** Convert it before drawing a freshness conclusion; it is
  the fastest way to tell a live series from a frozen historical one.
- **Related datasets overlap rather than abut.** A successor often re-publishes the tail of its
  predecessor, so plan a reconciliation step instead of concatenating them.

## OpenDataSoft (`/api/explore/v2.1/...`)

```
https://<portal>/api/explore/v2.1/catalog/datasets/<slug>/records?limit=2
https://<portal>/api/explore/v2.1/catalog/datasets/<slug>          # metadata
https://<portal>/api/explore/v2.1/catalog/datasets/<slug>/records?where=<field>%3D<value>&limit=10
```

The records response gives `total_count` plus real rows in one call, which is often enough to
vet a source outright. The metadata endpoint does **not** always expose a licence field — when it
returns nothing, read the dataset's information page before assuming a licence.

When the metadata endpoint, the information page HTML and the aggregator catalogue all fail to
produce a licence, that is a conclusion, not an unfinished search: record each channel you tried
and what it returned. On the page HTML, note that the string `license` appearing at all is often an
OpenDataSoft *feature flag* rather than a licence declaration — look for a link to a licence text or
a `creativecommons.org` URL, not for the word.

## NOAA CO-OPS (tides and currents)

No key. Two APIs matter:

```
# Observed data
https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
  ?product=hourly_height&application=<your-app>&begin_date=YYYYMMDD&end_date=YYYYMMDD
  &datum=STND&station=<id>&time_zone=gmt&units=english&format=json

# Thresholds and station inventory
https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=waterlevels&expand=floodlevels
https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/<id>/floodlevels.json
```

**The threshold's datum is not the datum you would guess, and `floodlevels.json` does not declare
it.** `nos_minor` and friends are expressed in the **station datum (`STND`)**. Query the water-level
product at `datum=MLLW` (the value most examples reach for) and compare it to `nos_minor` and
**every entity comes out below its threshold** — zero
exceedances at every station across thousands of station-days, which is a pure reference-frame
error wearing the costume of "this task has no positive class".

Settle it once with a record event, then keep `datum=STND`:

```
Boston 8443970, nos_minor 15.85 ft, 2018-01-03..2018-01-05 (the bomb-cyclone record tide)
  datum=MLLW  peak 15.022 ft  -> below threshold, i.e. "no flood during the record storm": wrong
  datum=STND  peak 18.547 ft  -> above threshold: correct
```

**Per-entity exceedance base rates, cheaply.** `hourly_height` allows ~200 years per request, so
take **one request per entity per year** (~8,760 rows), reduce it to a daily maximum as you read it,
and discard the hourly rows — memory stays flat no matter how many entity-years pass through.
Streaming this rather than buffering the rows is what keeps a twelve-station year inside a small
coordinator:

```
datagetter?product=hourly_height&datum=STND&units=english&time_zone=gmt
  &begin_date=20250101&end_date=20251231&station=<id>
```

Then `daily_max > nos_minor` per day, and count. Expect a **rare** class — a 12-station year
measured ~1.4% of station-days pooled, ranging 0% to ~4.7% per station, with several stations whose
annual maximum sat within 0.2 ft *below* their threshold. Report the per-station spread alongside
the pooled rate, and note that a near-miss annual maximum makes that entity's zero offset-sensitive.

**Prefer the provider's own flood determination when one exists, and cross-check against it.** The
CO-OPS Derived Product API publishes per-station flood counts at the NOS thresholds, with `STND` as
its documented default frame:

```
https://api.tidesandcurrents.noaa.gov/dpapi/prod/webapi/htf/htf_annual.json?station=<id>
https://api.tidesandcurrents.noaa.gov/dpapi/prod/webapi/htf/htf_daily.json?station=<id>&start_date=YYYYMMDD&end_date=YYYYMMDD
```

`htf_annual.json` returns `AnnualFloodCount[]`, one entry per year (a century of history for the
long-running stations), each carrying `minCount` / `modCount` / `majCount` and
`percent_completeness`. That is the authoritative flood-day count per station-year, and it matched a
recomputed `datum=STND` daily-maximum pass **exactly, on twelve of twelve stations for one year — 60
days against 60** — where the rejected `MLLW` pass produced 0. Agreement entity by entity is the
validation; a matching total alone would not have been.

Three things about this endpoint family are easy to get wrong:

- **The path is `htf`, not `htb`.** `htb.json` and `htb_monthly_max.json` are also served, but the
daily flood-status product under that prefix returns `count: 0` with an empty `floodLikelihood` list
for every station, date and range tried, including a known record year. An empty response is not
evidence that an entity never floods — check the endpoint family before concluding anything, and
note which variant you actually called.
- **`htf_daily.json`'s `count` is the number of days *returned*** (365 for a year), not a flood
  count. Reading it as one makes every station look like it flooded every day of the year. The real
  flags are on the per-day rows: `{day: "MM/DD/YYYY", maxWL, maxTime, minFlag, modFlag, majFlag,
  percent_completeness}` — note the `MM/DD/YYYY` day format and the `*Flag` names.
- **Date parameters are `start_date` / `end_date`.** A `year=` parameter returns HTTP 500, and
  `begin_date` also fails.

`floodlevels.json` returns `nos_minor|nos_moderate|nos_major` and `nws_minor|nws_moderate|nws_major`
per station, which is what turns a continuous series into a binary target. Retrieval limits are the
planning constraint: **6-minute data is capped at about one month per request, hourly data at ~200
years**, so a multi-year 6-minute backfill is many requests — worker work. That cap is exactly why
the resolution question has to be measured before choosing the cheap path: over the busiest
station-months of a real year, hourly daily maxima missed **1 of 17** flood days that the 6-minute
series caught, so an hourly-derived rate is a lower bound rather than the rate. Products such as tide
predictions and OFS model guidance are model output; including them as features turns the task into
"reproduce the provider's model".

## USGS NWIS (streamflow and other gauges)

```
https://waterservices.usgs.gov/nwis/iv/?format=json&sites=<site>&parameterCd=00060&period=P1D
```

Public domain, no key, `parameterCd=00060` is discharge in cfs. Values arrive with qualifiers
(`P` = provisional), which matter for a label definition and for reproducibility of past extracts.

## Is the target one class or a set? (multiclass versus multi-label)

Three cheap probes decide the shape of a task before any modelling is promised. All are aggregates;
none needs a model, a download or a candidate record yet.

**1. Grain, from one aggregate.** `$select=count(*) AS n, count(DISTINCT <entity_key>) AS n_keys`.
Equal counts mean one row per entity, so every categorical holds a single value per row and no per-row
label set exists - the task is k-way multiclass however many categorical columns the table has. Do not
build a set by folding single-valued columns together: the labels then co-occur by construction and a
solver can see the columns they were folded from.

```
# one row per incident? 1,049,636 rows against 1,049,612 distinct incident_number
$select=count(*) AS n, count(DISTINCT incident_number) AS n_keys
```

**2. Set-structure, from the parsed label blob.** When the label is text (a violations blob of
`"<code>. <DESCRIPTION> - Comments: <prose>"`), parse it to codes and report: distinct labels, labels
per row (mean/median/max), the share of labels appearing in >=1% of rows, and the top co-occurring
pairs. Labels that co-occur far above chance make a multi-label task; mutually exclusive labels make a
one-hot problem wearing a set-shaped column. Density against the outcome column is worth the same
query - mean labels per row by outcome level shows the set carries information a binary target throws
away.

**Assert the parse before aggregating.** A pattern that misses the blob's real separator returns zero
labels, and zero reads as "nothing was recorded" rather than "the regex is wrong". Require a nonzero
parsed count, and compare the *union* of two differently-ordered samples against each sample's own
count: a union smaller than one of its inputs is arithmetic proof that a side failed to parse.
Total-parsed against rows-with-a-blob is the same check from the other end. Expect the codes to have
accumulated several description spellings over a decade - key on the code number, keep each spelling as
recorded evidence, and count codes rather than spellings.

**3. Headroom, from counts alone.** Entropy and mutual information come out of a two-way group-by:

```
$select=<feature>, <target>, count(*) AS n &$group=<feature>,<target>
```

`H(target) = -sum p(t) log2 p(t)`; `I(target; feature) = H(target) - sum_f p(f) H(target | f)` with
`p(t | f)` the cell over the feature's row total. `I / H` is the fraction of the answer that column
carries. Beside it report the trivial baselines that make the number meaningful: the majority class,
the rate at which a near-copy column already equals the target (a final-category column against its
intake category), and the top-k accuracy the best single column already reaches. A high-entropy target
with one column carrying most of its information and location/time carrying ~1% each is a finding to
report, not a footnote: it says the honest task is what that column makes possible.

**Value counts per column catch a zero-information feature.** A column documented as useful can be a
constant across every row - a field described as "coarse call classification known at dispatch"
carrying one value over 1.05M rows. One group-by per shipped categorical is the check that catches it
before it is declared a feature.

**Two rules for blob labels.** The blob is the label source and stays out of the feature list, because
its prose comments are written during the observation. And a non-null blob is not an outcome: rows with
no conclusion can still carry text carried from an earlier visit, so filter the modelling pool on the
outcome column rather than on the label column being non-null.

## Cross-source joins

Rainfall, temperature and other drivers typically come from NOAA GHCN-Daily or NCEI CDO and join by
station plus date. Test the join before it becomes load-bearing: station coverage in the target
region is the usual failure, and the join key's timezone convention (local day versus UTC) silently
changes the label definition for event-per-day tasks.
