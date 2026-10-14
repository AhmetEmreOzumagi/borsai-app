"""Resmi kaynak indirme yardımcıları (KAP, SPK). Repo dışı; doğrulama görevi için.

Her istek W/requests.jsonl'e yazılır. KAP istekleri arası >= 3.5 s (dosya kilitli zaman damgası).
"""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

W = Path(__file__).resolve().parent.parent
CACHE = W / "cache"
CACHE.mkdir(exist_ok=True)
LOG = W / "logs" / "requests.jsonl"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) BorsAi-verifier (resmi belge dogrulama)"
KAP_GAP = 3.5
SPK_GAP = 1.0


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _throttle(host: str, gap: float) -> None:
    stamp = W / f".last_{host}"
    with open(W / f".lock_{host}", "a+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            last = float(stamp.read_text()) if stamp.exists() else 0.0
        except ValueError:
            last = 0.0
        wait = last + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        stamp.write_text(str(time.time()))
        fcntl.flock(lk, fcntl.LOCK_UN)


def _log(rec: dict) -> None:
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def http(url: str, data: bytes | None = None, headers: dict | None = None, tries: int = 6) -> tuple[bytes, dict]:
    host = "kap" if "kap.org.tr" in url else ("spk" if "spk.gov.tr" in url else "other")
    gap = KAP_GAP if host == "kap" else SPK_GAP
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    backoff = 10.0
    for attempt in range(tries):
        _throttle(host, gap)
        req = urllib.request.Request(url, data=data, headers=h, method="POST" if data is not None else "GET")
        t = now_utc()
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = resp.read()
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                _log({"url": url, "method": req.get_method(), "status": resp.status, "bytes": len(body),
                      "sha256": sha256(body), "accessed_utc": t,
                      "last_modified": hdrs.get("last-modified"), "post_body": data.decode() if data else None})
                return body, hdrs
        except urllib.error.HTTPError as e:
            _log({"url": url, "method": req.get_method(), "status": e.code, "accessed_utc": t,
                  "post_body": data.decode() if data else None})
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(backoff)
                backoff *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            _log({"url": url, "method": req.get_method(), "status": f"ERR {e}", "accessed_utc": t})
            time.sleep(backoff)
            backoff *= 2
    raise RuntimeError(f"indirilemedi: {url}")


def cached(name: str, url: str, **kw) -> tuple[bytes, dict]:
    """Önbellekli GET; meta (accessed_utc, sha, last_modified) yanında saklanır."""
    p = CACHE / name
    meta_p = CACHE / (name + ".meta.json")
    if p.exists() and meta_p.exists():
        return p.read_bytes(), json.loads(meta_p.read_text())
    body, hdrs = http(url, **kw)
    meta = {"url": url, "accessed_utc": now_utc(), "sha256": sha256(body), "bytes": len(body),
            "last_modified": hdrs.get("last-modified"), "content_type": hdrs.get("content-type")}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return body, meta


# ------------------------------------------------------------------ KAP

def kap_pdf(idx: int | str) -> tuple[bytes, dict]:
    return cached(f"kap/{idx}_bildirim.pdf", f"https://www.kap.org.tr/tr/api/BildirimPdf/{idx}")


def kap_html(idx: int | str) -> tuple[bytes, dict]:
    return cached(f"kap/{idx}_page.html", f"https://www.kap.org.tr/tr/Bildirim/{idx}")


def kap_page_info(idx: int | str) -> dict:
    """Bildirim sayfasından yayın zamanı ve ek listesi (yalnız bu bildirimin alanları)."""
    raw, meta = kap_html(idx)
    h = raw.decode("utf-8", "replace")
    m = re.search(r'publishDate\\":\\"(\d{4})\.(\d{2})\.(\d{2}) (\d{2}:\d{2}:\d{2})\\",\\"disclosureId\\":\\"[0-9a-f]+\\",\\"disclosureIndex\\":' + str(idx) + r'\b', h)
    pub = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}+03:00" if m else None
    s = re.search(r'\\"disclosureIndex\\":' + str(idx) + r',\\"summary\\":\\"((?:[^"\\]|\\\\.)*)\\"', h)
    kt = re.search(r'\\"kapTitle\\":\\"([^"\\]*)\\"', h)
    related = re.search(r'\\"relatedStocks\\":\\"([^"\\]*)\\"', h)
    subj = re.search(r'\\"subject\\":\\"([^"\\]*)\\"', h)
    atts = []
    for mm in re.finditer(r'href="https://www\.kap\.org\.tr/tr/api/file/download/([0-9a-f]{32})">([^<]*)</a>', h):
        if mm.group(1) not in [a[0] for a in atts]:
            atts.append((mm.group(1), mm.group(2)))
    if not atts:
        for fid in dict.fromkeys(re.findall(r'file/download/([0-9a-f]{32})', h)):
            atts.append((fid, ""))
    return {"idx": str(idx), "published_at": pub, "summary": s.group(1) if s else None,
            "kap_title": kt.group(1) if kt else None, "related": related.group(1) if related else None,
            "subject": subj.group(1) if subj else None,
            "attachments": atts, "page_accessed_utc": meta["accessed_utc"]}


def unwrap_java(b: bytes) -> bytes:
    if b[:4] == b"\xac\xed\x00\x05":
        i = b.find(b"%PDF")
        if i >= 0:
            return b[i:]
        # genel: 27 bayt başlık
        return b[27:]
    return b


def kap_attachment(fid: str) -> tuple[bytes, bytes, dict]:
    """(açılmış bayt, ham bayt, meta)."""
    raw, meta = cached(f"kap_att/{fid}.bin", f"https://www.kap.org.tr/tr/api/file/download/{fid}")
    return unwrap_java(raw), raw, meta


def kap_day(day: str) -> tuple[list, dict]:
    """byCriteria bir gün; ham yanıt önbelleğe YAZILMAZ, çağıran süzer."""
    body = json.dumps({"fromDate": day, "toDate": day, "mkkMemberOidList": [], "subjectList": []}).encode()
    raw, hdrs = http("https://www.kap.org.tr/tr/api/disclosure/members/byCriteria", data=body,
                     headers={"Content-Type": "application/json", "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu"})
    return json.loads(raw.decode("utf-8")), {"sha256": sha256(raw), "bytes": len(raw), "accessed_utc": now_utc()}


def kap_day_range(d0: str, d1: str) -> tuple[list, dict]:
    body = json.dumps({"fromDate": d0, "toDate": d1, "mkkMemberOidList": [], "subjectList": []}).encode()
    raw, hdrs = http("https://www.kap.org.tr/tr/api/disclosure/members/byCriteria", data=body,
                     headers={"Content-Type": "application/json", "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu"})
    return json.loads(raw.decode("utf-8")), {"sha256": sha256(raw), "bytes": len(raw), "accessed_utc": now_utc()}


def kap_time(s: str) -> str:
    """'04.02.2020 11:25:10' -> ISO +03:00."""
    d, t = s.split(" ")
    dd, mm, yy = d.split(".")
    return f"{yy}-{mm}-{dd}T{t}+03:00"


# ------------------------------------------------------------------ PDF metni

PY = "/Users/ahmet/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
