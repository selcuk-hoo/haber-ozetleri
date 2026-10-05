"""GEÇİCİ: Gemini 3.5 Flash çeviri denetçisi denemesi (çıktı [TESHIS] satırları)."""
import json, random, subprocess, sys
sys.path.insert(0, "scripts")
from ayarlar import K, KATEGORI_OZET_CUMLE, TURKCE_KAYNAKLAR
from besleme import makale_getir
from ceviri import Cevirmen
from ozet import basligi_temizle, ozet_olustur
import gemini_ceviri

def oku(ad):
    return json.loads(subprocess.run(["git", "show", f"origin/gh-pages:{ad}"], capture_output=True, text=True, check=True).stdout)

subprocess.run(["git", "fetch", "-q", "origin", "gh-pages"], check=True)
arsiv, onbellek = oku("arsiv.json"), oku("ceviri.json")
BILINEN = [
    "https://www.dw.com/en/north-and-south-korea-trade-accusations-over-landmines-that-injured-three-soldiers/a-79503854?maca=en-rss-en-world-4025-rdf",
    "https://www.cnn.com/world/asia/thailands-soft-power-play-culture-as-global-currency-spc",
    "https://www.cnn.com/2026/10/02/economy/us-jobs-report-september-final",
    "https://phys.org/news/2026-09-astronomers-lowest-mass-neutron-star.html",
]
adaylar = [k for k in arsiv if k["kategori"] in ("Gündem", "Teknoloji", "Bilim") and k["kaynak"] not in TURKCE_KAYNAKLAR
           and onbellek.get(k["url"], {}).get("ok") == "g" and k["url"] not in BILINEN]
random.seed(7)
secilen = [k for k in arsiv if k["url"] in BILINEN] + random.sample(adaylar, 36)

girdi, kayit = {}, {}
for i, k in enumerate(secilen):
    s = makale_getir(k["url"])
    if not s:
        continue
    en_b = basligi_temizle(s["baslik"], k["kaynak"])
    en_o = ozet_olustur(s["govde"], en_b, KATEGORI_OZET_CUMLE.get(k["kategori"], K), k["kaynak"])
    tr = onbellek[k["url"]]
    ayni = Cevirmen._tr_ozeti(en_o) == tr.get("oh")
    kimlik = f"h{i}"
    girdi[kimlik] = {"en_baslik": en_b, "en_ozet": en_o, "tr_baslik": tr.get("b", ""), "tr_ozet": tr.get("o", "")}
    kayit[kimlik] = (k["kaynak"], ayni)
    print(f"[TESHIS] {kimlik} [{k['kaynak']}] ayni={ayni}\n[TESHIS]  EN-B: {en_b}\n[TESHIS]  EN-O: {en_o}\n"
          f"[TESHIS]  TR-B: {tr.get('b')}\n[TESHIS]  TR-O: {tr.get('o')}")

import ceviri_denetcisi
c = Cevirmen(onbellek, lambda m: m, 0, bekleme=0)
haberler = [(u, v["en_baslik"], v["en_ozet"]) for u, v in ((secilen[int(k[1:])]["url"], v) for k, v in girdi.items())]
yarim = [u for u, en_b, en_o in haberler if c._bozuk_kayit(onbellek[u], "o", en_o)]
print(f"[TESHIS] yarım sayılan özet: {len(yarim)} {yarim}")
print(f"[TESHIS] denetle: {ceviri_denetcisi.denetle(c, haberler)}; {gemini_ceviri.kullanim_ozeti()}")
