"""Manşet: son 24 saatin en önemli olaylarının derlemesi, kategorilerin en
solundaki "Manşet" sekmesinde. Günde iki baskı (MANSET_SAATLERI, Türkiye
saatiyle 08:00 ve 17:00); gece okunmadığı için daha sık değil.

Her saatlik çalıştırmada olay süzgecinin Gündem grupları kayda eklenir
(manset_olaylari.json; aynı habere sahip gruplar birleşir, kaynak sayısı
büyür, olayın ilk görülme anı tutulur). Baskı saatinden sonraki ilk
çalıştırmada son 24 saatte ortaya çıkan olaylar iki Claude (Sonnet)
çağrısıyla işlenir:

1. Puanlama: en az 2 kaynaklı olaylar (başlık + ilk cümleler) kıstas
   kıstas 0-10 puanlanır (etki, kalıcılık, dönüm, eylem, Türkiye'ye
   yakınlık; ağırlıklar ayarlar.MANSET_AGIRLIKLAR). Puanı burada hesaplanır
   (modelin aritmetiğine bırakılmaz). Kaynak sayısı yalnız aday seçer:
   çok yazılan ama yerel ya da yalnız ilginç olay (03.10.2026: bir
   eyaletteki başarısız infaz) manşete girmesin diye.
2. Derleme: eşiği geçenler (en çok MANSET_EN_FAZLA) derlenir. Hiçbiri
   geçmezse o baskıda manşet (ve sekme) yok, ikinci çağrı yapılmaz.

Sonuç manset.json'a yazılır (puanlar ve gerekçeler dahil); öteki
çalıştırmalar yalnız onu okur. Baskı başına ~6,5 bin token.

Neden Sonnet: 3.5 Flash-Lite derlemesi olayı ters anlattı, olmayan
sözcükler yazdı (~6 puan); 3.8 / 3.5 Flash gece de 503 ve zaman aşımı verdi
(02.10.2026). Sonnet ~8,5. Claude yoksa ya da çağrı başarısız olursa manşet
gösterilmez, yanlış bilgi yerine boşluk tercih edilir.
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import claude_ceviri
from ayarlar import (
    MANSET_ADAY, MANSET_AGIRLIKLAR, MANSET_ARSIV_GUN, MANSET_EN_FAZLA, MANSET_ESIK, MANSET_KATEGORI,
    MANSET_SAATLERI, MANSET_TR_ADAY, MANSET_TR_AGIRLIKLAR, MANSET_TR_EN_FAZLA, MANSET_TR_ESIK,
    MANSET_KAYNAK_ADLARI, MANSET_TR_KAYNAKLAR, TR_SAATI,
)
from model import KaynakBolumu, Makale
from olaylar import ilk_cumleler
from tarih import gun_ay

UYE_UZUNLUGU = 700  # kayıtta bir haberin özetinden saklanan en çok karakter
SAKLAMA = timedelta(days=3)  # kayıttaki olaylar ve denemeler bu kadar tutulur
PENCERE = timedelta(hours=24)  # bir baskı bu süre içinde ortaya çıkan olaylara bakar
EN_FAZLA_DENEME = 3  # bir baskı için en çok bu kadar deneme (hata durumunda)
GOSTERIM = timedelta(hours=36)  # baskı üretilemezse önceki bu kadar süre gösterilir
# Üretim yöntemi; değişince o baskı yeniden hazırlanır.
SURUM = 7  # 2: önem puanlaması; 3: Türkiye kıstası; 4: günde iki baskı; 5: görsel; 6: Türkiye manşeti;
# 7: kendi haberi kuralı
ISTEK = "Aşağıdaki olaylar için kurallara göre Türkçe derleme yaz."
PUAN_ISTEGI = "Aşağıdaki olayları kıstaslara göre puanla."
KISTASLAR = tuple(MANSET_AGIRLIKLAR)
TR_KISTASLAR = tuple(MANSET_TR_AGIRLIKLAR)

PUAN_TALIMATI = """Sen bir Türk haber sitesinin editörüsün. Son 24 saatin dünya gündeminden,
birden fazla kaynağın yazdığı olaylar var. Okura "manşet" olarak hangilerinin
sunulacağına karar vermek için her olayı aşağıdaki kıstaslarla 0-10 arası puanla.
Ölçü olayın ne kadar konuşulduğu, ilginç ya da dramatik olduğu DEĞİL; dünyaya
etkisi ve bu etkinin kalıcılığıdır.
- "etki": etkinin genişliği. 0-2: bir kişi, bir şehir, bir eyalet (suç, kaza,
  insani ilgi hikâyesi, yerel tartışma). 5: bir ülkenin geneli ya da bir bölge.
  8-10: birçok ülke, küresel piyasalar, uluslararası düzen.
