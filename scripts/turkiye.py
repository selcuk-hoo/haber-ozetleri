"""Türkiye sekmesi (22.10.2026, kullanıcının isteği): Türk basınının ortak
gündeminden en önemli 5 olay (ilk sürümde 5, sonra 7), her biri birkaç gazetenin haberinden
derlenmiş tek bir özetle.

Ücretsiz sürüm (kullanıcı Claude'lu tasarımı "çok masraflı" buldu):
- Seçim yapay zekâsız: bir olayı kaç gazetenin yazdığı. Eşitlikte farklı
  kanatların (iktidara yakın, merkez, muhalif, bağımsız/yabancı) yazdığı
  öne geçer: hem iktidara yakın hem muhalif basının yazdığı olay ortak
  gündemdir, tek tarafın manşete taşıdığı değil.
- Gruplama: başlık + besleme özetindeki sözcük kökleri (ilk 5 harf)
  örtüşmesi; aday gruplar Gemini Flash-Lite'a doğrulatılır (aynı olay mı,
  Türkiye haberi mi, önemsiz mi: spor, magazin, üçüncü sayfa). Gemini yoksa
  sekme güncellenmez (yanlış birleşmiş grup yerine eski hâli).
- Derleme özet: Gemini Flash-Lite, olayı yazan gazetelerin metinlerinden.
  Yalnız olaya yeni bir gazete katıldıysa yeniden yazılır.
- TURKIYE_ARALIK'ta (2 saat) bir hesaplanır; aradaki çalıştırmalar kayıtlı
  hâli gösterir. Gemini: 2 saatte en çok 2 istek (doğrulama + derleme).

Gazetelerin haberleri sayfaya kart olarak girmez; yalnız bu seçim için
okunur. Kayıt dist/turkiye.json'da.
"""

import hashlib
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import trafilatura

import gemini_ceviri
from besleme import makale_getir

# (ad, görünen ad, besleme, kanat). Tarama: 22.10.2026, 20 site; BirGün,
# Bianet, Halk TV, Gazete Oksijen otomatik okumayı engelliyor. CNN Türk
# (tıklama tuzağı başlıklar), Milliyet (çoğu AA metni), Karar ve Diken
# (spor ağırlıklı genel besleme) alınmadı.
GAZETELER = [
    ("sabah", "Sabah", "https://www.sabah.com.tr/rss/gundem.xml", "iktidara yakın"),
    ("yenisafak", "Yeni Şafak", "https://www.yenisafak.com/rss?xml=gundem", "iktidara yakın"),
    ("trthaber", "TRT Haber", "https://www.trthaber.com/gundem_articles.rss", "kamu"),
    ("ntv", "NTV", "https://www.ntv.com.tr/turkiye.rss", "merkez"),
    ("hurriyet", "Hürriyet", "https://www.hurriyet.com.tr/rss/gundem", "merkez"),
    ("haberturk", "Habertürk", "https://www.haberturk.com/rss/kategori/gundem.xml", "merkez"),
    ("sozcu", "Sözcü", "https://www.sozcu.com.tr/feeds-rss-category-gundem", "muhalif"),
    ("cumhuriyet", "Cumhuriyet", "https://www.cumhuriyet.com.tr/rss/son_dakika.xml", "muhalif"),
    ("medyascope", "Medyascope", "https://medyascope.tv/feed/", "bağımsız"),
]
# Sayfadaki Türkçe kaynaklar da havuza girer (bkz. ayarlar.TURKCE_KAYNAKLAR).
SAYFA_KAYNAKLARI = {
    "t24.com.tr": ("T24", "muhalif"),
    "bbc.com/turkce": ("BBC Türkçe", "yabancı"),
    "dw.com/tr": ("DW Türkçe", "yabancı"),
    "tr.euronews.com": ("Euronews Türkçe", "yabancı"),
}

TURKIYE_ARALIK = timedelta(hours=2) - timedelta(minutes=10)  # saatlik çalıştırmada 2 saatte bir
PENCERE = timedelta(hours=24)  # son 24 saatin haberleri
OLAY_SAYISI = 7  # 5'te SPK'nın 5 gazetelik haberi eşitlikte 6. kalmıştı
EN_AZ_KAYNAK = 3
ADAY_SAYISI = 12  # Gemini'ye doğrulatılan en kalabalık aday grup
MODELLER = ("gemini-flash-lite-latest", "gemini-3.1-flash-lite")  # 2.5 Flash özeti İngilizce yazmıştı

