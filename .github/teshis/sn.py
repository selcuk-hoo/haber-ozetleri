"""GEÇİCİ teşhis: Science News beslemesinde son haberler ve bizim hattımızın sonucu."""
import sys
sys.path.insert(0, "scripts")
from ayarlar import KAYNAKLAR
from besleme import ATLANAN_ADRES, besleme_ogeleri, makale_getir
from ozet import ozet_olustur
adres = [a for _, ad, a in KAYNAKLAR if ad == "sciencenews.org"][0]
print("besleme:", adres)
urls, tarihler = besleme_ogeleri(adres, 20)
print(len(urls), "öğe")
for u in urls[:14]:
    durum = "ATLANDI (video)" if ATLANAN_ADRES.search(u) else ""
    if not durum:
        m = makale_getir(u)
        durum = "makale alınamadı" if not m else ("özet boş" if not ozet_olustur(m["govde"], m["baslik"], 5, "sciencenews.org") else "OK")
    print(f"  {tarihler.get(u, '-')}  {durum:18} {u}")
