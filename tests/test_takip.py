"""scripts/takip.py testleri: ilk görülme kaydı ve güncelleme algılama.

Çalıştırma: python -m unittest discover -s tests -v
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sayfa  # noqa: E402
from model import Makale  # noqa: E402
from takip import Takip, degisti_mi, imza, takibi_kaydet, takibi_yukle  # noqa: E402
from tarih import sira_zamani  # noqa: E402

T0 = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
URL = "https://www.cnn.com/2026/09/28/politics/trump-iran-deal"
BASLIK = "Trump weighs Iran deal"
OZET = "Talks resumed on Monday. Officials met in Oman. A deal is not expected soon. Markets rose."


def iso(zaman: datetime) -> str:
    return zaman.strftime("%Y-%m-%dT%H:%M:%S%z")


def tur(kayitlar: dict, zaman: datetime, haberler: list[tuple[str, str, str]], yayin: str = "", kaynak: str = "cnn.com") -> Takip:
    """Bir çalıştırmada bir kaynağın haberlerini görür."""
    takip = Takip(kayitlar, zaman)
    for url, baslik, ozet in haberler:
        takip.gor(url, baslik, ozet, yayin)
    takip.kaynak_bitti(kaynak)
    return takip


class IlkGorulme(unittest.TestCase):
    def test_listeden_dusup_geri_gelen_haber_yeni_sayilmaz(self):
        # CNN hatası: haber bir turda listeden düşünce kayıt siliniyor, geri
        # gelince o anın saatini alıp en üste çıkıyordu.
        kayitlar: dict = {}
        takip = tur(kayitlar, T0, [(URL, BASLIK, OZET)])
        self.assertEqual(takip.ilk_gorulme(URL), iso(T0))
        # İkinci tur: haber listede yok; kayıt kaydedilip yeniden okunur.
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "takip.json"
            tur(kayitlar, T0 + timedelta(hours=1), [])
            takibi_kaydet(yol, kayitlar, T0 + timedelta(hours=1))
            kayitlar = takibi_yukle(yol)
        takip = tur(kayitlar, T0 + timedelta(hours=6), [(URL, BASLIK, OZET)])
        self.assertEqual(takip.ilk_gorulme(URL), iso(T0))
        self.assertEqual(takip.guncellendi(URL), "")

    def test_yedi_gun_gorulmeyen_kayit_silinir(self):
        kayitlar: dict = {}
        tur(kayitlar, T0, [(URL, BASLIK, OZET)])
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "takip.json"
            takibi_kaydet(yol, kayitlar, T0 + timedelta(days=6))
            self.assertIn(URL, takibi_yukle(yol))
            takibi_kaydet(yol, kayitlar, T0 + timedelta(days=8))
            self.assertNotIn(URL, takibi_yukle(yol))

    def test_eski_ilk_gorulme_kaydindan_tohumlanir(self):
        with tempfile.TemporaryDirectory() as klasor:
            eski = Path(klasor) / "ilk_gorulme.json"
            eski.write_text(json.dumps({URL: iso(T0)}), encoding="utf-8")
            kayitlar = takibi_yukle(Path(klasor) / "yok.json", eski)
        takip = tur(kayitlar, T0 + timedelta(hours=5), [(URL, BASLIK, OZET)])
        self.assertEqual(takip.ilk_gorulme(URL), iso(T0))
        # İçerik ilk kez görülüyor: güncelleme sayılmaz.
        self.assertEqual(takip.guncellendi(URL), "")


class Guncelleme(unittest.TestCase):
    def test_imza_karsilastirma(self):
        eski = imza(BASLIK, OZET)
        self.assertFalse(degisti_mi(eski, imza(BASLIK, OZET)))
        # Noktalama/büyük harf farkı değişiklik değil.
        self.assertFalse(degisti_mi(eski, imza("TRUMP weighs Iran deal!", OZET)))
        self.assertTrue(degisti_mi(eski, imza("Trump rejects Iran deal", OZET)))
        # İlk cümle değişti ("son durum").
        self.assertTrue(degisti_mi(eski, imza(BASLIK, OZET.replace("Talks resumed on Monday.", "Talks collapsed on Tuesday."))))
        # Sona tek cümle eklendi: yetmez; iki yeni cümle: güncelleme.
        self.assertFalse(degisti_mi(eski, imza(BASLIK, OZET + " Oil fell.")))
        self.assertTrue(degisti_mi(eski, imza(BASLIK, OZET.replace("Markets rose.", "Oil fell. Gold rose."))))

    def test_icerigi_degisen_haber_guncellenir(self):
        kayitlar: dict = {}
        tur(kayitlar, T0, [(URL, BASLIK, OZET)])
        yeni_ozet = "Talks collapsed on Tuesday. " + OZET
        takip = tur(kayitlar, T0 + timedelta(hours=4), [(URL, BASLIK, yeni_ozet)])
        self.assertEqual(takip.guncellendi(URL), iso(T0 + timedelta(hours=4)))
        self.assertEqual(takip.guncellenen, [URL])
        self.assertEqual(takip.ilk_gorulme(URL), iso(T0))

    def test_uc_saat_dolmadan_guncellenmez_sonra_guncellenir(self):
        kayitlar: dict = {}
        tur(kayitlar, T0, [(URL, BASLIK, OZET)])
        yeni_ozet = "Talks collapsed on Tuesday. " + OZET
        takip = tur(kayitlar, T0 + timedelta(hours=1), [(URL, BASLIK, yeni_ozet)])
        self.assertEqual(takip.guncellendi(URL), "")
        # Aralık dolunca bekleyen değişiklik güncelleme sayılır.
        takip = tur(kayitlar, T0 + timedelta(hours=3), [(URL, BASLIK, yeni_ozet)])
        self.assertEqual(takip.guncellendi(URL), iso(T0 + timedelta(hours=3)))
        # Hemen ardından yine değişirse 3 saat bekler (canlı yayın sayfası).
        takip = tur(kayitlar, T0 + timedelta(hours=4), [(URL, "Trump rejects Iran deal", yeni_ozet)])
        self.assertEqual(takip.guncellendi(URL), iso(T0 + timedelta(hours=3)))

    def test_yayin_tarihinden_uc_saat_gecmeden_guncellenmez(self):
        # Beslemesinde tarih olan kaynak: yeni yayımlanmış haberin ilk
        # saatlerdeki düzeltmeleri güncelleme sayılmaz.
        kayitlar: dict = {}
        yayin = iso(T0 - timedelta(hours=1))
        tur(kayitlar, T0, [(URL, BASLIK, OZET)], yayin)
        takip = tur(kayitlar, T0 + timedelta(hours=1), [(URL, "Trump rejects Iran deal", OZET)], yayin)
        self.assertEqual(takip.guncellendi(URL), "")
        takip = tur(kayitlar, T0 + timedelta(hours=2), [(URL, "Trump rejects Iran deal", OZET)], yayin)
        self.assertEqual(takip.guncellendi(URL), iso(T0 + timedelta(hours=2)))

    def test_kaynagin_cogu_birden_degisirse_guncelleme_sayilmaz(self):
        # Bizim taraftaki değişiklik (yeni temizlik kuralı, özet uzunluğu)
        # bütün haberleri öne almasın.
        kayitlar: dict = {}
        haberler = [(f"https://x.com/{i}", f"Headline {i}", f"First {i}. Second {i}. Third {i}.") for i in range(6)]
        tur(kayitlar, T0, haberler, kaynak="x.com")
        degismis = [(u, b, "Intro line. " + o) for u, b, o in haberler[:4]] + haberler[4:]
        takip = tur(kayitlar, T0 + timedelta(hours=5), degismis, kaynak="x.com")
        self.assertEqual(takip.guncellenen, [])
        self.assertEqual(takip.toplu_degisen_kaynaklar, ["x.com"])
        # İmzalar yenilendi: sonraki turda aynı metin değişiklik sayılmaz.
        takip = tur(kayitlar, T0 + timedelta(hours=10), degismis, kaynak="x.com")
        self.assertEqual(takip.guncellenen, [])
        self.assertEqual(takip.toplu_degisen_kaynaklar, [])

    def test_kaynakta_tek_haber_degisirse_guncellenir(self):
        kayitlar: dict = {}
        haberler = [(f"https://x.com/{i}", f"Headline {i}", f"First {i}. Second {i}. Third {i}.") for i in range(6)]
        tur(kayitlar, T0, haberler, kaynak="x.com")
        degismis = [(haberler[0][0], "Headline 0 updated", haberler[0][2])] + haberler[1:]
        takip = tur(kayitlar, T0 + timedelta(hours=5), degismis, kaynak="x.com")
        self.assertEqual(takip.guncellenen, ["https://x.com/0"])


class SiraVeGosterim(unittest.TestCase):
    def makale(self, tarih: str, guncellendi: str = "") -> Makale:
        return Makale("bbc.co.uk", "Başlık", "https://x/1", "Özet.", "", tarih, False, guncellendi)

    def test_sira_guncellenme_anina_gore(self):
        eski_ama_guncel = self.makale(iso(T0 - timedelta(hours=10)), iso(T0))
        yeni = self.makale(iso(T0 - timedelta(hours=1)))
        self.assertGreater(sira_zamani(eski_ama_guncel), sira_zamani(yeni))
        self.assertEqual(sira_zamani(yeni), T0 - timedelta(hours=1))

    def test_kartta_yeni_isareti_icin_zaman(self):
        # "yeni" işareti (yeni.js) sıralama anına bakar: güncellenme anı.
        from model import Ceviriler
        m = self.makale(iso(T0 - timedelta(hours=10)), iso(T0))
        self.assertIn(f'data-zaman="{int(T0.timestamp())}"', sayfa._kart_html("Gündem", m, Ceviriler(), True))
        tarihsiz = self.makale("")
        self.assertNotIn("data-zaman", sayfa._kart_html("Gündem", tarihsiz, Ceviriler(), True))

    def test_tarih_satirinda_guncellendi_notu(self):
        # 28 Eylül 09:00 UTC = 12:00 TR; güncelleme 14:30 UTC = 17:30 TR.
        m = self.makale(iso(T0 - timedelta(hours=3)), iso(T0 + timedelta(hours=2, minutes=30)))
        self.assertEqual(sayfa._guncelleme_notu(m, True), " · güncellendi 17:30")
        self.assertEqual(sayfa._guncelleme_notu(m, False), " · updated 17:30")
        ertesi_gun = self.makale(iso(T0 - timedelta(hours=3)), iso(T0 + timedelta(days=1)))
        self.assertEqual(sayfa._guncelleme_notu(ertesi_gun, True), " · güncellendi 29 Eylül 15:00")
        # Güncelleme yok ya da yayın tarihi daha yeni: not yok.
        self.assertEqual(sayfa._guncelleme_notu(self.makale(iso(T0)), True), "")
        self.assertEqual(sayfa._guncelleme_notu(self.makale(iso(T0), iso(T0 - timedelta(hours=1))), True), "")


class TarihBicimi(unittest.TestCase):
    def test_gun_ve_ay_adi_yazilir(self):
        from tarih import tarihi_bicimlendir
        # 02.10 yerine "2 Ekim"; saat varsa Türkiye saatiyle (UTC+3).
        self.assertEqual(tarihi_bicimlendir("2026-10-02T09:15:00+0000"), "2 Ekim · 12:15")
        self.assertEqual(tarihi_bicimlendir("2026-09-28T22:30:00+0000"), "29 Eylül · 01:30")
        # Saat dilimsiz (yalnız tarih) kaynaklarda saat gösterilmez.
        self.assertEqual(tarihi_bicimlendir("2026-12-05"), "5 Aralık")
        self.assertEqual(tarihi_bicimlendir("tarih değil"), "tarih değil")


if __name__ == "__main__":
    unittest.main()
