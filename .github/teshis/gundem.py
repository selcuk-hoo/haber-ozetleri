"""GEÇİCİ teşhis: Gündem kaynaklarının bölüm/etiketleri ve aday kaynaklar."""

import re
import sys
from collections import Counter

sys.path.insert(0, "scripts")
from trafilatura import fetch_url  # noqa: E402

import besleme  # noqa: E402

MEVCUT = [
    ("aljazeera.com", "https://www.aljazeera.com/"),
    ("cnn.com", "https://www.cnn.com/"),
    ("scmp.com", "https://www.scmp.com/"),
    ("france24.com", "https://www.france24.com/en/rss"),
    ("aa.com.tr", "https://www.aa.com.tr/en/rss/default?cat=turkiye"),
    ("tr.euronews.com", "https://tr.euronews.com/rss"),
]
ADAYLAR = [
    ("bbc türkçe", "https://feeds.bbci.co.uk/turkce/rss.xml"),
    ("dw türkçe", "https://rss.dw.com/rdf/rss-tur-all"),
    ("africanews", "https://www.africanews.com/feed/rss"),
    ("africanews ana", "https://www.africanews.com/"),
    ("kyodo", "https://english.kyodonews.net/rss/all.xml"),
    ("nhk world", "https://www3.nhk.or.jp/nhkworld/en/news/"),
    ("batimes", "https://www.batimes.com.ar/feed"),
    ("mercopress", "https://en.mercopress.com/rss/"),
    ("the hindu", "https://www.thehindu.com/news/international/feeder/default.rss"),
]


def adaylari_al(adres, n):
    urls, tarihler = besleme.besleme_ogeleri(adres, n)
    if not urls:
        urls = besleme.besleme_listesi(adres, n)
    return urls, tarihler


def duvar(html: str) -> str:
    isaret = []
    for ad, kalip in [("ucretsiz=false", r'"isAccessibleForFree"\s*:\s*"?(?:false|False)'),
                      ("paywall", r"paywall"), ("subscribe", r"(?i)subscribe to (?:continue|read)")]:
        n = len(re.findall(kalip, html))
        if n:
            isaret.append(f"{ad}:{n}")
    return ",".join(isaret) or "-"


print("[TESHIS] ===== MEVCUT =====")
for ad, adres in MEVCUT:
    try:
        urls, _ = adaylari_al(adres, 40)
        bolumler = Counter("/".join(u.split("/")[3:6]) for u in urls)
        print(f"[TESHIS] == {ad}: {len(urls)} aday; bölümler {bolumler.most_common(12)}")
        for url in urls[:14]:
            s = besleme.makale_getir(url) or {}
            print(f"[TESHIS]   {url[:110]} || {s.get('baslik', '')[:80]} || {s.get('etiketler', [])[:8]}")
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {ad}: HATA {hata!r}")

print("[TESHIS] ===== ADAYLAR =====")
for ad, adres in ADAYLAR:
    try:
        urls, tarihler = adaylari_al(adres, 40)
        son = sorted((t for t in tarihler.values() if t), reverse=True)
        print(f"[TESHIS] == {ad}: {len(urls)} öğe, tarihli {len(son)}, son {son[:2]}, 10. {son[9:10]}, 25. {son[24:25]}")
        for url in urls[:6]:
            html = fetch_url(url) or ""
            s = besleme.makale_getir(url) or {}
            print(f"[TESHIS]   {url[:110]}")
            print(f"[TESHIS]     metin={len(s.get('govde', ''))} duvar={duvar(html)} tarih={s.get('tarih', '')[:10]}"
                  f" gorsel={'var' if s.get('gorsel') else 'yok'} etiket={s.get('etiketler', [])[:6]}")
            print(f"[TESHIS]     {s.get('baslik', '')[:90]} | {s.get('govde', '')[:220]!r}")
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {ad}: HATA {hata!r}")
