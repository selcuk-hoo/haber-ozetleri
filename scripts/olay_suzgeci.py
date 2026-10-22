"""Aynı olayı anlatan haberlerin gruplanması: gevşek aday + Gemini süzgeci.

olaylar.py'nin kelime benzerliğine dayalı gruplaması tek başına "aynı konu,
farklı olay" hataları yapıyordu (02.10.2026, 14 grubun 3'ü: "Tek günlük
korolar" ile "Anthropic'in VPN kısıtlaması", FAO yetkilisi ile Kızılay'ın
protez haberi). Burada algoritma gevşek eşikle ADAY gruplar üretir; Gemini
her adayda aynı somut olayı anlatanları seçer, ötekileri çıkarır. Gemini
sıfırdan grup kuramaz, yalnız adayları süzer.

Karar saklanır (olay_kararlari.json, gh-pages'te): aynı aday bir daha
sorulmaz; üyeleri azalmış bir aday (haber sayfadan düştü) eski karardan
türetilir. Yalnız yeni ya da yeni üye almış adaylar, çalıştırma başına tek
istekte sorulur. Gemini yoksa ya da cevap vermezse o haberler için bugünkü
temkinli algoritma (olaylar.ESIK) kullanılır.

Model 3.5 Flash-Lite: canlı adaylarda 10 olayın 10'u doğru, 1 sn; 3.5
Flash aynı sonucu 21 sn'de verdi, 3.1 Flash-Lite iki yanlış birleştirme
yaptı. Ücretsiz hakkı günde 500 istek (AI Studio, 02.10.2026).
"""

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import gemini_ceviri
import olaylar
from model import KaynakBolumu, Makale
from tarih import sira_zamani

GEVSEK_ESIK = 0.12
GEVSEK_ORTAK_ISIM = 1
MODELLER = ("gemini-flash-lite-latest", "gemini-3.5-flash")
SAKLAMA = timedelta(days=3)  # bu süre kullanılmayan karar silinir
ISTEK_BASINA_ADAY = 60

TALIMAT = """Sen bir haber sitesinin editörüsün. Bir algoritma benzer görünen haberleri aday
gruplar halinde topladı (kimlik [kaynak] başlık — ilk cümle). Her aday grupta
aynı somut olayı anlatan haberleri belirle; olayı farklı olanları çıkar. Bir
aday birden fazla olaya bölünebilir.
Aynı olay: aynı gelişme, açıklama, saldırı, karar ya da toplantı; o olaya
verilen tepkiler de (bir karara, reklama, saldırıya ya da sözlere ilgililerin,
partilerin, liderlerin verdiği tepkiler) ve olayın aynı günkü devamı aynı
olaydır. Yalnız aynı genel konu (ör. "Ukrayna savaşı", "Gazze", "ABD
seçimleri") YETMEZ: aynı konunun başka bir gelişmesi ayrı olaydır. Bir olayda
her kaynaktan en fazla bir haber. Açıklama yazma, yalnız JSON döndür.
Yalnız 2 ve daha fazla haberli olayları döndür: {"olaylar": [["h1", "h7"], ...]}"""

# Bu çalıştırmanın özeti (loga yazılır) ve sağlık takibi.
durum: dict = {"aday": 0, "kayitli": 0, "soruldu": 0, "hata": None}


# Talimat değişince artırılır: adaylar bir kez yeniden sorulur (eski kararların
# yalnız "aynı olay" dedikleri korunur, bkz. _onceki_birlesmeler).
# 2 (22.10.2026): tepkiler aynı olay sayılır. Amy Acton'ın saldırı reklamına
# yanıtı (BBC), Vance'in aynı reklam üstüne sözleri (France24) ve CNN'in canlı
# yayını "farklı açıklama" diye ayrı kartlarda kalıyordu.
SURUM = "2"


def anahtar(urller) -> str:
    return hashlib.sha1((SURUM + "\n" + "\n".join(sorted(urller))).encode("utf-8")).hexdigest()[:16]


