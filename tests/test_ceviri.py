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

    def test_turkce_kaynak_cevrilmeden_girer_ingilizcesi_gruplama_icin(self):
        sahte = SahteCevirmen()
        c = Cevirmen({}, SahteCevirmen(), 100, bekleme=0, ingilizceye_cevir=sahte)
        c.turkce_kaynak("u1", "Başlık", "Birinci cümle. İkinci cümle. Üçüncü cümle.")
        self.assertEqual(c.ceviriler.baslik("u1", ""), "Başlık")
        self.assertEqual(c.ceviriler.ozet("u1", ""), "Birinci cümle. İkinci cümle. Üçüncü cümle.")
        self.assertTrue(c.ceviriler.cevrildi_mi("u1"))
        self.assertEqual(c.ceviriler.ingilizceler["u1"], ("TR Başlık", "TR Birinci cümle. İkinci cümle."))
        # İkinci çalıştırma önbellekten
        ikinci = SahteCevirmen()
        c2 = Cevirmen(c.onbellek, SahteCevirmen(), 100, bekleme=0, ingilizceye_cevir=ikinci)
        c2.turkce_kaynak("u1", "Başlık", "Birinci cümle. İkinci cümle. Üçüncü cümle.")
        self.assertEqual(ikinci.cagrilar, [])
        self.assertIn("u1", c2.ceviriler.ingilizceler)

    def test_turkce_kaynak_google_yoksa_da_gosterilir(self):
        c = Cevirmen({}, SahteCevirmen(), 100, bekleme=0, ingilizceye_cevir=SahteCevirmen(hata_sonrasi=0))
        c.turkce_kaynak("u1", "Başlık", "Cümle.")
        self.assertTrue(c.ceviriler.cevrildi_mi("u1"))
        self.assertNotIn("u1", c.ceviriler.ingilizceler)

    def test_baslik_ilk_cumleyle_birlikte_cevrilir(self):
        sahte = SahteCevirmen()
        c = cevirmen(sahte=sahte)
        c.baslik("u1", "Cooking with the meatfluencer", "Tom Kerridge is the king of meat.")
        self.assertEqual(sahte.cagrilar, ["Cooking with the meatfluencer\nTom Kerridge is the king of meat."])
        self.assertEqual(c.ceviriler.baslik("u1", ""), "TR Cooking with the meatfluencer")
        # Eski haberler listesi (bağlamsız) aynı kaydı kullanır, yeniden çevirmez
        ikinci = SahteCevirmen()
        c2 = cevirmen(c.onbellek, ikinci)
        c2.baslik("u1", "Cooking with the meatfluencer")
        self.assertEqual((ikinci.cagrilar, c2.ceviriler.baslik("u1", "")), ([], "TR Cooking with the meatfluencer"))

    def test_eski_baslik_cevirisi_bir_kez_yenilenir(self):
        c = cevirmen()
        c.baslik("u1", "Title")  # eski (bağlamsız) çeviri
        sahte = SahteCevirmen()
        c2 = cevirmen(c.onbellek, sahte)
        c2.baslik("u1", "Title", "Context.")
        c2.baslik("u1", "Title", "Context.")
        self.assertEqual(sahte.cagrilar, ["Title\nContext."])
        # Google yoksa eski çeviri kullanılır (eskimiş sayılmaz: metin aynı)
        c3 = cevirmen({"u2": dict(c.onbellek["u1"])}, SahteCevirmen(hata_sonrasi=0))
        c3.baslik("u2", "Title", "Context.")
        self.assertEqual((c3.ceviriler.baslik("u2", ""), c3.eskimis), ("TR Title", 0))

    def test_satirlar_birlesirse_baslik_tek_basina_cevrilir(self):
        class Birlestiren(SahteCevirmen):
            def __call__(self, metin):
                return super().__call__(metin).replace("\n", " ")
        sahte = Birlestiren()
        c = cevirmen(sahte=sahte)
        c.baslik("u1", "Title", "Context.")
        self.assertEqual(sahte.cagrilar, ["Title\nContext.", "Title"])
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

    def test_turkce_kaynak_karti(self):
        tr = Makale("tr.euronews.com", "Türkçe başlık", "https://tr/1", "Türkçe özet.", "", "2026-09-24T12:00:00+0000")
        self.kategoriler["Gündem"].append(KaynakBolumu("tr.euronews.com", "", [tr]))
        c = self.ceviriler(10)
        c.basliklar[tr.url], c.ozetler[tr.url] = tr.baslik, tr.ozet
        html = sayfa.sayfa_olustur(self.kategoriler, self.eski, c)
        self.assertRegex(html, r'<article [^>]*data-url="https://tr/1" data-dil="tr">')
        # İngilizce (yedek) sayfada translate.goog'un dokunmaması için işaretli
        html = sayfa.sayfa_olustur(self.kategoriler, self.eski, Ceviriler())
        self.assertRegex(html, r'<article [^>]*data-url="https://tr/1" data-dil="tr" lang="tr" translate="no">')
        self.assertIn(">Türkçe başlık</a>", html)

    def test_cevirinin_cogu_yoksa_ingilizce_sayfa(self):
        html = sayfa.sayfa_olustur(self.kategoriler, self.eski, self.ceviriler(8))  # %80 < %90
        self.assertRegex(html, r'<html lang="en" data-uretim="\d+">')
        self.assertIn(">Title 0</a>", html)
        self.assertNotIn(">Başlık Title", html)
        self.assertNotIn(">Eski başlık<", html)
        self.assertIn('id="cevir-linki"', html)


if __name__ == "__main__":
    unittest.main()
