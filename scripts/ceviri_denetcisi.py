"""Gemini çevirilerinin denetimi (Gündem, Teknoloji, Bilim).

Çeviriyi yapan Gemini Flash-Lite bazen anlamı bozuyor: "29,000 jobs" →
"29.000 istihbarat", "It goes without saying that I am happy" → "Mutlu
olduğum söylenemez bile", talimattaki örneği yanlış yere uygulayıp
"University of Tasmania" → "Sidney Üniversitesi". Bir üst model (Gemini
3.5 Flash) İngilizce başlık + özetle Türkçesini karşılaştırır; yalnız
gerçek hataları bildirir ve düzeltilmiş metni verir. Düzeltme önbellekteki
çevirinin yerine yazılır.

Deneme (05.10.2026, 40 gerçek haber, tek istek, ~19 bin girdi + 2 bin
çıktı token): 37 haberin 5'inde gerçek hata buldu (iki yarım çeviri, bir
yanlış kelime, bir ters anlam, bir yanlış üniversite), yanlış alarm
vermedi. Sayfadan kalan künye ya da duyuru gibi kaynak kalıntılarını
yakalamadı; onlar ozet.py kurallarının işi (bulursa loga yazılır).

Ücretsiz hak model başına: 3.5 Flash günde 20 istek ve çeviri ile olay
süzgecinin yedeği de aynı modeli kullanıyor. Bu yüzden denetim her saat
değil, DENETIM_SAATLERI'nde ve en çok EN_FAZLA_ISTEK istekle yapılır
(günde ≤14, çoğunlukla ~8). Denetlenen haber önbellekte "d" ile işaretlenir (başlık ve
özetin o anki İngilizce özetleriyle); metin değişirse yeniden denetlenir.
"""

import json
import sys

import gemini_ceviri

MODEL = "gemini-3.5-flash"
# UTC saatleri: Türkiye saatiyle (UTC+3) 08-20 arası 2 saatte bir; gece
# denetim yok (kullanıcının isteği), gece gelen haberler 08'de denetlenir.
# Okurun baktığı saatlerde hatalı çeviri sayfada en çok ~2 saat kalır.
DENETIM_SAATLERI = {5, 7, 9, 11, 13, 15, 17}
PARCA_BOYU = 40  # bir istekteki haber
EN_FAZLA_ISTEK = 2  # bir çalıştırmada

SISTEM = """Sen bir Türk haber sitesinin kıdemli editörüsün. Her haber için İngilizce başlık ve metin ile
Türkçe başlık ve özet var. Türkçe özet İngilizce metnin ya çevirisi ya da kısa özetidir; özetin
metindeki bazı ayrıntıları atlaması sorun değildir. Görevin yalnız GERÇEK sorunları bulmak:

1. "ceviri": Türkçe metin İngilizcenin anlamını değiştiriyor ya da İngilizcede olmayan bilgi ekliyor (yanlış kelime: "jobs" → "istihbarat";
   yanlış sayı, kişi, ülke ya da para birimi; olumsuzluk ya da kesinlik derecesi kaybı; çevrilmeden
   kalmış ya da atlanmış cümle) ya da Türkçede belirgin bir yazım hatası var ("belirterak").
2. "kaynak": İngilizce metnin kendisi başlıktaki haberi anlatmıyor (sayfadaki başka bir içerik,
   duyuru, künye, yazar adı, tarih satırı ya da alakasız bir başlık özete karışmış).

Üslup tercihlerini, eşanlamlı kelime seçimlerini, küçük akıcılık farklarını SORUN SAYMA.
Emin değilsen bildirme.

Girdi: {"kimlik": {"en_baslik", "en_metin", "tr_baslik", "tr_ozet"}, ...}
Yalnız sorunlu haberleri içeren bir JSON nesnesi döndür (sorun yoksa {}):
{"kimlik": {"tur": "ceviri" | "kaynak", "neden": "kısa açıklama",
            "tr_baslik": "düzeltilmiş başlık (yalnız ceviri ve başlık yanlışsa)",
            "tr_ozet": "düzeltilmiş özetin tamamı (yalnız ceviri ve özet yanlışsa)"}}"""