def _onceki_birlesmeler(aday: list[str], kararlar: dict[str, dict]) -> list[set[str]]:
    """Adayın üyelerinden daha önce (herhangi bir sürümde) "aynı olay" diye
    birleştirilmiş olanlar."""
    kume = set(aday)
    sonuc = []
    for k in kararlar.values():
        for olay in k.get("olaylar", []):
            ic = {u for u in olay if u in kume}
            if len(ic) >= 2:
                sonuc.append(ic)
    return sonuc


def birlesmeleri_koru(olaylari: list[list[str]], onceki: list[set[str]]) -> list[list[str]]:
    """Daha önce birleştirilmiş haberler, aday yeni üye alıp yeniden
    sorulunca ayrılmasın (22.10.2026: BBC + CNN'in Amy Acton haberleri
    birleşmişti, France24 katılınca Gemini hiçbirini birleştirmedi)."""
    # Sıra korunur: aynı kaynaktan iki haber varsa Gemini'nin önce verdiği kalır.
    gruplar = [list(dict.fromkeys(o)) for o in olaylari]
    for p in onceki:
        kesisen = [g for g in gruplar if p & set(g)]
        birlesik = list(dict.fromkeys([u for g in kesisen for u in g] + sorted(p)))
        gruplar = [g for g in gruplar if not p & set(g)] + [birlesik]
    return gruplar


def kararlari_yukle(yol: Path) -> dict[str, dict]:
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def kararlari_kaydet(yol: Path, kararlar: dict[str, dict], simdi: datetime) -> None:
    sinir = (simdi - SAKLAMA).isoformat()
    guncel = {k: v for k, v in kararlar.items() if v.get("zaman", "") >= sinir}
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(guncel, ensure_ascii=False) + "\n", encoding="utf-8")


def _karar_bul(urller: list[str], kararlar: dict[str, dict]) -> list[list[str]] | None:
    """Adayın kararı: kendisininki ya da onu kapsayan (üyeleri azalmış)
    bir adayınki, adayın üyelerine daraltılarak."""
    karar = kararlar.get(anahtar(urller))
    kume = set(urller)
    if karar is None:
        karar = next((k for k in kararlar.values()
                      if k.get("s") == SURUM and kume <= set(k.get("urller", []))), None)
    if karar is None:
        return None
    return [[u for u in olay if u in kume] for olay in karar.get("olaylar", [])]


def gemini_sor(adaylar: list[list[Makale]], ingilizceler: dict[str, tuple[str, str]],
               uret: Callable[[str, str, str], str] | None = None) -> list[list[list[str]]] | None:
    """Adayların her biri için olaylar (url listeleri); başarısızsa None."""
    uret = uret or gemini_ceviri.metin_uret
    kimlik: dict[str, str] = {}
    satirlar = []
    for i, aday in enumerate(adaylar):
        satirlar.append(f"Aday {i}:")
        for m in aday:
            k = f"h{len(kimlik)}"
            kimlik[k] = m.url
            baslik, ozet = ingilizceler.get(m.url, (m.baslik, m.ozet))
            satirlar.append(f"{k} [{m.kaynak}] {baslik} — {olaylar.ilk_cumleler(ozet, 1)[:300]}")
        satirlar.append("")
    for model in MODELLER:
        try:
            metin = uret(model, TALIMAT, "\n".join(satirlar))
            cevap = json.loads(metin[metin.index("{"):metin.rindex("}") + 1])
            break
        except Exception as hata:  # noqa: BLE001 - olmazsa temkinli algoritma
            print(f"Olay süzgeci ({model}) cevap alamadı: {hata!r}", file=sys.stderr)
            durum["hata"] = repr(hata)[:300]
    else:
        return None
    durum["hata"] = None
    hangi_aday = {m.url: i for i, aday in enumerate(adaylar) for m in aday}
    sonuc: list[list[list[str]]] = [[] for _ in adaylar]
    for olay in cevap.get("olaylar", []):
        urller = [kimlik[k] for k in dict.fromkeys(olay) if isinstance(k, str) and k in kimlik]
        if not urller:
            continue
        # Bir olay tek adayın içinde kalır (ilk üyenin adayı).
        i = hangi_aday[urller[0]]
        sonuc[i].append([u for u in urller if hangi_aday[u] == i])
    return sonuc


