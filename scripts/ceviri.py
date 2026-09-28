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
- Türkçe kaynakların (ayarlar.TURKCE_KAYNAKLAR) metni çevrilmeden sayfaya
  girer. Yalnız başlıkları ve ilk iki cümleleri İngilizceye çevrilir; bu
  metin sayfada görünmez, aynı olayı anlatan İngilizce haberlerle
  gruplamada kullanılır (bkz. olaylar.py).
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
from olaylar import ilk_cumleler

GOOGLE_ADRESI = "https://translate.googleapis.com/translate_a/single"
CALISTIRMA_BASINA_CAGRI = 500
CAGRI_ARASI_BEKLEME = 0.15  # sn
# Hata sonrası yeniden denemeden önceki beklemeler (sn). 429 çoğu zaman
# birkaç saniye içinde geçiyor; bütün denemeler çalıştırmaya en fazla
# ~40 sn ekler (çeviri durunca sonraki metinler için hiç denenmez).
YENIDEN_DENEME_BEKLEMELERI = (5, 30)
BASLIK_SURUMU = 2  # 2: başlık, özetin ilk cümlesiyle birlikte çevriliyor


def google_cevir(metin: str, kaynak: str = "en", hedef: str = "tr") -> str:
    adres = GOOGLE_ADRESI + "?" + urllib.parse.urlencode(
        {"client": "gtx", "sl": kaynak, "tl": hedef, "dt": "t", "q": metin}
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
    "o": özet, "oh": hash}}; Türkçe kaynaklarda "b"/"o" yerine İngilizce
    "eb"/"eo" (başlık, ilk cümleler)."""

    def __init__(
        self,
        onbellek: dict[str, dict[str, str]],
        cevir: Callable[[str], str] = google_cevir,
        cagri_siniri: int = CALISTIRMA_BASINA_CAGRI,
        bekleme: float = CAGRI_ARASI_BEKLEME,
        ingilizceye_cevir: Callable[[str], str] | None = None,
    ):
        self.onbellek = onbellek
        self._cevir = cevir
        self._ingilizceye = ingilizceye_cevir or (lambda metin: google_cevir(metin, "tr", "en"))
        self._kalan = cagri_siniri
        self._bekleme = bekleme
        self.durdu = False
        self.yeni = 0
        self.eskimis = 0  # yenisi alınamadığı için önceki çevirisi kullanılan metin
        self.ceviriler = Ceviriler()

    # Google'a tek çağrı: sınır/durma kontrolü, yeniden deneme ve sayaçlar.
    def _cagir(self, metin: str, cevir: Callable[[str], str]) -> str | None:
        if self.durdu or self._kalan <= 0:
            return None
        ceviri = self._dene(metin, cevir)
        if ceviri is None:
            return None
        self._kalan -= 1
        self.yeni += 1
        if self._bekleme:
            time.sleep(self._bekleme)
        return ceviri

    # Yenisi alınamadıysa önceki çeviri: kaynak metni biraz değişmiş (ör.
    # özet yeniden çıkarılmış) bir haberin önceki çevirisi İngilizcesinden
    # iyidir.
    def _onceki(self, kayit: dict[str, str], tur: str, ozet: str) -> str | None:
        if not kayit.get(tur):
            return None
        if kayit.get(tur + "h") != ozet:
            self.eskimis += 1
        return kayit[tur]

    def _metin(self, tur: str, url: str, kaynak_metin: str, cevir: Callable[[str], str] | None = None) -> str | None:
        kayit = self.onbellek.setdefault(url, {})
        ozet = _ozetle(kaynak_metin)
        if kayit.get(tur + "h") == ozet:
            return kayit[tur]
        ceviri = self._cagir(kaynak_metin, cevir or self._cevir)
        if ceviri is None:
            return self._onceki(kayit, tur, ozet)
        kayit[tur], kayit[tur + "h"] = ceviri, ozet
        return ceviri

    # Başlık tek başına çevrilince bağlamsız kalıyor ("meatfluencer" → "et
    # akıcısı"); özetin ilk cümlesiyle birlikte, ayrı satırlarda gönderilip
    # yalnız ilk satır alınır. Kayıtta "bv" = BASLIK_SURUMU: eski
    # (bağlamsız) çeviriler sayfadaki haberlerde bir kez yenilenir; eski
    # haberler listesinde (bağlam yok) olduğu gibi kullanılır.
    def _baglamli_baslik(self, url: str, ingilizce: str, baglam: str) -> str | None:
        kayit = self.onbellek.setdefault(url, {})
        ozet = _ozetle(ingilizce)
        if kayit.get("bh") == ozet and kayit.get("bv") == BASLIK_SURUMU:
            return kayit["b"]
        ceviri = self._cagir(ingilizce + "\n" + baglam, self._cevir)
        if ceviri is not None:
            satirlar = [s.strip() for s in ceviri.split("\n") if s.strip()]
            # Satırlar ayrılamadıysa (Google birleştirdiyse) bağlamsız çevrilir.
            baslik = satirlar[0] if len(satirlar) >= 2 else self._cagir(ingilizce, self._cevir)
            if baslik:
                kayit["b"], kayit["bh"], kayit["bv"] = baslik, ozet, BASLIK_SURUMU
                return baslik
        return self._onceki(kayit, "b", ozet)

    def _dene(self, metin: str, cevir: Callable[[str], str]) -> str | None:
        for bekleme in (*YENIDEN_DENEME_BEKLEMELERI, None):
            try:
                return cevir(metin)
            except Exception as hata:  # noqa: BLE001 - çeviri alınamazsa metin İngilizce kalır
                if bekleme is None:
                    print(f"çeviri durduruldu: {hata!r}", file=sys.stderr)
                    self.durdu = True
                    return None
                print(f"çeviri hatası ({hata!r}), {bekleme} sn sonra tekrar denenecek", file=sys.stderr)
                time.sleep(bekleme if self._bekleme else 0)
        return None

    def baslik(self, url: str, ingilizce: str, baglam: str | None = None) -> None:
        tr = self._baglamli_baslik(url, ingilizce, baglam) if baglam else self._metin("b", url, ingilizce)
        if tr is not None:
            self.ceviriler.basliklar[url] = tr

    def ozet(self, url: str, ingilizce: str) -> None:
        tr = self._metin("o", url, ingilizce)
        if tr is not None:
            self.ceviriler.ozetler[url] = tr

    # Türkçe kaynaktaki haber: metni olduğu gibi kullanılır; gruplama için
    # başlığı ve özetin ilk iki cümlesi İngilizceye çevrilir (alınamazsa
    # haber yine gösterilir, yalnız gruplanmaz). Eski haberler listesinde
    # (ozet=None) yalnız başlık gerekir.
    def turkce_kaynak(self, url: str, baslik: str, ozet: str | None = None) -> None:
        self.ceviriler.basliklar[url] = baslik
        if ozet is None:
            return
        self.ceviriler.ozetler[url] = ozet
        eb = self._metin("eb", url, baslik, self._ingilizceye)
        eo = self._metin("eo", url, ilk_cumleler(ozet), self._ingilizceye)
        if eb is not None and eo is not None:
            self.ceviriler.ingilizceler[url] = (eb, eo)
