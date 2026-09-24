"""GEÇİCİ teşhis 3: AA görselleri başka sitelerden (translate.goog) yükleniyor mu?"""
import re, urllib.request
import feedparser
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

def al(url, ref=None):
    h = dict(UA, Accept="image/avif,image/webp,image/*,*/*;q=0.8")
    if ref: h["Referer"] = ref
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20)

f = feedparser.parse("https://www.aa.com.tr/en/rss/default?cat=turkiye")
for e in f.entries[:4]:
    html = urllib.request.urlopen(urllib.request.Request(e.link, headers=UA), timeout=20).read().decode("utf-8", "replace")
    m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
    if not m:
        print("og:image yok", e.link); continue
    u = m.group(1)
    print("\n", u)
    for ref in (None, "https://selcuk--hoo-github-io.translate.goog/", "https://selcuk-hoo.github.io/haber-ozetleri/"):
        try:
            g = al(u, ref)
            print(f"  HTTP {g.status} {g.headers.get('content-type')} {len(g.read())} bayt ref={ref}"
                  f" CORP={g.headers.get('cross-origin-resource-policy')}")
        except Exception as ex:
            print(f"  HATA ref={ref}: {ex}")
