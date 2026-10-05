"""GEÇİCİ: gemini_ozet üretim koduyla 24 gerçek haberde özet ([TESHIS] satırları). Tek Flash-Lite isteği."""
import json, random, subprocess, sys
sys.path.insert(0, "scripts")
from ayarlar import K, TURKCE_KAYNAKLAR, YZ_OZET_CUMLE, YZ_OZET_KATEGORILERI
from besleme import makale_getir
from ceviri import Cevirmen
from model import Makale
from ozet import basligi_temizle, ozet_olustur
import gemini_ceviri, gemini_ozet

subprocess.run(["git", "fetch", "-q", "origin", "gh-pages"], check=True)
oku = lambda ad: json.loads(subprocess.run(["git", "show", f"origin/gh-pages:{ad}"], capture_output=True, text=True, check=True).stdout)
arsiv, onbellek = oku("arsiv.json"), oku("ceviri.json")
adaylar = [k for k in arsiv if k["kategori"] in YZ_OZET_KATEGORILERI and k["kaynak"] not in TURKCE_KAYNAKLAR]
random.seed(11)
secilen = [k for k in adaylar if "rethink-its-ai-data-centre" in k["url"]] + random.sample(adaylar[:150], 23)
makaleler = []
for k in secilen:
    s = makale_getir(k["url"])
    if not s:
        continue
    b = basligi_temizle(s["baslik"], k["kaynak"])
    makaleler.append(Makale(k["kaynak"], b, k["url"], ozet_olustur(s["govde"], b, K, k["kaynak"]), "", "",
                            uzun=ozet_olustur(s["govde"], b, YZ_OZET_CUMLE, k["kaynak"])[:2000]))
c = Cevirmen({}, lambda m: m, 0, bekleme=0)
gemini_ozet.ozetle(c, makaleler)
for m in makaleler:
    print(f"[TESHIS] ===== [{m.kaynak}] {m.baslik}\n[TESHIS] TR-B: {onbellek.get(m.url, {}).get('b')}\n"
          f"[TESHIS] ESKİ: {onbellek.get(m.url, {}).get('o', '')[:600]}\n[TESHIS] YENİ: {c.yz_ozeti(m.url, m.uzun)}\n"
          f"[TESHIS] EN : {m.uzun[:900]}")
print(f"[TESHIS] kullanım: {gemini_ceviri.kullanim_ozeti()}")
