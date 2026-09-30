"""scripts/saglik.py testleri: süren sorun sayaçları ve uyarı metni.

Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import saglik  # noqa: E402


class Saglik(unittest.TestCase):
    def test_esigi_asan_sorun_uyarilir_gecince_susar(self):
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "saglik.json"
            for _ in range(saglik.ESIK - 1):
                self.assertEqual(saglik.saglik_guncelle(yol, {"google": True, "kaynak:Gündem / cnn.com": False}), [])
            sorunlar = saglik.saglik_guncelle(yol, {"google": True, "kaynak:Gündem / cnn.com": False})
            self.assertEqual(len(sorunlar), 1)
            self.assertIn("Google Çeviri", sorunlar[0])
            # Sorun geçti: sayaç sıfırlanır.
            self.assertEqual(saglik.saglik_guncelle(yol, {"google": False}), [])

    def test_bilinmeyen_sinyal_sayaci_degistirmez(self):
        # Claude'a gidecek metin olmayan turlar ne sorunu uzatır ne sıfırlar.
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "saglik.json"
            for _ in range(saglik.ESIK - 1):
                saglik.saglik_guncelle(yol, {"claude": True})
            self.assertEqual(saglik.saglik_guncelle(yol, {"claude": None}), [])
            self.assertEqual(len(saglik.saglik_guncelle(yol, {"claude": True})), 1)

    def test_kaldirilan_kaynagin_sayaci_duser_ve_bozuk_dosya(self):
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "saglik.json"
            yol.write_text("bozuk", encoding="utf-8")
            saglik.saglik_guncelle(yol, {"kaynak:Gezi / x.com": True})
            saglik.saglik_guncelle(yol, {"google": False})
            self.assertNotIn("kaynak:Gezi / x.com", yol.read_text(encoding="utf-8"))

    def test_uyari_metni(self):
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "uyari.md"
            saglik.uyari_yaz(yol, [])
            self.assertEqual(yol.read_text(encoding="utf-8"), "")
            saglik.uyari_yaz(yol, [saglik.aciklama("kaynak:Gündem / cnn.com") + " (6 çalıştırmadır)"])
            metin = yol.read_text(encoding="utf-8")
            self.assertIn("Gündem / cnn.com", metin)
            self.assertIn("kendiliğinden kapanır", metin)


if __name__ == "__main__":
    unittest.main()
