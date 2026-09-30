"""Claude çevirisi (scripts/claude_ceviri.py) testleri. Claude'a gidilmiyor;
çağrı yerine sahte fonksiyon veriliyor.

Çalıştırma: python -m unittest discover -s tests -v
"""

import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import claude_ceviri  # noqa: E402
import haber_uret  # noqa: E402
from ceviri import Cevirmen  # noqa: E402
from model import Makale  # noqa: E402


class Cevap(unittest.TestCase):
    def test_json_ayiklanir(self):
        self.assertEqual(claude_ceviri.cevabi_ayikla('{"b0": "Başlık"}'), {"b0": "Başlık"})
        # Kod bloğu işareti ya da önünde sonunda metin olsa da.
        self.assertEqual(claude_ceviri.cevabi_ayikla('```json\n{"b0": "Başlık", "o1": "Özet."}\n```'),
                         {"b0": "Başlık", "o1": "Özet."})
        with self.assertRaises(ValueError):
            claude_ceviri.cevabi_ayikla("Üzgünüm, çeviremiyorum.")

    def test_parcalar_halinde_cevrilir(self):
        cagrilar = []

        def cagir(parca):
            cagrilar.append(list(parca))
            return {k: "TR " + v for k, v in parca.items()}

        metinler = {f"o{i}": f"text {i}" for i in range(claude_ceviri.PARCA_BOYU + 3)}
        sonuc = claude_ceviri.toplu_cevir(metinler, cagir)
        self.assertEqual(len(cagrilar), 2)
        self.assertEqual(sonuc["o0"], "TR text 0")
        self.assertEqual(len(sonuc), len(metinler))

    def test_hata_olunca_durur_kalanlar_google_a(self):
        def cagir(parca):
            raise RuntimeError("kullanım limiti")

        self.assertEqual(claude_ceviri.toplu_cevir({"b0": "Title"}, cagir), {})

    def test_cevapta_olmayan_ya_da_fazladan_kimlik_alinmaz(self):
        sonuc = claude_ceviri.toplu_cevir({"b0": "A", "b1": "B"}, lambda p: {"b0": "Ç", "x9": "?"})
        self.assertEqual(sonuc, {"b0": "Ç"})


class UretimeBaglanti(unittest.TestCase):
    def makale(self):
        return Makale("bonappetit.com", "Cottage Cheese Meatballs", "https://x/k", "Adding cottage cheese works.", "", "")

    def test_claude_cevirisi_onbellege_yazilir_google_a_gidilmez(self):
        google = mock.Mock(side_effect=lambda m: "GOOGLE " + m)
        cevirmen = Cevirmen({}, google, 10, bekleme=0)
        m = self.makale()
        with mock.patch.object(claude_ceviri, "kullanilabilir_mi", return_value=True), \
             mock.patch.object(claude_ceviri, "toplu_cevir",
                               side_effect=lambda metinler: {k: "CLAUDE " + v for k, v in metinler.items()}):
            with contextlib.redirect_stdout(io.StringIO()):
                haber_uret.claude_ile_cevir(cevirmen, [m])
        cevirmen.baslik(m.url, m.baslik)
        cevirmen.ozet(m.url, m.ozet)
        self.assertEqual(cevirmen.ceviriler.basliklar[m.url], "CLAUDE Cottage Cheese Meatballs")
        self.assertEqual(cevirmen.ceviriler.ozetler[m.url], "CLAUDE Adding cottage cheese works.")
        google.assert_not_called()
        # Sonraki çalıştırmada Claude'a yeniden gidilmez.
        self.assertFalse(cevirmen.claude_gerekli_mi("b", m.url, m.baslik))

    def test_google_cevirisi_olan_metin_bir_kez_claude_a_gider(self):
        m = self.makale()
        cevirmen = Cevirmen({}, lambda metin: "GOOGLE " + metin, 10, bekleme=0)
        cevirmen.baslik(m.url, m.baslik)
        self.assertTrue(cevirmen.claude_gerekli_mi("b", m.url, m.baslik))

    def test_claude_yoksa_google(self):
        m = self.makale()
        cevirmen = Cevirmen({}, lambda metin: "GOOGLE " + metin, 10, bekleme=0)
        with mock.patch.object(claude_ceviri, "kullanilabilir_mi", return_value=False):
            with contextlib.redirect_stdout(io.StringIO()):
                haber_uret.claude_ile_cevir(cevirmen, [m])
        cevirmen.baslik(m.url, m.baslik)
        self.assertEqual(cevirmen.ceviriler.basliklar[m.url], "GOOGLE Cottage Cheese Meatballs")


if __name__ == "__main__":
    unittest.main()
