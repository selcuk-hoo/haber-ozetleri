"""Modüller arasında taşınan haber verisi."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Makale:
    kaynak: str  # KAYNAKLAR'daki kaynak adı, ör. "bbc.co.uk"
    baslik: str
    url: str
    ozet: str
    gorsel: str  # boş olabilir
    tarih: str  # ISO 8601 ("%Y-%m-%dT%H:%M:%S%z"); boş olabilir
    # tarih gerçek yayın saati değil, bu haberi ilk gördüğümüz an
    # (bkz. tarih.py, ilk görülme kaydı); sayfada "~" ile işaretlenir.
    tahmini: bool = False


@dataclass
class KaynakBolumu:
    ad: str  # kaynak adı
    adres: str  # besleme/anasayfa adresi
    makaleler: list[Makale] = field(default_factory=list)


# "Older news" listesindeki bir haber (bkz. arsiv.py). Özet ve görsel
# saklanmıyor, sadece başlık ve orijinal adres.
@dataclass(frozen=True)
class ArsivKaydi:
    kategori: str
    kaynak: str
    baslik: str
    url: str
    tarih: str  # Makale.tarih ile aynı biçim
    tahmini: bool
    # Arşive ilk girdiği an (ISO 8601). Tarihi ayrıştırılamayan haberlerin
    # süresi buna göre dolar.
    eklendi: str
