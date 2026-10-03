"""GEÇİCİ teşhis: (A) yeni kaynak adayları (CNA, The Diplomat), (B) Gemini
özeti ile mevcut "ilk N cümle" özetinin karşılaştırması. Anahtar loga
yazılmaz; Gemini'ye tek istek gider."""

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "scripts")
import gemini_ceviri  # noqa: E402
from besleme import besleme_ogeleri, makale_getir  # noqa: E402
from ceviri import onbellegi_yukle  # noqa: E402
from ozet import ozet_olustur  # noqa: E402

# (A) Kaynak adayları
ADAYLAR = [
    ("CNA Asya", "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511"),
    ("CNA Dünya", "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6311"),
    ("CNA Son", "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml"),
    ("The Diplomat", "https://thediplomat.com/feed/"),
]


def ham(url):
    try:
        istek = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(istek, timeout=20) as y:
            return y.read(400000).decode("utf-8", "replace")
    except Exception as h:  # noqa: BLE001
        return f"HATA {h!r}"


for ad, adres in ADAYLAR:
    urls, tarihler = besleme_ogeleri(adres, 12)
    print(f"[TESHIS] ===== {ad}: {len(urls)} öğe; tarihler: {sorted(tarihler.values(), reverse=True)[:4]}")
    for url in urls[:4]:
        m = makale_getir(url)
        if not m:
            print(f"[TESHIS]   ALINAMADI {url}")
            continue
        sayfa = ham(url)
        duvar = ("isAccessibleForFree\":false" in sayfa.replace(" ", "") or "paywall" in sayfa.lower()
                 or "subscribe to read" in sayfa.lower())
        ozet = ozet_olustur(m["govde"], m["baslik"], 5, "")
        print(f"[TESHIS]   {m['tarih']} | {m['baslik'][:90]} | metin {len(m['govde'])} harf | görsel {'var' if m['gorsel'] else 'YOK'}"
              f" | duvar {'VAR?' if duvar else 'yok'} | etiketler {m['etiketler'][:6]}")
        print(f"[TESHIS]     özet: {ozet[:400]}")

# (B) Gemini özeti karşılaştırması
ORNEKLER = [("Gündem", "bbc.co.uk", "https://feeds.bbci.co.uk/news/world/rss.xml"),
            ("Gündem", "aljazeera.com", "https://www.aljazeera.com/xml/rss/all.xml"),
            ("Teknoloji", "theverge.com", "https://www.theverge.com/rss/index.xml"),
            ("Teknoloji", "arstechnica.com", "https://feeds.arstechnica.com/arstechnica/index"),
            ("Bilim", "sciencenews.org", "https://www.sciencenews.org/feed")]
onbellek = onbellegi_yukle(Path("dist/ceviri.json"))
metinler, bilgi = {}, {}
for kat, kaynak, adres in ORNEKLER:
    urls, _ = besleme_ogeleri(adres, 6)
    alinan = 0
    for url in urls:
        if alinan == 2:
            break
        m = makale_getir(url)
        if not m:
            continue
        alinan += 1
        k = f"o{len(metinler)}"
        metinler[k] = ozet_olustur(m["govde"], m["baslik"], 12, kaynak)[:2000]
        bilgi[k] = (kat, kaynak, m["baslik"], ozet_olustur(m["govde"], m["baslik"], 5, kaynak),
                    onbellek.get(url, {}).get("o", "(önbellekte çevirisi yok)"))

TALIMAT = """Sen bir Türk haber sitesinin editörüsün. Her metin bir haberin ilk paragrafları
(İngilizce). Her biri için Türkçe 2-3 cümlelik bir özet yaz: haberin asıl bilgisini
ver (ne oldu, kim, nerede, neden önemli). Sahne kuran giriş, anekdot ya da alıntıyla
başlama; okur ilk cümlede haberi öğrensin. Yalnız metindeki bilgiyi kullan, yorum ve
tahmin ekleme; sayı, isim ve tarihleri değiştirme; "reportedly", "allegedly" gibi
kesinlik kayıtlarını koru ("bildirildi", "iddia edildi"); kişi, kurum ve yayın adlarını
çevirme; ABD başkanı için "ABD Başkanı" de. Metin içinde tırnak gerekirse “ ” kullan.
Yalnız JSON döndür: {"o0": "...", ...}"""
try:
    cevap = gemini_ceviri.metin_uret("gemini-flash-lite-latest", TALIMAT, json.dumps(metinler, ensure_ascii=False))
    ozetler = json.loads(cevap[cevap.index("{"):cevap.rindex("}") + 1])
except Exception as h:  # noqa: BLE001
    print(f"[TESHIS] Gemini hatası: {h!r}")
    ozetler = {}
print(f"[TESHIS] Gemini kullanımı: {gemini_ceviri.kullanim_ozeti()}")
for k, (kat, kaynak, baslik, ozet, tr) in bilgi.items():
    print(f"[TESHIS] ===== {k} [{kat} / {kaynak}] {baslik}")
    print(f"[TESHIS] EN (şimdiki, ilk 5 cümle): {ozet[:700]}")
    print(f"[TESHIS] TR (şimdiki çeviri): {tr[:700]}")
    print(f"[TESHIS] GEMINI ÖZETİ: {ozetler.get(k)}")
