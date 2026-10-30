"""Reproduce the CBK access/licence/archive evidence for cbk-tbill-auction-rate-direction.

Usage: python3 probe_cbk.py [--keep]
Every step is read-only; artifacts land in a scratch dir next to this script.
Note: the coordinator resolver NXDOMAINs www.centralbank.go.ke; fetches pin the IP
(192.124.249.9, resolved via dns.google on 2026-10-30). Re-resolve before reuse.
"""
import re
import subprocess
import sys
import time

IP = "192.124.249.9"  # re-resolve: curl -sS 'https://dns.google/resolve?name=www.centralbank.go.ke'
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
BASE = "https://www.centralbank.go.ke"


def fetch(path, out):
    url = BASE + path if path.startswith("/") else path
    cmd = ["curl", "-sS", "-L", "--resolve", f"www.centralbank.go.ke:443:{IP}",
           "--max-time", "30", "-A", UA, url, "-o", out, "-w",
           "HTTP %{http_code} bytes %{size_download} time %{time_total}s\n"]
    subprocess.run(cmd, check=True)


def main():
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    scratch = f"probe-out-{stamp}"
    subprocess.run(["mkdir", "-p", scratch], check=True)

    # 1. The archive page: status + link census
    fetch("/bills-bonds/treasury-bills/", f"{scratch}/tbills.html")
    raw = open(f"{scratch}/tbills.html", encoding="utf-8", errors="replace").read()
    links = sorted(set(re.findall(r'href="([^"]+\.pdf)"', raw)))
    dates = set()
    for link in links:
        for m in re.findall(r"(\d{1,2})[-.](\d{1,2})[-.](20\d\d)", link):
            d, mn, y = m
            dates.add(f"{y}-{int(mn):02d}-{int(d):02d}")
    print(f"distinct pdf links: {len(links)}; dated results: {len(dates)}",
          f"earliest {min(dates) if dates else '-'} latest {max(dates) if dates else '-'}")

    # 2. The licence channels
    for path in ["/privacypolicy/", "/terms", "/terms-of-use", "/disclaimer",
                 "/privacy-policy", "/legal", "/robots.txt", "/sitemap.xml"]:
        r = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
                            "--resolve", f"www.centralbank.go.ke:443:{IP}",
                            "--max-time", "20", "-A", UA, BASE + path],
                           capture_output=True, text=True)
        print(f"terms-path {path}: HTTP {r.stdout.strip()}")
    raw = open(f"{scratch}/tbills.html", encoding="utf-8", errors="replace").read()
    foot = re.findall(r"(?is)<footer.*?</footer>", raw)
    print("footer ©:", re.findall(r"©[^<]{0,60}", foot[0]) if foot else "none")

    # 3. One auction PDF: fetch + text-extract (pypdf) + notice grep
    href = next(h for h in links if "2705" in h and h.startswith("/uploads"))
    from urllib.parse import quote
    fetch(quote(href.replace(BASE, ""), safe="/"), f"{scratch}/auction.pdf")
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    reader = PdfReader(f"{scratch}/auction.pdf")
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    open(f"{scratch}/auction.txt", "w").write(text)
    notices = [l.strip() for l in text.splitlines()
               if re.search(r"(?i)copyright|©|rights|attribut|reproduc|licen[cs]e|disclaimer", l)]
    print(f"auction pdf pages: {len(reader.pages)}; notice lines: {notices or 'NONE'}")
    print("first 30 text lines:")
    for line in text.splitlines()[:30]:
        print("  ", line)
    print(f"scratch dir: {scratch} (pass --keep to retain; deleted otherwise)")
    if "--keep" not in sys.argv:
        subprocess.run(["rm", "-rf", scratch], check=True)


if __name__ == "__main__":
    main()
