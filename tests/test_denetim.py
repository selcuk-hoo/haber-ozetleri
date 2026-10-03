"""İçerik denetimi (scripts/denetim.py) testleri; örnekler canlı sayfadan
(03.10.2026).

Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import denetim  # noqa: E402
import saglik  # noqa: E402
from model import Ceviriler, KaynakBolumu, Makale  # noqa: E402

ARS = ("On Friday, Amazon committed to donating more than $1 billion over the next five years to communities"
       " neighboring data centers. In a press release, Amazon said the money is for local projects, and critics say"
       " that the plan is a way to quiet the backlash.")
GALERI = ("Dünyanın en olağanüstü köpek fotoğraflarını sergileyen yarışmanın 18 kazanan karesi. “Bu fotoğraf, pitbullara"
          " duyulan karmaşık duyguları aktarıyor.” Fotoğraf: Katie Brockman “Bu fotoğraf, barınaktaki köpekleri yakalıyor.”")
SIRADAN = ("Apple, üçüncü taraf uygulama geliştiricilerinin mesaj geçmişlerine erişmesini engellemek için macOS gizlilik"
           " ayarlarını değiştirdiğini açıkladı. Karar, The Desk'in bildirdiği aboneliğe dair tartışmaların ardından geldi.")


class Sorun(unittest.TestCase):
    def test_gercek_bulgular(self):
        self.assertEqual(denetim.sorun("Köpek ödülleri", GALERI, True), "kalıntı “Fotoğraf: K”")
        self.assertEqual(denetim.sorun("Amazon’s $1B plan draws backlash", ARS, True), "çevrilmemiş İngilizce")
        self.assertEqual(denetim.sorun("Kore", "Kuzey Kore DMZ'nin sınırlarını zorluyor mu?", True),
                         "çok kısa özet (43 harf)")
        self.assertEqual(denetim.sorun("Sling TV yeni günlük paketini sundu", "Sling TV yeni günlük paketini sundu. " + SIRADAN, True),
                         "özet başlığı tekrarlıyor")

    def test_siradan_metin_temiz(self):
        # "abonelik", "reklam", "fotoğraf" gibi sıradan sözcükler alarm vermez.
        self.assertIsNone(denetim.sorun("Apple macOS ayarlarını değiştirdi", SIRADAN, True))
        self.assertIsNone(denetim.sorun("Reklam sektörü", "Reklam sektörü büyüdü; fotoğrafçılar da yeni işler buldu. "
                                        "Türkiye'de reklam harcamaları geçen yıla göre arttı.", True))
        # Türkçe kaynak İngilizce sözcük denetimine girmez.
        self.assertIsNone(denetim.sorun("Başlık", ARS, False))


class Denetle(unittest.TestCase):
    def test_kartlar_ve_saglik_kaydi(self):
        ars = Makale("arstechnica.com", "Amazon’s plan", "https://a/1", ARS, "", "")
        cevrilmemis = Makale("bbc.co.uk", "Hidden", "https://b/1", ARS, "", "")
        kisa = Makale("dw.com", "Kore", "https://d/1", "Short.", "", "")
        kategoriler = {"Teknoloji": [KaynakBolumu("x", "", [ars, cevrilmemis, kisa])]}
        ceviri = Ceviriler({ars.url: "Amazon’s plan", kisa.url: "Kore"},
                           {ars.url: ARS, kisa.url: "Kuzey Kore DMZ'yi zorluyor mu?"})
        bulgular = denetim.denetle(kategoriler, ceviri, set())
        # Çevirisi olmayan kart sayfada gösterilmediği için taranmaz.
        self.assertEqual(len(bulgular), 2)
        self.assertEqual(len(denetim.ciddi(bulgular)), 1)
        self.assertIn("arstechnica.com", denetim.ciddi(bulgular)[0])
        self.assertIn("çevrilmemiş İngilizce", denetim.ayrinti(bulgular))

    def test_saglik_kaydinda_ornekler(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "saglik.json"
            for _ in range(saglik.ESIK):
                sorunlar = saglik.saglik_guncelle(yol, {"icerik": True}, {"icerik": "  - Teknoloji / ars: “x” — y"})
        self.assertEqual(len(sorunlar), 1)
        self.assertIn("İçerik denetimi", sorunlar[0])
        self.assertIn("  - Teknoloji / ars", sorunlar[0])


if __name__ == "__main__":
    unittest.main()
