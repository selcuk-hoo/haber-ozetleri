"""Yarım çeviri kontrolü ve Gemini çeviri denetçisi (scripts/ceviri_denetcisi.py)
testleri. Gemini'ye gidilmiyor; çağrı yerine sahte fonksiyon veriliyor.

Çalıştırma: python -m unittest discover -s tests -v
"""

import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ceviri_denetcisi  # noqa: E402
from ceviri import Cevirmen  # noqa: E402

# 05.10.2026: DW'nin mayın haberinin özeti; Gemini yalnız ilk satırı çevirdi.
EN_OZET = ("Is North Korea pushing the limits of the DMZ? October 2, 2026 Pyongyang and Seoul are trading "
           "increasingly hostile accusations across the Demilitarized Zone (DMZ) that divides the peninsula, "
           "10 days after three South Korean soldiers were injured by a land mine on the South's side of the border.")
YARIM = "Kuzey Kore DMZ'nin sınırlarını zorluyor mu?"
TAM = ("Kuzey Kore DMZ'nin sınırlarını zorluyor mu? 2 Ekim 2026 Pyongyang ve Seul, üç Güney Koreli askerin "
       "sınırın güney tarafındaki bir mayınla yaralanmasından 10 gün sonra, yarımadayı bölen Askerden "
       "Arındırılmış Bölge (DMZ) boyunca giderek sertleşen suçlamalarda bulunuyor.")


def cevirmen(onbellek=None):
    return Cevirmen(onbellek if onbellek is not None else {}, lambda m: "G " + m, 100, bekleme=0)


class YarimCeviri(unittest.TestCase):
    def test_yarim_ceviri_kaydedilmez_eskisi_yenilenir(self):
        c = cevirmen()
        c.claude_kaydet("o", "u1", EN_OZET, YARIM, isaret="g")
        self.assertNotIn("u1", c.onbellek)
        c.claude_kaydet("o", "u1", EN_OZET, TAM, isaret="g")
        self.assertEqual(c.onbellek["u1"]["o"], TAM)
        # Önbellekte kalmış eski yarım kayıt yeniden çevrilir.
        eski = cevirmen({"u2": {"o": YARIM, "oh": Cevirmen._tr_ozeti(EN_OZET), "ok": "g"}})
        self.assertTrue(eski.ceviri_gerekli_mi("o", "u2", EN_OZET))

    def test_baska_alfabeden_harf_karisan_ceviri_kaydedilmez(self):
        # 05.10.2026, SCMP: "destekliyorлар"; MercoPress: "an وطنlarına".
        en = "They bring big investments, support cloud and AI infrastructure, and governments fear falling behind."
        c = cevirmen()
        c.claude_kaydet("o", "u1", en, "Büyük yatırımlar getiriyorlar, bulut altyapısını destekliyorлар.", isaret="g")
        c.claude_kaydet("o", "u2", en, "Savaştan zarar görmüş an وطنlarına döndüler.", isaret="g")
        self.assertEqual(c.onbellek, {})
        # Kaynakta da olan harf serbest.
        self.assertFalse(Cevirmen._cevrilmemis("They discovered γ-Fe in ERα cells.", "γ-Fe'yi ERα hücrelerinde buldular."))

    def test_kisa_metin_ve_google_cevirisine_bakilmaz(self):
        # Başlıklarda oran güvenilir değil.
        self.assertFalse(Cevirmen._cevrilmemis("North and South Korea trade accusations over landmines", "Kore'ler suçlaşıyor"))
        # Google'ın kaydı (işaretsiz) bozuk sayılmaz.
        c = cevirmen({"u1": {"o": YARIM, "oh": Cevirmen._tr_ozeti(EN_OZET)}})
        self.assertFalse(c.ceviri_gerekli_mi("o", "u1", EN_OZET))


def gemini_kaydi(b, o, en_b, en_o):
    return {"b": b, "bh": Cevirmen._tr_ozeti(en_b), "bk": "g", "o": o, "oh": Cevirmen._tr_ozeti(en_o), "ok": "g"}


