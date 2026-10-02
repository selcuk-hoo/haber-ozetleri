"""GEÇİCİ teşhis: T24 ve ANKA. Besleme adresi bulma, öğe sayısı/tarihler,
makale metni, abonelik duvarı işaretleri, spor/magazin payı, özet
temizliği. Claude/Gemini kullanmaz."""

import collections
import re
import sys
import urllib.request

sys.path.insert(0, "scripts")
import besleme  # noqa: E402
from ozet import ozet_olustur  # noqa: E402
from trafilatura import fetch_url  # noqa: E402

SITELER = {
    "t24": ["https://t24.com.tr/rss", "https://t24.com.tr/rss/haber/gundem", "https://t24.com.tr/"],
    "anka": ["https://www.ankahaber.net/rss", "https://www.ankahaber.net/rss/manset", "https://www.ankahaber.net/",
             "https://ankahaber.net/rss", "https://www.anka.com.tr/rss", "https://anka.com.tr/"],
}
SPOR = re.compile(r"/(spor|magazin|sporx|yasam|saglik|teknoloji|otomobil|sinema|muzik|tv|astroloji)/", re.I)


def duvar(html):
    isaret = []
    for ad, kalip in [("ucretsiz=false", r'"isAccessibleForFree"\s*:\s*"?(?:false|False)'), ("paywall", r"paywall"),
                      ("abone", r"(?i)abone ol|üye ol ve oku|premium"), ("login", r"(?i)giriş yap(?:arak| ve)")]:
        n = len(re.findall(kalip, html))
        if n:
            isaret.append(f"{ad}:{n}")
    return ",".join(isaret) or "-"


for site, adresler in SITELER.items():
    print(f"[TESHIS] ########## {site}")
    calisan = None
    for adres in adresler:
        try:
            urls, tarihler = besleme.besleme_ogeleri(adres, 40)
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] {adres}: HATA {type(hata).__name__}")
            continue
        print(f"[TESHIS] {adres}: {len(urls)} öğe, tarihli {len(tarihler)}")
        if urls and calisan is None:
            calisan = (adres, urls, tarihler)
    if not calisan:
        # Ana sayfadaki besleme adayları
        for adres in adresler[-1:]:
            print(f"[TESHIS] anasayfa besleme adayları ({adres}): {besleme._anasayfa_besleme_adaylari(adres)[:8]}")
        try:
            html = fetch_url(adresler[-1]) or ""
            bag = re.findall(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*>', html)
            print(f"[TESHIS] link rel alternate: {bag[:5]}")
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] anasayfa okunamadı: {type(hata).__name__}")
        continue
    adres, urls, tarihler = calisan
    print(f"[TESHIS] SEÇİLEN besleme: {adres}")
    bolum = collections.Counter(re.sub(r"^https?://[^/]+/([^/]+)/.*", r"\1", u) for u in urls)
    print(f"[TESHIS] adres bölümleri: {bolum.most_common(12)}")
    print(f"[TESHIS] spor/magazin vb. adres payı: {sum(1 for u in urls if SPOR.search(u))}/{len(urls)}")
    ts = sorted(tarihler.values(), reverse=True)
    print(f"[TESHIS] tarihler: ilk {ts[:2]}, 10. {ts[9:10]}, 20. {ts[19:20]}, son {ts[-1:]}")
    for u in urls[:10]:
        s = besleme.makale_getir(u)
        if not s:
            print(f"[TESHIS] --- {u}\n[TESHIS]   makale alınamadı")
            continue
        html = fetch_url(u) or ""
        print(f"[TESHIS] --- {u}")
        print(f"[TESHIS]   başlık: {s['baslik'][:100]} | metin={len(s['govde'])} duvar={duvar(html)} "
              f"görsel={'var' if s['gorsel'] else 'yok'} etiket={s['etiketler'][:6]}")
        print(f"[TESHIS]   HAM: {s['govde'][:260]!r}")
        print(f"[TESHIS]   ÖZET: {ozet_olustur(s['govde'], s['baslik'], 3, site)[:400]}")
