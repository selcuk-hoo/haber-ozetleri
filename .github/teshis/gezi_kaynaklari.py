"""GEÇİCİ teşhis: aday gezi kaynakları ve abonelik duvarı işaretleri."""

import re
import sys

sys.path.insert(0, "scripts")
from trafilatura import fetch_url  # noqa: E402

import besleme  # noqa: E402

ADAYLAR = [
    ("cntraveler.com", "https://www.cntraveler.com/"),
    ("bonappetit.com", "https://www.bonappetit.com/feed/rss"),
    ("lonelyplanet.com", "https://www.lonelyplanet.com/"),
    ("theguardian.com/travel", "https://www.theguardian.com/travel/rss"),
    ("bbc.com/travel", "https://www.bbc.com/travel/feed.rss"),
    ("atlasobscura.com", "https://www.atlasobscura.com/feeds/latest"),
    ("afar.com", "https://www.afar.com/"),
    ("travelandleisure.com", "https://www.travelandleisure.com/"),
]


def duvar_isaretleri(html: str) -> str:
    isaretler = []
    for ad, kalip in [
        ("ucretsiz=false", r'"isAccessibleForFree"\s*:\s*"?(?:false|False)'),
        ("ucretsiz=true", r'"isAccessibleForFree"\s*:\s*"?(?:true|True)'),
        ("paywall", r"paywall"),
        ("subscribe-to-continue", r"(?i)subscribe to (?:continue|read)"),
        ("metered", r"(?i)meter(?:ed)?[-_ ]?(?:paywall|wall|count)"),
    ]:
        n = len(re.findall(kalip, html))
        if n:
            isaretler.append(f"{ad}:{n}")
    return ",".join(isaretler) or "-"


for ad, adres in ADAYLAR:
    try:
        urls, tarihler = besleme.besleme_ogeleri(adres, 30)
        if not urls:
            urls = besleme.besleme_listesi(adres, 30)
        son = sorted((t for t in tarihler.values() if t), reverse=True)[:3]
        print(f"[TESHIS] {ad}: {len(urls)} öğe, son tarihler {son}")
        for url in urls[:4]:
            html = fetch_url(url) or ""
            sonuc = besleme.makale_getir(url)
            govde = (sonuc or {}).get("govde", "")
            print(f"[TESHIS]   {url}")
            print(f"[TESHIS]     html={len(html)} metin={len(govde)} duvar={duvar_isaretleri(html)}"
                  f" etiket={(sonuc or {}).get('etiketler', [])[:6]}")
            print(f"[TESHIS]     {(sonuc or {}).get('baslik', '')[:90]} | {govde[:160]!r}")
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {ad}: HATA {hata!r}")
