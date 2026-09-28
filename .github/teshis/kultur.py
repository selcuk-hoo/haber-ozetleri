# Geçici teşhis: Sanat & Kültür için kaliteli kaynak adayları.
import sys
sys.path.insert(0, "scripts")
from besleme import besleme_ogeleri, makale_getir
from ozet import ozet_olustur

ADAYLAR = [
    "https://www.bbc.com/culture/feed.rss",
    "https://feeds.bbci.co.uk/culture/rss.xml",
    "https://www.theartnewspaper.com/rss.xml",
    "https://www.theartnewspaper.com/",
    "https://hyperallergic.com/feed/",
    "https://lithub.com/feed/",
    "https://www.apollo-magazine.com/feed/",
    "https://k24kitap.org/",
    "https://www.k24kitap.org/rss",
    "https://www.theguardian.com/artanddesign/rss",
    "https://www.theguardian.com/books/rss",
    "https://www.theguardian.com/stage/rss",
]
for u in ADAYLAR:
    urls, t = besleme_ogeleri(u, 10)
    print(f"\n[TESHIS] ===== {u}: {len(urls)} öğe")
    for x in urls[:10]:
        print(f"[TESHIS]    {t.get(x, '-')[:16]} {x}")
    for x in urls[:2]:
        s = makale_getir(x)
        if s is None:
            print(f"[TESHIS]    makale_getir=None {x}")
            continue
        print(f"[TESHIS]    BAŞLIK: {s['baslik']} | görsel={'var' if s.get('gorsel') else 'yok'}")
        print(f"[TESHIS]    ÖZET: {ozet_olustur(s['govde'], s['baslik'], 4, 'x')[:450]}")
