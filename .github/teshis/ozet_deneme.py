"""GEÇİCİ teşhis: (1) kalıntı görülen kaynakların İngilizce özetleri,
(2) mevcut özet ile Claude'un yazdığı özetin karşılaştırması."""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
import haber_uret  # noqa: E402
from ayarlar import CEVIRI_DOSYASI  # noqa: E402
from besleme import makale_getir  # noqa: E402
from ceviri import onbellegi_yukle  # noqa: E402
from ozet import ozet_olustur  # noqa: E402
from takip import Takip  # noqa: E402


def haberler(kategori, ad, adres):
    return haber_uret.kaynak_haberleri(kategori, ad, adres, Takip({}, datetime.now(timezone.utc)), set())


print("[TESHIS] ===== 1. KALINTILAR =====")
for kategori, ad, adres in [
    ("Gündem", "cnn.com", "https://www.cnn.com/"),
    ("Gündem", "france24.com", "https://www.france24.com/en/rss"),
    ("Gündem", "aa.com.tr", "https://www.aa.com.tr/en/rss/default?cat=turkiye"),
    ("Yemek", "theguardian.com", "https://www.theguardian.com/food/rss"),
    ("Sanat & Kültür", "lithub.com", "https://lithub.com/feed/"),
]:
    for m in haberler(kategori, ad, adres)[:4]:
        print(f"[TESHIS] {ad} | {m.baslik}")
        print(f"[TESHIS]    {m.ozet}")

print("[TESHIS] ===== 2. KARŞILAŞTIRMA =====")
SISTEM = """Sen bir Türk haber sitesinin editörüsün. Sana İngilizce bir yazının başlığı ve ilk bölümü veriliyor.
Türk okur için 4-5 cümlelik Türkçe bir özet yaz:
- İlk cümlede yazının asıl konusunu, haberini ya da iddiasını ver. Giriş anekdotunu ya da sahne betimlemesini atla ya da en fazla yarım cümleyle geç.
- Yalnız metinde yazanı aktar. Yorum, değerlendirme, metinde olmayan bilgi ya da tahmin ekleme; metin konuya varmadan bitiyorsa metinde olanla yetin.
- Kişi, kurum, eser, restoran ve yer adlarını çevirme; eser adının Türkçede yerleşik adı varsa onu kullan.
- Doğal, akıcı, yazım kurallarına uygun Türkçe kullan.
Girdi bir JSON nesnesidir: {"kimlik": {"baslik": "...", "metin": "..."}, ...}.
Yalnızca aynı kimliklerle bir JSON nesnesi döndür: {"kimlik": "Türkçe özet", ...}. Tırnak gerekirse “ ” kullan. Başka metin yazma."""

secim = [
    ("Sanat & Kültür", "aeon.co", "https://aeon.co/feed.rss", 2),
    ("Sanat & Kültür", "theguardian.com", "https://www.theguardian.com/culture/rss", 2),
    ("Sanat & Kültür", "bbc.com", "https://www.bbc.com/culture/feed.rss", 1),
    ("Gezi", "theguardian.com", "https://www.theguardian.com/travel/rss", 1),
    ("Gezi", "bbc.com", "https://www.bbc.com/travel/feed.rss", 1),
    ("Gezi", "lonelyplanet.com", "https://www.lonelyplanet.com/", 1),
    ("Yemek", "eater.com", "https://www.eater.com/", 1),
    ("Yemek", "saveur.com", "https://www.saveur.com/feed/", 1),
]
onbellek = onbellegi_yukle(CEVIRI_DOSYASI)
girdi, bilgi = {}, {}
for kategori, ad, adres, n in secim:
    for m in haberler(kategori, ad, adres)[:n]:
        sayfa = makale_getir(m.url) or {}
        uzun = ozet_olustur(sayfa.get("govde", ""), m.baslik, 16, ad) if sayfa else m.ozet
        kimlik = f"s{len(girdi)}"
        girdi[kimlik] = {"baslik": m.baslik, "metin": uzun}
        kayit = onbellek.get(m.url) or onbellek.get(haber_uret._normal(m.url)) or {}
        bilgi[kimlik] = (ad, m.baslik, kayit.get("b", ""), kayit.get("o", ""), len(uzun))

komut = ["claude", "-p", "Aşağıdaki JSON nesnesindeki her yazı için kurallara göre Türkçe özet yaz.",
         "--output-format", "json", "--tools", "", "--max-turns", "1", "--no-session-persistence",
         "--system-prompt", SISTEM, "--model", "sonnet"]
s = subprocess.run(komut, input=json.dumps(girdi, ensure_ascii=False), capture_output=True, text=True, timeout=400,
                   cwd=os.environ.get("RUNNER_TEMP") or None)
zarf = json.loads(s.stdout)
print(f"[TESHIS] kullanım: {zarf.get('usage')} maliyet ${zarf.get('total_cost_usd')}")
sonuc = haber_uret.claude_ceviri.cevabi_ayikla(zarf.get("result") or "")
for kimlik, (ad, baslik, tr_baslik, tr_ozet, uzunluk) in bilgi.items():
    print(f"[TESHIS] ### {ad} | {tr_baslik or baslik} (girdi {uzunluk} karakter)")
    print(f"[TESHIS] ŞİMDİ: {tr_ozet}")
    print(f"[TESHIS] CLAUDE: {sonuc.get(kimlik, '(yok)')}")
