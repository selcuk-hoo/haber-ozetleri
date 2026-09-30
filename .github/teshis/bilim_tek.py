"""GEÇİCİ teşhis: Bilim ve Teknoloji etiketleri ve aday kaynaklar."""

import re
import sys
from collections import Counter

sys.path.insert(0, "scripts")
from trafilatura import fetch_url  # noqa: E402

import besleme  # noqa: E402


def adaylar(adres, n):
    urls, tarihler = besleme.besleme_ogeleri(adres, n)
    if not urls:
        urls = besleme.besleme_listesi(adres, n)
    return urls, tarihler


for ad, adres, n in [("theverge", "https://www.theverge.com/rss/index.xml", 25),
                     ("techcrunch", "https://techcrunch.com/feed/", 20),
                     ("phys.org", "https://phys.org/rss-feed/", 25)]:
    urls, _ = adaylar(adres, n)
    say = Counter()
    print(f"[TESHIS] ===== {ad}: {len(urls)}")
    for url in urls[:n]:
        s = besleme.makale_getir(url) or {}
        say.update(s.get("etiketler", []))
        print(f"[TESHIS] {s.get('baslik', '')[:80]} || {s.get('etiketler', [])[:8]}")
    print(f"[TESHIS] sık etiketler: {say.most_common(25)}")


def duvar(html):
    isaret = []
    for a, k in [("ucretsiz=false", r'"isAccessibleForFree"\s*:\s*"?(?:false|False)'), ("paywall", r"paywall"),
                 ("subscribe", r"(?i)subscribe to (?:continue|read)")]:
        n = len(re.findall(k, html))
        if n:
            isaret.append(f"{a}:{n}")
    return ",".join(isaret) or "-"


for ad, adres in [
    ("quanta", "https://www.quantamagazine.org/feed/"),
    ("knowable", "https://knowablemagazine.org/rss"),
    ("ars bilim", "https://feeds.arstechnica.com/arstechnica/science"),
    ("eos", "https://eos.org/feed"),
    ("ars", "https://feeds.arstechnica.com/arstechnica/index"),
    ("theregister", "https://www.theregister.com/headlines.atom"),
    ("mit tech review", "https://www.technologyreview.com/feed/"),
    ("webrazzi", "https://webrazzi.com/feed/"),
]:
    try:
        urls, tarihler = adaylar(adres, 30)
        son = sorted((t for t in tarihler.values() if t), reverse=True)
        print(f"[TESHIS] == {ad}: {len(urls)} öğe, tarihli {len(son)}, son {son[:2]}, 10. {son[9:10]}, 20. {son[19:20]}")
        for url in urls[:6]:
            html = fetch_url(url) or ""
            s = besleme.makale_getir(url) or {}
            print(f"[TESHIS]   metin={len(s.get('govde', ''))} duvar={duvar(html)} gorsel={'var' if s.get('gorsel') else 'yok'}"
                  f" etiket={s.get('etiketler', [])[:6]}")
            print(f"[TESHIS]     {s.get('baslik', '')[:95]} | {s.get('govde', '')[:200]!r}")
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {ad}: HATA {hata!r}")
