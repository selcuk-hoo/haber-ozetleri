"""scripts/besleme.py testleri (ağa çıkmayanlar).

Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

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


if __name__ == "__main__":
    unittest.main()
