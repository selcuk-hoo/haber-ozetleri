"""Kategori vetosu (ayarlar.KATEGORI_VETO, haber_uret.vetolu_mu) testleri.
Başlıklar, 08.10.2026'da Yemek ve Gezi sekmelerinde görülen gerçek haberler.

Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from haber_uret import etiket_vetolu_mu, vetolu_mu  # noqa: E402

ICKI_YEMEK = [
    "French wine industry facing historic low harvest after extreme summer heat",
    "A vodkatini, a garibaldi and a shrub – your essential autumn cocktails – recipes",
    "Cocktail of the week: Palé Hall’s Have your cake and drink it – recipe",
    "At Himkok, one of the world’s best bars, cultural exchange matters most",
    "The 10 best craft beers to drink this autumn",
]
ICKI_GEZI = [
    "Canada's bizarre mummified toe cocktail",
    "My search for the perfect Italian aperitivo in Verona",
    "Avrupa'nın en iyi şarap bölgeleri: Slovenya, Fransa ve İtalya'yı geride bırakıyor",
    "Londra'nın en iyi pubları ve barları",
    "Bir rakı sofrasında İstanbul",
    "Inside Scotland’s whisky distilleries",
]
KALANLAR = [
    "What to Eat and Drink in Norway",  # kahve/çay karışık rehber kalır
    "Food in Egypt: The Best Things to Eat and Drink",
    "Rachel Roddy’s cheese bread ball recipe",
    "The best protein bars, tested",
    "A salad bar that raises the bar for lunch",
    "Why Bar Harbor is Maine’s best-kept secret",
    "Biraz daha şans: Karadeniz'de yürüyüş rotaları",  # "biraz" bira değil
    "Barış yürüyüşü İstanbul'da yemek turu",  # "barış" bar değil
    "Venice Simplon-Orient-Express 2027 rotasına Monte Carlo ekleniyor",
    "A fish-and-chip rival opens in Hackney",
]


class IckiVetosu(unittest.TestCase):
    def test_yemek_ve_gezide_icki_haberleri_vetolanir(self):
        for baslik in ICKI_YEMEK:
            self.assertTrue(vetolu_mu(baslik, "Yemek"), baslik)
            self.assertTrue(vetolu_mu(baslik, "Gezi"), baslik)
        for baslik in ICKI_GEZI:
            self.assertTrue(vetolu_mu(baslik, "Gezi"), baslik)

    def test_sıradan_basliklara_dokunmaz(self):
        for baslik in KALANLAR:
            self.assertFalse(vetolu_mu(baslik, "Yemek"), baslik)
            self.assertFalse(vetolu_mu(baslik, "Gezi"), baslik)

    def test_baska_kategoriler_etkilenmez(self):
        # Sanat & Kültür'de şarap sergisi, Gündem'de içki yasağı haberi kalır.
        for kategori in ("Sanat & Kültür", "Gündem", "Bilim", "Teknoloji"):
            self.assertFalse(vetolu_mu(ICKI_YEMEK[0], kategori), kategori)


class IckiEtiketVetosu(unittest.TestCase):
    # Etiketler 11.10.2026'da canlı Yemek ve Gezi haberlerinden okundu; ilk
    # liste (şarap) gerçek, "cocktails" ve "beer" listeleri Guardian'ın
    # etiket adlarına göre örnek.
    ICKI = [
        # Guardian "Cold comforts: the most satisfying autumn whites"
        ["wine", "food", "spanish food and drink", "italian food and drink", "eastern european food and drink",
         "south african food and drink"],
        ["cocktails", "drinks", "food"],
        ["beer", "food and drink", "craft beer"],
    ]
    KALANLAR = [
        ["dessert", "pastry", "food", "pie", "baking", "french food and drink", "vegetarian food and drink",
         "herbs and spices"],
        ["coffee", "travel", "coffee & tea", "culture", "drinks", "features"],  # Saveur kahve turları kalır
        ["food", "restaurants", "american food and drink", "british food and drink"],
        ["eater", "pagetype:feature", "dining-out", "travel-guides", "travel-restaurants", "summer-travel"],
        ["spa breaks", "alps holidays", "rest and relaxation", "chamonix holidays", "france holidays", "travel"],
        ["adventure travel", "australia holidays", "travel", "travelling solo", "western australia holidays"],
        ["recipes", "starch", "stir fry", "techniques", "pasta & noodle recipes"],
        [],
    ]

    def test_icki_etiketli_haber_vetolanir(self):
        for etiketler in self.ICKI:
            self.assertTrue(etiket_vetolu_mu(etiketler, "Yemek"), etiketler)
            self.assertTrue(etiket_vetolu_mu(etiketler, "Gezi"), etiketler)

    def test_icki_olmayan_etiketlere_dokunmaz(self):
        for etiketler in self.KALANLAR:
            self.assertFalse(etiket_vetolu_mu(etiketler, "Yemek"), etiketler)
            self.assertFalse(etiket_vetolu_mu(etiketler, "Gezi"), etiketler)

    def test_baska_kategoriler_etkilenmez(self):
        for kategori in ("Sanat & Kültür", "Gündem", "Bilim", "Teknoloji"):
            self.assertFalse(etiket_vetolu_mu(self.ICKI[0], kategori), kategori)


if __name__ == "__main__":
    unittest.main()
