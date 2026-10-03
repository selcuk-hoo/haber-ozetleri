"""Dünün özetleri: Gündem'in başında önceki günün en çok kaynağın yazdığı
olaylarının derlemesi.

Her çalıştırmada olay süzgecinin Gündem grupları günün kaydına eklenir
(dun_olaylari.json; aynı habere sahip gruplar birleşir, kaynak sayısı
büyür). Türkiye gününün ilk çalıştırmasında önceki günün olayları iki
Claude (Sonnet) çağrısıyla işlenir:

1. Puanlama: en az 2 kaynaklı olaylar (başlık + ilk cümleler) kıstas
   kıstas 0-10 puanlanır (etki, kalıcılık, dönüm, eylem, Türkiye'ye
   yakınlık; bkz. ayarlar.DUN_OZETI_AGIRLIKLAR). Puanı burada hesaplanır
   (modelin aritmetiğine bırakılmaz). Kaynak sayısı yalnız aday seçer:
   çok yazılan ama yerel ya da yalnız ilginç olay (03.10.2026: bir
   eyaletteki başarısız infaz) özete girmesin diye.
2. Derleme: eşiği geçenler (en çok DUN_OZETI_EN_FAZLA) derlenir. Hiçbiri
   geçmezse kutu yok, ikinci çağrı yapılmaz.

Sonuç dun_ozeti.json'a yazılır (puanlar ve gerekçeler dahil); saatlik
çalıştırmalar yalnız onu okur. Günde ~10 bin token (haftalık limitin ~%1'i).

Neden Sonnet: 3.5 Flash-Lite derlemesi olayı ters anlattı, olmayan
sözcükler yazdı (~6 puan); 3.8 / 3.5 Flash gece de 503 ve zaman aşımı verdi
(02.10.2026). Sonnet ~8,5. Claude yoksa ya da çağrı başarısız olursa kutu
gösterilmez, yanlış bilgi yerine boşluk tercih edilir.

İlk kurulumda önceki günün kaydı yoktur; o çalıştırmada görülen gruplar
"dün" sayılır (bir kez).
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import claude_ceviri
from ayarlar import (
    DUN_OZETI_ADAY, DUN_OZETI_AGIRLIKLAR, DUN_OZETI_EN_FAZLA, DUN_OZETI_ESIK, DUN_OZETI_KATEGORI,
    DUN_OZETI_TURKIYE_EK, TR_SAATI,
)
from model import KaynakBolumu, Makale
from olaylar import ilk_cumleler

UYE_UZUNLUGU = 700  # kayıtta bir haberin özetinden saklanan en çok karakter
SAKLAMA_GUN = 4  # kayıt bu kadar gün tutulur
EN_FAZLA_DENEME = 3  # bir gün için en çok bu kadar Claude çağrısı (hata durumunda)
GOSTERIM_GUN = 3  # özet bu kadar gün eskiye kadar gösterilir
ISTEK = "Aşağıdaki olaylar için kurallara göre Türkçe derleme yaz."
PUAN_ISTEGI = "Aşağıdaki olayları kıstaslara göre puanla."
KISTASLAR = (*DUN_OZETI_AGIRLIKLAR, "turkiye")

PUAN_TALIMATI = """Sen bir Türk haber sitesinin editörüsün. Önceki günün dünya gündeminden,
birden fazla kaynağın yazdığı olaylar var. Okura "dünün özeti" olarak hangilerinin
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
adlarını çevirme; ABD başkanı için "ABD Başkanı" de; "bugün", "dün" gibi
göreli zaman sözcükleri kullanma.
Metin içinde tırnak gerekirse “ ” kullan (JSON bozulmasın).
Yalnız JSON döndür: {"g0": {"baslik": "...", "ozet": "..."}, ...}"""


def gun_anahtari(zaman: datetime) -> str:
    """Türkiye saatine göre gün, "2026-10-02"."""
    return zaman.astimezone(TR_SAATI).date().isoformat()


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
    return {"kaynak": m.kaynak, "baslik": m.baslik, "ozet": m.ozet[:UYE_UZUNLUGU], "url": m.url}


def olaylari_kaydet(kayit: dict, gruplar: dict[tuple[str, str], list[Makale]],
                    kategoriler: dict[str, list[KaynakBolumu]], simdi: datetime) -> None:
    """Bu çalıştırmanın Gündem gruplarını bugünün kaydına ekler. Ortak
    haberi olan gruplar tek olayda birleşir (olay sonraki saatlerde yeni
    kaynak alırsa büyür)."""
    makale = {m.url: m for b in kategoriler.get(DUN_OZETI_KATEGORI, []) for m in b.makaleler}
    gunler = kayit.setdefault("gunler", {})
    olaylar: list[dict] = gunler.setdefault(gun_anahtari(simdi), [])
    for (kat, oncu_url), digerleri in gruplar.items():
        if kat != DUN_OZETI_KATEGORI or oncu_url not in makale:
            continue
        uyeler = [_uye(makale[oncu_url])] + [_uye(m) for m in digerleri]
        urller = {u["url"] for u in uyeler}
        kesisen = [o for o in olaylar if urller & {u["url"] for u in o["uyeler"]}]
        for o in kesisen:
            olaylar.remove(o)
        birlesik: dict[str, dict] = {}
        for o in kesisen + [{"uyeler": uyeler}]:
            for u in o["uyeler"]:
                birlesik.setdefault(u["kaynak"], u)
        olaylar.append({"uyeler": list(birlesik.values())})
    sinir = gun_anahtari(simdi - timedelta(days=SAKLAMA_GUN))
    for ad in ("gunler", "denemeler"):
        if ad in kayit:
            kayit[ad] = {g: v for g, v in kayit[ad].items() if g >= sinir}


def adaylar(olaylar: list[dict], sayi: int = DUN_OZETI_ADAY) -> list[dict]:
    """Puanlanacak olaylar: en az 2 kaynaklılar, en çok kaynaklılar önce."""
    secilen = [o for o in olaylar if len({u["kaynak"] for u in o["uyeler"]}) >= 2]
    secilen.sort(key=lambda o: -len(o["uyeler"]))
    return secilen[:sayi]


def _json(metin: str):
    eslesme = re.search(r"\{.*\}", metin, re.S)
    if not eslesme:
        raise ValueError(f"cevapta JSON yok: {metin[:200]}")
    return json.loads(eslesme.group(0))


def puan(kistaslar: dict) -> float:
    """Kıstasların ağırlıklı ortalaması + Türkiye'ye yakınlık eki."""
    ortalama = sum(w * kistaslar[k] for k, w in DUN_OZETI_AGIRLIKLAR.items()) / sum(DUN_OZETI_AGIRLIKLAR.values())
    return round(ortalama + DUN_OZETI_TURKIYE_EK * kistaslar["turkiye"] / 10, 2)


