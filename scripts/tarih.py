"""Tarih ayrıştırma/biçimlendirme ve "ilk görülme" kaydı."""

import json
from datetime import datetime, timezone
from pathlib import Path

from ayarlar import TR_SAATI

# CNN, Al Jazeera gibi gerçek bir RSS beslemesi olmayan (anasayfadan
# otomatik keşifle veya site haritasından çekilen) kaynaklarda ne sayfada
# ne beslemede tarih bulunabiliyor. Bu dosya, öyle bir makaleyi ilk kez
# gördüğümüz anı url'e göre kalıcı olarak saklar; sonraki çalıştırmalarda
# gerçek tarih hâlâ yoksa bu "ilk görülme" zamanı yedek olarak kullanılır
# (bkz. uret()). Sadece main'de commit'lenir (workflow'a bakın) — gerçek
# yayın saati DEĞİL, sırf sıralama ve "en azından bir saat göster" için.
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


def ilk_gorulmeleri_yukle() -> dict[str, str]:
    try:
        return json.loads(ILK_GORULME_DOSYASI.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# Sadece bu çalıştırmada gerçekten karşılaşılan url'ler (gorulen_urller)
# saklanır; bir makale artık hiçbir kaynağın ilk N haberi arasında değilse
# (sitede de görünmüyor) kaydı burada da düşer. Bu, dosyanın kaynak sayısı
# × N ile sınırlı kalmasını sağlar, sınırsız büyümez.
def ilk_gorulmeleri_kaydet(harita: dict[str, str], gorulen_urller: set[str]) -> None:
    guncel = {url: tarih for url, tarih in harita.items() if url in gorulen_urller}
    ILK_GORULME_DOSYASI.write_text(
        json.dumps(guncel, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
