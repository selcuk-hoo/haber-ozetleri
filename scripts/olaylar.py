"""Aynı olayı anlatan haberleri gruplama (yapay zeka olmadan).

İki haber, başlıkları ve özetlerinin ilk iki cümlesi TF-IDF kosinüs
benzerliğiyle yeterince yakınsa VE en az iki ortak özel isim/sayı
paylaşıyorsa (Putin, Miami, Albanese, 81…) aynı olay sayılır. Sadece aynı
kategorideki farklı kaynaklar birleşir; bir grupta her kaynaktan tek haber
olur.

Bir gruptaki HER haber çifti bu ölçütü sağlamalı (tam bağlantılı
birleştirme); "aynı konu, farklı olay" eşleşmelerini azaltan bu. Eşik canlı sitedeki iki farklı anın haberleriyle
ayarlandı (0.30: 22 grubun 21'i doğru, biri sınırda). Kaçırılan bir
birleşme zararsız (haberler ayrı kart kalır); yanlış birleşme daha kötü
olduğu için eşik temkinli.
"""

import math
import re
from collections import Counter
from dataclasses import replace
from functools import lru_cache
from datetime import datetime, timedelta

from model import KaynakBolumu, Makale
from tarih import sira_anahtari, sira_zamani

ESIK = 0.30
EN_AZ_ORTAK_ISIM = 2
# Öncüyle arasında bundan fazla zaman olan haber aynı olay sayılmaz.
ZAMAN_PENCERESI = timedelta(hours=48)

_DURAK = set(
    """a an the and or but of in on at to for from by with as is are was were be been being has have had
    it its this that these those he she they his her their them we our you your i not no will would can could may
    might said says say also after before over into about than more most new one two three who what when where
    which while up out off just all any some such only other there here how why do does did so if then per mr ms
    """.split()
)
# Aynı kaynağın aynı haberi ikinci bir adresle vermesi (yazım hatası
# düzeltilmiş kopya, bir iki kelimesi değişmiş başlık, aynı yazının iki
# ayrı adresi). Başlıklardaki kelimelerin örtüşmesi
# (Jaccard) 0.7 ve arada en fazla 12 saat, ya da 0.5 ve en fazla 1 saat.
# 7 günlük arşivde denendi: "10. kadın" / "11. kadın" (30 saat arayla) ya
# da "Dışişleri Bakanı İranlı / Bahreynli mevkidaşıyla görüştü" (4 saat,
# 0.67) gibi ayrı haberler tekrar sayılmıyor.
TEKRAR_ESIKLERI = ((0.7, timedelta(hours=12)), (0.5, timedelta(hours=1)))
TEKRAR_EN_UZUN = max(sure for _, sure in TEKRAR_ESIKLERI)


@lru_cache(maxsize=None)
def _baslik_kelimeleri(baslik: str) -> tuple[frozenset[str], frozenset[str]]:
    """(küçük harfli kelimeler, özel isimler ve sayılar). İlk kelime büyük
    harfle başladığı için özel isim sayılmaz."""
    kelimeler = [k for k in re.findall(r"[\w$.]+", baslik.replace("’", "'")) if len(k) > 1]
    ozel = frozenset(k.lower() for k in kelimeler[1:] if k[0].isupper() or any(c.isdigit() for c in k))
    return frozenset(k.lower() for k in kelimeler), ozel


def tekrar_mi(baslik1: str, tarih1: str, baslik2: str, tarih2: str) -> bool:
    return zamanla_tekrar_mi(baslik1, sira_anahtari(tarih1), baslik2, sira_anahtari(tarih2))


def zamanla_tekrar_mi(baslik1: str, zaman1: datetime, baslik2: str, zaman2: datetime) -> bool:
    fark = abs(zaman1 - zaman2)
    if fark > TEKRAR_EN_UZUN:
        return False
    (a, ozel_a), (b, ozel_b) = _baslik_kelimeleri(baslik1), _baslik_kelimeleri(baslik2)
    if not a or not b:
        return False
    # İki başlıkta da ötekinde olmayan bir özel isim ya da sayı varsa ayrı
    # haber ("Endonezya'da yapılacak 11 şey" / "Karadağ'da yapılacak 18 şey",
    # "10. kadın" / "11. kadın").
    if (ozel_a - b) and (ozel_b - a):
        return False
    ortaklik = len(a & b) / len(a | b)
    return any(ortaklik >= esik and fark <= sure for esik, sure in TEKRAR_ESIKLERI)


# Özel isim gibi büyük harfle yazılan ama olay ayırt etmeyen kelimeler.
_GENEL_ISIM = set(
    """live updates says said new why how what who when after first world news more president prime minister
    government state officials people day week year told update""".split()
)


def ilk_cumleler(metin: str, n: int = 2) -> str:
    return " ".join(re.split(r"(?<=[.!?])\s+", metin)[:n])


def _kelimeler(metin: str) -> list[str]:
    return [
        k for k in re.findall(r"[a-zçğıöşüâ0-9][a-zçğıöşüâ0-9'-]+", metin.lower())
        if k not in _DURAK and len(k) > 2
    ]


