"""scripts/web/ altındaki sayfa JS/CSS dosyalarının testleri.

Çalıştırma: python -m unittest discover -s tests -v
"""

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sayfa  # noqa: E402
from model import KaynakBolumu  # noqa: E402

JS_KLASORU = sayfa.WEB_KLASORU / "js"


class WebDosyalari(unittest.TestCase):
    def test_her_js_dosyasi_listede(self):
        # Listede olmayan bir dosya sessizce sayfaya girmezdi.
        self.assertEqual(sorted(p.name for p in JS_KLASORU.glob("*.js")), sorted(sayfa.JS_DOSYALARI))

    @unittest.skipUnless(shutil.which("node"), "node yok")
    def test_js_sozdizimi(self):
        for ad in sayfa.JS_DOSYALARI:
            with self.subTest(dosya=ad):
                sonuc = subprocess.run(["node", "--check", str(JS_KLASORU / ad)], capture_output=True, text=True)
                self.assertEqual(sonuc.returncode, 0, sonuc.stderr)

    def test_kategori_verisi_yerlestiriliyor(self):
        html = sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "https://x", [])]})
        self.assertNotIn("__KATEGORI_VERISI__", html)
        self.assertIn('var KATEGORI_VERISI = {"Gündem": [["bbc.co.uk", 0, 0]]};', html)


if __name__ == "__main__":
    unittest.main()
