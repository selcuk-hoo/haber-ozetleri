"""Tarih ayrıştırma/biçimlendirme ve haber sırası."""

from datetime import datetime, timezone
from pathlib import Path

from ayarlar import TR_SAATI

# Eski ilk görülme kaydı (yerini takip.py'nin gh-pages'teki takip.json'u
# aldı). Yalnız takip.json henüz yokken bir kez tohum olarak okunur;
# ilk yayından sonra dosya ve bu sabit silinebilir.
ILK_GORULME_DOSYASI = Path(__file__).resolve().parent / "ilk_gorulme.json"


# Saat dilimi bilgisi varsa (article:published_time gibi etiketlerden
# geldiyse) Türkiye saatine çevirip saatiyle gösterir; kaynakta sadece
# tarih varsa (saat bilgisi yoksa) yalnızca tarihi gösterir.
# trafilatura/htmldate saat dilimi bulamadığında saati "T00:00:00" olarak
# dolduruyor (offsetsiz) — bu, saati bilinmiyor demek, gece yarısı demek
# değil. Üç biçim de denenir; saat dilimi olmayanlarda saat gösterilmez.
_TARIH_BICIMLERI = ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")


def tarihi_ayristir(ham: str) -> datetime | None:
    for bicim in _TARIH_BICIMLERI:
        try:
            return datetime.strptime(ham, bicim)
        except ValueError:
            continue
    return None


def tarihi_bicimlendir(ham: str) -> str:
    zaman = tarihi_ayristir(ham)
    if zaman is None:
        return ham
    if zaman.tzinfo is not None:
        yerel = zaman.astimezone(TR_SAATI)
        return yerel.strftime("%d.%m · %H:%M")
    return zaman.strftime("%d.%m")


# Sıralama için: ayrıştırılabilen tarihler karşılaştırılabilir olsun diye
# UTC'ye sabitlenir; ayrıştırılamayan/boş tarihler en eskiymiş gibi
# davranıp listenin sonuna düşer.
def sira_anahtari(tarih: str) -> datetime:
    zaman = tarihi_ayristir(tarih)
    if zaman is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return zaman if zaman.tzinfo else zaman.replace(tzinfo=timezone.utc)


# Haberin sayfadaki sırası: yayın tarihi ile içerik güncellenme anının
# (bkz. takip.py) geç olanı.
def sira_zamani(m) -> datetime:
    return max(sira_anahtari(m.tarih), sira_anahtari(getattr(m, "guncellendi", "")))


# Sayfa tarihi ile besleme tarihinden GÜVENİLİR olanı seçer; ikisi de
# güvenilir değilse boş döner (çağıran taraf bu durumda ilk görülme
# zamanına düşer, bkz. uret()). Sayfa tarihi boş DEĞİLSE bile saat dilimi
# taşımıyor olabilir — htmldate, sayfada bulduğu ama saati belirsiz bir
# tarihi "T00:00:00" ile dolduruyor (bkz. _TARIH_BICIMLERI üstündeki not).
# Bu saatsiz/yer tutucu değer CNN, Al Jazeera gibi anasayfa kaynaklarında
# sıkça çıkıyor ve bir haberin gerçekte ne zaman yayınlandığına dair
# güvenilir bir sinyal değil (bazen sayfadaki alakasız bir tarih, bazen
# eski bir "son güncelleme" olabiliyor). Bu yüzden sadece saat dilimli
# (gerçekten ayrıştırılmış) tarihler "güvenilir" sayılır: sayfa tarihi
# saat dilimliyse ona güvenilir; değilse besleme'nin (her zaman saat
# dilimli üretilen) tarihi kullanılır; o da yoksa boş dönülür.
def guvenilir_tarih(sayfa_tarihi: str, besleme_tarihi: str) -> str:
    sayfa_zaman = tarihi_ayristir(sayfa_tarihi) if sayfa_tarihi else None
    if sayfa_zaman is not None and sayfa_zaman.tzinfo is not None:
        return sayfa_tarihi
    return besleme_tarihi