def grupla(
    kategoriler: dict[str, list[KaynakBolumu]],
    ingilizceler: dict[str, tuple[str, str]],
    turkce_kaynaklar: frozenset[str] | set[str],
    kararlar: dict[str, dict],
    sor: Callable[[list[list[Makale]], dict[str, tuple[str, str]]], list[list[list[str]]] | None] | None = None,
    simdi: datetime | None = None,
) -> dict[tuple[str, str], list[Makale]]:
    """olaylar.olaylari_grupla ile aynı biçim: {(kategori, öncü url): [diğerleri]}.
    sor None ise (Gemini yok) yalnız kayıtlı kararlar ve temkinli algoritma."""
    simdi = simdi or datetime.now(timezone.utc)
    makale = {m.url: (kat, m) for kat, bolumler in kategoriler.items() for b in bolumler for m in b.makaleler}
    adaylar = [
        [oncu] + [m.url for m in digerleri]
        for (_, oncu), digerleri in olaylar.olaylari_grupla(
            kategoriler, ingilizceler, turkce_kaynaklar, esik=GEVSEK_ESIK, en_az_ortak_isim=GEVSEK_ORTAK_ISIM).items()
    ]
    durum.update(aday=len(adaylar), kayitli=0, soruldu=0)
    bilinmeyen = [a for a in adaylar if _karar_bul(a, kararlar) is None][:ISTEK_BASINA_ADAY]
    if bilinmeyen and sor is not None:
        cevap = sor([[makale[u][1] for u in a] for a in bilinmeyen], ingilizceler)
        if cevap is not None:
            durum["soruldu"] = len(bilinmeyen)
            for a, olaylari in zip(bilinmeyen, cevap):
                olaylari = birlesmeleri_koru(olaylari, _onceki_birlesmeler(a, kararlar))
                kararlar[anahtar(a)] = {"urller": a, "olaylar": olaylari, "zaman": simdi.isoformat(), "s": SURUM}

    olay_listesi: list[list[str]] = []
    karari_olan: set[str] = set()
    for a in adaylar:
        karar = _karar_bul(a, kararlar)
        if karar is None:
            continue
        kayit = kararlar.get(anahtar(a))
        if kayit is not None:
            kayit["zaman"] = simdi.isoformat()
        else:
            # Üyeleri azalmış aday: kendi kaydı da tutulur (kapsayan eski
            # karar silinse de geçerli kalsın).
            kararlar[anahtar(a)] = {"urller": a, "olaylar": karar, "zaman": simdi.isoformat(), "s": SURUM}
        durum["kayitli"] += 1
        karari_olan.update(a)
        olay_listesi.extend(karar)
    # Kararı olmayan haberler için bugünkü temkinli gruplama.
    for (_, oncu), digerleri in olaylar.olaylari_grupla(kategoriler, ingilizceler, turkce_kaynaklar).items():
        uyeler = [oncu] + [m.url for m in digerleri]
        if not karari_olan & set(uyeler):
            olay_listesi.append(uyeler)

    sonuc: dict[tuple[str, str], list[Makale]] = {}
    for olay in olay_listesi:
        uyeler: list[Makale] = []
        kaynaklar: set[str] = set()
        for u in olay:
            if u in makale and makale[u][1].kaynak not in kaynaklar:
                kaynaklar.add(makale[u][1].kaynak)
                uyeler.append(makale[u][1])
        if len(uyeler) < 2:
            continue
        uyeler.sort(key=sira_zamani, reverse=True)
        sonuc[(makale[uyeler[0].url][0], uyeler[0].url)] = uyeler[1:]
    return sonuc


def ozet() -> str:
    d = durum
    return (f"{d['aday']} aday ({d['kayitli']} kararlı, {d['soruldu']} yeni soruldu)"
            + (f"; hata: {d['hata']}" if d["hata"] else ""))
