#!/bin/sh
# GeoRiskPH ArcGIS services directory enumeration, 2026-10-30.
echo "== /arcgis/rest/services root =="
timeout 30 curl -sS "https://portal.georisk.gov.ph/arcgis/rest/services?f=json" -w "\nHTTP %{http_code}\n" -o /opt/data/cache/scratch/georisk_root.json
python3 -c "
import json
try:
    d = json.load(open('/opt/data/cache/scratch/georisk_root.json'))
    print('folders:', d.get('folders'))
    print('services:', [s.get('name') for s in d.get('services',[])])
except Exception as e:
    print('parse failed:', e, open('/opt/data/cache/scratch/georisk_root.json').read()[:200])
"
echo
echo "== /arcgis/rest/services/PAGASA folder =="
timeout 30 curl -sS "https://portal.georisk.gov.ph/arcgis/rest/services/PAGASA?f=json" -w "\nHTTP %{http_code}\n" -o /opt/data/cache/scratch/georisk_pfc_folder.json
python3 -c "
import json
try:
    d = json.load(open('/opt/data/cache/scratch/georisk_pfc_folder.json'))
    print('services:', json.dumps(d.get('services',[]), indent=1)[:2000])
except Exception as e:
    print('parse failed:', e, open('/opt/data/cache/scratch/georisk_pfc_folder.json').read()[:200])
"
