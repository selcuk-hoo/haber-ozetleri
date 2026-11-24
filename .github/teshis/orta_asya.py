"""Geçici teşhis: Orta Asya kaynak adayları (besleme, tarih, metin, duvar)."""
import re
import sys

import trafilatura

sys.path.insert(0, "scripts")
from besleme import besleme_ogeleri, makale_getir  # noqa: E402

ADAYLAR = {
    "eurasianet": "https://eurasianet.org/rss",
    "timesca": "https://timesca.com/feed/",
    "kun.uz": "https://kun.uz/en/news/rss",
    "24.kg": "https://24.kg/english/rss/",
    "astanatimes": "https://astanatimes.com/feed/",
    "akipress": "https://akipress.com/rss/news_en.rss",
}
for ad, adres in ADAYLAR.items():
    try:
        urller, tarihler = besleme_ogeleri(adres, 30)
    except Exception as h:  # noqa: BLE001
        print(f"[TESHIS] {ad}: HATA {h!r}")
        continue
    t = sorted((tarihler.get(u, "") for u in urller), reverse=True)
    print(f"[TESHIS] {ad}: {len(urller)} öğe; en yeni {t[:1]} en eski {t[-1:]}")
    for u in urller[:4]:
        s = makale_getir(u)
        sayfa = trafilatura.fetch_url(u) or ""
        duvar = "DUVAR" if re.search(r'isAccessibleForFree"?\s*:\s*"?false|paywall', sayfa, re.I) else ""
        if not s:
            print(f"[TESHIS]   ✗ {u}")
            continue
        print(f"[TESHIS]   {tarihler.get(u,'')[:16]} | {len(s['govde'])} harf {duvar} | {s['baslik'][:95]}")

# RFE/RL: Orta Asya beslemelerini bul
sayfa = trafilatura.fetch_url("https://www.rferl.org/rssfeeds") or ""
for adres, ad in re.findall(r'href="(/api/[^"]+)"[^>]*>([^<]{2,60})<', sayfa):
    if re.search(r"Central Asia|Kazakh|Kyrgyz|Tajik|Turkmen|Uzbek", ad):
        print(f"[TESHIS] rferl besleme: {ad.strip()} https://www.rferl.org{adres}")
print(f"[TESHIS] rferl rssfeeds sayfası {len(sayfa)} harf")
