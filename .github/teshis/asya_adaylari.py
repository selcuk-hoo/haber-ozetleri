"""GEÇİCİ teşhis: SCMP'ye Asya'dan alternatif kaynak adayları (besleme, tarih, metin boyu, paywall)."""
import re
import statistics
import sys

import trafilatura

sys.path.insert(0, "scripts")
from besleme import besleme_ogeleri, makale_getir  # noqa: E402

ADAYLAR = {
    "Japan Times": ["https://www.japantimes.co.jp/feed/"],
    "Korea Herald": ["https://www.koreaherald.com/rss/newsAll", "https://www.koreaherald.com/common/rss_xml.php?ct=102"],
    "Korea JoongAng Daily": ["https://koreajoongangdaily.joins.com/rss/news.xml",
                             "https://koreajoongangdaily.joins.com/rss"],
    "Korea Times": ["https://www.koreatimes.co.kr/www/rss/world.xml", "https://www.koreatimes.co.kr/www/rss/nation.xml"],
    "Focus Taiwan": ["https://focustaiwan.tw/rss/aall.xml", "https://focustaiwan.tw/rss"],
    "Taipei Times": ["https://www.taipeitimes.com/xml/index.rss"],
    "Mainichi": ["https://mainichi.jp/english/rss/etc/english_news.rss", "https://mainichi.jp/rss/etc/english.rss"],
    "Straits Times Asia": ["https://www.straitstimes.com/news/asia/rss.xml"],
    "Bangkok Post": ["https://www.bangkokpost.com/rss/data/topstories.xml", "https://www.bangkokpost.com/rss/data/world.xml"],
    "Jakarta Post": ["https://www.thejakartapost.com/rss", "https://www.thejakartapost.com/feed"],
    "VnExpress International": ["https://e.vnexpress.net/rss/news.rss"],
    "Rappler": ["https://www.rappler.com/feed/"],
    "Dawn": ["https://www.dawn.com/feeds/home"],
    "Indian Express World": ["https://indianexpress.com/section/world/feed/"],
    "Sixth Tone": ["https://www.sixthtone.com/rss", "https://www.sixthtone.com/feed"],
    "Nikkei Asia": ["https://asia.nikkei.com/rss/feed/nar"],
}
for ad, adresler in ADAYLAR.items():
    urls, tarihler = [], {}
    kullanilan = ""
    for adres in adresler:
        try:
            urls, tarihler = besleme_ogeleri(adres, 10)
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] {ad}: {adres} hata {hata!r}")
            continue
        if urls:
            kullanilan = adres
            break
    if not urls:
        print(f"[TESHIS] {ad}: BESLEME YOK / BOŞ")
        continue
    boylar, kapali, basliklar = [], 0, []
    for u in urls[:5]:
        s = makale_getir(u)
        if not s:
            continue
        boylar.append(len(s["govde"]))
        basliklar.append(s["baslik"][:80])
        h = trafilatura.fetch_url(u) or ""
        if re.search(r'isAccessibleForFree"?\s*:\s*"?false', h, re.I):
            kapali += 1
    print(f"[TESHIS] {ad}: besleme={len(urls)} öğe, tarihli={len(tarihler)}, makale={len(boylar)}, "
          f"medyan_boy={int(statistics.median(boylar)) if boylar else 0}, en_kisa={min(boylar) if boylar else 0}, "
          f"paywall={kapali}/{len(boylar)}  [{kullanilan}]")
    for b in basliklar[:3]:
        print(f"[TESHIS]     - {b}")
