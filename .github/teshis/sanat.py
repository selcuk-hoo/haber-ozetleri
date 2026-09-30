"""GEÇİCİ teşhis: Sanat & Kültür etiketleri ve aday kaynaklar."""

import re
import sys

sys.path.insert(0, "scripts")
from trafilatura import fetch_url  # noqa: E402

import besleme  # noqa: E402


def adaylar(adres, n):
    urls, tarihler = besleme.besleme_ogeleri(adres, n)
    if not urls:
        urls = besleme.besleme_listesi(adres, n)
    return urls, tarihler


for ad, adres, n in [("guardian kültür", "https://www.theguardian.com/culture/rss", 30),
                     ("euronews kültür", "https://tr.euronews.com/rss?level=vertical&name=culture", 25),
                     ("scmp sanat", "https://www.scmp.com/lifestyle/arts-culture", 12)]:
    urls, _ = adaylar(adres, n)
    print(f"[TESHIS] ===== {ad}: {len(urls)}")
    for url in urls[:n]:
        s = besleme.makale_getir(url) or {}
        print(f"[TESHIS] {'/'.join(url.split('/')[3:5])[:20]:20} {s.get('baslik', '')[:85]} || {s.get('etiketler', [])[:9]}")


def duvar(html):
    isaret = []
    for a, k in [("ucretsiz=false", r'"isAccessibleForFree"\s*:\s*"?(?:false|False)'), ("paywall", r"paywall"),
                 ("subscribe", r"(?i)subscribe to (?:continue|read)")]:
        n = len(re.findall(k, html))
        if n:
            isaret.append(f"{a}:{n}")
    return ",".join(isaret) or "-"


for ad, adres in [
    ("guardian klasik", "https://www.theguardian.com/music/classicalmusicandopera/rss"),
    ("smithsonian", "https://www.smithsonianmag.com/rss/arts-culture/"),
    ("aeon", "https://aeon.co/feed.rss"),
    ("hyperallergic", "https://hyperallergic.com/feed/"),
    ("lithub", "https://lithub.com/feed/"),
    ("dezeen", "https://www.dezeen.com/feed/"),
    ("artnews", "https://www.artnews.com/feed/"),
    ("japantimes kültür", "https://www.japantimes.co.jp/culture/feed/"),
]:
    try:
        urls, tarihler = adaylar(adres, 30)
        son = sorted((t for t in tarihler.values() if t), reverse=True)
        print(f"[TESHIS] == {ad}: {len(urls)} öğe, tarihli {len(son)}, son {son[:2]}, 10. {son[9:10]}")
        for url in urls[:7]:
            html = fetch_url(url) or ""
            s = besleme.makale_getir(url) or {}
            print(f"[TESHIS]   metin={len(s.get('govde', ''))} duvar={duvar(html)} etiket={s.get('etiketler', [])[:6]}")
            print(f"[TESHIS]     {s.get('baslik', '')[:95]} | {s.get('govde', '')[:170]!r}")
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {ad}: HATA {hata!r}")