- "kalicilik": sonuçlarının süresi. 0-2: tek seferlik, birkaç gün içinde unutulur.
  5: haftalarca sürer. 8-10: aylar, yıllar (yasa, anlaşma, seçim sonucu, savaşta
  kalıcı değişiklik).
- "donum": süren bir sürecin gidişatını değiştiriyor mu. 0-2: süren hikâyenin
  sıradan bir günü ya da gidişatı olmayan tekil olay. 5: kayda değer yeni
  gelişme. 8-10: dönüm noktası (ateşkes, rejim değişikliği, ilk kez olan karar).
- "eylem": 0-2: açıklama, tehdit, uyarı, yorum. 5: başlatılmış süreç, öneri,
  oylama hazırlığı. 8-10: alınmış karar, imzalanmış anlaşma, gerçekleşmiş eylem.
- "turkiye": Türkiye'ye yakınlık. 0: ilgisi yok. 5: bölgeyi, Türkiye'nin
  komşularını, enerjisini ya da göç yollarını etkiliyor. 10: doğrudan Türkiye.
Tek ülkenin iç meselesi o ülkenin dışına taşmıyorsa etkide düşük alır. Dünya
bilgini kullan ama yalnız metinlerde yazan olayı puanla.
Her olaya bir cümlelik "gerekce" yaz. Yalnız JSON döndür:
{"g0": {"etki": 7, "kalicilik": 6, "donum": 5, "eylem": 8, "turkiye": 2, "gerekce": "..."}, ...}"""

TR_PUAN_TALIMATI = """Sen bir Türk haber sitesinin editörüsün. Son 24 saatte Türkçe kaynakların ve
AA'nın yazdığı haberler var (bazısını birden fazla kaynak yazmış). Manşete bir de
Türkiye'nin en önemli olayını koymak için her olayı aşağıdaki kıstaslarla 0-10
arası puanla. Ölçü olayın Türkiye'deki önemi ve ağırlığıdır; magazin, spor,
asayiş ve tek kişinin hikâyesi düşük alır.
- "kapsam": Türkiye'de kaç kişiyi etkiliyor. 0-2: bir kişi, bir il, küçük bir
  grup. 5: bir kesim, sektör ya da bölge. 8-10: ülkenin geneli.
- "kalicilik": sonuçlarının süresi. 0-2: birkaç gün içinde unutulur. 5:
  haftalarca sürer. 8-10: aylar, yıllar (yasa, yargı kararı, seçim, kalıcı
  politika değişikliği).
- "kurumsal": devlete, yargıya, demokrasiye, basın özgürlüğüne, ekonomi
  politikasına etkisi. 0-2: yok. 5: bir kurumda kayda değer gelişme. 8-10:
  anayasal düzen, temel haklar ya da ekonomi yönetiminde önemli değişiklik.
- "kamuoyu": toplumda tartışma yaratması, sembolik önemi, gündemi belirlemesi.
  0-2: ilgi görmez. 5: bir kesimde tartışılır. 8-10: ülkenin konuştuğu olay.
- "dis_iliskiler": Türkiye'nin dış ilişkilerine ve uluslararası konumuna etkisi
  (zirve, BM ziyareti, anlaşma, kriz). 0-2: yok. 5: kayda değer. 8-10: önemli.
