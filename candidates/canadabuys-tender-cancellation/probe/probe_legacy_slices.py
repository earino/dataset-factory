import csv, io, urllib.request
from collections import Counter

BASE = "/opt/data/cache/scratch/cb/"
LEG = "https://canadabuys.canada.ca/opendata/pub/2009-2022-tenderNoticeHistorical-AvisAppelOffresHistorique.csv"
csv.field_size_limit(10_000_000)

SIZE = 558413231
SLICES = [(3_000_000, 400_000), (150_000_000, 400_000), (330_000_000, 400_000), (520_000_000, 400_000)]

def fetch_range(url, start, length):
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{start+length-1}", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")

for start, length in SLICES:
    txt = fetch_range(LEG, start, length)
    cut = txt.find("\n")
    body = txt[cut + 1:] if start > 0 else txt  # drop partial first line
    r = csv.reader(io.StringIO(body))
    year = Counter(); status = Counter(); ntype = Counter(); n = 0; ex = []
    for row in r:
        if len(row) < 21:
            continue
        n += 1
        pub = row[5][:10]
        year[pub[:4]] += 1
        status[row[10]] += 1
        ntype[row[19]] += 1
        if row[10].upper() == "CANCELLED" and len(ex) < 3:
            ex.append((row[4], pub, row[6][:19], row[19], row[33][:40], row[0][:40]))
    print(f"slice @{start}: rows={n}")
    print("  years:", dict(sorted(year.items())))
    print("  status:", dict(status.most_common(6)))
    print("  types:", {k: v for k, v in ntype.most_common(5)})
    for e in ex:
        print("  CANCELLED example:", e)

# dated examples from the FY2023-24 file (local)
TN = BASE + "2023-2024-TenderNotice-AvisAppelOffres.csv"
print("\n== FY2023-24 dated examples (original rows, amendmentNumber=000) ==")
with open(TN, encoding="utf-8-sig", errors="replace") as f:
    r = csv.DictReader(f)
    shown_c = 0; shown_e = 0
    for row in r:
        if row["amendmentNumber-numeroModification"].strip() not in ("", "000", "0"):
            continue
        st = row["tenderStatus-appelOffresStatut-eng"].strip().upper()
        if st == "CANCELLED" and shown_c < 2 and "REQUEST FOR PROPOSAL" in row["noticeType-avisType-eng"].upper():
            shown_c += 1
            print("CANCELLED RFP:", row["solicitationNumber-numeroSollicitation"], "| pub", row["publicationDate-datePublication"], "| close", row["tenderClosingDate-appelOffresDateCloture"], "| entity", row["contractingEntityName-nomEntitContractante-eng"][:40], "| title", row["title-titre-eng"][:60])
        if st == "EXPIRED" and shown_e < 1 and "REQUEST FOR PROPOSAL" in row["noticeType-avisType-eng"].upper():
            shown_e += 1
            print("EXPIRED  RFP:", row["solicitationNumber-numeroSollicitation"], "| pub", row["publicationDate-datePublication"], "| close", row["tenderClosingDate-appelOffresDateCloture"], "| entity", row["contractingEntityName-nomEntitContractante-eng"][:40])
        if shown_c >= 2 and shown_e >= 1:
            break
