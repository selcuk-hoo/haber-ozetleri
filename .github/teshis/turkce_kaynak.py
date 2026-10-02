"""GEÇİCİ teşhis: T24 ve ANKA'nın EN YENİ haberleri (site haritasının
sonu), makale metni ve besleme izleri. Claude/Gemini kullanmaz."""

import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "scripts")
import besleme  # noqa: E402
from ozet import ozet_olustur  # noqa: E402

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BOSLUK = re.compile(r"\s+")


def al(adres, sinir=6_000_000):
    istek = urllib.request.Request(adres, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(istek, timeout=20) as y:
        return y.read(sinir).decode("utf-8", "replace")


def loclar(gv):
    return re.findall(r"<loc>([^<]+)</loc>", gv)


def makale_yaz(site, urls):
    for u in urls:
        s = besleme.makale_getir(u)
        print(f"[TESHIS] --- {u}")
        if not s:
            print("[TESHIS]   makale alınamadı")
            continue
        print(f"[TESHIS]   başlık: {s['baslik'][:100]} | tarih={s['tarih'] or '-'} metin={len(s['govde'])} "
              f"görsel={'var' if s['gorsel'] else 'yok'} etiket={s['etiketler'][:6]}")
        print(f"[TESHIS]   HAM: {BOSLUK.sub(' ', s['govde'][:300])!r}")
        print(f"[TESHIS]   ÖZET: {ozet_olustur(s['govde'], s['baslik'], 3, site)[:350]}")


print("[TESHIS] ########## t24")
try:
    ana = al("https://t24.com.tr/", 400000)
    izler = re.findall(r'[^"\s]{0,60}(?:rss|feed|atom)[^"\s]{0,40}', ana, re.I)[:8]
    print(f"[TESHIS] anasayfa rss/feed/atom geçen yerler: {izler}")
except Exception as hata:  # noqa: BLE001
    print(f"[TESHIS] anasayfa: {type(hata).__name__}")
try:
    harita = loclar(al("https://t24.com.tr/sitemap.xml"))
    gunlukler = [y for y in harita if re.search(r"sitemap-\d{8}\.xml", y)]
    print(f"[TESHIS] günlük haritalar: {len(gunlukler)}; son 3: {gunlukler[-3:]}")
    bugun = datetime.now(timezone.utc) + timedelta(hours=3)
    toplanan = []
    for gun in range(0, 3):
        ad = (bugun - timedelta(days=gun)).strftime("%Y%m%d")
        adres = f"https://media-cdn.t24.com.tr/media/sitemaps/sitemap-{ad}.xml"
        try:
            gv = al(adres)
            yerler = [y for y in loclar(gv) if "t24.com.tr" in y]
            print(f"[TESHIS] {adres}: {len(yerler)} adres; örnek: {yerler[:3]}; "
                  f"lastmod/yayın etiketleri: {re.findall(r'<(?:lastmod|news:publication_date)>([^<]+)<', gv)[:2]}")
            toplanan += yerler
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] {adres}: {type(hata).__name__} {str(hata)[:80]}")
    makale_yaz("t24", toplanan[-8:])
except Exception as hata:  # noqa: BLE001
    print(f"[TESHIS] t24 harita hata: {type(hata).__name__} {str(hata)[:100]}")

print("[TESHIS] ########## ankahaber.net")
try:
    for no in (7, 6):
        gv = al(f"https://ankahaber.net/sitemap/{no}.xml")
        yerler = loclar(gv)
        print(f"[TESHIS] sitemap/{no}.xml: {len(yerler)} adres; ilk {yerler[:1]} son {yerler[-3:]}; "
              f"lastmod {re.findall(r'<lastmod>([^<]+)<', gv)[:1]}...{re.findall(r'<lastmod>([^<]+)<', gv)[-1:]}")
        if no == 7:
            son = [y for y in yerler if "/haber/detay/" in y][-8:]
    makale_yaz("ankahaber.net", son)
except Exception as hata:  # noqa: BLE001
    print(f"[TESHIS] anka hata: {type(hata).__name__} {str(hata)[:100]}")
