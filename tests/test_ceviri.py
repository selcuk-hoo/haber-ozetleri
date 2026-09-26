"""Sunucu tarafı çeviri (scripts/ceviri.py) ve Türkçe sayfa üretimi testleri.

Google'a gidilmiyor; çevirmen yerine sahte bir fonksiyon veriliyor.
Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sayfa  # noqa: E402
from ceviri import Cevirmen, onbellegi_kaydet, onbellegi_yukle  # noqa: E402
from model import ArsivKaydi, Ceviriler, KaynakBolumu, Makale  # noqa: E402


class SahteCevirmen:
    def __init__(self, hata_sonrasi=None):
        self.cagrilar = []
        self.hata_sonrasi = hata_sonrasi

    def __call__(self, metin):
        if self.hata_sonrasi is not None and len(self.cagrilar) >= self.hata_sonrasi:
            raise OSError("429 Too Many Requests")
        self.cagrilar.append(metin)
        return "TR " + metin


def cevirmen(onbellek=None, sahte=None, sinir=100):
    return Cevirmen(onbellek if onbellek is not None else {}, sahte or SahteCevirmen(), sinir, bekleme=0)


class Onbellek(unittest.TestCase):
    def test_cevirir_ve_onbellekten_okur(self):
        sahte = SahteCevirmen()
        c = cevirmen(sahte=sahte)
        c.baslik("u1", "Title")
        c.ozet("u1", "Summary.")
        self.assertEqual((c.ceviriler.baslik("u1", "Title"), c.ceviriler.ozet("u1", "Summary.")), ("TR Title", "TR Summary."))
        self.assertTrue(c.ceviriler.cevrildi_mi("u1"))

        ikinci_sahte = SahteCevirmen()
        c2 = cevirmen(c.onbellek, ikinci_sahte)
        c2.baslik("u1", "Title")
        c2.ozet("u1", "Summary.")
        self.assertEqual(ikinci_sahte.cagrilar, [])  # önbellekten geldi
        self.assertEqual(c2.yeni, 0)
        self.assertTrue(c2.ceviriler.cevrildi_mi("u1"))

    def test_ingilizce_metin_degisince_yeniden_cevrilir(self):
        c = cevirmen()
        c.ozet("u1", "Old summary.")
        sahte = SahteCevirmen()
        c2 = cevirmen(c.onbellek, sahte)
        c2.ozet("u1", "Updated summary.")
        self.assertEqual(sahte.cagrilar, ["Updated summary."])
        self.assertEqual(c2.ceviriler.ozet("u1", ""), "TR Updated summary.")

    def test_yenisi_alinamazsa_onceki_ceviri_kullanilir(self):
        c = cevirmen()
        c.ozet("u1", "Old summary.")
        c2 = cevirmen(c.onbellek, SahteCevirmen(hata_sonrasi=0))
        c2.ozet("u1", "Updated summary.")
        c2.baslik("u2", "Brand new")
        self.assertEqual(c2.ceviriler.ozet("u1", ""), "TR Old summary.")
        self.assertEqual(c2.eskimis, 1)
        self.assertNotIn("u2", c2.ceviriler.basliklar)
        # Önbellekteki kayıt değişmedi: sonraki çalıştırma yeniden dener
        sahte = SahteCevirmen()
        cevirmen(c2.onbellek, sahte).ozet("u1", "Updated summary.")
        self.assertEqual(sahte.cagrilar, ["Updated summary."])

    def test_gecici_hatadan_sonra_tekrar_dener(self):
        class IkiKezHata(SahteCevirmen):
            def __init__(self):
                super().__init__()
                self.hata = 2

            def __call__(self, metin):
                if self.hata:
                    self.hata -= 1
                    raise OSError("429 Too Many Requests")
                return super().__call__(metin)

        c = cevirmen(sahte=IkiKezHata())
        c.baslik("u1", "Title")
        self.assertFalse(c.durdu)
        self.assertEqual(c.ceviriler.baslik("u1", ""), "TR Title")

    def test_cagri_siniri(self):
        c = cevirmen(sinir=3)
        for i in range(5):
            c.baslik(f"u{i}", f"Title {i}")
        self.assertEqual(len(c.ceviriler.basliklar), 3)
        self.assertEqual(c.ceviriler.baslik("u4", "Title 4"), "Title 4")  # İngilizce kaldı

    def test_hata_olunca_durur(self):
        sahte = SahteCevirmen(hata_sonrasi=2)
        c = cevirmen(sahte=sahte)
        for i in range(5):
            c.baslik(f"u{i}", f"Title {i}")
        self.assertTrue(c.durdu)
        self.assertEqual(len(c.ceviriler.basliklar), 2)
        self.assertEqual(len(sahte.cagrilar), 2)  # durduktan sonra Google'a gidilmedi

    def test_kaydet_budar_ve_yukler(self):
        c = cevirmen()
        c.baslik("tut", "A")
        c.baslik("at", "B")
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "ceviri.json"
            onbellegi_kaydet(yol, c.onbellek, {"tut"})
            self.assertEqual(set(onbellegi_yukle(yol)), {"tut"})
            yol.write_text("bozuk", encoding="utf-8")
            self.assertEqual(onbellegi_yukle(yol), {})


def makale(i):
    return Makale("bbc.co.uk", f"Title {i}", f"https://x/{i}", f"Summary {i}.", "", "2026-09-24T12:00:00+0000")


class TurkceSayfa(unittest.TestCase):
    def setUp(self):
        self.makaleler = [makale(i) for i in range(10)]
        self.kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", self.makaleler)]}
        self.eski = [ArsivKaydi("Gündem", "bbc.co.uk", "Old title", "https://x/eski", "2026-09-23T10:00:00+0000", False,
                                "2026-09-23T10:00:00+0000")]

    def ceviriler(self, adet):
        c = Ceviriler()
        for m in self.makaleler[:adet]:
            c.basliklar[m.url] = "Başlık " + m.baslik
            c.ozetler[m.url] = "Özet " + m.ozet
        c.basliklar["https://x/eski"] = "Eski başlık"
        return c

    def test_cevrilmis_sayfa_turkce(self):
        html = sayfa.sayfa_olustur(self.kategoriler, self.eski, self.ceviriler(9))  # %90
        self.assertRegex(html, r'<html lang="tr" translate="no" data-dil="tr" data-uretim="\d+">')
        self.assertIn(">Başlık Title 0</a>", html)
        self.assertIn("<p>Özet Summary 0.</p>", html)
        self.assertIn(">Eski başlık</a>", html)
        self.assertNotIn('id="cevir-linki"', html)
        # Çevirisi alınamamış haber bu yayında hiç gösterilmez (İngilizce
        # kart çıkmaz); bir sonraki çalıştırmada çevrilip gelir.
        self.assertNotIn('data-url="https://x/9"', html)
        self.assertNotIn(">Title 9</a>", html)
        self.assertIn("9 haber", html)

    def test_cevirinin_cogu_yoksa_ingilizce_sayfa(self):
        html = sayfa.sayfa_olustur(self.kategoriler, self.eski, self.ceviriler(8))  # %80 < %90
        self.assertRegex(html, r'<html lang="en" data-uretim="\d+">')
        self.assertIn(">Title 0</a>", html)
        self.assertNotIn(">Başlık Title", html)
        self.assertNotIn(">Eski başlık<", html)
        self.assertIn('id="cevir-linki"', html)


if __name__ == "__main__":
    unittest.main()