# Spor, magazin, hizmet haberi: adres ve başlık kalıbı (Gemini de eler).
ATLANAN_ADRES = re.compile(r"/(?:spor|magazin|yasam|astroloji|burc|saglik|teknoloji|otomobil|kultur|sanat|dizi"
                           r"|televizyon|galeri|video|foto|dunya)(?:/|-)", re.I)
ATLANAN_BASLIK = re.compile(r"\b(?:loto|çekiliş|burç|hava durumu|canlı izle|maç|gol|transfer|şampiyonlar ligi"
                            r"|avrupa ligi|konferans ligi|süper lig)\b", re.I)

_DURAK = set("""ve ile bir bu şu da de ki için gibi daha çok en olan oldu olarak sonra önce ama ya veya
hem ise mi mı mu mü ne kadar her yeni son ilk iki üç dedi açıkladı etti yaptı
geldi verdi tarafından üzerine karşı göre kendi büyük var yok""".split())


def _kucuk(metin: str) -> str:
    return metin.replace("İ", "i").replace("I", "ı").lower()


def kokler(metin: str) -> set[str]:
    """Sözcüklerin ilk 5 harfi (Türkçe ekleri kabaca atar: "SPK'dan" → "spk",
    "duyurusu" → "duyur"). İki basamaklı ve uzun sayılar da kalır ("48 kişi")."""
    sonuc = set()
    for s in re.findall(r"[a-zçğıöşüâîû0-9]+(?:'[a-zçğıöşü]+)?", re.sub("[’‘`]", "'", _kucuk(metin))):
        s = s.split("'")[0]
        if s in _DURAK or len(s) < (2 if s.isdigit() else 3):
            continue
        sonuc.add(s[:5])
    return sonuc


def benzer_mi(a: set[str], b: set[str]) -> bool:
    ortak = len(a & b)
    return ortak >= 2 and ortak >= 0.25 * min(len(a), len(b))