def puanla(olaylar: list[dict], uret: Callable[[str, str], str] | None = None) -> list[dict | None]:
    """Her olay için {kıstas: 0-10, "gerekce", "puan"}; cevabı eksik olay
    None. Hiçbiri puanlanamazsa ValueError."""
    uret = uret or (lambda sistem, girdi: claude_ceviri.metin_uret(PUAN_ISTEGI, girdi, sistem))
    girdi = "\n\n".join(
        f"Olay g{i}:\n" + "\n".join(f"[{u['kaynak']}] {u['baslik']} — {ilk_cumleler(u['ozet'], 2)[:400]}"
                                     for u in o["uyeler"])
        for i, o in enumerate(olaylar))
    veri = _json(uret(PUAN_TALIMATI, girdi))
    sonuc: list[dict | None] = []
    for i in range(len(olaylar)):
        d = veri.get(f"g{i}") if isinstance(veri, dict) else None
        try:
            kistaslar = {k: max(0.0, min(10.0, float(d[k]))) for k in KISTASLAR}
        except (TypeError, KeyError, ValueError):
            sonuc.append(None)
            continue
        kistaslar["gerekce"] = str(d.get("gerekce") or "")[:300]
        kistaslar["puan"] = puan(kistaslar)
        sonuc.append(kistaslar)
    if not any(sonuc):
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
            "baslik": baslik, "ozet": ozet, "puan": o.get("puan"),
            "kaynaklar": [{"ad": u["kaynak"], "url": u["url"]} for u in o["uyeler"]],
        })
    if not sonuc:
        raise ValueError(f"kullanılabilir derleme yok: {metin[:200]}")
    return sonuc


def guncelle(kayit: dict, ozet: dict | None, simdi: datetime,
             gruplar: dict[tuple[str, str], list[Makale]], kategoriler: dict[str, list[KaynakBolumu]],
             kapali: bool = False, zorla: bool = False,
             uret: Callable[[str, str], str] | None = None) -> dict | None:
    """Günün olaylarını kaydeder; önceki günün özeti yoksa (ya da zorla)
    puanlatıp eşiği geçenleri derletir (günde bir kez; kapali ise hiç).
    Kaydedilecek özeti döndürür (eşiği geçen yoksa "olaylar" boş)."""
    ilk = not kayit.get("gunler")
    olaylari_kaydet(kayit, gruplar, kategoriler, simdi)
    gunler = kayit["gunler"]
    dun, bugun = gun_anahtari(simdi - timedelta(days=1)), gun_anahtari(simdi)
    if ilk and dun not in gunler and bugun in gunler:
        gunler[dun] = gunler.pop(bugun)  # ilk kurulum: görülen olaylar "dün" sayılır
    if kapali or ((ozet or {}).get("gun") == dun and not zorla):
        return ozet
    secilen = adaylar(gunler.get(dun, []))
    denemeler = kayit.setdefault("denemeler", {})
    if not secilen or (denemeler.get(dun, 0) >= EN_FAZLA_DENEME and not zorla):
        return ozet
    denemeler[dun] = denemeler.get(dun, 0) + 1
    try:
        puanlar = puanla(secilen, uret)
        sirali = sorted(
            ((p, o) for p, o in zip(puanlar, secilen) if p and p["puan"] >= DUN_OZETI_ESIK),
            key=lambda x: -x[0]["puan"])[:DUN_OZETI_EN_FAZLA]
        derlenen = derle([{**o, "puan": p["puan"]} for p, o in sirali], uret) if sirali else []
    except Exception as hata:  # noqa: BLE001 - özet olmazsa kutu yok
        print(f"Dünün özeti hazırlanamadı ({hata!r})", file=sys.stderr)
        return ozet
    return {
        "gun": dun, "uretildi": simdi.isoformat(), "olaylar": derlenen,
        "puanlar": [{"baslik": o["uyeler"][0]["baslik"], "kaynak": len(o["uyeler"]), **(p or {})}
                    for p, o in zip(puanlar, secilen)],
    }


def gosterilecek(ozet: dict | None, simdi: datetime) -> dict | None:
    """Sayfadaki kutu: son GOSTERIM_GUN gün içindeki, olayı olan özet."""
    if ozet and ozet.get("olaylar") and ozet.get("gun", "") >= gun_anahtari(simdi - timedelta(days=GOSTERIM_GUN)):
        return ozet
    return None
