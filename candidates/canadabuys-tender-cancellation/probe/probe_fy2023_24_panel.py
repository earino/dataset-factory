import csv
from collections import Counter, defaultdict
from datetime import date

BASE = "/opt/data/cache/scratch/cb/"
csv.field_size_limit(10_000_000)

TN = BASE + "2023-2024-TenderNotice-AvisAppelOffres.csv"
AW = [BASE + "2023-2024-awardNotice-avisAttribution.csv", BASE + "2024-2025-awardNotice-avisAttribution.csv"]

n_rows = 0
amend_rows = 0
sol_status = {}      # solicitation -> latest status (max amendment row wins)
sol_pub = {}
sol_close = {}
sol_type = Counter()
sol_method = Counter()
type_status = defaultdict(Counter)
method_status = defaultdict(Counter)
sol_first_type = {}
pub_year = Counter()

def norm(s):
    return (s or "").strip().upper()

with open(TN, encoding="utf-8-sig", errors="replace") as f:
    r = csv.DictReader(f)
    for row in r:
        n_rows += 1
        sol = norm(row["solicitationNumber-numeroSollicitation"])
        if not sol:
            continue
        am = norm(row["amendmentNumber-numeroModification"])
        status = norm(row["tenderStatus-appelOffresStatut-eng"])
        ntype = norm(row["noticeType-avisType-eng"])
        meth = norm(row["procurementMethod-methodeApprovisionnement-eng"])
        pub = norm(row["publicationDate-datePublication"])
        clo = norm(row["tenderClosingDate-appelOffresDateCloture"])
        try:
            amend_n = float(am) if am else 0.0
        except ValueError:
            amend_n = 0.0
        if amend_n > 0:
            amend_rows += 1
        prev = sol_status.get(sol)
        if prev is None or amend_n >= prev[0]:
            sol_status[sol] = (amend_n, status, ntype, meth, pub, clo)

print("tender file rows:", n_rows, "| rows with amendmentNumber>0:", amend_rows)
print("distinct solicitationNumbers:", len(sol_status))
print("duplicate sollicitations (rows beyond first):", n_rows - len(sol_status))

# overall current status of distinct solicitations
status_all = Counter(v[1] for v in sol_status.values())
print("status mix (distinct solicitations):", dict(status_all))

# publication date range & FY coverage
pubs = [v[4][:10] for v in sol_status.values() if v[4]]
print("publicationDate range:", min(pubs), "..", max(pubs))
for p in pubs:
    pub_year[p[:4]] += 1
print("publication year mix:", dict(sorted(pub_year.items())))

# notice type / method mixes and status by type
type_status2 = defaultdict(Counter)
for v in sol_status.values():
    type_status2[v[2]][v[1]] += 1
    sol_method[v[3]] += 1
    sol_type[v[2]] += 1

print("\nnotice type mix + status:")
for t, c in sol_type.most_common():
    print(f"  {t[:55]:57s} n={c:6d}  {dict(type_status2[t])}")

print("\nprocurement method mix:")
for m, c in sol_method.most_common():
    print(f"  {m[:75]:77s} n={c}")

# closing date presence and pub->close duration
have_close = sum(1 for v in sol_status.values() if v[5])
print("\nsolicititations with tenderClosingDate:", have_close, "/", len(sol_status))
import statistics
durs = []
for v in list(sol_status.values())[:200000]:
    try:
        pd = date.fromisoformat(v[4][:10]); cd = date.fromisoformat(v[5][:10])
        if cd >= pd:
            durs.append((cd - pd).days)
    except Exception:
        pass
if durs:
    print("pub->close days: n=%d median=%d p10=%d p90=%d" % (len(durs), statistics.median(durs), sorted(durs)[len(durs)//10], sorted(durs)[int(len(durs)*0.9)]))

# ---- award notices join ----
award_hdr = None
award_sols = {}
award_dates = {}
n_aw = 0
for path in AW:
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        r = csv.DictReader(f)
        if award_hdr is None:
            award_hdr = r.fieldnames
        for row in r:
            n_aw += 1
            s = norm(row.get("solicitationNumber-numeroSollicitation"))
            if not s:
                continue
            award_sols[s] = award_sols.get(s, 0) + 1
            d = norm(row.get("contractAwardDate-dateAttributionContrat"))[:10]
            if d and s not in award_dates:
                award_dates[s] = d

print("\naward files rows:", n_aw, "| distinct award solicitationNumbers:", len(award_sols))
print("award header cols:", len(award_hdr) if award_hdr else None)
print("sample award cols:", [h for h in (award_hdr or [])][:14])

# join: distinct FY23-24 solicitations -> any award notice in FY23-24/24-25 files
hit = sum(1 for s in sol_status if s in award_sols)
print("FY23-24 solicitations with award notice in the two award files: %d / %d (%.2f%%)" % (hit, len(sol_status), 100*hit/len(sol_status)))

# by type, and by status
print("\njoin by notice type:")
for t, c in sol_type.most_common():
    tt = sum(1 for s, v in sol_status.items() if v[2] == t and s in award_sols)
    print(f"  {t[:55]:57s} awarded={tt:6d}/{c:6d} ({100*tt/max(c,1):.1f}%)")

print("\njoin by status:")
for st, c in status_all.most_common():
    ss = sum(1 for s, v in sol_status.items() if v[1] == st and s in award_sols)
    print(f"  {st[:20]:22s} awarded={ss:6d}/{c:6d} ({100*ss/max(c,1):.1f}%)")

# cancellation rate restricted to genuine competition solicitations (RFP-like)
RFP_TYPES = {"REQUEST FOR PROPOSAL", "REQUEST FOR STANDING OFFER", "REQUEST FOR SUPPLY ARRANGEMENT", "RFP AGAINST SUPPLY ARRANGEMENT", "INVITATION TO QUALIFY"}
elig = {s: v for s, v in sol_status.items() if v[2] in RFP_TYPES}
el_st = Counter(v[1] for v in elig.values())
print("\nRFP-like population n=%d status mix: %s" % (len(elig), dict(el_st)))
el_aw = sum(1 for s in elig if s in award_sols)
print("RFP-like with award notice:", el_aw, "(%.2f%%)" % (100*el_aw/max(len(elig),1)))