Protokol haberleri ("… görüştü", "… kabul etti") sonuç doğurmuyorsa düşük alır.
Olay Türkiye ile ilgili değilse (yalnız Türkçe yazılmış bir dünya haberiyse)
"turkiye_haberi": false yaz. Haber, yazan yayın kuruluşunun kendisiyle
ilgiliyse (kendisine erişim engeli, kendi çalışanı, kendi davası, kendi
kampanyası) ve onu başka bir kaynak yazmamışsa "kendi_haberi": true yaz:
kurumun kendi haberi manşete girmez. Yalnız metinlerde yazan olayı puanla.
Her olaya bir cümlelik "gerekce" yaz. Yalnız JSON döndür:
{"g0": {"turkiye_haberi": true, "kapsam": 7, "kalicilik": 6, "kurumsal": 5, "kamuoyu": 8, "dis_iliskiler": 1, "gerekce": "..."}, ...}"""

TALIMAT = """Sen bir Türk haber sitesinin editörüsün. Her olayda aynı olayı anlatan farklı
kaynakların haberleri var (İngilizce ya da Türkçe; kaynak adı alan adı olarak
verilmiş: aljazeera.com, dw.com/tr, t24.com.tr gibi). Her olay için Türkçe tek
bir derleme yaz:
- "baslik": tarafsız, bilgi eklemeyen bir haber başlığı.
- "ozet": 4-6 cümle. Olayın ne olduğunu anlat; kaynaklar farklı bilgi, rakam
  ya da vurgu veriyorsa kaynağını belirterek göster ("Al Jazeera'ya göre…",
  "Moscow Times ise … yazdı"). Kaynak adını bilinen yayın adıyla yaz (Al
  Jazeera, BBC, DW Türkçe, T24). Tek kaynağa dayanan iddiayı o kaynağa bağla.
