#!/bin/sh
# Reachability probe for Indian government hosts, 2026-10-30 tick.
for u in https://data.gov.in https://api.data.gov.in; do
  echo "== $u =="
  timeout 15 curl -sS -o /dev/null -w "HTTP %{http_code} in %{time_total}s remote=%{remote_ip}\n" "$u"
done
