""""Older news" arşivinin (scripts/arsiv.py) ve sayfadaki listesinin testleri.

Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sayfa  # noqa: E402
from arsiv import arsivi_guncelle, arsivi_kaydet, arsivi_yukle, eski_haberler  # noqa: E402
from model import ArsivKaydi, KaynakBolumu, Makale  # noqa: E402

SIMDI = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)


def makale(url: str, tarih: str, baslik: str = "Başlık", kaynak: str = "bbc.co.uk") -> Makale:
    return Makale(kaynak, baslik, url, "Özet.", "", tarih)


def kayit(url: str, tarih: str, kategori: str = "Gündem", kaynak: str = "bbc.co.uk", eklendi: str = "") -> ArsivKaydi:
    return ArsivKaydi(kategori, kaynak, "Eski başlık", url, tarih, False, eklendi or tarih)


class ArsivGuncelleme(unittest.TestCase):
    def test_sayfadakiler_eklenir_eskiler_korunur(self):
        onceki = [kayit("https://x/eski", "2026-09-22T08:00:00+0000")]
        kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", [makale("https://x/yeni", "2026-09-24T10:00:00+0000")])]}
        arsiv = arsivi_guncelle(onceki, kategoriler, SIMDI)
        self.assertEqual([k.url for k in arsiv], ["https://x/yeni", "https://x/eski"])

    def test_yedi_gunden_eskiler_duser(self):
        onceki = [
            kayit("https://x/6gun", "2026-09-18T13:00:00+0000"),
            kayit("https://x/8gun", "2026-09-16T12:00:00+0000"),
        ]
        arsiv = arsivi_guncelle(onceki, {}, SIMDI)
        self.assertEqual([k.url for k in arsiv], ["https://x/6gun"])

    def test_tarihsiz_haberin_suresi_eklenme_anina_gore(self):
        onceki = [
            kayit("https://x/yeni", "", eklendi="2026-09-23T12:00:00+0000"),
            kayit("https://x/eski", "", eklendi="2026-09-10T12:00:00+0000"),
        ]
        arsiv = arsivi_guncelle(onceki, {}, SIMDI)
        self.assertEqual([k.url for k in arsiv], ["https://x/yeni"])

    def test_tekrar_gorulen_haber_guncellenir_eklenme_ani_korunur(self):
        onceki = [kayit("https://x/a", "2026-09-23T08:00:00+0000", eklendi="2026-09-23T08:30:00+0000")]
        kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", [makale("https://x/a", "2026-09-23T08:00:00+0000", "Yeni başlık")])]}
        (k,) = arsivi_guncelle(onceki, kategoriler, SIMDI)
        self.assertEqual((k.baslik, k.eklendi), ("Yeni başlık", "2026-09-23T08:30:00+0000"))

    def test_eski_haberler_sayfadakileri_ve_kaldirilan_kaynaklari_disarida_birakir(self):
        arsiv = [
            kayit("https://x/sayfada", "2026-09-24T10:00:00+0000"),
            kayit("https://x/dustu", "2026-09-23T10:00:00+0000"),
            kayit("https://x/kaldirildi", "2026-09-23T09:00:00+0000", kaynak="eskikaynak.com"),
        ]
        kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", [makale("https://x/sayfada", "2026-09-24T10:00:00+0000")])]}
        self.assertEqual([k.url for k in eski_haberler(arsiv, kategoriler)], ["https://x/dustu"])

    def test_kaydet_yukle_ve_bozuk_dosya(self):
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "arsiv.json"
            kayitlar = [kayit("https://x/a", "2026-09-23T10:00:00+0000")]
            arsivi_kaydet(yol, kayitlar)
            self.assertEqual(arsivi_yukle(yol), kayitlar)
            yol.write_text("bozuk", encoding="utf-8")
            self.assertEqual(arsivi_yukle(yol), [])
            self.assertEqual(arsivi_yukle(Path(klasor) / "yok.json"), [])


class ArsivSayfasi(unittest.TestCase):
    def test_gunlere_ayrilir_ve_sayilar_veride(self):
        kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", [])]}
        eski = [
            kayit("https://x/b", "2026-09-23T21:30:00+0000"),  # TR: 24 Eylül 00:30
            kayit("https://x/a", "2026-09-23T10:00:00+0000"),  # TR: 23 Eylül 13:00
        ]
        html = sayfa.sayfa_olustur(kategoriler, eski)
        self.assertIn('var KATEGORI_VERISI = {"Gündem": [["bbc.co.uk", 0, 2, 0]]};', html)
        self.assertLess(html.index("Thursday, 24 September"), html.index("Wednesday, 23 September"))
        self.assertIn('<a href="https://x/b" target="_blank" rel="noopener">Eski başlık</a>', html)
        self.assertIn("00:30 &middot; bbc.co.uk", html)
        self.assertIn('data-gorunum="eski"', html)


if __name__ == "__main__":
    unittest.main()
