#!/usr/bin/env python3
"""Probe: Korea KOSIS/KMA access posture (2026-10-22). Documents the signup/key walls."""
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (scout-research; dataset-factory)"}

def get(url, limit=60000):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            return r.status, r.read(limit)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:600]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode()

st, body = get("https://kosis.kr/openapi/")
text = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
for kw in ("인증키", "활용신청", "회원가입"):
    print("kosis.kr/openapi contains", kw, "->", kw in text)
for url in ("https://data.kma.go.kr/data/", "https://data.kma.go.kr/member/login.do"):
    st, body = get(url, limit=8000)
    print(url, "-> HTTP", st, "len", len(body), "(JS shell if ~1872 bytes)")
