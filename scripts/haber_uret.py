#!/usr/bin/env python3
"""Haber kaynaklarından özet sayfasını (dist/index.html) üretir.

GitHub Actions'ta çalışıp statik bir HTML üretir. Sayfa lang="en"
işaretlenir; Türkçe okuyucular translate.goog çevirisine yönlendirilir.

Modüller:
  ayarlar.py  kaynaklar, haber sayıları, eşikler (elle değiştirilen her şey)
  besleme.py  kaynaklardan haber adreslerini ve makale metinlerini çekme
  ozet.py     özet üretimi ve kaynağa özgü temizlik kuralları
  tarih.py    tarih ayrıştırma/biçimlendirme, ilk görülme kaydı
  sayfa.py    HTML sayfası, robots.txt, sitemap.xml (CSS/JS: web/)
  model.py    modüller arasında taşınan Makale / KaynakBolumu

Gereksinim: trafilatura, feedparser
"""

from datetime import datetime, timezone

from courlan import normalize_url

from ayarlar import CIKTI, ESKI_HABER_ESIGI, K, KATEGORI_SAYISI, KAYNAK_SAYISI, KAYNAKLAR, N
from besleme import ATLANAN_ADRES, besleme_listesi, besleme_ogeleri, makale_getir
from model import KaynakBolumu, Makale
from ozet import ozet_olustur
from sayfa import sayfa_olustur, yan_dosyalari_yaz
from tarih import guvenilir_tarih, ilk_gorulmeleri_kaydet, ilk_gorulmeleri_yukle, tarihi_ayristir


# Haberin tarihini ve bunun tahmini olup olmadığını döner. Sayfa ya da
# besleme güvenilir bir tarih vermiyorsa (CNN, Al Jazeera gibi gerçek
# RSS'i olmayan kaynaklarda görülüyor) haberi ilk gördüğümüz an
# kullanılır: daha önce görmüşsek kayıttaki an, ilk kezse şimdi (kayda
# da yazılır). Bu gerçek yayın saati değil; sayfada "~" ile gösterilir.
def _tarih_bul(sayfa_tarihi: str, besleme_tarihi: str, url: str, ilk_gorulme: dict[str, str]) -> tuple[str, bool]:
    tarih = guvenilir_tarih(sayfa_tarihi, besleme_tarihi)
    if tarih:
        return tarih, False
    onceki = ilk_gorulme.get(url)
    if not onceki:
        onceki = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
        ilk_gorulme[url] = onceki
    return onceki, True


def _cok_eski_mi(tarih: str) -> bool:
    zaman = tarihi_ayristir(tarih)
    if zaman is None or zaman.tzinfo is None:
        return False
    return datetime.now(timezone.utc) - zaman > ESKI_HABER_ESIGI


# Bir kaynağın en yeni haberlerini çekip özetler. ilk_gorulme ve
# gorulen_urller tüm kaynaklar arasında paylaşılıyor; burada güncellenir.
def kaynak_haberleri(
    kategori: str, ad: str, adres: str, ilk_gorulme: dict[str, str], gorulen_urller: set[str]
) -> list[Makale]:
    sayi = KAYNAK_SAYISI.get(ad, KATEGORI_SAYISI.get(kategori, N))
    # Video sayfaları atlanıp eski haberler elendiğinde yerleri
    # sonrakilerle dolsun diye iki katı aday alınıyor; hedef sayıya
    # ulaşınca durulduğu için fazladan sayfa ancak gerekirse çekiliyor.
    aday_sayisi = sayi * 2
    urls, besleme_tarihleri = besleme_ogeleri(adres, aday_sayisi)
    if not urls:
        # Gerçek bir besleme yok (anasayfa/site haritası kaynağı, ör. CNN,
        # Al Jazeera) — site haritası yoluna düş; tarih bilgisi olmaz.
        urls = besleme_listesi(adres, aday_sayisi)

    makaleler: list[Makale] = []
    for url in urls:
        if len(makaleler) >= sayi:
            break
        if ATLANAN_ADRES.search(url):
            continue
        sonuc = makale_getir(url)
        if sonuc is None:
            continue
        ozet = ozet_olustur(sonuc["govde"], sonuc["baslik"], K, ad)
        if not ozet:
            continue
        try:
            normal_url = normalize_url(url)
        except Exception:  # noqa: BLE001
            normal_url = url
        gorulen_urller.add(normal_url)

        tarih, tahmini = _tarih_bul(sonuc["tarih"], besleme_tarihleri.get(normal_url, ""), normal_url, ilk_gorulme)
        if _cok_eski_mi(tarih):
            continue
        makaleler.append(Makale(ad, sonuc["baslik"], url, ozet, sonuc["gorsel"], tarih, tahmini))
    return makaleler


def uret() -> None:
    ilk_gorulme = ilk_gorulmeleri_yukle()
    gorulen_urller: set[str] = set()
    kategoriler: dict[str, list[KaynakBolumu]] = {}

    for kategori, ad, adres in KAYNAKLAR:
        makaleler = kaynak_haberleri(kategori, ad, adres, ilk_gorulme, gorulen_urller)
        kategoriler.setdefault(kategori, []).append(KaynakBolumu(ad, adres, makaleler))
        print(f"{kategori} / {ad}: {len(makaleler)} haber")

    ilk_gorulmeleri_kaydet(ilk_gorulme, gorulen_urller)

    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(sayfa_olustur(kategoriler), encoding="utf-8")
    yan_dosyalari_yaz(CIKTI.parent)

    toplam = sum(len(b.makaleler) for bolumler in kategoriler.values() for b in bolumler)
    print(f"Bitti: {CIKTI} ({toplam} haber)")


if __name__ == "__main__":
    uret()
