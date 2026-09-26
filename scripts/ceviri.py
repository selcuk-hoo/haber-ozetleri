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
- Uç nokta resmi bir API değil; ara sıra "429 Too Many Requests" veriyor.
  Hata alınınca artan aralıklarla birkaç kez denenir, yine olmazsa o
  çalıştırmada çeviri durur. Metni değişmiş bir haberin önceki çevirisi
  varsa o kullanılır; hiç çevirisi olmayan yeni haberler o yayında
  sayfaya konmaz, bir sonraki çalıştırmada çevrilip gelir (bkz. sayfa.py).
  Kartların çoğu çevrilemediyse (uzun süreli engel) sayfa eskisi gibi
  İngilizce üretilir (bkz. sayfa.py TURKCE_ESIGI).
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
# Hata sonrası yeniden denemeden önceki beklemeler (sn). 429 çoğu zaman
# birkaç saniye içinde geçiyor; bütün denemeler çalıştırmaya en fazla
# ~40 sn ekler (çeviri durunca sonraki metinler için hiç denenmez).
YENIDEN_DENEME_BEKLEMELERI = (5, 30)


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
        self.eskimis = 0  # yenisi alınamadığı için önceki çevirisi kullanılan metin
        self.ceviriler = Ceviriler()

    def _metin(self, tur: str, url: str, ingilizce: str) -> str | None:
        kayit = self.onbellek.setdefault(url, {})
        ozet = _ozetle(ingilizce)
        if kayit.get(tur + "h") == ozet:
            return kayit[tur]
        ceviri = None if self.durdu or self._kalan <= 0 else self._dene(ingilizce)
        if ceviri is None:
            # Kaynak metni biraz değişmiş (ör. özet yeniden çıkarılmış) bir
            # haberin önceki çevirisi İngilizcesinden iyidir.
            if kayit.get(tur):
                self.eskimis += 1
                return kayit[tur]
            return None
        self._kalan -= 1
        self.yeni += 1
        kayit[tur], kayit[tur + "h"] = ceviri, ozet
        if self._bekleme:
            time.sleep(self._bekleme)
        return ceviri

    def _dene(self, ingilizce: str) -> str | None:
        for bekleme in (*YENIDEN_DENEME_BEKLEMELERI, None):
            try:
                return self._cevir(ingilizce)
            except Exception as hata:  # noqa: BLE001 - çeviri alınamazsa metin İngilizce kalır
                if bekleme is None:
                    print(f"çeviri durduruldu: {hata!r}", file=sys.stderr)
                    self.durdu = True
                    return None
                print(f"çeviri hatası ({hata!r}), {bekleme} sn sonra tekrar denenecek", file=sys.stderr)
                time.sleep(bekleme if self._bekleme else 0)
        return None

    def baslik(self, url: str, ingilizce: str) -> None:
        tr = self._metin("b", url, ingilizce)
        if tr is not None:
            self.ceviriler.basliklar[url] = tr

    def ozet(self, url: str, ingilizce: str) -> None:
        tr = self._metin("o", url, ingilizce)
        if tr is not None:
            self.ceviriler.ozetler[url] = tr
