"""GEÇİCİ teşhis: Anadolu Ajansı (İngilizce) kaynak olarak uygun mu?"""
import sys, urllib.request
sys.path.insert(0, "scripts")
from besleme import besleme_ogeleri, makale_getir
from ozet import ozet_olustur

ADAYLAR = [
    "https://www.aa.com.tr/en/rss/default?cat=guncel",
    "https://www.aa.com.tr/en/rss/default?cat=turkiye",
    "https://www.aa.com.tr/en/rss/default?cat=world",
    "https://www.aa.com.tr/en",
]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

for aday in ADAYLAR:
    try:
        r = urllib.request.urlopen(urllib.request.Request(aday, headers=UA), timeout=20)
        print(f"HTTP {r.status} {r.headers.get('content-type')} {aday}")
    except Exception as e:
        print(f"HTTP HATA {aday}: {e}")
    urls, tarihler = besleme_ogeleri(aday, 12)
    print(f"  besleme: {len(urls)} öğe, {len(tarihler)} tarihli")
    for u in urls[:12]:
        print("   ", tarihler.get(u, "-"), u)

urls, tarihler = besleme_ogeleri(ADAYLAR[0], 12) or ([], {})
if not urls:
    urls, tarihler = besleme_ogeleri(ADAYLAR[3], 12)
for u in urls[:6]:
    m = makale_getir(u)
    print("\n====", u)
    if not m:
        print("  makale alınamadı"); continue
    print("  başlık:", m["baslik"])
    print("  sayfa tarihi:", m["tarih"], "| besleme tarihi:", tarihler.get(u, "-"))
    print("  görsel:", m["gorsel"])
    if m["gorsel"]:
        for ref in (None, "https://selcuk--hoo-github-io.translate.goog/"):
            h = dict(UA)
            if ref: h["Referer"] = ref
            try:
                g = urllib.request.urlopen(urllib.request.Request(m["gorsel"], headers=h), timeout=20)
                print(f"  görsel HTTP {g.status} {g.headers.get('content-type')} referer={ref}")
            except Exception as e:
                print(f"  görsel HATA referer={ref}: {e}")
    print("  ham gövde başı:", m["govde"][:500].replace("\n", " "))
    print("  ÖZET:", ozet_olustur(m["govde"], m["baslik"], 5, "aa.com.tr"))
