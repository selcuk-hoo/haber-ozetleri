# Geçici: Yemek/Gezi/Sanat & Kültür yazılarının ilk 10 cümlesi (Google'a gitmez).
import re, sys
sys.path.insert(0, "scripts")
from ayarlar import ATLANAN_BOLUMLER, KATEGORI_OZET_CUMLE, KAYNAKLAR
from besleme import ATLANAN_ADRES, besleme_ogeleri, besleme_listesi, makale_getir
from ozet import basligi_temizle, ozet_olustur

for kat, ad, adres in KAYNAKLAR:
    if kat not in ("Yemek", "Gezi", "Sanat & Kültür"):
        continue
    urls, _ = besleme_ogeleri(adres, 12)
    if not urls:
        urls = besleme_listesi(adres, 12)
    atla = ATLANAN_BOLUMLER.get((kat, ad))
    n = 0
    for u in urls:
        if n >= 4:
            break
        if ATLANAN_ADRES.search(u) or (atla and re.search(atla, u)):
            continue
        s = makale_getir(u)
        if not s:
            continue
        b = basligi_temizle(s["baslik"], ad)
        oz = ozet_olustur(s["govde"], b, KATEGORI_OZET_CUMLE[kat], ad)
        if not oz:
            continue
        n += 1
        cumleler = re.split(r'(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9"“(])', oz)
        print(f"\n[TESHIS] ##### {kat} | {ad} | {b} ({len(cumleler)} cümle)")
        for i, c in enumerate(cumleler, 1):
            print(f"[TESHIS] {i:2}. {c[:170]}")