class Denetci(unittest.TestCase):
    EN_B = "The US economy added just 29,000 jobs last month"
    EN_O = "The US labor market hit a soft patch in September as the economy added just 29,000 jobs."
    TR_B = "ABD ekonomisi geçen ay yalnızca 29 bin istihdam yarattı"
    TR_O = "ABD iş gücü piyasası eylül ayında ekonominin yalnızca 29.000 istihbarat eklemesiyle zayıfladı."

    def setUp(self):
        self.onbellek = {
            "u1": gemini_kaydi(self.TR_B, self.TR_O, self.EN_B, self.EN_O),
            "u2": gemini_kaydi("Başlık", "Özet metni.", "Title", "Summary text."),
            "u3": {"b": "Google", "bh": Cevirmen._tr_ozeti("G"), "o": "Google.", "oh": Cevirmen._tr_ozeti("G.")},
        }
        self.haberler = [("u1", self.EN_B, self.EN_O, ""), ("u2", "Title", "Summary text.", ""), ("u3", "G", "G.", "")]
        self.cagrilar = []

    def cagir(self, girdi):
        self.cagrilar.append(girdi)
        u1 = next(k for k, v in girdi.items() if v["en_baslik"] == self.EN_B)
        u2 = next(k for k, v in girdi.items() if v["en_baslik"] == "Title")
        return {u1: {"tur": "ceviri", "neden": "jobs → istihbarat",
                     "tr_ozet": "ABD iş gücü piyasası eylül ayında ekonominin yalnızca 29.000 istihdam yaratmasıyla zayıfladı."},
                u2: {"tur": "kaynak", "neden": "künye"}}

    def test_duzeltme_yazilir_bir_daha_sorulmaz(self):
        c = cevirmen(self.onbellek)
        with contextlib.redirect_stdout(io.StringIO()):
            sayac = ceviri_denetcisi.denetle(c, self.haberler, cagir=self.cagir)
        self.assertEqual(sayac, {"denetlenen": 2, "duzeltilen": 1, "kaynak": 1})
        self.assertIn("istihdam yaratmasıyla", c.onbellek["u1"]["o"])
        self.assertEqual(c.onbellek["u1"]["b"], self.TR_B)
        # Google çevirisi denetime gitmez.
        self.assertEqual(len(self.cagrilar[0]), 2)
        # Düzeltilen çeviri önbellekten okunur, yeniden çevrilmez.
        self.assertFalse(c.ceviri_gerekli_mi("o", "u1", self.EN_O))
        # Aynı metinler ikinci kez sorulmaz.
        ceviri_denetcisi.denetle(c, self.haberler, cagir=self.cagir)
        self.assertEqual(len(self.cagrilar), 1)

    def test_ingilizcesi_degisen_haber_yeniden_denetlenir(self):
        c = cevirmen(self.onbellek)
        with contextlib.redirect_stdout(io.StringIO()):
            ceviri_denetcisi.denetle(c, self.haberler, cagir=self.cagir)
        c.claude_kaydet("o", "u2", "Summary text, updated.", "Güncel özet metni.", isaret="g")
        ceviri_denetcisi.denetle(c, [("u2", "Title", "Summary text, updated.", "")], cagir=lambda g: self.cagrilar.append(g) or {})
        self.assertEqual(len(self.cagrilar), 2)

    def test_yarim_duzeltme_kabul_edilmez_hata_olunca_durur(self):
        c = cevirmen(self.onbellek)
        uzun = "The US labor market hit a soft patch in September. " * 6
        c.onbellek["u1"]["oh"] = Cevirmen._tr_ozeti(uzun)
        c.onbellek["u1"]["o"] = "ABD iş gücü piyasası eylül ayında zayıf bir dönem geçirdi. " * 6
        sahte = lambda g: {k: {"tur": "ceviri", "tr_ozet": "Kısa."} for k in g}  # noqa: E731
        with contextlib.redirect_stdout(io.StringIO()):
            ceviri_denetcisi.denetle(c, [("u1", self.EN_B, uzun, "")], cagir=sahte)
        self.assertTrue(c.onbellek["u1"]["o"].startswith("ABD iş gücü"))

        def hata(_):
            raise TimeoutError("zaman aşımı")
        c2 = cevirmen(dict(self.onbellek))
        with contextlib.redirect_stderr(io.StringIO()):
            sayac = ceviri_denetcisi.denetle(c2, self.haberler, cagir=hata)
        self.assertEqual(sayac["denetlenen"], 0)
        self.assertNotIn("d", c2.onbellek["u2"])


if __name__ == "__main__":
    unittest.main()
