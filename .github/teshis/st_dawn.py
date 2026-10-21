"""GEÇİCİ teşhis: Straits Times (Asya) ve Dawn beslemeleri: paywall, bölüm, etiket, tarih."""
import re
import sys

import trafilatura

sys.path.insert(0, "scripts")
from besleme import besleme_ogeleri, makale_getir  # noqa: E402

KAPALI = re.compile(r'isAccessibleForFree"?\s*:\s*"?false', re.I)


def tara(ad, adres, n, goster_paywall):
    try:
        urls, tarihler = besleme_ogeleri(adres, n)
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {ad}: HATA {hata!r}")
        return
    print(f"[TESHIS] ==== {ad} ({adres}): {len(urls)} öğe, besleme tarihi {len(tarihler)}")
    kapali = 0
    for u in urls[:n]:
        s = makale_getir(u)
        if not s:
            print(f"[TESHIS]   ALINAMADI {u[-70:]}")
            continue
        pw = ""
        if goster_paywall:
            h = trafilatura.fetch_url(u) or ""
            if KAPALI.search(h):
                kapali += 1
                pw = " PAYWALL"
        yol = re.sub(r"^https?://[^/]+", "", u)[:60]
        print(f"[TESHIS]   {len(s['govde']):5d}{pw} | {yol} | {s['baslik'][:60]} | etiket={list(s.get('etiketler', ()))[:4]} | tarih={'var' if s['tarih'] else 'YOK'}")
    if goster_paywall:
        print(f"[TESHIS]   paywall: {kapali}/{min(n, len(urls))}")


tara("Straits Times Asya", "https://www.straitstimes.com/news/asia/rss.xml", 20, True)
for ad, adres in (("Dawn world", "https://www.dawn.com/feeds/world"), ("Dawn home", "https://www.dawn.com/feeds/home"),
                  ("Dawn latest", "https://www.dawn.com/feeds/latest-news")):
    tara(ad, adres, 10, False)
