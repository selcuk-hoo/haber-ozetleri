"""GEÇİCİ: Türk gazetelerinin RSS beslemeleri var mı, metin alınabiliyor mu?"""
import re, sys
from datetime import datetime, timezone
sys.path.insert(0, "scripts")
import feedparser
import trafilatura
from trafilatura.feeds import find_feed_urls
from besleme import makale_getir

ADAYLAR = {
    "NTV": ["https://www.ntv.com.tr/turkiye.rss", "https://www.ntv.com.tr/gundem.rss", "https://www.ntv.com.tr"],
    "Habertürk": ["https://www.haberturk.com/rss/kategori/gundem.xml", "https://www.haberturk.com/rss", "https://www.haberturk.com"],
    "Hürriyet": ["https://www.hurriyet.com.tr/rss/gundem", "https://www.hurriyet.com.tr/rss/anasayfa", "https://www.hurriyet.com.tr"],
    "Sabah": ["https://www.sabah.com.tr/rss/gundem.xml", "https://www.sabah.com.tr/rss/anasayfa.xml", "https://www.sabah.com.tr"],
    "Sözcü": ["https://www.sozcu.com.tr/feeds-rss-category-gundem", "https://www.sozcu.com.tr/rss/gundem.xml", "https://www.sozcu.com.tr"],
    "Cumhuriyet": ["https://www.cumhuriyet.com.tr/rss/son_dakika.xml", "https://www.cumhuriyet.com.tr/rss", "https://www.cumhuriyet.com.tr"],
    "Milliyet": ["https://www.milliyet.com.tr/rss/rssnew/gundemrss.xml", "https://www.milliyet.com.tr"],
    "BirGün": ["https://www.birgun.net/rss/home", "https://www.birgun.net"],
    "Karar": ["https://www.karar.com/rss", "https://www.karar.com"],
    "TRT Haber": ["https://www.trthaber.com/gundem_articles.rss", "https://www.trthaber.com"],
    "CNN Türk": ["https://www.cnnturk.com/feed/rss/turkiye/news", "https://www.cnnturk.com"],
    "Yeni Şafak": ["https://www.yenisafak.com/rss?xml=gundem", "https://www.yenisafak.com"],
    "Evrensel": ["https://www.evrensel.net/rss/haber.xml", "https://www.evrensel.net"],
    "Bianet": ["https://bianet.org/bianet.rss", "https://bianet.org"],
    "Medyascope": ["https://medyascope.tv/feed/"],
    "Diken": ["https://www.diken.com.tr/feed/"],
    "Halk TV": ["https://halktv.com.tr/service/rss.php", "https://halktv.com.tr"],
    "Gazete Oksijen": ["https://gazeteoksijen.com/rss", "https://gazeteoksijen.com"],
    "Dünya": ["https://www.dunya.com/rss", "https://www.dunya.com"],
    "Bloomberg HT": ["https://www.bloomberght.com/rss", "https://www.bloomberght.com"],
}
simdi = datetime.now(timezone.utc)


def besleme_dene(adres):
    ham = trafilatura.fetch_url(adres)
    if not ham:
        return None, "indirilemedi"
    d = feedparser.parse(ham)
    if d.entries:
        return d, ""
    return None, "besleme değil"


for ad, adresler in ADAYLAR.items():
    bulunan, notlar = None, []
    for adres in adresler:
        if not adres.endswith((".com", ".tr", ".org", ".net", ".tv")) or "rss" in adres or "feed" in adres:
            d, hata = besleme_dene(adres)
            if d:
                bulunan = (adres, d)
                break
            notlar.append(f"{adres}: {hata}")
        else:
            try:
                for f in find_feed_urls(adres)[:0] or []:
                    pass
                ham = trafilatura.fetch_url(adres)
                adaylar = re.findall(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*href="([^"]+)"', ham or "")
                notlar.append(f"{adres}: anasayfa {'alındı' if ham else 'indirilemedi'}, link: {adaylar[:3]}")
                for a in adaylar[:3]:
                    a = a if a.startswith("http") else adres.rstrip("/") + "/" + a.lstrip("/")
                    d, _ = besleme_dene(a)
                    if d:
                        bulunan = (a, d)
                        break
                if bulunan:
                    break
            except Exception as h:  # noqa: BLE001
                notlar.append(f"{adres}: {h!r}")
    if not bulunan:
        print(f"[TESHIS] ### {ad}: YOK  " + " | ".join(notlar)[:400])
        continue
    adres, d = bulunan
    tarihler = []
    for o in d.entries:
        t = o.get("published_parsed") or o.get("updated_parsed")
        if t:
            tarihler.append(datetime(*t[:6], tzinfo=timezone.utc))
    son24 = sum((simdi - t).total_seconds() < 86400 for t in tarihler)
    en_yeni = max(tarihler).strftime("%d.%m %H:%M") if tarihler else "-"
    print(f"[TESHIS] ### {ad}: {adres}  öğe={len(d.entries)} tarihli={len(tarihler)} son24sa={son24} en_yeni={en_yeni}")
    for o in d.entries[:2]:
        s = makale_getir(o.link)
        ham = trafilatura.fetch_url(o.link) or ""
        duvar = "DUVAR" if re.search(r'isAccessibleForFree"?\s*:\s*"?false', ham, re.I) else ""
        if s:
            print(f"[TESHIS]   {o.title[:70]} | metin={len(s['govde'])} harf {duvar} | {s['govde'][:120]!r}")
        else:
            print(f"[TESHIS]   {o.title[:70]} | METİN ALINAMADI {duvar} {o.link[:80]}")