def _duz(metin: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", metin or ""))).strip()


def besleme_oku(adres: str, simdi: datetime) -> list[dict]:
    ham = trafilatura.fetch_url(adres)
    if not ham:
        return []
    sonuc = []
    for o in feedparser.parse(ham).entries:
        t = o.get("published_parsed") or o.get("updated_parsed")
        zaman = datetime(*t[:6], tzinfo=timezone.utc) if t else simdi
        if simdi - zaman > PENCERE or not o.get("link"):
            continue
        baslik = _duz(o.get("title", ""))
        if not baslik or ATLANAN_ADRES.search(o.link) or ATLANAN_BASLIK.search(baslik):
            continue
        sonuc.append({"url": o.link, "baslik": baslik, "ozet": _duz(o.get("summary", ""))[:400],
                      "zaman": zaman.isoformat()})
    return sonuc


def grupla(haberler: list[dict]) -> list[list[dict]]:
    """Aday gruplar (en az iki ayrı kaynak), kaynak sayısına göre büyükten
    küçüğe. İlk sürümde (22.10.2026) basit birleştirme zincirleme gidiyordu:
    "soruşturma", "tutuklama" gibi sık sözcükler SPK, fon tasfiyesi ve tefeci
    operasyonunu tek gruba topladı. Şimdi çok sık geçen kökler sayılmaz ve bir
    haber gruba ancak oradakilerin en az yarısına benziyorsa girer."""
    kok = [kokler(h["baslik"] + " " + h["ozet"][:200]) for h in haberler]
    sayim = Counter(r for k in kok for r in k)
    sinir = max(6, 0.03 * len(haberler))
    kok = [{r for r in k if sayim[r] <= sinir} for k in kok]
    kumeler: list[list[int]] = []
    for i in sorted(range(len(haberler)), key=lambda i: haberler[i]["zaman"], reverse=True):
        en_iyi, en_cok = None, 0
        for kume in kumeler:
            benzeyen = sum(benzer_mi(kok[i], kok[j]) for j in kume)
            if benzeyen * 2 >= len(kume) and benzeyen > en_cok:
                en_iyi, en_cok = kume, benzeyen
        if en_iyi is not None:
            en_iyi.append(i)
        else:
            kumeler.append([i])
    adaylar = [[haberler[i] for i in k] for k in kumeler if len({haberler[i]["kaynak"] for i in k}) >= 2]
    return sorted(adaylar, key=lambda g: (-len({h["kaynak"] for h in g}), -len(g)))


DOGRULAMA = """Sen bir Türk haber sitesinin editörüsün. Aşağıda Türk gazetelerinden haber grupları var;
bir algoritma kelime benzerliğiyle grupladı, yanılabilir: bir grupta birden çok olay olabilir.
Her grup için grubun içindeki somut olayları ayır ("olaylar"). Her olay için:
- "haberler": o olayı anlatan haberlerin kimlikleri (aynı olay, karar, açıklama ya da gelişme; o
  olaya verilen tepkiler de aynı olaydır; yalnız aynı genel konu, ör. "yolsuzluk soruşturmaları",
  "ekonomi" yetmez). Aynı kişinin aynı gün açıkladığı iki ayrı karar iki ayrı olaydır.
- "turkiye": bu olay bir Türkiye haberi mi (Türkiye'de olan ya da Türkiye'yi doğrudan ilgilendiren);
  yabancı ülkede olup Türkiye'yi ilgilendirmeyen dünya haberi false,
- "onemsiz": spor, magazin, ünlülerin hayatı ve adli işleri (uyuşturucu testi, gözaltı; kamu
  görevlisi ya da siyasetçi değillerse), üçüncü sayfa (tek bir kaza, cinayet, kavga), hava durumu,
  hizmet bilgisi (burs başvurusu, sonuç ilanı) ise true.
Tek haberli olayları yazma. Yalnız JSON döndür:
{"g0": {"olaylar": [{"haberler": ["h0", "h3"], "turkiye": true, "onemsiz": false}]}, ...}"""

DERLEME = """Sen bir Türk haber sitesinin editörüsün. Her olay için farklı Türk gazetelerinin aynı
olayı anlatan haberleri verildi. Her olay için:
- "baslik": kısa, yansız bir Türkçe başlık (en çok 12 sözcük; gazetelerin yorum katan sözcüklerini
  kullanma),
- "ozet": 3-4 cümlelik Türkçe derleme: önce ne oldu (kim, ne, nerede), sonra metinlerde varsa son
  durum ve önemli ayrıntı. Gazetelerin verdiği bilgiyi birleştir, aynı bilgiyi tekrarlama.
Yansız ol: iddiaları ve suçlamaları kimin söylediğiyle yaz ("… iddia etti", "… açıkladı"); bir
gazetenin yorumunu ya da sıfatını gerçek gibi aktarma. Yalnız metinlerdeki bilgiyi kullan; sayı,
isim ve tarihleri değiştirme. Yalnız Türk alfabesiyle, yazım kurallarına uygun yaz.
Yalnız JSON döndür: {"o0": {"baslik": "...", "ozet": "..."}, ...}"""


def _gemini(talimat: str, girdi: str, uret=None) -> dict | None:
    uret = uret or gemini_ceviri.metin_uret
    for model in MODELLER:
        try:
            metin = uret(model, talimat, girdi)
            return json.loads(metin[metin.index("{"):metin.rindex("}") + 1])
        except Exception as hata:  # noqa: BLE001 - olmazsa eski hâl kalır
            print(f"Türkiye ({model}) cevap alamadı: {hata!r}", file=sys.stderr)
    return None


# Doğrulama talimatı değişince artırılır (adaylar bir kez yeniden sorulur).
# 2 (22.10.2026): bir adaydan birden çok olay; Gürlek'in iki açıklaması
# (başsavcılar, 71 faili meçhul) tek adaydaydı, yalnız biri alınıyordu.
SURUM = "2"


def _anahtar(urller) -> str:
    return hashlib.sha1((SURUM + "|" + "|".join(sorted(urller))).encode()).hexdigest()[:12]


def dogrula(adaylar: list[list[dict]], kararlar: dict, uret=None) -> list[list[dict]] | None:
    """Gemini'nin onayladığı olaylar (Türkiye haberi, önemsiz değil). Daha
    önce sorulmuş aday (aynı üyeler) yeniden sorulmaz. Gemini cevap
    vermezse None."""
    sorulacak = {f"g{i}": a for i, a in enumerate(adaylar) if _anahtar(h["url"] for h in a) not in kararlar}
    if sorulacak:
        satirlar, kimlik = [], {}
        for g, aday in sorulacak.items():
            satirlar.append(f"{g}:")
            for h in aday:
                k = f"h{len(kimlik)}"
                kimlik[k] = h["url"]
                satirlar.append(f"  {k} [{h['ad']}] {h['baslik']} — {h['ozet'][:200]}")
        cevap = _gemini(DOGRULAMA, "\n".join(satirlar), uret)
        if cevap is None:
            return None
        for g, aday in sorulacak.items():
            c = cevap.get(g) if isinstance(cevap.get(g), dict) else {}
            olaylar = []
            for o in c.get("olaylar", []) if isinstance(c.get("olaylar"), list) else []:
                if isinstance(o, dict):
                    olaylar.append({"haberler": [kimlik[k] for k in o.get("haberler", []) if k in kimlik],
                                    "gecerli": bool(o.get("turkiye")) and not o.get("onemsiz")})
            kararlar[_anahtar(h["url"] for h in aday)] = {"olaylar": olaylar}
    sonuc = []
    for aday in adaylar:
        for olay in kararlar[_anahtar(h["url"] for h in aday)].get("olaylar", []):
            uyeler = [h for h in aday if h["url"] in set(olay["haberler"])]
            if olay["gecerli"] and len({h["kaynak"] for h in uyeler}) >= EN_AZ_KAYNAK:
                sonuc.append(uyeler)
    return sonuc


def sec(olaylar: list[list[dict]]) -> list[list[dict]]:
    """Kaynak sayısı, eşitlikte kanat çeşitliliği, sonra en yeni haber."""
    return sorted(olaylar, key=lambda o: (len({h["kaynak"] for h in o}), len({h["kanat"] for h in o}),
                                          max(h["zaman"] for h in o)), reverse=True)[:OLAY_SAYISI]


def _metin_secimi(uyeler: list[dict], en_cok: int = 4) -> list[dict]:
    """Derlemeye giden haberler: farklı kanatlardan, kaynak başına bir tane."""
    secilen, kanatlar, kaynaklar = [], set(), set()
    for tur in (0, 1):
        for h in uyeler:
            if len(secilen) >= en_cok or h["kaynak"] in kaynaklar or (tur == 0 and h["kanat"] in kanatlar):
                continue
            secilen.append(h)
            kanatlar.add(h["kanat"])
            kaynaklar.add(h["kaynak"])
    return secilen


def derle(olaylar: list[list[dict]], getir=None, uret=None) -> dict[int, dict]:
    """{olay sırası: {"baslik", "ozet", "gorsel"}}; alınamayanlar yok."""
    getir = getir or makale_getir
    satirlar, gorseller = [], {}
    for i, uyeler in enumerate(olaylar):
        satirlar.append(f"o{i}:")
        for h in _metin_secimi(uyeler):
            s = getir(h["url"])
            metin = (s["govde"] if s else h["ozet"])[:1500]
            if s and s.get("gorsel") and i not in gorseller:
                gorseller[i] = s["gorsel"]
            satirlar.append(f"  [{h['ad']}] {h['baslik']}\n  {metin}")
    cevap = _gemini(DERLEME, "\n".join(satirlar), uret) or {}
    from ceviri import Cevirmen  # döngüsel içe aktarmadan kaçınmak için burada
    sonuc = {}
    for i in range(len(olaylar)):
        c = cevap.get(f"o{i}")
        if not isinstance(c, dict) or not isinstance(c.get("ozet"), str) or not isinstance(c.get("baslik"), str):
            continue
        ozet = c["ozet"].strip()
        if len(ozet) < 60 or Cevirmen.ingilizce_mi(ozet) or Cevirmen.YABANCI_HARF.search(ozet + c["baslik"]):
            continue
        sonuc[i] = {"baslik": c["baslik"].strip(), "ozet": ozet, "gorsel": gorseller.get(i, "")}
    return sonuc


def zamani_mi(kayit: dict, simdi: datetime) -> bool:
    son = kayit.get("hesap")
    return not son or simdi - datetime.fromisoformat(son) >= TURKIYE_ARALIK


def guncelle(kayit: dict, haberler: list[dict], simdi: datetime, uret=None, getir=None) -> dict:
    """kayit: önceki turkiye.json. Yeni hâli döndürür (değişmediyse aynısı).
    Gemini yoksa (deneme dalı) aday gruplar yalnız loga yazılır."""
    kararlar = {k: v for k, v in kayit.get("kararlar", {}).items()}
    adaylar = grupla(haberler)[:ADAY_SAYISI]
    if uret is None and not gemini_ceviri.kullanilabilir_mi():
        print(f"Türkiye: {len(haberler)} haber, {len(adaylar)} aday (Gemini yok, sekme güncellenmedi)")
        for a in adaylar:
            print(f"  [{len({h['kaynak'] for h in a})} kaynak] " + " | ".join(f"{h['ad']}: {h['baslik'][:60]}" for h in a))
        return kayit
    olaylar = dogrula(adaylar, kararlar, uret)
    if olaylar is None:
        return kayit
    secilen = sec(olaylar)
    eski = kayit.get("olaylar", [])
    yeni, derlenecek = [], []
    for uyeler in secilen:
        urller = {h["url"] for h in uyeler}
        onceki = next((o for o in eski if urller & set(o["urller"])), None)
        kaynaklar = sorted({h["kaynak"] for h in uyeler})
        o = {
            "urller": sorted(urller | set(onceki["urller"] if onceki else [])),
            "kaynaklar": [{"ad": h["ad"], "url": h["url"]} for h in _kaynak_basina_bir(uyeler)],
            "kaynak_imzasi": kaynaklar,
            "ilk": (onceki or {}).get("ilk", min(h["zaman"] for h in uyeler)),
            "baslik": (onceki or {}).get("baslik", ""), "ozet": (onceki or {}).get("ozet", ""),
            "gorsel": (onceki or {}).get("gorsel", ""), "tur": "turkiye",
        }
        # Özet yalnız olaya yeni bir gazete katıldıysa yeniden yazılır.
        if not onceki or not o["ozet"] or set(kaynaklar) - set(onceki.get("kaynak_imzasi", [])):
            derlenecek.append((len(yeni), uyeler))
        yeni.append(o)
    if derlenecek:
        sonuc = derle([u for _, u in derlenecek], getir, uret)
        for j, (i, _) in enumerate(derlenecek):
            if j in sonuc:
                yeni[i].update({k: v for k, v in sonuc[j].items() if v})
    yeni = [o for o in yeni if o["ozet"]]
    # Kararlar 2 gün saklanır (aynı aday yeniden sorulmasın).
    for k in list(kararlar):
        kararlar[k].setdefault("zaman", simdi.isoformat())
        if simdi - datetime.fromisoformat(kararlar[k]["zaman"]) > timedelta(days=2):
            del kararlar[k]
    print(f"Türkiye: {len(haberler)} haber, {len(adaylar)} aday, {len(olaylar)} olay, "
          f"{len(derlenecek)} derleme; Gemini: {gemini_ceviri.kullanim_ozeti()}")
    for o in yeni:
        print(f"  [{len(o['kaynak_imzasi'])} kaynak] {o['baslik']}")
    return {"hesap": simdi.isoformat(), "olaylar": yeni, "kararlar": kararlar}


def _kaynak_basina_bir(uyeler: list[dict]) -> list[dict]:
    goruldu, sonuc = set(), []
    for h in sorted(uyeler, key=lambda h: h["zaman"], reverse=True):
        if h["kaynak"] not in goruldu:
            goruldu.add(h["kaynak"])
            sonuc.append(h)
    return sonuc


def haberleri_topla(sayfa_makaleleri: list, simdi: datetime) -> list[dict]:
    """Gazetelerin beslemeleri + sayfadaki Türkçe kaynakların haberleri."""
    haberler = []
    for ad, gorunen, adres, kanat in GAZETELER:
        try:
            ogeler = besleme_oku(adres, simdi)
        except Exception as hata:  # noqa: BLE001 - bir gazete düşerse ötekiler sürer
            print(f"Türkiye: {gorunen} okunamadı ({hata!r})", file=sys.stderr)
            ogeler = []
        print(f"Türkiye / {gorunen}: {len(ogeler)} haber")
        haberler += [dict(h, kaynak=ad, ad=gorunen, kanat=kanat) for h in ogeler]
    for m in sayfa_makaleleri:
        if m.kaynak in SAYFA_KAYNAKLARI:
            gorunen, kanat = SAYFA_KAYNAKLARI[m.kaynak]
            haberler.append({"url": m.url, "baslik": m.baslik, "ozet": m.ozet[:400], "zaman": simdi.isoformat(),
                             "kaynak": m.kaynak, "ad": gorunen, "kanat": kanat})
    return haberler


def yukle(yol: Path) -> dict:
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def kaydet(yol: Path, kayit: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(kayit, ensure_ascii=False) + "\n", encoding="utf-8")