def _cagir(girdi: dict) -> dict:
    cevap = gemini_ceviri.metin_uret(MODEL, SISTEM, json.dumps(girdi, ensure_ascii=False), sicaklik=0.1)
    sonuc = json.loads(cevap)
    if not isinstance(sonuc, dict):
        raise ValueError("cevap JSON nesnesi değil")
    return sonuc


def _imza(kayit: dict) -> str:
    return f"{kayit.get('bh')}/{kayit.get('oh')}/{kayit.get('yh')}"


def denetle(cevirmen, haberler: list[tuple[str, str, str, str]], cagir=None) -> dict:
    """haberler: (url, İngilizce başlık, İngilizce ilk cümleler, yapay zekâ
    özetinin kaynağı ya da ""), en yeni önce. Başlığı ya da özeti Gemini'nin
    olan, güncel ve henüz denetlenmemiş haberler denetlenir; düzeltmeler
    önbelleğe yazılır. Yapay zekâ özeti (bkz. gemini_ozet.py) varsa sayfada o
    görünür; kaynağıyla karşılaştırılır. Özet sayılar döner."""
    cagir = cagir or _cagir
    onbellek = cevirmen.onbellek
    bekleyen: dict[str, tuple[str, str, str, dict]] = {}  # url → (en_b, en_metin, özet alanı, kayıt)
    for url, en_b, en_o, uzun in haberler:
        kayit = onbellek.get(url, {})
        yz = cevirmen.yz_ozeti(url, uzun)
        if not ("g" in (kayit.get("bk"), kayit.get("ok")) or yz) or kayit.get("d") == _imza(kayit):
            continue
        # Çevirisi bu turda değişecek (İngilizcesi değişmiş ya da bozuk) haber bekler.
        if cevirmen.ceviri_gerekli_mi("b", url, en_b) or (not yz and cevirmen.ceviri_gerekli_mi("o", url, en_o)):
            continue
        bekleyen[url] = (en_b, uzun, "y", kayit) if yz else (en_b, en_o, "o", kayit)
    sayac = {"denetlenen": 0, "duzeltilen": 0, "kaynak": 0}
    urller = list(bekleyen)[:PARCA_BOYU * EN_FAZLA_ISTEK]
    for i in range(0, len(urller), PARCA_BOYU):
        parca = {f"h{j}": url for j, url in enumerate(urller[i:i + PARCA_BOYU])}
        girdi = {k: {"en_baslik": bekleyen[u][0], "en_metin": bekleyen[u][1],
                     "tr_baslik": bekleyen[u][3].get("b", ""), "tr_ozet": bekleyen[u][3].get(bekleyen[u][2], "")}
                 for k, u in parca.items()}
        try:
            sonuc = cagir(girdi)
        except Exception as hata:  # noqa: BLE001 - denetim olmazsa çeviriler olduğu gibi kalır
            print(f"Çeviri denetimi yapılamadı ({MODEL}): {hata!r}", file=sys.stderr)
            break
        for kimlik, url in parca.items():
            en_b, en_metin, ozet_alani, kayit = bekleyen[url]
            bulgu = sonuc.get(kimlik)
            if isinstance(bulgu, dict) and bulgu.get("tur") == "ceviri":
                duzeldi = False
                for tur, alan, en in (("b", "tr_baslik", en_b), (ozet_alani, "tr_ozet", en_metin)):
                    yeni = (bulgu.get(alan) or "").strip()
                    gecersiz = cevirmen.yz_gecersiz if tur == "y" else cevirmen._cevrilmemis
                    if yeni and yeni != kayit.get(tur) and not gecersiz(en, yeni):
                        print(f"[DENETIM] {url}\n  neden: {bulgu.get('neden')}\n"
                              f"  önce : {kayit.get(tur, '')[:300]}\n  sonra: {yeni[:300]}")
                        kayit[tur] = yeni
                        duzeldi = True
                sayac["duzeltilen"] += duzeldi
            elif isinstance(bulgu, dict) and bulgu.get("tur") == "kaynak":
                print(f"[DENETIM] kaynak kalıntısı? {url}: {bulgu.get('neden')}")
                sayac["kaynak"] += 1
            kayit["d"] = _imza(kayit)
            sayac["denetlenen"] += 1
    return sayac
