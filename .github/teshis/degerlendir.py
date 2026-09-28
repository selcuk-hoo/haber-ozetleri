# Geçici: başlık çevirisi tek başına / özetin ilk cümlesiyle birlikte.
import sys, time
sys.path.insert(0, "scripts")
from besleme import besleme_ogeleri, makale_getir
from ceviri import google_cevir
from olaylar import ilk_cumleler
from ozet import basligi_temizle, ozet_olustur

KAYNAKLAR = [
    ("theguardian.com", "https://www.theguardian.com/food/rss"),
    ("bbc.com", "https://www.bbc.com/culture/feed.rss"),
    ("theguardian.com", "https://www.theguardian.com/culture/rss"),
    ("theverge.com", "https://www.theverge.com/rss/index.xml"),
    ("bbc.co.uk", "https://feeds.bbci.co.uk/news/world/rss.xml"),
]
ornekler = []
for ad, adres in KAYNAKLAR:
    urls, _ = besleme_ogeleri(adres, 4)
    for u in urls[:4]:
        s = makale_getir(u)
        if s:
            b = basligi_temizle(s["baslik"], ad)
            ornekler.append((b, ozet_olustur(s["govde"], b, 5, ad)))
farkli = 0
for baslik, oz in ornekler:
    try:
        tek = google_cevir(baslik)
        time.sleep(1.5)
        bag = google_cevir(baslik + "\n" + ilk_cumleler(oz, 1))
        time.sleep(1.5)
    except Exception as h:
        print("[TESHIS] hata", h)
        break
    satirlar = [x.strip() for x in bag.split("\n") if x.strip()]
    ilk = satirlar[0] if satirlar else "?"
    farkli += tek != ilk
    print(f"[TESHIS] {'≠' if tek != ilk else ' '} {baslik}\n[TESHIS]      tek: {tek}\n[TESHIS]      bağ: {ilk}  (satır={len(satirlar)})")
print(f"[TESHIS] {len(ornekler)} başlığın {farkli} tanesinde çeviri farklı")
