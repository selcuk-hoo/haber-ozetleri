"""Gündem derlemesi (scripts/gundem_derleme.py) testleri. Gemini'ye gidilmiyor.

Çalıştırma: python -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import gundem_derleme  # noqa: E402
from model import Makale  # noqa: E402

SIMDI = datetime(2026, 10, 22, 21, 0, tzinfo=timezone.utc)
OZET = ("Ohio valilik yarışında Cumhuriyetçi aday Vivek Ramaswamy'nin, Demokrat rakibi Amy Acton'ın annesini"
        " konu alan saldırı reklamı tepki çekti. Acton reklamı “iğrenç” diye niteledi.")


def m(kaynak, baslik):
    return Makale(kaynak, baslik, f"https://{kaynak}/{len(baslik)}", baslik + ".", "", "", uzun=baslik + ". More.")


ACTON = [m("bbc.co.uk", "'This is despicable': Amy Acton responds to Ohio attack ad"),
         m("france24.com", "Vance tells Republicans to stop whining after Ramaswamy attack ad"),
         m("cnn.com", "Live updates: Trump on Ramaswamy ad about rival's estranged mother")]


def uret_(cevap, istekler):
    def uret(model, talimat, girdi):
        istekler.append(girdi)
        return json.dumps({o: {"baslik": "Ohio'daki saldırı reklamı tepki çekti", "ozet": cevap}
                           for o in (s[:-1] for s in girdi.splitlines() if s.startswith("o") and s.endswith(":"))})
    return uret


class Derleme(unittest.TestCase):
    def test_uc_kaynakli_olay_derlenir_iki_kaynakli_derlenmez(self):
        istekler = []
        with contextlib.redirect_stdout(io.StringIO()):
            kayit = gundem_derleme.guncelle([], [ACTON, ACTON[:2]], SIMDI, uret_(OZET, istekler))
        self.assertEqual(len(kayit), 1)
        self.assertEqual(kayit[0]["kaynaklar"], ["bbc.co.uk", "cnn.com", "france24.com"])
        self.assertEqual(gundem_derleme.ozet_bul(kayit, ACTON[2].url)["ozet"], OZET)
        self.assertEqual(istekler[0].count("[bbc.co.uk]"), 1)

    def test_yeniden_derleme_yalniz_yeni_kaynakla(self):
        istekler = []
        with contextlib.redirect_stdout(io.StringIO()):
            kayit = gundem_derleme.guncelle([], [ACTON], SIMDI, uret_(OZET, istekler))
            kayit = gundem_derleme.guncelle(kayit, [ACTON], SIMDI + timedelta(hours=1), uret_(OZET, istekler))
            self.assertEqual(len(istekler), 1)
            kayit = gundem_derleme.guncelle(kayit, [ACTON + [m("aljazeera.com", "Acton ad row")]],
                                            SIMDI + timedelta(hours=2), uret_(OZET, istekler))
        self.assertEqual(len(istekler), 2)
        self.assertEqual(len(kayit), 1)
        self.assertIn("aljazeera.com", kayit[0]["kaynaklar"])

    def test_ingilizce_ya_da_kisa_derleme_kaydedilmez(self):
        ingilizce = ("Republican candidate Vivek Ramaswamy's attack ad about the mother of his rival Amy Acton"
                     " drew criticism from the party and was called despicable by Acton.")
        for cevap in (ingilizce, "Kısa."):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(gundem_derleme.guncelle([], [ACTON], SIMDI, uret_(cevap, [])), [])

    def test_gemini_yoksa_bir_sey_yapilmaz(self):
        self.assertEqual(gundem_derleme.guncelle([], [ACTON], SIMDI), [])
        self.assertFalse(gundem_derleme.CALISIN)  # askıda


if __name__ == "__main__":
    unittest.main()
