"""GEÇİCİ teşhis: T24 ve ANKA'ya ham HTTP erişimi (durum kodu, yönlendirme,
içerik türü, gövde başı). Claude/Gemini kullanmaz."""

import re
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
BOSLUK = re.compile(r"\s+")
ADRESLER = [
    "https://t24.com.tr/robots.txt", "https://t24.com.tr/rss", "https://t24.com.tr/rss/haber/gundem",
    "https://t24.com.tr/", "https://t24.com.tr/rss/manset", "https://t24.com.tr/sitemap.xml",
    "https://ankahaber.net/robots.txt", "https://ankahaber.net/", "https://ankahaber.net/rss",
    "https://ankahaber.net/feed", "https://ankahaber.net/rss/manset", "https://ankahaber.net/sitemap.xml",
]
for adres in ADRESLER:
    istek = urllib.request.Request(adres, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(istek, timeout=12) as y:
            veri = y.read(60000)
            gv = veri.decode("utf-8", "replace")
            print(f"[TESHIS] {adres}: {y.status} -> {y.geturl()} | {y.headers.get('content-type')} | {len(veri)} bayt")
            print(f"[TESHIS]    gövde başı: {BOSLUK.sub(' ', gv[:240])!r}")
            for bag in re.findall(r'<link[^>]+(?:rss|atom)[^>]*>', gv, re.I)[:4]:
                print(f"[TESHIS]    LINK: {bag[:200]}")
            for yol in re.findall(r'(?i)sitemap:\s*(\S+)', gv)[:5]:
                print(f"[TESHIS]    SITEMAP: {yol}")
    except urllib.error.HTTPError as hata:
        print(f"[TESHIS] {adres}: HTTP {hata.code} {hata.reason} | {hata.headers.get('server')} | "
              f"{BOSLUK.sub(' ', hata.read(200).decode('utf-8', 'replace'))!r}")
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {adres}: {type(hata).__name__} {str(hata)[:100]}")
