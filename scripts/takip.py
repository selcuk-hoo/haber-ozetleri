"""Haber takibi: ilk görülme anı ve içerik güncellemeleri.

Her haber (url) için bir kayıt tutulur:
  ilk          haberi ilk gördüğümüz an. Kaynak güvenilir bir yayın saati
               vermiyorsa (CNN, Al Jazeera gibi) haberin tarihi budur,
               sayfada "~" ile gösterilir.
  son          haberi en son gördüğümüz an. Kayıt bundan TAKIP_SURESI
               sonra silinir. Haber bir turda kaynağın listesinden düşüp
               sonra geri gelirse kayıt durduğu için "yeni" sayılmaz
               (eskiden kayıt hemen siliniyordu; CNN'in anasayfa listesi
               oynadıkça aynı haber günde birkaç kez en üste çıkıyordu).
  imza         başlığın ve özet cümlelerinin kısa özetleri (hash).
  guncellendi  içerik son kez ne zaman "güncellendi" sayıldı (yoksa boş).

Güncelleme: haberin başlığı ya da ilk cümlesi değişmişse ya da özete en
az iki yeni cümle girmişse haber güncellenmiş sayılır, sırası o ana taşınır
ve sayfada "güncellendi" yazar. Canlı yayın sayfaları gibi sürekli değişen
haberler her turda zıplamasın diye bir haber en fazla GUNCELLEME_ARALIGI'nda
bir güncellenmiş sayılır; arada biriken değişiklik bekler. Bir kaynağın
haberlerinin çoğu aynı turda birden değişirse bu bizim tarafımızdaki bir
değişikliktir (yeni temizlik kuralı, özet uzunluğu): imzalar yenilenir ama
haberler güncellenmiş sayılmaz.

Dosya arşiv ve çeviri önbelleği gibi gh-pages'te durur (bkz. workflow).
"""

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tarih import sira_anahtari, tarihi_ayristir

TAKIP_SURESI = timedelta(days=7)
GUNCELLEME_ARALIGI = timedelta(hours=3)
# Bir kaynağın kaydı olan haberlerinden en az bu kadarı (ve en az
# TOPLU_DEGISIKLIK_EN_AZ tanesi) aynı turda değişmişse toplu değişiklik.
TOPLU_DEGISIKLIK_ORANI = 0.3
TOPLU_DEGISIKLIK_EN_AZ = 3

_CUMLE_SONU = re.compile(r"(?<=[.!?…])\s+")


def _iso(zaman: datetime) -> str:
    return zaman.strftime("%Y-%m-%dT%H:%M:%S%z")


def _kisa_hash(metin: str) -> str:
    sade = re.sub(r"\W+", " ", metin.lower()).strip()
    return hashlib.sha1(sade.encode("utf-8")).hexdigest()[:10]


def imza(baslik: str, ozet: str) -> dict:
    cumleler = [c for c in _CUMLE_SONU.split(ozet.strip()) if c]
    return {"b": _kisa_hash(baslik), "c": [_kisa_hash(c) for c in cumleler]}


def degisti_mi(eski: dict, yeni: dict) -> bool:
    if eski.get("b") != yeni["b"]:
        return True
    eski_c, yeni_c = eski.get("c", []), yeni["c"]
    if eski_c[:1] != yeni_c[:1]:
        return True
    return len(set(yeni_c) - set(eski_c)) >= 2


def takibi_yukle(yol: Path, yedek_ilk_gorulme: Path | None = None) -> dict[str, dict]:
    try:
        kayitlar = json.loads(yol.read_text(encoding="utf-8"))
        if isinstance(kayitlar, dict):
            return kayitlar
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    # İlk çalıştırma: eski ilk görülme kaydından (scripts/ilk_gorulme.json)
    # başla ki tarihi tahmini haberler bugünün saatini almasın.
    kayitlar = {}
    if yedek_ilk_gorulme is not None:
        try:
            for url, ilk in json.loads(yedek_ilk_gorulme.read_text(encoding="utf-8")).items():
                kayitlar[url] = {"ilk": ilk, "son": ilk}
        except (FileNotFoundError, json.JSONDecodeError, AttributeError):
            pass
    return kayitlar


def takibi_kaydet(yol: Path, kayitlar: dict[str, dict], simdi: datetime) -> None:
    sinir = simdi - TAKIP_SURESI
    guncel = {
        url: k for url, k in kayitlar.items()
        if (tarihi_ayristir(k.get("son", "")) or simdi) >= sinir
    }
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(guncel, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


class Takip:
    """Bir çalıştırma boyunca kayıtları günceller. Kaynak kaynak kullanılır:
    her haber için gor(), kaynağın haberleri bitince kaynak_bitti()."""

    def __init__(self, kayitlar: dict[str, dict], simdi: datetime):
        self.kayitlar = kayitlar
        self.simdi = simdi
        self._simdi_metni = _iso(simdi)
        # Bu kaynakta içeriği değişen haberler: (url, yeni imza, güncellenebilir mi)
        self._degisenler: list[tuple[str, dict, bool]] = []
        self._kayitli_sayisi = 0
        self.guncellenen: list[str] = []
        self.toplu_degisen_kaynaklar: list[str] = []

    def ilk_gorulme(self, url: str) -> str:
        """Haberin ilk görüldüğü an; ilk kez görülüyorsa şimdi."""
        kayit = self.kayitlar.get(url)
        return kayit["ilk"] if kayit else self._simdi_metni

    def gor(self, url: str, baslik: str, ozet: str, yayin_tarihi: str) -> None:
        yeni = imza(baslik, ozet)
        kayit = self.kayitlar.get(url)
        if kayit is None:
            self.kayitlar[url] = {"ilk": self._simdi_metni, "son": self._simdi_metni, "imza": yeni}
            return
        kayit["son"] = self._simdi_metni
        if "imza" not in kayit:
            # Eski ilk görülme kaydından gelen: içerik ilk kez görülüyor.
            kayit["imza"] = yeni
            return
        self._kayitli_sayisi += 1
        if not degisti_mi(kayit["imza"], yeni):
            return
        # Son güncellemeden (yoksa yayın/ilk görülme anından) beri
        # GUNCELLEME_ARALIGI geçmediyse değişiklik bekler; imza eski
        # kalır ki aralık dolunca hâlâ farklıysa güncelleme sayılsın.
        dayanak = kayit.get("guncellendi") or yayin_tarihi or kayit["ilk"]
        vakti_geldi = self.simdi - sira_anahtari(dayanak) >= GUNCELLEME_ARALIGI
        self._degisenler.append((url, yeni, vakti_geldi))

    def kaynak_bitti(self, kaynak: str) -> None:
        degisenler, kayitli = self._degisenler, self._kayitli_sayisi
        self._degisenler, self._kayitli_sayisi = [], 0
        if not degisenler:
            return
        toplu = (
            len(degisenler) >= TOPLU_DEGISIKLIK_EN_AZ
            and len(degisenler) >= TOPLU_DEGISIKLIK_ORANI * kayitli
        )
        if toplu:
            self.toplu_degisen_kaynaklar.append(kaynak)
            for url, yeni, _ in degisenler:
                self.kayitlar[url]["imza"] = yeni
            return
        for url, yeni, vakti_geldi in degisenler:
            if vakti_geldi:
                self.kayitlar[url]["imza"] = yeni
                self.kayitlar[url]["guncellendi"] = self._simdi_metni
                self.guncellenen.append(url)

    def guncellendi(self, url: str) -> str:
        kayit = self.kayitlar.get(url)
        return kayit.get("guncellendi", "") if kayit else ""
