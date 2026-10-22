"""GEÇİCİ: soru başlıklı haberlerde cevap Gemini'ye giden kesitte mi?"""
import re, sys
sys.path.insert(0, "scripts")
import feedparser
from besleme import makale_getir
from ozet import ozet_olustur
from ayarlar import YZ_OZET_CUMLE

URL = "https://www.aljazeera.com/news/2026/10/22/facebooks-wrongdoing-why-has-meta-been-fined-25bn-in-new-mexico"
adaylar = [("'Facebook's wrongdoing': Why has Meta been fined $25bn in New Mexico?", URL)]
for kaynak, adres in [("aljazeera.com", "https://www.aljazeera.com/xml/rss/all.xml"),
                      ("bbc.co.uk", "https://feeds.bbci.co.uk/news/world/rss.xml"),
                      ("france24.com", "https://www.france24.com/en/rss")]:
    for o in feedparser.parse(adres).entries[:40]:
        if o.title.strip().endswith("?") and o.link != URL:
            adaylar.append((o.title, o.link))
for baslik, url in adaylar[:8]:
    kaynak = re.search(r"https?://(?:www\.|feeds\.)?([^/]+)", url).group(1)
    kaynak = {"bbc.com": "bbc.co.uk"}.get(kaynak, kaynak)
    s = makale_getir(url)
    if not s:
        print(f"[TESHIS] alinamadi {url}")
        continue
    tam = ozet_olustur(s["govde"], baslik, 200, kaynak)
    uzun = ozet_olustur(s["govde"], baslik, YZ_OZET_CUMLE, kaynak)[:2000]
    u20 = ozet_olustur(s["govde"], baslik, 20, kaynak)[:4500]
    print(f"[TESHIS] === {baslik}\n[TESHIS] tam={len(tam)} uzun12={len(uzun)} uzun20={len(u20)}")
    if "Cambridge" in tam:
        print(f"[TESHIS] Cambridge konumu tam={tam.find('Cambridge')} 12'de={'Cambridge' in uzun} 20'de={'Cambridge' in u20}")
    print("[TESHIS] TAM: " + tam[:5000].replace("\n", " / "))
