# Geçici teşhis: Yemek kaynaklarının beslemesinde ne var, hangileri elenmiş.
import sys
from datetime import datetime, timezone
sys.path.insert(0, "scripts")
from ayarlar import KAYNAKLAR
from besleme import besleme_ogeleri, makale_getir
from ozet import ozet_olustur, basligi_temizle

print("[TESHIS] şu an", datetime.now(timezone.utc).isoformat())
for kat, ad, adres in KAYNAKLAR:
    if kat != "Yemek":
        continue
    urls, tarihler = besleme_ogeleri(adres, 20)
    print(f"\n[TESHIS] === {ad} ({adres}) — {len(urls)} öğe")
    for u in urls:
        s = makale_getir(u)
        if s is None:
            durum = "makale_getir=None"
        else:
            oz = ozet_olustur(s["govde"], basligi_temizle(s["baslik"], ad), 5, ad)
            durum = f"özet {len(oz)} kr" if oz else "ÖZET BOŞ"
        print(f"[TESHIS]  {tarihler.get(u, '(tarih yok)')[:25]:25} | {durum:18} | {u}")
