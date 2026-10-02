"""scripts/besleme.py testleri (ağa çıkmayanlar).

Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from unittest import mock  # noqa: E402

import besleme  # noqa: E402
from ayarlar import ANASAYFA_KAYNAKLARI, KAYNAKLAR, TURKCE_KAYNAKLAR  # noqa: E402
from besleme import _paylasim_gorseli  # noqa: E402


class PaylasimGorseli(unittest.TestCase):
    def test_og_image(self):
        # Anadolu Ajansı: trafilatura görsel döndürmüyor, og:image okunuyor.
        html = '<meta property="og:image" content="https://web-cdnprod.aa.com.tr/uploads/a.jpg"/>'
        self.assertEqual(_paylasim_gorseli(html, "https://www.aa.com.tr/en/x/1"), "https://web-cdnprod.aa.com.tr/uploads/a.jpg")

    def test_ters_oznitelik_sirasi_ve_goreli_adres(self):
        html = '<meta content="/img/b.jpg?w=1&amp;h=2" name="twitter:image">'
        self.assertEqual(_paylasim_gorseli(html, "https://site.com/a/b"), "https://site.com/img/b.jpg?w=1&h=2")

    def test_og_image_twitter_imagedan_once(self):
        html = '<meta name="twitter:image" content="https://x/t.jpg"><meta property="og:image" content="https://x/o.jpg">'
        self.assertEqual(_paylasim_gorseli(html, "https://x/"), "https://x/o.jpg")

    def test_gorsel_yok(self):
        self.assertEqual(_paylasim_gorseli("<p>metin</p>", "https://x/"), "")


class AnasayfaBaglantilari(unittest.TestCase):
    SAYFA = """
    <a href="https://t24.com.tr/haber/ilk-haber,111111">İlk</a>
    <a href="/haber/ikinci-haber,111112">İkinci</a>
    <a href="/haber/ilk-haber,111111">İlk (tekrar)</a>
    <a href="/yazarlar/biri/kose-yazisi,59281">Köşe</a>
    <a href="/video/bir-video,71810">Video</a>
    <a href="/haber/ucuncu-haber,111113?ref=ana">Üçüncü</a>
    <a href='https://t24.com.tr/haber/dorduncu-haber,111114'>Dördüncü</a>
    """

    def al(self, n):
        with mock.patch.object(besleme.trafilatura, "fetch_url", return_value=self.SAYFA):
            return besleme.anasayfa_baglantilari("https://t24.com.tr/", ANASAYFA_KAYNAKLARI["t24.com.tr"], n)

    def test_haber_baglantilari_sirayla_tekrarsiz(self):
        self.assertEqual(self.al(10), [
            "https://t24.com.tr/haber/ilk-haber,111111",
            "https://t24.com.tr/haber/ikinci-haber,111112",
            "https://t24.com.tr/haber/ucuncu-haber,111113",
            "https://t24.com.tr/haber/dorduncu-haber,111114",
        ])
        self.assertEqual(len(self.al(2)), 2)

    def test_sayfa_alinamazsa_bos(self):
        with mock.patch.object(besleme.trafilatura, "fetch_url", return_value=None):
            self.assertEqual(besleme.anasayfa_baglantilari("https://t24.com.tr/", r"/haber/\S+", 5), [])
        with mock.patch.object(besleme.trafilatura, "fetch_url", side_effect=OSError("ağ")):
            self.assertEqual(besleme.anasayfa_baglantilari("https://t24.com.tr/", r"/haber/\S+", 5), [])

    def test_t24_kayitli_ve_turkce(self):
        self.assertIn(("Gündem", "t24.com.tr", "https://t24.com.tr/"), KAYNAKLAR)
        self.assertIn("t24.com.tr", TURKCE_KAYNAKLAR)


if __name__ == "__main__":
    unittest.main()
