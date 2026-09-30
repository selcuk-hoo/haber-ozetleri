"""GEÇİCİ teşhis: Guardian gezi etiketleri ve Bon Appétit'e aday yemek kaynakları."""

import re
import sys

sys.path.insert(0, "scripts")
from trafilatura import fetch_url  # noqa: E402

import besleme  # noqa: E402

print("[TESHIS] === Guardian Travel etiketleri ===")
urls, _ = besleme.besleme_ogeleri("https://www.theguardian.com/travel/rss", 30)
for url in urls[:30]:
    s = besleme.makale_getir(url) or {}
    print(f"[TESHIS] {s.get('baslik', '')[:80]} || {s.get('etiketler', [])}")

ADAYLAR = [
    ("seriouseats.com", "https://www.seriouseats.com/"),
    ("foodandwine.com", "https://www.foodandwine.com/"),
    ("tastecooking.com", "https://tastecooking.com/feed/"),
    ("gastro obscura", "https://www.atlasobscura.com/feeds/gastro-obscura"),
    ("gastro obscura 2", "https://www.gastroobscura.com/feed"),
    ("food52.com", "https://food52.com/blog.rss"),
]


def duvar(html: str) -> str:
    isaret = []
    for ad, kalip in [("ucretsiz=false", r'"isAccessibleForFree"\s*:\s*"?(?:false|False)'),
                      ("paywall", r"paywall"), ("subscribe", r"(?i)subscribe to (?:continue|read)")]:
        n = len(re.findall(kalip, html))
        if n:
            isaret.append(f"{ad}:{n}")
    return ",".join(isaret) or "-"


for ad, adres in ADAYLAR:
    try:
        urls, tarihler = besleme.besleme_ogeleri(adres, 30)
        if not urls:
            urls = besleme.besleme_listesi(adres, 30)
        son = sorted((t for t in tarihler.values() if t), reverse=True)
        print(f"[TESHIS] === {ad}: {len(urls)} öğe, tarihli {len(son)}, son {son[:3]}, 7. {son[6:7]}")
        for url in urls[:8]:
            html = fetch_url(url) or ""
            s = besleme.makale_getir(url) or {}
            print(f"[TESHIS]   {url}")
            print(f"[TESHIS]     metin={len(s.get('govde', ''))} duvar={duvar(html)} tarih={s.get('tarih', '')[:10]}"
                  f" etiket={s.get('etiketler', [])[:8]}")
            print(f"[TESHIS]     {s.get('baslik', '')[:90]} | {s.get('govde', '')[:200]!r}")
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {ad}: HATA {hata!r}")
