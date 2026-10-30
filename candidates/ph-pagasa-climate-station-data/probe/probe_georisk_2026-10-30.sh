#!/bin/sh
# PH unpark probe, 2026-10-30: re-resolve PhilDA host; probe GeoRiskPH PAGASA
# Rainfall_Forecast_Observed ArcGIS service for currency and licence.
echo "== DNS philida.pagasa.dost.gov.ph =="
getent ahosts philida.pagasa.dost.gov.ph || echo "NO A RECORD (getent)"
timeout 10 curl -s "https://dns.google/resolve?name=philida.pagasa.dost.gov.ph&type=A" ; echo
echo
echo "== GeoRiskPH ArcGIS service metadata =="
timeout 30 curl -sS "https://portal.georisk.gov.ph/arcgis/rest/services/PAGASA/Rainfall_Forecast_Observed?f=json" -o /opt/data/cache/scratch/georisk_pfc_service.json -w "HTTP %{http_code} %{size_download}B in %{time_total}s\n"
python3 - <<'EOF'
import json
try:
    d = json.load(open('/opt/data/cache/scratch/georisk_pfc_service.json'))
    keep = {k: d.get(k) for k in ('serviceName','serviceDescription','copyrightText','spatialReference','layers','tables','currentVersion') if k in d}
    print(json.dumps(keep, indent=1)[:3000])
except Exception as e:
    print('parse failed:', e)
EOF
