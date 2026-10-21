"""GEÇİCİ teşhis: kaynak başına çekilen makale metni uzunlukları (SCMP kısalığı yaygın mı?)."""
import re
import statistics
import sys

import trafilatura

sys.path.insert(0, "scripts")
from ayarlar import KAYNAKLAR, TURKCE_KAYNAKLAR, YZ_OZET_KATEGORILERI  # noqa: E402
from besleme import besleme_ogeleri, makale_getir  # noqa: E402

for kategori, ad, adres in KAYNAKLAR:
    if kategori not in YZ_OZET_KATEGORILERI or ad in TURKCE_KAYNAKLAR or ad == "t24.com.tr":
        continue
    try:
        urls, _ = besleme_ogeleri(adres, 12 if ad == "scmp.com" else 8)
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {kategori}/{ad} besleme hatası {hata!r}")
        continue
    boylar, kisalar = [], []
    for u in urls[:7]:
        s = makale_getir(u)
        if not s:
            continue
        boylar.append(len(s["govde"]))
        if len(s["govde"]) < 1200:
            kisalar.append((len(s["govde"]), u.rsplit("/", 1)[-1][:60]))
    if boylar:
        print(f"[TESHIS] {kategori}/{ad}: n={len(boylar)} medyan={int(statistics.median(boylar))} "
              f"en_kisa={min(boylar)} 1200 altı={len(kisalar)}")
        for k in kisalar[:3]:
            print(f"[TESHIS]    kısa: {k}")
# SCMP: ham sayfada paywall işareti
for kategori, ad, adres in KAYNAKLAR:
    if ad == "scmp.com":
        urls, _ = besleme_ogeleri(adres, 6)
        for u in urls[:3]:
            h = trafilatura.fetch_url(u) or ""
            print(f"[TESHIS] SCMP ham sayfa {len(h)} harf; isAccessibleForFree="
                  f"{re.findall(r'isAccessibleForFree[^,]{0,20}', h)[:2]}; paywall={len(re.findall('paywall', h, re.I))}")
        break
