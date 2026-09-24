"""scripts/web/ altındaki sayfa JS/CSS dosyalarının testleri.

Çalıştırma: python -m unittest discover -s tests -v
"""

import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sayfa  # noqa: E402
from ayarlar import KAYNAKLAR  # noqa: E402
from model import KaynakBolumu, Makale  # noqa: E402

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
        self.assertIn('var KATEGORI_VERISI = {"Gündem": [["bbc.co.uk", 0, 0, 0]]};', html)

    def test_butonlarda_metin_yok(self):
        # Google Çeviri metnin üzerine gelince "orijinal metin" balonu
        # açıyor; üst bölümdeki ve kartlardaki butonların etiketi
        # data-etiket'ten CSS ile çiziliyor, içlerinde metin olmamalı.
        makale = Makale("bbc.co.uk", "Başlık", "https://x/1", "Özet.", "https://x/g.jpg", "2026-09-24T10:00:00+0000")
        html = sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "https://x", [makale])]})
        butonlar = re.findall(r"<button\b[^>]*>(.*?)</button>", html, re.S)
        self.assertGreater(len(butonlar), 10)
        for icerik in butonlar:
            self.assertEqual(re.sub(r"<span\b[^>]*></span>", "", icerik).strip(), "")
        self.assertRegex(html, r'<a id="cevir-linki"[^>]*></a>')
        self.assertIn('<summary data-etiket="Devamını oku"></summary>', html)
        # Üst bilgi satırı ve alt satırda metin yok.
        ust = re.search(r'<p class="meta">(.*?)</p>', html, re.S).group(1)
        self.assertEqual(re.sub(r"<[^>]*>", "", ust).strip(), "")
        self.assertRegex(html, r'<footer data-etiket="Otomatik oluşturuldu · [^"]+"></footer>')
        # Site adı ve alt başlık; İngilizce yedek sayfada da çevrilmesin.
        self.assertIn("<title>Dünyadan Notlar — Dünya basınından kısa kısa</title>", html)
        self.assertIn('<h1 translate="no">&#128240; Dünyadan Notlar</h1>', html)
        # Tarih · saat · kaynak satırı da metin değil.
        self.assertRegex(html, r'<p class="tarih" data-etiket="[0-9.]+ · [0-9:]+ · bbc.co.uk"></p>')
        self.assertRegex(html, r'<a class="src src-bbc-co-uk"[^>]*aria-label="bbc.co.uk"></a>')
        # Her kaynağın link maskesi sayfada tanımlı.
        for _, ad, _ in KAYNAKLAR:
            self.assertIn("." + sayfa.kaynak_sinifi(ad) + "{", html)


if __name__ == "__main__":
    unittest.main()
