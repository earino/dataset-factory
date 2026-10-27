# Probe: cross-check the measured filed-year cohorts against the IPO's own
# facts-and-figures workbook (Trade_marks_2016.xlsx, "Summary of trade mark
# activity", National UK applications). Fetches the 54 KB xlsx and parses it
# with the stdlib (zipfile + regex); prints published vs measured and the
# relative differences. Run 2026-10-27. The `measured` dict comes from
# probe_aggregate.py's per-year distinct-mark counts.
import urllib.request, zipfile, re, json

XLSX = "https://assets.publishing.service.gov.uk/media/5a74c648e5274a3f93b48b43/Trade_marks_2016.xlsx"
measured = {2012: 40275, 2013: 46355, 2014: 51075, 2015: 54291, 2016: 61648}  # probe_aggregate.py

data = urllib.request.urlopen(urllib.request.Request(XLSX), timeout=60).read()
open("Trade_marks_2016.xlsx", "wb").write(data)
z = zipfile.ZipFile("Trade_marks_2016.xlsx")
ss = re.findall(r"<si>(?:<t[^>]*>)?([^<]*)", z.read("xl/sharedStrings.xml").decode("utf-8", "replace"))
pub = {}
for sh in ["sheet1", "sheet2", "sheet3", "sheet4"]:
    x = z.read(f"xl/worksheets/{sh}.xml").decode("utf-8", "replace")
    if "UK Domestic Applications" not in x and ">4<" not in x:
        pass
    cells = re.findall(r'<c r="([A-Z]+\d+)"(?: s="\d+")?(?: t="(\w+)")?[^>]*>(?:<v>([^<]*)</v>)?', x)
    if not cells:
        continue
    grid = {}
    for ref, t, v in cells:
        if not v:
            continue
        mcol = re.match(r"([A-Z]+)", ref)
        mrow = re.match(r"[A-Z]+(\d+)", ref)
        if not mcol or not mrow:
            continue
        col, row = mcol.group(1), int(mrow.group(1))
        grid.setdefault(row, {})[col] = ss[int(v)] if t == "s" else v
    for r, row in sorted(grid.items()):
        # Section-1 shape: A=Year, B=National applications (with 'Applications' header two rows above)
        if row.get("B") == "Applications" or "Applications" in str(row.get("B", "")):
            for rr in range(r + 2, r + 9):
                g = grid.get(rr, {})
                y, b = g.get("A"), g.get("B")
                if y and b and y[:4].isdigit() and b.replace(",", "").isdigit():
                    pub[int(y[:4])] = int(b.replace(",", ""))
if not pub:
    raise SystemExit("published National applications row not found - inspect sheet XML")
print(json.dumps({"published_national_applications": pub}, indent=1))
for y in sorted(pub):
    m = measured.get(y)
    if m:
        print(f"{y}: published={pub[y]} measured={m} rel_diff={100*(m-pub[y])/pub[y]:+.2f}%")
