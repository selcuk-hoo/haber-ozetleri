# Geçici teşhis: Euronews Türkçe bölüm beslemeleri + yemek kaynağı adayları.
import re, sys, urllib.request
sys.path.insert(0, "scripts")
from besleme import besleme_ogeleri, makale_getir
from ozet import ozet_olustur

def indir(u):
    try:
        r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(r, timeout=20).read().decode("utf-8", "replace")
    except Exception as h:
        return f"HATA {h}"

print("[TESHIS] ===== Euronews bölüm beslemeleri")
for ad in ["travel", "news", "culture", "business", "next", "green"]:
    u = f"https://tr.euronews.com/rss?level=vertical&name={ad}"
    urls, t = besleme_ogeleri(u, 8)
    print(f"[TESHIS] {ad}: {len(urls)} öğe")
    for x in urls[:8]:
        print(f"[TESHIS]    {t.get(x,'-')[:16]} {x}")

print("[TESHIS] ===== Euronews genel beslemedeki yazıların bölüm bilgisi")
urls, _ = besleme_ogeleri("https://tr.euronews.com/rss", 15)
for x in urls:
    h = indir(x)
    bolum = re.findall(r'"articleSection"\s*:\s*"?([^",\]]+)', h)[:2]
    meta = re.findall(r'<meta[^>]+(?:property|name)="article:section"[^>]+content="([^"]+)"', h)[:2]
    dikey = re.findall(r'"vertical"\s*:\s*"([^"]+)"', h)[:2]
    print(f"[TESHIS]  section={bolum} meta={meta} vertical={dikey} | {x}")

ADAYLAR = [
    "https://www.foodinlife.com.tr/", "https://www.foodinlife.com.tr/feed/",
    "https://www.refikaninmutfagi.com/feed/", "https://www.refikaninmutfagi.com/",
    "https://www.yemekvekultur.com/", "https://www.vedatmilor.com/feed/",
    "https://www.lezzet.com.tr/", "https://culinarybackstreets.com/feed/",
    "https://www.tasteatlas.com/", "https://www.theguardian.com/food/rss",
]
for u in ADAYLAR:
    urls, t = besleme_ogeleri(u, 10)
    print(f"\n[TESHIS] ===== {u}: {len(urls)} öğe")
    for x in urls[:10]:
        print(f"[TESHIS]    {t.get(x,'-')[:16]} {x}")
    for x in urls[:2]:
        s = makale_getir(x)
        if s is None:
            print(f"[TESHIS]    makale_getir=None {x}")
            continue
        print(f"[TESHIS]    BAŞLIK: {s['baslik']} | GÖRSEL: {'var' if s.get('gorsel') else 'yok'}")
        print(f"[TESHIS]    ÖZET: {ozet_olustur(s['govde'], s['baslik'], 5, 'x')[:500]}")
