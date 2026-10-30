#!/bin/sh
# GeoRiskPH PAGASA/Rainfall_Forecast_Observed MapServer: layers + currency, 2026-10-30.
SVC="https://portal.georisk.gov.ph/arcgis/rest/services/PAGASA/Rainfall_Forecast_Observed/MapServer"
echo "== MapServer root metadata =="
timeout 30 curl -sS "$SVC?f=json" -o /opt/data/cache/scratch/rfo_root.json -w "HTTP %{http_code} %{size_download}B\n"
python3 -c "
import json
d = json.load(open('/opt/data/cache/scratch/rfo_root.json'))
keep = {k: d.get(k) for k in ('serviceDescription','copyrightText','layers','tables','currentVersion','timeInfo') if k in d}
print(json.dumps(keep, indent=1)[:2500])
"
echo
echo "== layer 0 fields =="
timeout 30 curl -sS "$SVC/0?f=json" -o /opt/data/cache/scratch/rfo_l0.json -w "HTTP %{http_code} %{size_download}B\n"
python3 -c "
import json
d = json.load(open('/opt/data/cache/scratch/rfo_l0.json'))
print('name:', d.get('name), 'currentVersion:', d.get('currentVersion'))
" 2>/dev/null || python3 -c "
import json
d = json.load(open('/opt/data/cache/scratch/rfo_l0.json'))
print('name:', d.get('name'), '| copyright:', d.get('copyrightText'))
print('fields:', [(f['name'], f['type']) for f in d.get('fields',[])][:15])
"
