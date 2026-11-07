# cl-sadu-respiratory-weekly — discovery notes (dropped on licence)

LatAm regional tick 2026-11-07, Chile. This lead was closed at step 1 of the
discovery order of work (licence first) — no schema, timing or split probes
were spent after the veto.

## The lead (why it was attractive)

Chile MINSAL/DEIS publishes the SADU weekly panel "Atenciones de urgencias de
causas respiratorias por semana epidemiológica": emergency-department
consultations and hospitalizations by respiratory cause group (IRA alta
J00-J06, influenza J09-J11, neumonía J12-J18, bronquitis/bronquiolitis J20-J21)
per establecimiento, epidemiological week and age group, 2008-2024, as parquet
and xlsx with a data dictionary. The publisher's own registration manual
motivates exactly the prediction a dataset would carry: winter-campaign
"asignación estratégica de recursos" and "alertas tempranas". Weekly national
respiratory-surge prediction per servicio de salud would have been a clean
operational panel task.

## Licence probe (decisive, 2026-11-07)

```
curl -s "https://datos.gob.cl/api/3/action/package_search?q=atenciones+urgencias+respiratorias+semana"
# -> package 'atenciones-de-urgencia-causas-respiratorias', org ministerio_de_salud:
#    "license_id": "cc-nc", "license_title": "Creative Commons Non-Commercial (Any)"

curl -s "https://datos.gob.cl/api/3/action/package_show?id=atenciones-de-urgencia"
# -> the DAU annual-aggregate package (the alternative channel, same publisher):
#    "license_id": "cc-nc"  (identical)
```

Both packages are the publisher's own designations, read from the national
portal's own metadata API. CC BY-NC permits redistribution and derivatives
non-commercially, but our releases exist for agent evaluation — routinely by
commercial parties — and project policy preserves upstream conditions
unchanged. An NC release would make the primary intended use infringing, so
the source is not clean for this project's distribution model.

## Decision

Dropped, licence class D (terms incompatible with intended use — not class C:
nothing is unresolved to ask about). Total spend: 2 API calls and 3 search
pages; no bulk downloads.

## Reopen conditions

1. MINSAL/DEIS re-designates either package under terms permitting commercial
   use (re-read the CKAN license_id).
2. A candidate-specific operator risk acceptance for NC terms on this source
   family (recorded per the licence-posture convention, never assumed).

The task shape (weekly respiratory-ED surge from a national surveillance
panel) is worth re-trying in a jurisdiction whose national health-data
licence permits any-purpose use — it was not rejected on task merits, which
were never probed.
