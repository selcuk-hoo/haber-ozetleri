# Geçici teşhis: yemek kaynağı adayları (durum kodu, besleme bağlantıları).
import re, sys, urllib.request
sys.path.insert(0, "scripts")
from besleme import besleme_ogeleri, makale_getir
from ozet import ozet_olustur

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
def indir(u):
    try:
        r = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"})
        y = urllib.request.urlopen(r, timeout=20)
        return y.status, y.headers.get("content-type", ""), y.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as h:
        return h.code, "", ""
    except Exception as h:
        return 0, str(h)[:80], ""

SITELER = {
    "foodinlife": ["https://www.foodinlife.com.tr/", "https://www.foodinlife.com.tr/rss", "https://www.foodinlife.com.tr/feed", "https://foodinlife.com.tr/"],
    "refika": ["https://www.refikaninmutfagi.com/", "https://refikaninmutfagi.com/feed/", "https://www.refikaninmutfagi.com/rss"],
    "yemekvekultur": ["https://www.yemekvekultur.com/", "https://yemekvekultur.com/feed/"],
    "vedatmilor": ["https://www.vedatmilor.com/", "https://vedatmilor.com/feed/"],
    "culinarybackstreets": ["https://culinarybackstreets.com/", "https://culinarybackstreets.com/feed/", "https://culinarybackstreets.com/rss"],
    "ozlemsturkishtable": ["https://ozlemsturkishtable.com/feed/"],
    "yemek.com": ["https://yemek.com/", "https://yemek.com/feed/", "https://yemek.com/rss/"],
    "lezzet": ["https://www.lezzet.com.tr/", "https://www.lezzet.com.tr/rss"],
    "gastromondiale": ["https://www.gastromondiale.com/feed/"],
    "tasteatlas": ["https://www.tasteatlas.com/"],
    "seriouseats": ["https://www.seriouseats.com/"],
    "foodandwine": ["https://www.foodandwine.com/"],
}
for ad, adresler in SITELER.items():
    print(f"\n[TESHIS] ===== {ad}")
    for u in adresler:
        kod, tur, govde = indir(u)
        linkler = re.findall(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*>', govde)[:3]
        besleme_mi = govde.lstrip().startswith("<?xml") or "<rss" in govde[:500]
        print(f"[TESHIS]  {kod} {tur[:30]} besleme={besleme_mi} {u}")
        for l in linkler:
            print(f"[TESHIS]     link: {l[:160]}")
        if besleme_mi:
            ogeler = re.findall(r"<(?:pubDate|updated|published)>([^<]+)<", govde)[:5]
            print(f"[TESHIS]     tarihler: {ogeler}")
            urls, t = besleme_ogeleri(u, 3)
            print(f"[TESHIS]     feedparser: {len(urls)} öğe")
            for x in urls[:1]:
                s = makale_getir(x)
                if s:
                    print(f"[TESHIS]     {s['baslik']} | görsel={'var' if s.get('gorsel') else 'yok'}")
                    print(f"[TESHIS]     {ozet_olustur(s['govde'], s['baslik'], 3, 'x')[:400]}")
                else:
                    print(f"[TESHIS]     makale_getir=None {x}")