Kurallar: yalnız metinlerde olan bilgiyi kullan, yorum ve tahmin ekleme; sayı,
isim ve tarihleri değiştirme; rakamlar zamanla değişmişse (ölü sayısı gibi)
en güncelini esas al, eskisini yazma; "reportedly", "allegedly" gibi kesinlik
kayıtlarını koru ("bildirildi", "iddia edildi"); kişi, kurum ve yayın
adlarını çevirme; kaynaklardaki İngilizce ifade ve alıntıları Türkçeye çevir
(özgün haliyle bırakma); ABD başkanı için "ABD Başkanı" de; "bugün", "dün"
gibi göreli zaman sözcükleri kullanma.
Metin içinde tırnak gerekirse “ ” kullan (JSON bozulmasın).
Yalnız JSON döndür: {"g0": {"baslik": "...", "ozet": "..."}, ...}"""


def baski_ani(simdi: datetime) -> datetime:
    """Şu andan önceki son baskı saati (Türkiye saatiyle)."""
    yerel = simdi.astimezone(TR_SAATI)
    anlar = [
        (yerel - timedelta(days=g)).replace(hour=saat, minute=0, second=0, microsecond=0)
        for g in (0, 1) for saat in MANSET_SAATLERI
    ]
    return max(a for a in anlar if a <= yerel)


def etiket(ozet: dict) -> str:
    """"3 Ekim · sabah baskısı"."""
    an = datetime.fromisoformat(ozet["baski"])
    return f"{gun_ay(an)} · {'sabah' if an.hour < 12 else 'akşam'} baskısı"


def yukle(yol: Path) -> dict:
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def kaydet(yol: Path, veri: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(veri, ensure_ascii=False) + "\n", encoding="utf-8")


def _uye(m: Makale) -> dict:
    return {"kaynak": m.kaynak, "baslik": m.baslik, "ozet": m.ozet[:UYE_UZUNLUGU], "url": m.url, "gorsel": m.gorsel}


def olaylari_kaydet(kayit: dict, gruplar: dict[tuple[str, str], list[Makale]],
                    kategoriler: dict[str, list[KaynakBolumu]], simdi: datetime) -> None:
    """Bu çalıştırmanın Gündem gruplarını ve gruba girmemiş Türkiye
    haberlerini (MANSET_TR_KAYNAKLAR; Türkiye manşeti için tek kaynaklı da)
    kayda ekler. Ortak haberi olan gruplar tek olayda birleşir (olay
    sonraki saatlerde yeni kaynak alırsa büyür); ilk görülme anı korunur."""
    makale = {m.url: m for b in kategoriler.get(MANSET_KATEGORI, []) for m in b.makaleler}
    olaylar: list[dict] = kayit.setdefault("olaylar", [])
    an = simdi.isoformat()
    gruplu = [[makale[oncu_url]] + list(digerleri) for (kat, oncu_url), digerleri in gruplar.items()
              if kat == MANSET_KATEGORI and oncu_url in makale]
    gruptakiler = {m.url for g in gruplu for m in g}
    tekler = [[m] for m in makale.values() if m.kaynak in MANSET_TR_KAYNAKLAR and m.url not in gruptakiler]
    for grup in gruplu + tekler:
        uyeler = [_uye(m) for m in grup]
        urller = {u["url"] for u in uyeler}
        kesisen = [o for o in olaylar if urller & {u["url"] for u in o["uyeler"]}]
        for o in kesisen:
            olaylar.remove(o)
        birlesik: dict[str, dict] = {}
        for o in kesisen:
            for u in o["uyeler"]:
                birlesik.setdefault(u["kaynak"], u)
        for u in uyeler:  # bu turda görülen haberin güncel hali
            birlesik[u["kaynak"]] = u
        ilk = min([o["ilk"] for o in kesisen] + [an])
        olaylar.append({"ilk": ilk, "son": an, "uyeler": list(birlesik.values())})
    sinir = simdi - SAKLAMA
    kayit["olaylar"] = [o for o in olaylar if datetime.fromisoformat(o["son"]) >= sinir]
    kayit["denemeler"] = {b: n for b, n in kayit.get("denemeler", {}).items()
                          if datetime.fromisoformat(b) >= sinir}


def adaylar(olaylar: list[dict], baski: datetime, sayi: int = MANSET_ADAY) -> list[dict]:
    """Puanlanacak olaylar: baskıdan önceki 24 saatte ortaya çıkmış, en az 2
    kaynaklılar; en çok kaynaklılar önce."""
    bas = baski - PENCERE
    secilen = [o for o in olaylar
               if datetime.fromisoformat(o["ilk"]) >= bas and len({u["kaynak"] for u in o["uyeler"]}) >= 2]
    secilen.sort(key=lambda o: -len(o["uyeler"]))
    return secilen[:sayi]


def kendi_haberi(olay: dict) -> bool:
    """Yalnız bir kaynağın yazdığı ve başlığında o kaynağın adı geçen haber
    (T24'ün "T24'e erişim engeli" haberleri): kurumun kendi haberi."""
    kaynaklar = {u["kaynak"] for u in olay["uyeler"]}
    if len(kaynaklar) != 1:
        return False
    desen = MANSET_KAYNAK_ADLARI.get(next(iter(kaynaklar)))
    return bool(desen) and all(re.search(desen, u["baslik"]) for u in olay["uyeler"])


def tr_adaylar(olaylar: list[dict], baski: datetime, haric: set[str] = frozenset(),
               sayi: int = MANSET_TR_ADAY) -> list[dict]:
    """Türkiye manşeti adayları: son 24 saatte ortaya çıkmış, Türkçe
    kaynakların ya da AA'nın yazdığı olaylar (tek kaynaklı da); haric'teki
    haberleri içerenler (dünya manşetine girenler) ve kurumun kendi haberi
    hariç."""
    bas = baski - PENCERE
    secilen = [o for o in olaylar
               if datetime.fromisoformat(o["ilk"]) >= bas
               and any(u["kaynak"] in MANSET_TR_KAYNAKLAR for u in o["uyeler"])
               and not haric & {u["url"] for u in o["uyeler"]}
               and not kendi_haberi(o)]
    secilen.sort(key=lambda o: (len(o["uyeler"]), o["son"]), reverse=True)
    return secilen[:sayi]


def _json(metin: str):
    eslesme = re.search(r"\{.*\}", metin, re.S)
    if not eslesme:
        raise ValueError(f"cevapta JSON yok: {metin[:200]}")
    return json.loads(eslesme.group(0))


def puan(kistaslar: dict, agirliklar: dict = MANSET_AGIRLIKLAR) -> float:
    """Kıstasların ağırlıklı ortalaması."""
    toplam = sum(agirliklar.values())
    return round(sum(w * kistaslar[k] for k, w in agirliklar.items()) / toplam, 2)


def puanla(olaylar: list[dict], uret: Callable[[str, str], str] | None = None,
           talimat: str = PUAN_TALIMATI, agirliklar: dict = MANSET_AGIRLIKLAR) -> list[dict | None]:
    """Her olay için {kıstas: 0-10, "gerekce", "puan"}; cevabı eksik ya da
    Türkiye haberi olmadığı söylenen (Türkiye talimatında) olay None.
    Hiçbiri puanlanamazsa ValueError."""
    uret = uret or (lambda sistem, girdi: claude_ceviri.metin_uret(PUAN_ISTEGI, girdi, sistem))
    girdi = "\n\n".join(
        f"Olay g{i}:\n" + "\n".join(f"[{u['kaynak']}] {u['baslik']} — {ilk_cumleler(u['ozet'], 2)[:400]}"
                                     for u in o["uyeler"])
        for i, o in enumerate(olaylar))
    veri = _json(uret(talimat, girdi))
    sonuc: list[dict | None] = []
    cevaplanan = 0
    for i in range(len(olaylar)):
        d = veri.get(f"g{i}") if isinstance(veri, dict) else None
        try:
            kistaslar = {k: max(0.0, min(10.0, float(d[k]))) for k in agirliklar}
        except (TypeError, KeyError, ValueError):
            sonuc.append(None)
            continue
        cevaplanan += 1
        if d.get("turkiye_haberi") is False or d.get("kendi_haberi") is True:
            sonuc.append(None)
            continue
        kistaslar["gerekce"] = str(d.get("gerekce") or "")[:300]
        kistaslar["puan"] = puan(kistaslar, agirliklar)
        sonuc.append(kistaslar)
    if not cevaplanan:
        raise ValueError("hiçbir olay puanlanamadı")
    return sonuc


def derle(olaylar: list[dict], uret: Callable[[str, str], str] | None = None) -> list[dict]:
    """Olaylar için [{"baslik", "ozet", "kaynaklar": [{"ad", "url"}]}]. Cevabı
    kullanılamayan olay atlanır; hiçbiri kullanılamazsa ValueError."""
    uret = uret or (lambda sistem, girdi: claude_ceviri.metin_uret(ISTEK, girdi, sistem))
    girdi = "\n\n".join(
        f"Olay g{i}:\n" + "\n".join(f"[{u['kaynak']}] {u['baslik']}\n{u['ozet']}" for u in o["uyeler"])
        for i, o in enumerate(olaylar))
    metin = uret(TALIMAT, girdi)
    veri = _json(metin)
    sonuc = []
    for i, o in enumerate(olaylar):
        d = veri.get(f"g{i}") if isinstance(veri, dict) else None
        baslik = str(d.get("baslik") or "").strip() if isinstance(d, dict) else ""
        ozet = str(d.get("ozet") or "").strip() if isinstance(d, dict) else ""
        if not baslik or len(ozet) < 60:
            continue
        sonuc.append({
            "baslik": baslik, "ozet": ozet, "puan": o.get("puan"), "tur": o.get("tur", "dunya"),
            # Görsel: olayı yazan kaynakların haber görsellerinden ilki.
            "gorsel": next((u["gorsel"] for u in o["uyeler"] if u.get("gorsel")), ""),
            "kaynaklar": [{"ad": u["kaynak"], "url": u["url"]} for u in o["uyeler"]],
        })
    if not sonuc:
        raise ValueError(f"kullanılabilir derleme yok: {metin[:200]}")
    return sonuc


def guncelle(kayit: dict, ozet: dict | None, simdi: datetime,
             gruplar: dict[tuple[str, str], list[Makale]], kategoriler: dict[str, list[KaynakBolumu]],
             kapali: bool = False, zorla: bool = False,
             uret: Callable[[str, str], str] | None = None) -> dict | None:
    """Olayları kaydeder; son baskı saatinin manşeti yoksa (ya da zorla)
    puanlatıp eşiği geçenleri derletir (kapali ise hiç). Kaydedilecek
    manşeti döndürür (eşiği geçen yoksa "olaylar" boş)."""
    olaylari_kaydet(kayit, gruplar, kategoriler, simdi)
    baski = baski_ani(simdi)
    hazir = (ozet or {}).get("baski") == baski.isoformat() and (ozet or {}).get("surum") == SURUM
    if kapali or (hazir and not zorla):
        return ozet
    secilen = adaylar(kayit["olaylar"], baski)
    denemeler = kayit.setdefault("denemeler", {})
    anahtar = baski.isoformat()
    if denemeler.get(anahtar, 0) >= EN_FAZLA_DENEME and not zorla:
        return ozet
    denemeler[anahtar] = denemeler.get(anahtar, 0) + 1
    try:
        puanlar = puanla(secilen, uret) if secilen else []
        dunya = _esigi_gecenler(puanlar, secilen, MANSET_ESIK, MANSET_EN_FAZLA)
        # Türkiye manşeti: dünya manşetine girenler dışındaki Türkiye haberleri,
        # kendi kıstaslarıyla.
        haric = {u["url"] for _, o in dunya for u in o["uyeler"]}
        tr_secilen = tr_adaylar(kayit["olaylar"], baski, haric)
        tr_puanlar = puanla(tr_secilen, uret, TR_PUAN_TALIMATI, MANSET_TR_AGIRLIKLAR) if tr_secilen else []
        turkiye = _esigi_gecenler(tr_puanlar, tr_secilen, MANSET_TR_ESIK, MANSET_TR_EN_FAZLA)
        secilenler = ([{**o, "puan": p["puan"]} for p, o in dunya]
                      + [{**o, "puan": p["puan"], "tur": "turkiye"} for p, o in turkiye])
        derlenen = derle(secilenler, uret) if secilenler else []
    except Exception as hata:  # noqa: BLE001 - manşet olmazsa sekme yok
        print(f"Manşet hazırlanamadı ({hata!r})", file=sys.stderr)
        return ozet
    return {
        "baski": anahtar, "surum": SURUM, "uretildi": simdi.isoformat(), "olaylar": derlenen,
        "puanlar": _puan_tablosu(puanlar, secilen), "tr_puanlar": _puan_tablosu(tr_puanlar, tr_secilen),
    }


def _esigi_gecenler(puanlar: list[dict | None], olaylar: list[dict], esik: float, en_fazla: int):
    """[(puan, olay)]: eşiği geçenler, puanı yüksek olan önce."""
    return sorted(((p, o) for p, o in zip(puanlar, olaylar) if p and p["puan"] >= esik),
                  key=lambda x: -x[0]["puan"])[:en_fazla]


def _puan_tablosu(puanlar: list[dict | None], olaylar: list[dict]) -> list[dict]:
    return [{"baslik": o["uyeler"][0]["baslik"], "kaynak": len(o["uyeler"]), **(p or {})}
            for p, o in zip(puanlar, olaylar)]


def gosterilecek(ozet: dict | None, simdi: datetime) -> dict | None:
    """Sayfadaki manşet: olayı olan ve GOSTERIM süresinden eski olmayan baskı."""
    if not ozet or not ozet.get("olaylar") or "baski" not in ozet:
        return None
    if datetime.fromisoformat(ozet["baski"]) < simdi - GOSTERIM:
        return None
    return ozet


def arsive_ekle(arsiv: list[dict], ozet: dict | None, simdi: datetime) -> list[dict]:
    """Olayı olan baskıyı önceki baskılar listesine ekler (aynı baskı yeniden
    hazırlandıysa yerine koyar); MANSET_ARSIV_GUN günden eskiler düşer.
    Yeniden eskiye sıralı."""
    sinir = simdi - timedelta(days=MANSET_ARSIV_GUN)
    liste = [b for b in arsiv if datetime.fromisoformat(b["baski"]) >= sinir]
    if ozet and ozet.get("olaylar"):
        kayit = {"baski": ozet["baski"], "olaylar": [
            {k: o.get(k) for k in ("baslik", "ozet", "tur", "kaynaklar")} for o in ozet["olaylar"]]}
        liste = [b for b in liste if b["baski"] != ozet["baski"]] + [kayit]
    return sorted(liste, key=lambda b: b["baski"], reverse=True)
