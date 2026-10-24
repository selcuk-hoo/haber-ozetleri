"""Çok kaynaklı olayların haberlerini sayfada tutma (scripts/tutulan.py) testleri.

Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import haber_uret  # noqa: E402
import tutulan  # noqa: E402
from ayarlar import KAYNAK_SAYISI  # noqa: E402
from model import Makale  # noqa: E402
from takip import Takip  # noqa: E402

SIMDI = datetime(2026, 10, 22, 19, 0, tzinfo=timezone.utc)


def makale(url, kaynak):
    return Makale(kaynak, "Başlık", url, "Özet.", "", "")


class Kayit(unittest.TestCase):
    def test_cok_kaynakli_olay_kaydedilir_tek_kaynakli_kaydedilmez(self):
        olaylar = [("Gündem", [makale("https://a/1", "bbc.co.uk"), makale("https://b/1", "dw.com")]),
                   ("Gündem", [makale("https://a/2", "bbc.co.uk"), makale("https://a/3", "bbc.co.uk")])]
        kayit = tutulan.guncelle({}, olaylar, SIMDI)
        self.assertEqual(set(kayit), {"https://a/1", "https://b/1"})
        self.assertEqual(tutulan.kaynak_icin(kayit, "Gündem", "bbc.co.uk", SIMDI), ["https://a/1"])
        self.assertEqual(tutulan.kaynak_icin(kayit, "Bilim", "bbc.co.uk", SIMDI), [])

    def test_ilk_an_korunur_12_saatte_duser(self):
        olay = [("Gündem", [makale("https://a/1", "bbc.co.uk"), makale("https://b/1", "dw.com")])]
        kayit = tutulan.guncelle({}, olay, SIMDI)
        # Olaya sonradan katılan haber olayın ilk anını alır.
        sonra = SIMDI + timedelta(hours=5)
        olay2 = [("Gündem", olay[0][1] + [makale("https://c/1", "cnn.com")])]
        kayit = tutulan.guncelle(kayit, olay2, sonra)
        self.assertEqual(kayit["https://c/1"]["ilk"], SIMDI.isoformat())
        self.assertEqual(len(tutulan.kaynak_icin(kayit, "Gündem", "cnn.com", SIMDI + timedelta(hours=11))), 1)
        self.assertEqual(tutulan.kaynak_icin(kayit, "Gündem", "cnn.com", SIMDI + timedelta(hours=13)), [])
        self.assertEqual(tutulan.guncelle(kayit, [], SIMDI + timedelta(hours=13)), {})

    def test_dosya(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "tutulan.json"
            self.assertEqual(tutulan.yukle(yol), {})
            tutulan.kaydet(yol, {"https://a/1": {"kategori": "Gündem", "kaynak": "x", "ilk": "t"}})
            self.assertEqual(tutulan.yukle(yol)["https://a/1"]["kaynak"], "x")


class KaynakHaberleri(unittest.TestCase):
    def test_tutulan_haber_sira_dolsa_da_eklenir(self):
        urls = [f"https://www.aljazeera.com/news/2026/10/22/{i}" for i in range(20)]
        konular = ["Beijing trade", "Tokyo floods", "Manila election", "Seoul defectors", "Jakarta budget",
                   "Hanoi exports", "Delhi smog", "Taipei chips", "Bangkok protests", "Dhaka garments",
                   "Kathmandu quake", "Colombo debt", "Kabul aid", "Yangon junta", "Ulaanbaatar mining",
                   "Phnom Penh casinos", "Vientiane dams", "Karachi port", "Busan shipyard", "Osaka expo"]
        eski = "https://www.aljazeera.com/news/2026/10/22/eski-olay"
        sayfa_ = {"baslik": "", "govde": "First. Second.", "gorsel": "", "tarih": "", "etiketler": []}

        def getir(url):
            konu = "Shamonda virus found in humans" if url == eski else konular[int(url.rsplit("/", 1)[1])]
            return dict(sayfa_, baslik=f"{konu} dominate regional headlines")
        sayi = KAYNAK_SAYISI[("Gündem", "aljazeera.com")]
        # Adres tarihleri gerçek saate göre "çok eski" olmasın (bkz. test_arsiv).
        with mock.patch.object(haber_uret, "besleme_ogeleri", return_value=(urls, {})), \
             mock.patch.object(haber_uret, "makale_getir", side_effect=getir), \
             mock.patch.object(haber_uret, "_cok_eski_mi", return_value=False):
            makaleler = haber_uret.kaynak_haberleri("Gündem", "aljazeera.com", "https://x", Takip({}, SIMDI),
                                                    tutulan=[eski, urls[2]])
        adresler = [m.url for m in makaleler]
        # İlk N haber (tutulan urls[2] zaten aralarında) + sırası geçmiş tutulan haber.
        self.assertEqual(adresler, urls[:sayi] + [eski])


if __name__ == "__main__":
    unittest.main()
