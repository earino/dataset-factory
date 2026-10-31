import csv
from collections import Counter

csv.field_size_limit(10_000_000)
TN = "/opt/data/cache/scratch/cb/2023-2024-TenderNotice-AvisAppelOffres.csv"

sol = {}
with open(TN, encoding="utf-8-sig", errors="replace") as f:
    r = csv.DictReader(f)
    for row in r:
        s = (row["solicitationNumber-numeroSollicitation"] or "").strip().upper()
        if not s:
            continue
        try:
            am = float((row["amendmentNumber-numeroModification"] or "").strip() or 0)
        except ValueError:
            am = -1
        sol.setdefault(s, []).append((am, row["publicationDate-datePublication"][:10], row["tenderStatus-appelOffresStatut-eng"], row["noticeType-avisType-eng"]))

dups = {s: v for s, v in sol.items() if len(v) > 1}
print("solicitations with >1 row:", len(dups))
same_pub = 0; later_pub = 0; status_switch = 0; am_prefix_rows = 0
for s, rows in dups.items():
    pubs = [x[1] for x in rows]
    if len(set(pubs)) == 1:
        same_pub += 1
    else:
        later_pub += 1
        if max(pubs) > min(pubs):
            pass
    sts = set(x[2].upper() for x in rows)
    if len(sts) > 1:
        status_switch += 1
for s, rows in list(dups.items())[:6]:
    print(" ", s, [(x[0], x[1], x[2]) for x in rows])

# original rows (amendment 000 or minimal counter) publication date == min publication date?
mismatch = 0
for s, rows in sol.items():
    orig = [x for x in rows if x[0] in (0.0, -1.0)]
    if orig and orig[0][1] != min(x[1] for x in rows):
        mismatch += 1
print("solicitations where amendment-000 row pub != earliest row pub:", mismatch)
print("dups: same-pub-date rows:", same_pub, "| differing pub dates:", later_pub, "| status differs across rows:", status_switch)

# also: 'Cancelled-' title prefix check in FY23-24 file
pref = 0
with open(TN, encoding="utf-8-sig", errors="replace") as f:
    r = csv.DictReader(f)
    for row in r:
        if (row["title-titre-eng"] or "").strip().lower().startswith("cancelled"):
            pref += 1
print("rows whose title starts with 'Cancelled':", pref)
