import csv, io

csv.field_size_limit(10_000_000)

for name in ["legacy_head.csv", "complete_head.csv"]:
    print("====", name)
    txt = open(name, encoding="utf-8-sig", errors="replace").read()
    cut = txt.rfind("\n")
    body = txt[:cut] if cut > 0 else txt
    r = csv.reader(io.StringIO(body))
    hdr = next(r)
    print("cols:", len(hdr))
    for i, h in enumerate(hdr):
        print(" ", i, h)
    n = 0
    for row in r:
        n += 1
        if n <= 2:
            print("  row sample:", [c[:24] for c in row[:10]])
    print("rows read:", n)
