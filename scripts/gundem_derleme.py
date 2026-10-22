"""Gündem'in çok kaynaklı olaylarına derleme özet (22.10.2026, DENEME).

Türkiye sekmesinin benzeri, Gündem'in içinde: olay süzgecinin en az
EN_AZ_KAYNAK kaynaklı gruplarında ana kartın özeti yerine kaynakların
metinlerinden derlenmiş tek bir Türkçe özet. Ötekiler (ilgili haberler,
tek kaynaklı haberler) bugünkü gibi kalır; bakış açısı farkı kaybolmasın diye
kaynakların ayrı haberleri kartın altında durur.

Kullanıcının kararıyla önce deneme: GOSTER False iken derlemeler yalnız
yazılır (dist/gundem_derleme.json, loga [DERLEME]), sayfaya girmez.
Gemini Flash-Lite (ücretsiz kota): çalıştırma başına en çok 1 istek; bir
olayın derlemesi yalnız gruba yeni kaynak katılınca yenilenir.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import gemini_ceviri

GOSTER = False
EN_AZ_KAYNAK = 3
ISTEK_BASINA_OLAY = 8
SAKLAMA = timedelta(days=2)
MODELLER = ("gemini-flash-lite-latest", "gemini-3.1-flash-lite")  # 2.5 Flash özeti İngilizce yazmıştı

TALIMAT = """Sen bir Türk haber sitesinin editörüsün. Her olay için farklı yayın kuruluşlarının
(BBC, Al Jazeera, CNN, DW…) aynı olayı anlatan haberleri verildi; çoğu İngilizce. Her olay için:
- "baslik": kısa, yansız bir Türkçe başlık (en çok 12 sözcük),
- "ozet": 3-4 cümlelik Türkçe derleme: önce ne oldu (kim, ne, nerede), sonra metinlerde varsa son
  durum, tepkiler ve önemli ayrıntı. Kaynakların verdiği bilgiyi birleştir, aynı bilgiyi tekrarlama.
  Kaynaklar bir noktada farklı şey söylüyorsa ya da biri ötekilerinde olmayan bir iddiayı aktarıyorsa
  bunu kaynağıyla yaz ("Al Jazeera'ya göre …").
Yansız ol: iddiaları kimin söylediğiyle yaz; kesinlik kayıtlarını koru ("bildirildi", "iddia edildi").
Yalnız metinlerdeki bilgiyi kullan; sayı, isim ve tarihleri değiştirme; kişi, kurum ve yayın adlarını
çevirme; ülke ve şehir adlarının Türkçede yerleşik biçimini kullan. Özetin tamamı Türkçe olsun;
yalnız Türk alfabesiyle, yazım kurallarına uygun yaz.
Yalnız JSON döndür: {"o0": {"baslik": "...", "ozet": "..."}, ...}"""


def yukle(yol: Path) -> list[dict]:
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        return veri if isinstance(veri, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def kaydet(yol: Path, kayit: list[dict]) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(kayit, ensure_ascii=False) + "\n", encoding="utf-8")


def _gemini(girdi: str, uret=None) -> dict | None:
    uret = uret or gemini_ceviri.metin_uret
    for model in MODELLER:
        try:
            metin = uret(model, TALIMAT, girdi)
            return json.loads(metin[metin.index("{"):metin.rindex("}") + 1])
        except Exception as hata:  # noqa: BLE001 - olmazsa derleme yok, kart eskisi gibi
            print(f"Gündem derlemesi ({model}) cevap alamadı: {hata!r}", file=sys.stderr)
    return None


def guncelle(kayit: list[dict], olaylar: list[list], simdi: datetime, uret=None) -> list[dict]:
    """olaylar: [[öncü Makale, öteki Makale'ler…]] (Gündem grupları). Yeni ya
    da yeni kaynak almış olaylar derlenir; kayıt döner."""
    from ceviri import Cevirmen  # döngüsel içe aktarmadan kaçınmak için burada
    sinir = (simdi - SAKLAMA).isoformat()
    kayit = [o for o in kayit if o.get("zaman", "") >= sinir]
    bekleyen = []
    for uyeler in olaylar:
        kaynaklar = sorted({m.kaynak for m in uyeler})
        if len(kaynaklar) < EN_AZ_KAYNAK:
            continue
        urller = {m.url for m in uyeler}
        onceki = next((o for o in kayit if urller & set(o["urller"])), None)
        if onceki is not None:
            onceki["urller"] = sorted(urller | set(onceki["urller"]))
            if not set(kaynaklar) - set(onceki["kaynaklar"]):
                continue
        bekleyen.append((uyeler, kaynaklar, onceki))
    bekleyen = bekleyen[:ISTEK_BASINA_OLAY]
    if not bekleyen or (uret is None and not gemini_ceviri.kullanilabilir_mi()):
        return kayit
    satirlar = []
    for i, (uyeler, _, _) in enumerate(bekleyen):
        satirlar.append(f"o{i}:")
        for m in uyeler[:5]:
            satirlar.append(f"  [{m.kaynak}] {m.baslik}\n  {(m.uzun or m.ozet)[:1200]}")
    cevap = _gemini("\n".join(satirlar), uret) or {}
    for i, (uyeler, kaynaklar, onceki) in enumerate(bekleyen):
        c = cevap.get(f"o{i}")
        if not isinstance(c, dict) or not isinstance(c.get("ozet"), str) or not isinstance(c.get("baslik"), str):
            continue
        ozet, baslik = c["ozet"].strip(), c["baslik"].strip()
        kaynak_metin = " ".join(m.baslik + " " + (m.uzun or m.ozet) for m in uyeler).lower()
        aksanli = set(Cevirmen.LATIN_YABANCI.findall(ozet.lower())) - set(Cevirmen.LATIN_YABANCI.findall(kaynak_metin))
        if len(ozet) < 60 or Cevirmen.ingilizce_mi(ozet) or Cevirmen.YABANCI_HARF.search(ozet + baslik) or aksanli:
            continue
        yeni = {"urller": sorted({m.url for m in uyeler} | set((onceki or {}).get("urller", []))),
                "kaynaklar": kaynaklar, "baslik": baslik, "ozet": ozet, "zaman": simdi.isoformat()}
        if onceki is not None:
            onceki.update(yeni)
        else:
            kayit.append(yeni)
        print(f"[DERLEME] {baslik} ({', '.join(kaynaklar)})\n  {ozet}")
    return kayit


def ozet_bul(kayit: list[dict], url: str) -> dict | None:
    return next((o for o in kayit if url in o["urller"]), None)
