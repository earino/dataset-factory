#!/usr/bin/env python3
"""Probe 5: enumerate proposicoes + proposicoesAutores year-file availability.

HEAD every proposicoes-{ano}.csv and proposicoesAutores-{ano}.csv for
1991-2025, print sizes, and verify the download budget assumption for the
worker build (~35 files per family). Also verifies the HTTP status for
the first and last year of each family.
"""
import urllib.error
import urllib.request

BASE = "https://dadosabertos.camara.leg.br/arquivos/{family}/csv/{family}-{ano}.csv"
UA = {"User-Agent": "dataset-factory/camara-probe5"}


def head(url):
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, int(resp.headers.get("Content-Length") or 0), \
                resp.headers.get("Last-Modified")
    except urllib.error.HTTPError as error:
        return error.code, 0, None
    except Exception as error:  # noqa: BLE001 - report and continue
        return f"ERR:{error}", 0, None


def main():
    for family in ("proposicoes", "proposicoesAutores"):
        total, missing = 0, []
        sizes = {}
        for year in range(1991, 2026):
            status, size, modified = head(BASE.format(family=family, ano=year))
            sizes[year] = (status, size)
            if status == 200:
                total += size
            else:
                missing.append((year, status))
        print(f"== {family}: 200-OK years {35 - len(missing)}/35, "
              f"total {total:,} bytes ({total / 1e6:.1f} MB)")
        print("   missing:", missing if missing else "none")
        for year in (1991, 2005, 2014, 2022, 2025):
            print(f"   {year}: {sizes[year]}")


if __name__ == "__main__":
    main()