def _ozel_isimler(m: Makale) -> set[str]:
    metin = m.baslik + ". " + ilk_cumleler(m.ozet)
    isimler = set()
    for w in re.findall(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-zA-Z'’-]{2,}|[A-Z]{2,}|\d{2,})", metin):
        w = re.sub(r"[’']s$", "", w.lower())
        if w not in _GENEL_ISIM and w not in _DURAK:
            isimler.add(w)
    return isimler


def _vektorler(makaleler: list[Makale]) -> list[dict[str, float]]:
    # Başlık iki kez sayılıyor: olayı en yoğun anlatan kısım o.
    belgeler = [Counter(_kelimeler(m.baslik) * 2 + _kelimeler(ilk_cumleler(m.ozet))) for m in makaleler]
    df = Counter(w for b in belgeler for w in b)
    n = len(belgeler)
    vektorler = []
    for b in belgeler:
        # Tek bir haberde geçen kelime iki haberi bağlayamaz; atlanıyor.
        v = {w: c * math.log(n / df[w]) for w, c in b.items() if df[w] > 1}
        uzunluk = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vektorler.append({w: x / uzunluk for w, x in v.items()})
    return vektorler


def _kosinus(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0.0) for w, x in a.items())


# Döner: {(kategori, öncü url'i): [aynı olayı anlatan diğer haberler]}.
# IDF tüm sayfadaki haberler üzerinden hesaplanır (kategori başına az haber
# var). Öncü, grubun en yeni haberi. ingilizceler: Türkçe kaynaklardaki
# haberlerin İngilizce (başlık, ilk cümleler) çevirisi, url'e göre;
# karşılaştırma bunlarla yapılır ki Türkçe bir haber aynı olayın İngilizce
# haberleriyle eşleşebilsin. Çevirisi olmayan Türkçe haber gruplanmaz.
def olaylari_grupla(
    kategoriler: dict[str, list[KaynakBolumu]],
    ingilizceler: dict[str, tuple[str, str]] | None = None,
    turkce_kaynaklar: frozenset[str] | set[str] = frozenset(),
    esik: float | None = None,
    en_az_ortak_isim: int | None = None,
) -> dict[tuple[str, str], list[Makale]]:
    # esik / en_az_ortak_isim: olay süzgecinin gevşek adayları için (bkz.
    # olay_suzgeci.py); verilmezse bugünkü temkinli eşikler.
    esik = ESIK if esik is None else esik
    en_az_ortak_isim = EN_AZ_ORTAK_ISIM if en_az_ortak_isim is None else en_az_ortak_isim
    ingilizceler = ingilizceler or {}
    tumu = [
        (kat, m) for kat, bolumler in kategoriler.items() for b in bolumler for m in b.makaleler
        if m.kaynak not in turkce_kaynaklar or m.url in ingilizceler
    ]
    if not tumu:
        return {}
    karsilastirilan = [
        replace(m, baslik=ingilizceler[m.url][0], ozet=ingilizceler[m.url][1]) if m.url in ingilizceler else m
        for _, m in tumu
    ]
    vektorler = _vektorler(karsilastirilan)
    isimler = [_ozel_isimler(m) for m in karsilastirilan]
    zamanlar = [sira_zamani(m) for _, m in tumu]

    def benzerlik(i: int, j: int) -> float:
        """Aynı olay sayılabilecek çiftin puanı; sayılamıyorsa 0."""
        if tumu[i][0] != tumu[j][0] or tumu[i][1].kaynak == tumu[j][1].kaynak:
            return 0.0
        if abs(zamanlar[i] - zamanlar[j]) > ZAMAN_PENCERESI:
            return 0.0
        if len(isimler[i] & isimler[j]) < en_az_ortak_isim:
            return 0.0
        puan = _kosinus(vektorler[i], vektorler[j])
        return puan if puan >= esik else 0.0

    # Tam bağlantılı birleştirme: en benzer çiftten başlayarak iki grup,
    # ancak aralarındaki HER çift aynı olay sayılabiliyorsa birleşir. Sıra
    # bağımsız; zincirleme yok (A~B ve B~C diye A ile C aynı gruba düşmez).
    ciftler = sorted(
        ((puan, i, j) for i in range(len(tumu)) for j in range(i + 1, len(tumu)) if (puan := benzerlik(i, j))),
        reverse=True,
    )
    grup_no = list(range(len(tumu)))
    uyeler: dict[int, list[int]] = {i: [i] for i in range(len(tumu))}
    for _, i, j in ciftler:
        a, b = grup_no[i], grup_no[j]
        if a == b:
            continue
        if not all(benzerlik(x, y) for x in uyeler[a] for y in uyeler[b]):
            continue
        for x in uyeler[b]:
            grup_no[x] = a
        uyeler[a].extend(uyeler.pop(b))

    sonuc: dict[tuple[str, str], list[Makale]] = {}
    for grup in uyeler.values():
        if len(grup) < 2:
            continue
        grup.sort(key=lambda i: zamanlar[i], reverse=True)
        kategori, oncu = tumu[grup[0]]
        sonuc[(kategori, oncu.url)] = [tumu[i][1] for i in grup[1:]]
    return sonuc
