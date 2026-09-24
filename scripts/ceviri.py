"""Başlık ve özetlerin sunucu tarafında Türkçeye çevrilmesi (Google Çeviri).

Sayfa eskiden İngilizce üretilip okura translate.goog üzerinden
çevriliyordu; bu, çeviri balonlarına, kurumsal ağlardaki engellere ve
görsel sorunlarına yol açıyordu. Artık metinler üretim sırasında aynı
Google çevirisiyle (tarayıcı eklentilerinin kullandığı ücretsiz "gtx" uç
noktası) Türkçeye çevrilip sayfaya doğrudan Türkçe yazılıyor.

- Her metin bir kez çevrilir: sonuç, İngilizce metnin özetiyle (hash)
  birlikte ceviri.json'da saklanır (arşiv gibi gh-pages'te). Kaynak metin
  değişirse yeniden çevrilir.
- Çalıştırma başına çağrı sınırı var; ilk çalıştırmada kalanlar sonraki
  çalıştırmalarda tamamlanır.
- Uç nokta resmi bir API değil; hata verirse o çalıştırmada çeviri durur,
  çevrilemeyen metinler İngilizce kalır. Kartların çoğu çevrilemediyse
  sayfa eskisi gibi İngilizce üretilir (bkz. sayfa.py TURKCE_ESIGI).
"""

import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

from model import Ceviriler

GOOGLE_ADRESI = "https://translate.googleapis.com/translate_a/single"
CALISTIRMA_BASINA_CAGRI = 500
CAGRI_ARASI_BEKLEME = 0.15  # sn


def google_cevir(metin: str) -> str:
    adres = GOOGLE_ADRESI + "?" + urllib.parse.urlencode(
        {"client": "gtx", "sl": "en", "tl": "tr", "dt": "t", "q": metin}
    )
    istek = urllib.request.Request(adres, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(istek, timeout=20) as yanit:
        veri = json.loads(yanit.read().decode("utf-8"))
    ceviri = "".join(parca[0] for parca in veri[0] if parca and parca[0])
    if not ceviri.strip():
        raise ValueError("boş çeviri")
    return ceviri


def _ozetle(metin: str) -> str:
    return hashlib.sha1(metin.encode("utf-8")).hexdigest()[:12]


def onbellegi_yukle(yol: Path) -> dict[str, dict[str, str]]:
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def onbellegi_kaydet(yol: Path, onbellek: dict[str, dict[str, str]], tutulacak_urller: set[str]) -> None:
    # Sayfada ya da arşivde olmayan haberlerin çevirisi düşer; dosya
    # arşivle birlikte sınırlı kalır.
    guncel = {url: kayit for url, kayit in onbellek.items() if url in tutulacak_urller}
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(guncel, ensure_ascii=False) + "\n", encoding="utf-8")


class Cevirmen:
    """Önbellekli çevirmen. Kayıt biçimi: {url: {"b": başlık, "bh": hash,
    "o": özet, "oh": hash}}."""

    def __init__(
        self,
        onbellek: dict[str, dict[str, str]],
        cevir: Callable[[str], str] = google_cevir,
        cagri_siniri: int = CALISTIRMA_BASINA_CAGRI,
        bekleme: float = CAGRI_ARASI_BEKLEME,
    ):
        self.onbellek = onbellek
        self._cevir = cevir
        self._kalan = cagri_siniri
        self._bekleme = bekleme
        self.durdu = False
        self.yeni = 0
        self.ceviriler = Ceviriler()

    def _metin(self, tur: str, url: str, ingilizce: str) -> str | None:
        kayit = self.onbellek.setdefault(url, {})
        ozet = _ozetle(ingilizce)
        if kayit.get(tur + "h") == ozet:
            return kayit[tur]
        if self.durdu or self._kalan <= 0:
            return None
        ceviri = None
        for deneme in range(2):
            try:
                ceviri = self._cevir(ingilizce)
                break
            except Exception as hata:  # noqa: BLE001 - çeviri alınamazsa metin İngilizce kalır
                if deneme == 0:
                    time.sleep(2 if self._bekleme else 0)
                    continue
                print(f"çeviri durduruldu: {hata!r}", file=sys.stderr)
                self.durdu = True
                return None
        self._kalan -= 1
        self.yeni += 1
        kayit[tur], kayit[tur + "h"] = ceviri, ozet
        if self._bekleme:
            time.sleep(self._bekleme)
        return ceviri

    def baslik(self, url: str, ingilizce: str) -> None:
        tr = self._metin("b", url, ingilizce)
        if tr is not None:
            self.ceviriler.basliklar[url] = tr

    def ozet(self, url: str, ingilizce: str) -> None:
        tr = self._metin("o", url, ingilizce)
        if tr is not None:
            self.ceviriler.ozetler[url] = tr
