"""GEÇİCİ teşhis: SCMP Cosco haberi, Gemini'ye giden metin ve haberin tamamı."""
import sys

sys.path.insert(0, "scripts")
from ayarlar import YZ_OZET_CUMLE  # noqa: E402
from besleme import makale_getir  # noqa: E402
from ozet import basligi_temizle, ozet_olustur  # noqa: E402

url = "https://www.scmp.com/business/china-business/article/3371550/shipping-giant-cosco-launches-new-routes-ride-out-iran-war-climate-risks"
s = makale_getir(url)
if not s:
    print("[TESHIS] alınamadı")
    sys.exit(0)
b = basligi_temizle(s["baslik"], "scmp.com")
uzun = ozet_olustur(s["govde"], b, YZ_OZET_CUMLE, "scmp.com")[:2000]
print(f"[TESHIS] BASLIK: {b}")
print(f"[TESHIS] GOVDE: {len(s['govde'])} harf; GEMINI'YE GIDEN: {len(uzun)} harf")
print(f"[TESHIS] --- GEMINI'YE GIDEN ---")
for p in uzun.split("\n"):
    print(f"[TESHIS] | {p}")
print(f"[TESHIS] --- TAMAMI ---")
for p in s["govde"].split("\n"):
    if p.strip():
        print(f"[TESHIS] | {p.strip()}")
