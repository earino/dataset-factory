# Verify Dec 2019 CSV: event-level per quarter? rows, date range, URN multiplicity, label mix.
import csv
from collections import Counter
from datetime import datetime

rows = list(csv.reader(open("mi-dec2019.csv", encoding="cp1252", errors="replace")))
hdr = rows[0]
data = [r for r in rows[1:] if any(v.strip() for v in r)]
print("header:", hdr)
print("n data rows:", len(data))
i_date = hdr.index("Inspection date")
i_urn = hdr.index("Provider URN")
i_type = hdr.index("Inspection type group")
i_overall = hdr.index("Overall Effectiveness")
i_ptype = hdr.index("Provider type")

def d(s):
    try:
        return datetime.strptime(s, "%d/%m/%Y")
    except Exception:
        return None

dates = sorted([d(r[i_date]) for r in data if d(r[i_date])])
print("date range:", dates[0].date(), "..", dates[-1].date())
urns = Counter(r[i_urn] for r in data)
print("distinct URNs:", len(urns), "| URNs with >1 row:", sum(1 for v in urns.values() if v > 1),
      "| max rows/URN:", max(urns.values()))
print("Provider type:", Counter(r[i_ptype] for r in data).most_common(5))
print("Inspection type group:", Counter(r[i_type] for r in data).most_common())
print("Overall Effectiveness:", Counter(r[i_overall] for r in data).most_common())
# quarterly count sanity
per_q = Counter(d(r[i_date]).strftime("%Y-%m") for r in data if d(r[i_date]))
print("events per month (last 8):", sorted(per_q.items())[-8:])
