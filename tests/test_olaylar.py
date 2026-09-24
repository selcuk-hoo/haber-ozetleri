"""Aynı olayı anlatan haberleri gruplama (scripts/olaylar.py) testleri.

Örnekler canlı sitede görülen gerçek başlık/özetlerden kısaltıldı.
Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sayfa  # noqa: E402
from model import KaynakBolumu, Makale  # noqa: E402
from olaylar import olaylari_grupla  # noqa: E402


def m(kaynak, baslik, ozet, saat="2026-09-24T12:00:00+0000", url=None):
    return Makale(kaynak, baslik, url or f"https://{kaynak}/{abs(hash(baslik))}", ozet, "", saat)


MEDYA = [
    m("bbc.co.uk", "Trump media ban: White House restores access to CNN, Politico and MS NOW after judge's order",
      "The White House has restored access for CNN, Politico and MS NOW reporters. A federal judge ordered Donald"
      " Trump to lift the ban on Thursday.", "2026-09-24T16:00:00+0000"),
    m("cnn.com", "CNN, MS NOW and Politico allowed back into the White House after judge orders Trump",
      "CNN, MS NOW and Politico were allowed back into the White House on Thursday. A judge ordered the Trump"
      " administration to lift its ban.", "2026-09-24T15:00:00+0000"),
    m("france24.com", "Politico, CNN and MS NOW return to White House hours after judge reorders Trump to lift ban",
      "Reporters from Politico, CNN and MS NOW returned to the White House. The judge reordered Trump to lift the"
      " ban on the outlets.", "2026-09-24T14:00:00+0000"),
]
DIGER = [
    m("dw.com", "Pope Leo XIV visits France as he reflects on Europe's future",
      "Pope Leo XIV arrived in Paris on Thursday. The pontiff will meet President Emmanuel Macron."),
    m("aljazeera.com", "Israel offers cash to firms hit by trade ban; Europe dithers on new rules",
      "Israel is offering cash to companies hit by a Turkish trade ban. European officials are divided."),
    m("scmp.com", "Croatian court approves extradition of Nord Stream blast suspect to Germany",
      "A Croatian court approved the extradition of a Ukrainian suspect to Germany over the Nord Stream blasts."),
    m("aa.com.tr", "Excavations at Türkiye's Aspendos reveal settlement dating back 6,000 years",
      "Archaeologists at Aspendos in Antalya found traces of a settlement dating back 6,000 years."),
]


def kategoriler(**kat_makaleler):
    sonuc = {}
    for kat, makaleler in kat_makaleler.items():
        bolumler = {}
        for x in makaleler:
            bolumler.setdefault(x.kaynak, KaynakBolumu(x.kaynak, "", [])).makaleler.append(x)
        sonuc[kat.replace("_", " ")] = list(bolumler.values())
    return sonuc


class Gruplama(unittest.TestCase):
    def test_ayni_olay_farkli_kaynaklar_birlesir(self):
        gruplar = olaylari_grupla(kategoriler(Gundem=MEDYA + DIGER))
        self.assertEqual(list(gruplar), [("Gundem", MEDYA[0].url)])  # öncü: en yeni haber
        self.assertEqual({x.kaynak for x in gruplar[("Gundem", MEDYA[0].url)]}, {"cnn.com", "france24.com"})

    def test_ilgisiz_haberler_birlesmez(self):
        self.assertEqual(olaylari_grupla(kategoriler(Gundem=DIGER)), {})

    def test_ayni_kaynaktan_iki_haber_birlesmez(self):
        ikinci = m("bbc.co.uk", MEDYA[1].baslik, MEDYA[1].ozet, url="https://bbc.co.uk/ikinci")
        gruplar = olaylari_grupla(kategoriler(Gundem=[MEDYA[0], ikinci] + DIGER))
        self.assertEqual(gruplar, {})

    def test_farkli_kategoriler_birlesmez(self):
        self.assertEqual(olaylari_grupla(kategoriler(Gundem=[MEDYA[0]] + DIGER, Teknoloji=[MEDYA[1]])), {})

    def test_zaman_penceresi(self):
        eski = m("cnn.com", MEDYA[1].baslik, MEDYA[1].ozet, "2026-09-21T12:00:00+0000")
        self.assertEqual(olaylari_grupla(kategoriler(Gundem=[MEDYA[0], eski] + DIGER)), {})


class Sayfada(unittest.TestCase):
    def test_oncu_kartta_liste_digerleri_grupta(self):
        html = sayfa.sayfa_olustur(kategoriler(Gundem=MEDYA + DIGER))
        self.assertIn('data-etiket="Bu olayı 2 kaynak daha haberleştirdi"', html)
        self.assertEqual(html.count('data-grupta="1"'), 2)
        self.assertNotIn(f'data-url="{MEDYA[0].url}" data-grupta', html)
        # Menü sayıları: [kaynak, son, eski, gruplanan]
        self.assertIn('["cnn.com", 1, 0, 1]', html)


if __name__ == "__main__":
    unittest.main()
