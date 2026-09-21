import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
from trafilatura.feeds import find_feed_urls
import feedparser

HEDEFLER = [
    "https://www.dailysabah.com/rss/turkiye",
    "https://www.themoscowtimes.com/rss/news",
]

print(f"[TESHIS] su an: {datetime.now(timezone.utc).isoformat()}", file=sys.stderr)

for url in HEDEFLER:
    print(f"\n[TESHIS] === {url} ===", file=sys.stderr)

    d = feedparser.parse(url)
    print(f"[TESHIS] feedparser: bozo={d.get('bozo')} girdi={len(d.entries)}", file=sys.stderr)
    print("[TESHIS] feedparser HAM SIRASI (ilk 6):", file=sys.stderr)
    for e in d.entries[:6]:
        print(f"[TESHIS]   {e.get('published', e.get('updated','(tarih yok)'))} | {e.get('link')}", file=sys.stderr)

    try:
        ffu = find_feed_urls(url)
    except Exception as hata:
        print(f"[TESHIS] find_feed_urls HATA: {hata}", file=sys.stderr)
        continue
    print(f"[TESHIS] find_feed_urls: {len(ffu)} url döndürdü", file=sys.stderr)
    print("[TESHIS] find_feed_urls SIRASI (ilk 10):", file=sys.stderr)
    for u in ffu[:10]:
        print(f"[TESHIS]   {u}", file=sys.stderr)

    # feedparser'in ilk 5 linki find_feed_urls'un ilk 10'u icinde var mi?
    feedparser_ilk5 = [e.get("link") for e in d.entries[:5]]
    ffu_ilk10 = set(ffu[:10])
    for link in feedparser_ilk5:
        print(f"[TESHIS]   feedparser'in yeni linki find_feed_urls ilk10'da mi? {link in ffu_ilk10} | {link}", file=sys.stderr)
