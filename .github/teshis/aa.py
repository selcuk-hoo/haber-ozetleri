"""GEÇİCİ teşhis 2: Anadolu Ajansı haberlerinin görseli nerede?"""
import re, sys, urllib.request
import feedparser
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

def al(url, ref=None):
    h = dict(UA)
    if ref: h["Referer"] = ref
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20)

f = feedparser.parse("https://www.aa.com.tr/en/rss/default?cat=turkiye")
e = f.entries[0]
print("RSS alanları:", sorted(e.keys()))
for k in ("media_content", "media_thumbnail", "enclosures", "links", "image"):
    if k in e: print(" ", k, "=", e[k])
print("  summary:", (e.get("summary") or "")[:600])

for e in f.entries[:3]:
    print("\n====", e.link)
    html = al(e.link).read().decode("utf-8", "replace")
    for m in re.findall(r"<meta[^>]+(?:image|img)[^>]*>|<link[^>]+image_src[^>]*>", html, re.I):
        print("  META", m[:300])
    imgs = re.findall(r"<img[^>]+>", html)
    print("  img sayısı:", len(imgs))
    for m in imgs[:12]:
        print("  IMG", m[:250])
    ld = re.findall(r'"image"\s*:\s*(\{[^}]*\}|\[[^\]]*\]|"[^"]*")', html)
    print("  JSON-LD image:", ld[:3])
    aday = re.search(r'https://cdnuploads\.aa\.com\.tr/[^"\'\s>]+\.(?:jpg|jpeg|png|webp)', html)
    if aday:
        u = aday.group(0)
        for ref in (None, "https://selcuk--hoo-github-io.translate.goog/", "https://selcuk-hoo.github.io/"):
            try:
                g = al(u, ref); print(f"  görsel HTTP {g.status} {g.headers.get('content-type')} ref={ref} {u}")
            except Exception as ex:
                print(f"  görsel HATA ref={ref}: {ex}")
