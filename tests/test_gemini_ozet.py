"""Yapay zekâ özeti (scripts/gemini_ozet.py) testleri. Gemini'ye gidilmiyor;
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

import ceviri_denetcisi  # noqa: E402
import gemini_ceviri  # noqa: E402
import gemini_ozet  # noqa: E402
import haber_uret  # noqa: E402
from ceviri import Cevirmen  # noqa: E402
from model import KaynakBolumu, Makale  # noqa: E402

# 05.10.2026, SCMP: ilk cümleler giriş; asıl bilgi (bedel) ancak alt başlıkta.
BASLIK = "‘At what cost?’: Southeast Asia starts to rethink AI data centre boom"
ILK = "There is a great eagerness to attract investment, said Mark Manantan."
UZUN = (ILK + " As Thailand suspends projects and Malaysia faces grid strain, regulators are learning that"
        " hosting the AI boom carries a heavy price. Governments had good reasons to compete aggressively.")
OZET = ("Tayland veri merkezi projelerini askıya alırken Malezya'nın elektrik şebekesi zorlanıyor; Güneydoğu"
        " Asya'daki düzenleyiciler yapay zeka patlamasına ev sahipliği yapmanın ağır bir bedeli olduğunu görüyor.")


def makale(url="https://s/1", uzun=UZUN):
    return Makale("scmp.com", BASLIK, url, ILK, "", "", uzun=uzun)


class Ozetle(unittest.TestCase):
    def test_ozet_yazilir_bir_daha_istenmez(self):
        c = Cevirmen({}, lambda m: "G " + m, 10, bekleme=0)
        istekler = []

        def cagir(model, parca):
            istekler.append(parca)
            return {k: OZET for k in parca}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(gemini_ozet.ozetle(c, [makale(), makale("https://s/2", "")], cagir=cagir), 1)
            gemini_ozet.ozetle(c, [makale()], cagir=cagir)
        self.assertEqual(len(istekler), 1)
        self.assertEqual(list(istekler[0].values()), [{"baslik": BASLIK, "metin": UZUN}])
        self.assertEqual(c.yz_ozeti("https://s/1", UZUN), OZET)
        # Kaynak metin değişince özet geçersiz.
        self.assertIsNone(c.yz_ozeti("https://s/1", UZUN + " More."))

    def test_gecersiz_ozet_kaydedilmez(self):
        c = Cevirmen({}, lambda m: "G " + m, 10, bekleme=0)
        for kotu in ("Kısa.", OZET.replace("zorlanıyor", "zorlanıyorлар"), UZUN):
            with contextlib.redirect_stdout(io.StringIO()):
                gemini_ozet.ozetle(c, [makale()], cagir=lambda model, parca, k=kotu: {i: k for i in parca})
            self.assertIsNone(c.yz_ozeti("https://s/1", UZUN), kotu)


class Uretim(unittest.TestCase):
    def test_sayfada_yz_ozeti_ilk_cumleler_cevrilmez(self):
        m = makale()
        c = Cevirmen({}, lambda x: "G " + x, 10, bekleme=0)
        c.yz_ozeti_kaydet(m.url, UZUN, OZET)
        onbellek = c.onbellek
        gonderilen = []

        def toplu(metinler, kategori=""):
            gonderilen.extend(metinler.values())
            return {}
        with mock.patch.dict("os.environ", {"CEVIRI_KAPALI": "1"}), \
             mock.patch.object(haber_uret, "onbellegi_yukle", return_value=onbellek), \
             mock.patch.object(haber_uret, "onbellegi_kaydet"), \
             mock.patch.object(haber_uret, "claude_ile_cevir"), \
             mock.patch.object(gemini_ceviri, "kullanilabilir_mi", return_value=True), \
             mock.patch.object(gemini_ceviri, "toplu_cevir", side_effect=toplu), \
             mock.patch.object(ceviri_denetcisi, "DENETIM_SAATLERI", set()), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ceviriler = haber_uret.cevir({"Gündem": [KaynakBolumu("scmp.com", "", [m])]}, [])
        self.assertEqual(ceviriler.ozetler[m.url], OZET)
        self.assertNotIn(ILK, gonderilen)  # ilk cümleler Gemini'ye çeviriye gitmedi
        self.assertIn(BASLIK, gonderilen)

    def test_ozet_yoksa_eski_yontem(self):
        m = makale()
        with mock.patch.dict("os.environ", {"CEVIRI_KAPALI": "1"}), \
             mock.patch.object(haber_uret, "onbellegi_yukle", return_value={}), \
             mock.patch.object(haber_uret, "onbellegi_kaydet"), \
             mock.patch.object(haber_uret, "claude_ile_cevir"), \
             mock.patch.object(gemini_ceviri, "kullanilabilir_mi", return_value=True), \
             mock.patch.object(gemini_ceviri, "toplu_cevir",
                               side_effect=lambda metinler, kategori="", cagir=None: {} if cagir else
                               {k: "GEMINI " + v for k, v in metinler.items()}), \
             mock.patch.object(ceviri_denetcisi, "DENETIM_SAATLERI", set()), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ceviriler = haber_uret.cevir({"Gündem": [KaynakBolumu("scmp.com", "", [m])]}, [])
        self.assertEqual(ceviriler.ozetler[m.url], "GEMINI " + ILK)


class Denetim(unittest.TestCase):
    def test_yz_ozeti_kaynagiyla_denetlenir_duzeltme_yazilir(self):
        m = makale()
        c = Cevirmen({}, lambda x: "G " + x, 10, bekleme=0)
        c.yz_ozeti_kaydet(m.url, UZUN, OZET)
        c.claude_kaydet("b", m.url, BASLIK, "“Ne pahasına?”: Güneydoğu Asya veri merkezi patlamasını sorguluyor", isaret="g")
        duzgun = OZET.replace("ağır bir bedeli", "yüksek bir bedeli")
        girdiler = []

        def cagir(girdi):
            girdiler.append(girdi)
            return {k: {"tur": "ceviri", "neden": "x", "tr_ozet": duzgun} for k in girdi}
        with contextlib.redirect_stdout(io.StringIO()):
            sayac = ceviri_denetcisi.denetle(c, [(m.url, m.baslik, m.ozet, m.uzun)], cagir=cagir)
        self.assertEqual(sayac["duzeltilen"], 1)
        self.assertEqual(list(girdiler[0].values())[0]["en_metin"], UZUN)
        self.assertEqual(c.yz_ozeti(m.url, UZUN), duzgun)


if __name__ == "__main__":
    unittest.main()
