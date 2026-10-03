"""Dünün özetleri: Gündem'in başında önceki günün en çok kaynağın yazdığı
olaylarının derlemesi.

Her çalıştırmada olay süzgecinin Gündem grupları günün kaydına eklenir
(dun_olaylari.json; aynı habere sahip gruplar birleşir, kaynak sayısı
büyür). Türkiye gününün ilk çalıştırmasında önceki günün en çok kaynaklı
DUN_OZETI_OLAY_SAYISI olayı tek Claude (Sonnet) çağrısıyla derlenir ve
dun_ozeti.json'a yazılır; saatlik çalıştırmalar yalnız onu okur. Günde bir
çağrı, ~10 bin token (haftalık limitin ~%1'i).

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
from ayarlar import DUN_OZETI_KATEGORI, DUN_OZETI_OLAY_SAYISI, TR_SAATI
from model import KaynakBolumu, Makale

UYE_UZUNLUGU = 700  # kayıtta bir haberin özetinden saklanan en çok karakter
SAKLAMA_GUN = 4  # kayıt bu kadar gün tutulur
EN_FAZLA_DENEME = 3  # bir gün için en çok bu kadar Claude çağrısı (hata durumunda)
GOSTERIM_GUN = 3  # özet bu kadar gün eskiye kadar gösterilir
ISTEK = "Aşağıdaki olaylar için kurallara göre Türkçe derleme yaz."

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


def secim(olaylar: list[dict], sayi: int = DUN_OZETI_OLAY_SAYISI) -> list[dict]:
    """En çok kaynağın yazdığı olaylar (en az 2 kaynak)."""
    adaylar = [o for o in olaylar if len({u["kaynak"] for u in o["uyeler"]}) >= 2]
    adaylar.sort(key=lambda o: -len(o["uyeler"]))
    return adaylar[:sayi]


def derle(olaylar: list[dict], uret: Callable[[str, str], str] | None = None) -> list[dict]:
    """Olaylar için [{"baslik", "ozet", "kaynaklar": [{"ad", "url"}]}]. Cevabı
    kullanılamayan olay atlanır; hiçbiri kullanılamazsa ValueError."""
    uret = uret or (lambda sistem, girdi: claude_ceviri.metin_uret(ISTEK, girdi, sistem))
    girdi = "\n\n".join(
        f"Olay g{i}:\n" + "\n".join(f"[{u['kaynak']}] {u['baslik']}\n{u['ozet']}" for u in o["uyeler"])
        for i, o in enumerate(olaylar))
    metin = uret(TALIMAT, girdi)
    eslesme = re.search(r"\{.*\}", metin, re.S)
    if not eslesme:
        raise ValueError(f"cevapta JSON yok: {metin[:200]}")
    veri = json.loads(eslesme.group(0))
    sonuc = []
    for i, o in enumerate(olaylar):
        d = veri.get(f"g{i}") if isinstance(veri, dict) else None
        baslik = str(d.get("baslik") or "").strip() if isinstance(d, dict) else ""
        ozet = str(d.get("ozet") or "").strip() if isinstance(d, dict) else ""
        if not baslik or len(ozet) < 60:
            continue
        sonuc.append({
            "baslik": baslik, "ozet": ozet,
            "kaynaklar": [{"ad": u["kaynak"], "url": u["url"]} for u in o["uyeler"]],
        })
    if not sonuc:
        raise ValueError(f"kullanılabilir derleme yok: {metin[:200]}")
    return sonuc


def guncelle(kayit: dict, ozet: dict | None, simdi: datetime,
             gruplar: dict[tuple[str, str], list[Makale]], kategoriler: dict[str, list[KaynakBolumu]],
             kapali: bool = False, uret: Callable[[str, str], str] | None = None) -> dict | None:
    """Günün olaylarını kaydeder; önceki günün özeti yoksa derler (günde
    bir kez; kapali ise hiç). Gösterilecek özeti ya da None döndürür."""
    ilk = not kayit.get("gunler")
    olaylari_kaydet(kayit, gruplar, kategoriler, simdi)
    gunler = kayit["gunler"]
    dun, bugun = gun_anahtari(simdi - timedelta(days=1)), gun_anahtari(simdi)
    if ilk and dun not in gunler and bugun in gunler:
        gunler[dun] = gunler.pop(bugun)  # ilk kurulum: görülen olaylar "dün" sayılır
    if (ozet or {}).get("gun") != dun and not kapali:
        secilen = secim(gunler.get(dun, []))
        denemeler = kayit.setdefault("denemeler", {})
        if secilen and denemeler.get(dun, 0) < EN_FAZLA_DENEME:
            denemeler[dun] = denemeler.get(dun, 0) + 1
            try:
                ozet = {"gun": dun, "uretildi": simdi.isoformat(), "olaylar": derle(secilen, uret)}
            except Exception as hata:  # noqa: BLE001 - özet olmazsa kutu yok
                print(f"Dünün özeti derlenemedi ({hata!r})", file=sys.stderr)
    if ozet and ozet.get("gun", "") >= gun_anahtari(simdi - timedelta(days=GOSTERIM_GUN)) and ozet.get("olaylar"):
        return ozet
    return None
