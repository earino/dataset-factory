#!/usr/bin/env python3
"""Bounded server-side aggregate probes for datasus-sinasc-cesarean-share-decline.

Uses the DATASUS TABNET national SINASC table (Nascidos vivos - Brasil,
/cgi/tabcgi.exe?sinasc/cnv/nvbr.def) with formato=prn so only small
aggregate text crosses the wire. No microdata is downloaded here.

Usage:
  python3 probe_tabnet_parto.py national     # year x parto, all periods (tiny)
  python3 probe_tabnet_parto.py months 2024  # month x parto for one year (tiny)
  python3 probe_tabnet_parto.py mun <year>   # municipality x parto for one year
  python3 probe_tabnet_parto.py transitions  # parse local mun files, base rates
"""
import os
import re
import sys
import time
import urllib.parse
import urllib.request

BASE = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sinasc/cnv/nvbr.def"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

YEAR_FILES = {y: "nvbr%02d.dbf" % (y % 100) for y in range(1994, 2027)}


def post(fields, timeout=120):
    # TABNET pages are iso-8859-1: percent-escape the latin-1 bytes of each
    # value, exactly as a browser would submit from the def page.
    parts = []
    for k, vs in fields:
        vs = [vs] if isinstance(vs, str) else vs
        for v in vs:
            kb = urllib.parse.quote(k.encode("latin-1", "replace"), safe="")
            vb = urllib.parse.quote(v.encode("latin-1", "replace"), safe="/")
            parts.append(kb + "=" + vb)
    body = "&".join(parts).encode("ascii")
    req = urllib.request.Request(BASE, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("latin-1")


def national():
    fields = [
        ("Linha", "Ano_do_nascimento"),
        ("Coluna", "Tipo_de_parto"),
        ("Incremento", "Nascim_p/resid.mãe"),
    ] + [("Arquivos", YEAR_FILES[y]) for y in sorted(YEAR_FILES)]
    fields += [("formato", "prn"), ("mostre", "Mostra")]
    txt = post(fields)
    open(os.path.join(OUT, "national_year_parto.txt"), "w").write(txt)
    print(txt[:3000])


def months(year):
    fields = [
        ("Linha", "Mês_do_nascimento"),
        ("Coluna", "Tipo_de_parto"),
        ("Incremento", "Nascim_p/resid.mãe"),
        ("Arquivos", YEAR_FILES[int(year)]),
        ("formato", "prn"),
        ("mostre", "Mostra"),
    ]
    txt = post(fields)
    open(os.path.join(OUT, "month_%s_parto.txt" % year), "w").write(txt)
    print(txt[:2000])


def mun(year):
    fields = [
        ("Linha", "Município"),
        ("Coluna", "Tipo_de_parto"),
        ("Incremento", "Nascim_p/resid.mãe"),
        ("Arquivos", YEAR_FILES[int(year)]),
        ("formato", "prn"),
        ("mostre", "Mostra"),
    ]
    txt = post(fields)
    path = os.path.join(OUT, "mun_parto_%s.txt" % year)
    open(path, "w").write(txt)
    print("saved %s (%d bytes)" % (path, len(txt)))


MUN_LINE = re.compile(r'^"(\d+)\s+(.*?)";(.*)$')


def parse_mun(path):
    """Return {mun_code: {'name':..,'Vaginal':int,'Cesáreo':int,'Ignorado':int,'Total':int}}"""
    import html as _html

    rows = {}
    header = None
    for raw in open(path, encoding="latin-1"):
        line = _html.unescape(raw).rstrip("\r\n")
        m = MUN_LINE.match(line)
        if not m:
            if line.startswith('"Munic') and ";" in line:
                header = [c.strip().strip('"') for c in line.split(";")]
            continue
        code, name, rest = m.group(1), m.group(2).strip(), m.group(3)
        vals = []
        for v in rest.split(";"):
            v = v.strip().replace(".", "")
            vals.append(int(v) if v.isdigit() else 0)
        rec = {"name": name}
        if header:
            for lab, v in zip(header[1:], vals):
                rec[lab] = v
        else:
            # columns observed in the prn output for these queries:
            # Vaginal;Cesáreo|Cesário;Ignorado;Total  (label varies by query)
            for lab, v in zip(["Vaginal", "Cesáreo", "Ignorado", "Total"], vals):
                rec[lab] = v
        # canonical keys: TABNET labels the cesarean column "Cesáreo" in the
        # national year table and "Cesário" in the municipality table.
        rec["Ces"] = next(
            (v for k, v in rec.items() if k != "Ces" and k.startswith("Ces")), 0
        )
        rows[code] = rec
    return rows


def ces_share(rows, code):
    r = rows.get(code)
    if not r:
        return None
    tot = r.get("Total", 0)
    if not tot:
        return None
    return r.get("Ces", 0), r.get("Vaginal", 0), r.get("Ignorado", 0), tot


def transitions():
    years = [1998, 2000, 2002, 2004, 2009, 2011, 2012, 2014, 2015, 2016, 2017, 2019, 2021, 2022, 2024]
    tables = {}
    for y in years:
        p = os.path.join(OUT, "mun_parto_%d.txt" % y)
        if not os.path.exists(p):
            print("missing", p, "- run 'mun %d' first" % y)
            continue
        tables[y] = parse_mun(p)
    for y in years:
        t = tables.get(y)
        if not t:
            continue
        n_ces = sum(1 for r in t.values() if r.get("Ces", 0) > 0)
        print("year %d: %d municipality rows, %d with Cesáreo>0" % (y, len(t), n_ces))
    for t0, t2 in [(1998, 2000), (2002, 2004), (2009, 2011), (2012, 2014), (2014, 2016), (2017, 2019), (2019, 2021), (2022, 2024)]:
        if t0 not in tables or t2 not in tables:
            continue
        both = set(tables[t0]) & set(tables[t2])
        stats = []
        for floor in (100, 200, 500):
            elig = []
            for c in both:
                a = ces_share(tables[t0], c)
                b = ces_share(tables[t2], c)
                if not a or not b:
                    continue
                if a[3] >= floor and b[3] >= floor:
                    elig.append((b[0] / b[3] - a[0] / a[3]))
            if not elig:
                continue
            n = len(elig)
            dec2 = sum(1 for d in elig if d <= -0.02)
            inc2 = sum(1 for d in elig if d >= 0.02)
            print(
                "transition %d->%d floor>=%d: n=%d  decline>=2pp: %d (%.1f%%)  rise>=2pp: %d (%.1f%%)"
                % (t0, t2, floor, n, dec2, 100.0 * dec2 / n, inc2, 100.0 * inc2 / n)
            )


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "national":
        national()
    elif cmd == "months":
        months(sys.argv[2])
    elif cmd == "mun":
        mun(sys.argv[2])
    elif cmd == "transitions":
        transitions()
    else:
        print(__doc__)
        sys.exit(2)
