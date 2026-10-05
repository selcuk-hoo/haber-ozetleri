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

SISTEM = """Sen bir Türk haber sitesinin kıdemli editörüsün. Her haber için İngilizce başlık ve özet ile
bunların Türkçe çevirisi var. Görevin yalnız GERÇEK sorunları bulmak:

1. "ceviri": Türkçe metin İngilizcenin anlamını değiştiriyor (yanlış kelime: "jobs" → "istihbarat";
   yanlış sayı, kişi, ülke ya da para birimi; olumsuzluk ya da kesinlik derecesi kaybı; çevrilmeden
   kalmış İngilizce cümle) ya da Türkçede belirgin bir yazım hatası var ("belirterak").
2. "kaynak": İngilizce özetin kendisi başlıktaki haberi anlatmıyor (sayfadaki başka bir içerik,
   duyuru, künye, yazar adı, tarih satırı ya da alakasız bir başlık özete karışmış).

Üslup tercihlerini, eşanlamlı kelime seçimlerini, küçük akıcılık farklarını SORUN SAYMA.
Emin değilsen bildirme.

Girdi: {"kimlik": {"en_baslik", "en_ozet", "tr_baslik", "tr_ozet"}, ...}
Yalnız sorunlu haberleri içeren bir JSON nesnesi döndür (sorun yoksa {}):
{"kimlik": {"tur": "ceviri" | "kaynak", "neden": "kısa açıklama",
            "tr_baslik": "düzeltilmiş başlık (yalnız ceviri ve başlık yanlışsa)",
            "tr_ozet": "düzeltilmiş özetin tamamı (yalnız ceviri ve özet yanlışsa)"}}"""

for model in ("gemini-3.5-flash", "gemini-2.5-flash"):
    once = dict(gemini_ceviri.kullanim)
    try:
        cevap = gemini_ceviri.metin_uret(model, SISTEM, json.dumps(girdi, ensure_ascii=False), sicaklik=0.1)
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {model} HATA {hata!r}")
        continue
    g = gemini_ceviri.kullanim["girdi"] - once["girdi"]
    c = gemini_ceviri.kullanim["cikti"] - once["cikti"]
    print(f"[TESHIS] ===== {model}: {len(girdi)} haber, {g} girdi + {c} çıktı token")
    try:
        sonuc = json.loads(cevap)
    except Exception:  # noqa: BLE001
        print(f"[TESHIS] bozuk JSON: {cevap[:500]!r}")
        continue
    for kimlik, v in sonuc.items():
        print(f"[TESHIS] {model} {kimlik} {kayit.get(kimlik)} {json.dumps(v, ensure_ascii=False)}")
