import urllib.request
import feedparser
import sys
from datetime import datetime, timezone

HEDEFLER = [
    "https://www.dailysabah.com/rss/turkiye",
    "https://www.themoscowtimes.com/rss/news",
]

print(f"[TESHIS] su an: {datetime.now(timezone.utc).isoformat()}", file=sys.stderr)

for url in HEDEFLER:
    print(f"\n[TESHIS] === {url} ===", file=sys.stderr)
    try:
        istek = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; haber-ozetleri-teshis/1.0)",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        })
        with urllib.request.urlopen(istek, timeout=20) as yanit:
            veri = yanit.read()
            print(f"[TESHIS] HTTP {yanit.status}, boyut={len(veri)}", file=sys.stderr)
            onemli_basliklar = ["cache-control", "age", "cf-cache-status", "x-cache",
                                 "last-modified", "etag", "expires", "date", "server", "via"]
            for b in onemli_basliklar:
                deger = yanit.headers.get(b)
                if deger:
                    print(f"[TESHIS]   {b}: {deger}", file=sys.stderr)
    except Exception as hata:
        print(f"[TESHIS] HATA: {hata}", file=sys.stderr)
        continue

    d = feedparser.parse(veri)
    print(f"[TESHIS] bozo={d.get('bozo')} girdi={len(d.entries)}", file=sys.stderr)
    for e in d.entries[:5]:
        print(f"[TESHIS]   {e.get('published', e.get('updated','(tarih yok)'))} | {e.get('link')}", file=sys.stderr)
