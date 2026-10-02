"""GEÇİCİ teşhis: T24 ve ANKA site haritaları ve makale metinleri.
Claude/Gemini kullanmaz."""

import collections
import re
import sys
import urllib.request

sys.path.insert(0, "scripts")
import besleme  # noqa: E402
from ozet import ozet_olustur  # noqa: E402
from trafilatura import fetch_url  # noqa: E402

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BOSLUK = re.compile(r"\s+")
SPOR = re.compile(r"/(spor|magazin|sporx|yasam|saglik|teknoloji|otomobil|sinema|muzik|tv|astroloji|ekonomi)/", re.I)


def al(adres, sinir=400000):
    istek = urllib.request.Request(adres, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(istek, timeout=15) as y:
        return y.read(sinir).decode("utf-8", "replace")


def duvar(html):
    isaret = []
    for ad, kalip in [("ucretsiz=false", r'"isAccessibleForFree"\s*:\s*"?(?:false|False)'), ("paywall", r"paywall"),
                      ("abone", r"(?i)abone ol|premium"), ("login", r"(?i)giriş yap(?:arak| ve)")]:
        n = len(re.findall(kalip, html))
        if n:
            isaret.append(f"{ad}:{n}")
    return ",".join(isaret) or "-"


for site, ana, haritalar in [
    ("t24", "https://t24.com.tr/", ["https://t24.com.tr/sitemap.xml"]),
    ("ankahaber.net", "https://ankahaber.net/", ["https://ankahaber.net/sitemap-index.xml"]),
]:
    print(f"[TESHIS] ########## {site}")
    for harita in haritalar:
        try:
            gv = al(harita)
            yerler = re.findall(r"<loc>([^<]+)</loc>", gv)
            son = re.findall(r"<lastmod>([^<]+)</lastmod>", gv)
            print(f"[TESHIS] {harita}: {len(yerler)} <loc>, lastmod örnek {son[:2]}")
            for y in yerler[:14]:
                print(f"[TESHIS]    {y}")
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] {harita}: {type(hata).__name__} {str(hata)[:80]}")
    try:
        urls = besleme.besleme_listesi(ana, 40)
    except Exception as hata:  # noqa: BLE001
        urls = []
        print(f"[TESHIS] besleme_listesi hata: {type(hata).__name__}")
    print(f"[TESHIS] besleme_listesi({ana}): {len(urls)} adres")
    for u in urls[:12]:
        print(f"[TESHIS]    {u}")
    bolum = collections.Counter(re.sub(r"^https?://[^/]+/([^/]+)/.*", r"\1", u) for u in urls)
    print(f"[TESHIS] bölümler: {bolum.most_common(10)}; spor/magazin vb.: {sum(1 for u in urls if SPOR.search(u))}/{len(urls)}")
    for u in urls[:8]:
        s = besleme.makale_getir(u)
        if not s:
            print(f"[TESHIS] --- {u}\n[TESHIS]   makale alınamadı")
            continue
        try:
            html = al(u)
        except Exception:  # noqa: BLE001
            html = ""
        print(f"[TESHIS] --- {u}")
        print(f"[TESHIS]   başlık: {s['baslik'][:100]} | tarih={s['tarih'] or '-'} metin={len(s['govde'])} "
              f"duvar={duvar(html)} görsel={'var' if s['gorsel'] else 'yok'} etiket={s['etiketler'][:6]}")
        print(f"[TESHIS]   HAM: {BOSLUK.sub(' ', s['govde'][:280])!r}")
        print(f"[TESHIS]   ÖZET: {ozet_olustur(s['govde'], s['baslik'], 3, site)[:400]}")
