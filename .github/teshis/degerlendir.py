# Geçici: yeni özet penceresi ve bağlamlı başlık çevirisi, eskisiyle yan yana.
import sys, time
sys.path.insert(0, "scripts")
import ozet as ozet_mod
from besleme import besleme_ogeleri, makale_getir
from ceviri import google_cevir
from olaylar import ilk_cumleler
from ozet import basligi_temizle, ozet_olustur

KAYNAKLAR = [
    ("theguardian.com", "https://www.theguardian.com/food/rss"),
    ("bbc.com", "https://www.bbc.com/culture/feed.rss"),
    ("theguardian.com", "https://www.theguardian.com/culture/rss"),
    ("theartnewspaper.com", "https://www.theartnewspaper.com/rss.xml"),
    ("bbc.co.uk", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("dw.com", "https://rss.dw.com/rdf/rss-en-world"),
    ("aa.com.tr", "https://www.aa.com.tr/en/rss/default?cat=turkiye"),
    ("phys.org", "https://phys.org/rss-feed/"),
    ("cntraveler.com", "https://www.cntraveler.com/"),
    ("saveur.com", "https://www.saveur.com/feed/"),
    ("tr.euronews.com", "https://tr.euronews.com/rss?level=vertical&name=culture"),
]
yeni_pencere = ozet_mod._en_iyi_pencere
toplam = degisen = 0
ornekler = []
for ad, adres in KAYNAKLAR:
    urls, _ = besleme_ogeleri(adres, 5)
    for u in urls[:5]:
        s = makale_getir(u)
        if not s:
            continue
        baslik = basligi_temizle(s["baslik"], ad)
        ozet_mod._en_iyi_pencere = lambda c, b, k: c[:k]
        eski = ozet_olustur(s["govde"], baslik, 5, ad)
        ozet_mod._en_iyi_pencere = yeni_pencere
        yeni = ozet_olustur(s["govde"], baslik, 5, ad)
        toplam += 1
        if ad != "tr.euronews.com":
            ornekler.append((baslik, yeni))
        if eski != yeni:
            degisen += 1
            print(f"\n[TESHIS] ##### {ad} | {baslik}\n[TESHIS] ESKİ: {eski[:600]}\n[TESHIS] YENİ: {yeni[:600]}")
print(f"\n[TESHIS] özet: {toplam} yazının {degisen} tanesinde pencere kaydı")

print("\n[TESHIS] ===== Başlık çevirisi: tek başına / bağlamlı")
for baslik, oz in ornekler[:30]:
    try:
        tek = google_cevir(baslik)
        time.sleep(0.2)
        bag = google_cevir(baslik + "\n" + ilk_cumleler(oz, 1))
        satirlar = [x.strip() for x in bag.split("\n") if x.strip()]
        time.sleep(0.2)
    except Exception as h:
        print("[TESHIS] hata", h); break
    isaret = "  " if tek == satirlar[0] else "≠ "
    print(f"[TESHIS] {isaret}{baslik}\n[TESHIS]      tek: {tek}\n[TESHIS]      bağ: {satirlar[0] if satirlar else '?'} (satır={len(satirlar)})")
