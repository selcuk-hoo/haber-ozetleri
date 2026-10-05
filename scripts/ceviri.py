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

from markalar import markali_mi, markalari_koruyarak
from model import Ceviriler
from olaylar import ilk_cumleler

GOOGLE_ADRESI = "https://translate.googleapis.com/translate_a/single"
CALISTIRMA_BASINA_CAGRI = 500
CAGRI_ARASI_BEKLEME = 0.15  # sn
# Hata sonrası yeniden denemeden önceki beklemeler (sn). 429 çoğu zaman
# birkaç saniye içinde geçiyor; bütün denemeler çalıştırmaya en fazla
# ~40 sn ekler (çeviri durunca sonraki metinler için hiç denenmez).
YENIDEN_DENEME_BEKLEMELERI = (5, 30)
# Marka adı içeren metinlerin önbellek özetine eklenir; markalar.py'deki
# liste büyüyüp eski çevirilerin yenilenmesi gerekirse artırılır.
MARKA_SURUMU = "marka1:"


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
    "eb"/"eo" (başlık, ilk cümleler). "bk"/"ok": "c" ise çeviri Claude'un,
    "g" ise Gemini'nin."""

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
        self.claude = 0  # bu çalıştırmada Claude'un çevirdiği metin
        self.gemini = 0  # bu çalıştırmada Gemini'nin çevirdiği metin
        self.ceviriler = Ceviriler()

    # İngilizce → Türkçe metinlerin önbellek özeti. Markalı metinlerin özeti
    # farklı: marka koruması gelmeden önceki (adı çevrilmiş olabilen) kayıt
    # bir kez yenilenir (bkz. markalar.py).
    @staticmethod
    def _tr_ozeti(kaynak_metin: str) -> str:
        return _ozetle(MARKA_SURUMU + kaynak_metin) if markali_mi(kaynak_metin) else _ozetle(kaynak_metin)

    # Claude çevirisi (bkz. claude_ceviri.py): önbellekte bu metnin Claude
    # çevirisi yoksa (hiç yoksa ya da Google'ınki varsa) True.
    def claude_gerekli_mi(self, tur: str, url: str, kaynak_metin: str) -> bool:
        kayit = self.onbellek.get(url, {})
        return kayit.get(tur + "h") != self._tr_ozeti(kaynak_metin) or kayit.get(tur + "k") != "c"

    # Gemini ya da Claude metni çevirmeden aynen geri verebiliyor (03.10.2026:
    # Ars Technica'nın bir haberi Türkçe sayfada İngilizce kaldı) ya da yarım
    # bırakabiliyor: Gemini bazen özetin yalnız ilk cümlesini çeviriyor
    # (05.10.2026: Gemini özetlerinin %4,9'u tek cümleydi, Google'ınkilerin
    # %0,2'si; DW'nin mayın haberi kartta "Kuzey Kore DMZ'nin sınırlarını
    # zorluyor mu?" diye kalmıştı). Türkçe metin İngilizceyle aşağı yukarı
    # aynı uzunlukta; yarısından kısası eksik sayılır (kısa metinlerde,
    # başlıklarda oran güvenilir değil, bakılmaz). Böyle bir "çeviri"
    # kaydedilmez; önbellekte olanı da yokmuş sayılır, metin yeniden
    # çevrilir (Gemini yine yapamazsa Google'a kalır).
    EKSIK_ORAN = 0.5
    EKSIK_EN_KISA = 200

    @classmethod
    def _cevrilmemis(cls, kaynak_metin: str, ceviri: str) -> bool:
        kaynak, ceviri = kaynak_metin.strip(), ceviri.strip()
        if ceviri == kaynak:
            return True
        return len(kaynak) >= cls.EKSIK_EN_KISA and len(ceviri) < cls.EKSIK_ORAN * len(kaynak)

    def _bozuk_kayit(self, kayit: dict, tur: str, kaynak_metin: str) -> bool:
        return kayit.get(tur + "k") in ("c", "g") and self._cevrilmemis(kaynak_metin, kayit.get(tur, ""))

    def claude_kaydet(self, tur: str, url: str, kaynak_metin: str, ceviri: str, isaret: str = "c") -> None:
        if self._cevrilmemis(kaynak_metin, ceviri):
            return
        kayit = self.onbellek.setdefault(url, {})
        kayit[tur], kayit[tur + "h"], kayit[tur + "k"] = ceviri, self._tr_ozeti(kaynak_metin), isaret
        if isaret == "g":
            self.gemini += 1
        else:
            self.claude += 1

    # Gemini çevirisi (bkz. gemini_ceviri.py): bu metnin hiç çevirisi yoksa
    # (İngilizcesi değişmişse de) True. Google'la çevrilmiş eski metinler
    # yeniden çevrilmez, kota boşa gitmesin.
    def ceviri_gerekli_mi(self, tur: str, url: str, kaynak_metin: str) -> bool:
        kayit = self.onbellek.get(url, {})
        return kayit.get(tur + "h") != self._tr_ozeti(kaynak_metin) or self._bozuk_kayit(kayit, tur, kaynak_metin)

    def _metin(self, tur: str, url: str, kaynak_metin: str, cevir: Callable[[str], str] | None = None) -> str | None:
        kayit = self.onbellek.setdefault(url, {})
        ozet = _ozetle(kaynak_metin)
        if cevir is None:
            # İngilizce → Türkçe: marka adları korunur (bkz. markalar.py).
            cevir = lambda m: markalari_koruyarak(m, self._cevir)  # noqa: E731
            ozet = self._tr_ozeti(kaynak_metin)
        if kayit.get(tur + "h") == ozet and not self._bozuk_kayit(kayit, tur, kaynak_metin):
            return kayit[tur]
        ceviri = None if self.durdu or self._kalan <= 0 else self._dene(kaynak_metin, cevir)
        if ceviri is None:
            # Kaynak metni biraz değişmiş (ör. özet yeniden çıkarılmış) bir
            # haberin önceki çevirisi İngilizcesinden iyidir.
            if kayit.get(tur) and not self._bozuk_kayit(kayit, tur, kaynak_metin):
                self.eskimis += 1
                return kayit[tur]
            return None
        self._kalan -= 1
        self.yeni += 1
        kayit[tur], kayit[tur + "h"] = ceviri, ozet
        kayit.pop(tur + "k", None)
        if self._bekleme:
            time.sleep(self._bekleme)
        return ceviri

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

    def baslik(self, url: str, ingilizce: str) -> None:
        tr = self._metin("b", url, ingilizce)
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
