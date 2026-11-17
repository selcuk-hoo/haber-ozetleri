import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import haber_uret  # noqa: E402
from tarih import gelecekte_mi, guvenilir_tarih  # noqa: E402


def _an(**fark) -> str:
    return (datetime.now(timezone.utc) + timedelta(**fark)).strftime("%Y-%m-%dT%H:%M:%S%z")


class GelecekTarihi(unittest.TestCase):
    def test_gelecekte_mi(self):
        self.assertTrue(gelecekte_mi(_an(days=9)))
        self.assertFalse(gelecekte_mi(_an(hours=2)))  # saat dilimi kayması payı
        self.assertFalse(gelecekte_mi(_an(days=-30)))
        self.assertFalse(gelecekte_mi(""))
        self.assertFalse(gelecekte_mi("saçma"))

    def test_gelecekteki_sayfa_tarihi_beslemeye_duser(self):
        # BBC Culture 3 Kasım haberine 26 Kasım demişti (17.11.2026).
        gecmis = _an(days=-2)
        self.assertEqual(guvenilir_tarih(_an(days=9), gecmis), gecmis)
        self.assertEqual(guvenilir_tarih(gecmis, _an(days=9)), gecmis)

    def test_ikisi_de_gelecekteyse_bos(self):
        self.assertEqual(guvenilir_tarih(_an(days=9), _an(days=9)), "")

    def test_sirada_ilk_gorulme_kullanilir(self):
        class Takip:
            def ilk_gorulme(self, url):
                return "2026-11-05T11:01:01+0000"

        self.assertEqual(haber_uret._tarih_bul(_an(days=9), _an(days=9), "u", Takip()),
                         ("2026-11-05T11:01:01+0000", True))
        gecmis = _an(days=-1)
        self.assertEqual(haber_uret._tarih_bul(gecmis, "", "u", Takip()), (gecmis, False))


if __name__ == "__main__":
    unittest.main()
