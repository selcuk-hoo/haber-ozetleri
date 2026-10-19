"""GEÇİCİ teşhis: Euronews Türkçe haberinin tam metni ve sitedeki özeti."""
import sys

sys.path.insert(0, "scripts")
from besleme import makale_getir  # noqa: E402
from ozet import basligi_temizle, ozet_olustur  # noqa: E402

url = "https://tr.euronews.com/2026/10/19/polonyada-bir-anne-yurumek-istemeyen-iki-oglunu-dag-yolunda-yalniz-birakti"
s = makale_getir(url)
if not s:
    print("[TESHIS] alınamadı")
    sys.exit(0)
b = basligi_temizle(s["baslik"], "tr.euronews.com")
print(f"[TESHIS] BASLIK: {b}")
print(f"[TESHIS] SITEDEKI OZET (5 cümle): {ozet_olustur(s['govde'], b, 5, 'tr.euronews.com')}")
print(f"[TESHIS] GOVDE UZUNLUK: {len(s['govde'])} harf, {s['govde'].count(chr(10))} satır")
for satir in s["govde"].splitlines():
    if satir.strip():
        print(f"[TESHIS] | {satir.strip()}")
