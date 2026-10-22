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
# (Gerçek başlık "‘At what cost?’: …" idi; soru başlıkları ayrı talimatla
# gider, bkz. SoruBasligi.)
BASLIK = "Southeast Asia starts to rethink AI data centre boom"
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


# 13.10.2026, Euronews Türkçe: ilk 5 cümle giriş paragrafıyla bitiyor, haberin sonu görünmüyor.
TR_BASLIK = "Polonya'da bir anne, yürümek istemeyen iki oğlunu dağ yolunda yalnız bıraktı"
TR_ILK = "Olay, cumartesi günü Polonya Turizm ve Gezi Derneği'nin (PTTK) Rzeszów şubesinden bir grubun yürüyüşü sırasında ortaya çıktı."
TR_UZUN = (TR_ILK + " Grup, patikanın kenarında ağlayan 8 yaşındaki bir çocukla şaşkın halde duran 14 yaşındaki ağabeyini buldu."
           " Anne bir süre sonra geri döndü. Küçük çocuk annesinin elini tutunca ağlamayı bıraktı. Olay yerel yetkililere bildirildi.")
TR_OZET = ("Polonya'da yürüyüş yapan bir anne, 8 ve 14 yaşındaki oğullarını sisli bir dağ yolunda yalnız bıraktı; "
           "çocukları bir grup turist buldu. Anne bir süre sonra döndü, olay yerel yetkililere bildirildi.")


def tr_makale(url="https://e/1", uzun=TR_UZUN):
    return Makale("tr.euronews.com", TR_BASLIK, url, TR_ILK, "", "", uzun=uzun)


class TurkceKaynak(unittest.TestCase):
    def test_turkce_kaynak_kendi_talimatiyla_ayri_istekte(self):
        c = Cevirmen({}, lambda m: "G " + m, 10, bekleme=0)
        istekler = []

        def cagir(model, parca):
            istekler.append(list(parca.values()))
            return {k: (TR_OZET if v["baslik"] == TR_BASLIK else OZET) for k, v in parca.items()}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(gemini_ozet.ozetle(c, [makale(), tr_makale()], cagir=cagir), 2)
        self.assertEqual(len(istekler), 2)  # yabancı ve Türkçe kaynak ayrı isteklerde
        self.assertEqual(c.yz_ozeti("https://e/1", TR_UZUN), TR_OZET)

    def test_talimat_sonu_ve_tekrari_ister(self):
        self.assertIn("son durumunu", gemini_ozet.TALIMAT_TR)
        self.assertIn("iki kez", gemini_ozet.TALIMAT_TR)

    def test_bozuk_yazimli_ozet_kaydedilmez(self):
        # 15 Türkçe özetin 3'ü Flash-Lite yazım bozukluğuydu ("takónktaki").
        c = Cevirmen({}, lambda m: "G " + m, 10, bekleme=0)
        kotu = TR_OZET.replace("takımdaki", "takónktaki").replace("grup turist", "grup turíst")
        with contextlib.redirect_stdout(io.StringIO()):
            gemini_ozet.ozetle(c, [tr_makale()], cagir=lambda model, parca: {i: kotu for i in parca})
        self.assertIsNone(c.yz_ozeti("https://e/1", TR_UZUN))
        # Kaynaktaki aksanlı özel ad serbest.
        uzun = TR_UZUN + " Sébastien Lecornu açıklama yaptı."
        iyi = TR_OZET + " Sébastien Lecornu açıklama yaptı."
        self.assertTrue(c.yz_ozeti_kaydet("https://e/2", uzun, iyi))

    def test_sayfada_gemini_ozeti_gruplama_ilk_cumlelerden(self):
        m = tr_makale()
        c = Cevirmen({}, lambda x: "G " + x, 10, bekleme=0)
        c.yz_ozeti_kaydet(m.url, TR_UZUN, TR_OZET)
        gonderilen = []
        with mock.patch.dict("os.environ", {"CEVIRI_KAPALI": "1"}), \
             mock.patch.object(haber_uret, "onbellegi_yukle", return_value=c.onbellek), \
             mock.patch.object(haber_uret, "onbellegi_kaydet"), \
             mock.patch.object(haber_uret, "claude_ile_cevir"), \
             mock.patch.object(gemini_ceviri, "kullanilabilir_mi", return_value=True), \
             mock.patch.object(gemini_ceviri, "ingilizceye_cevir",
                               side_effect=lambda metinler: gonderilen.extend(metinler.values()) or {}), \
             mock.patch.object(gemini_ceviri, "toplu_cevir", return_value={}), \
             mock.patch.object(ceviri_denetcisi, "DENETIM_SAATLERI", set()), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ceviriler = haber_uret.cevir({"Gündem": [KaynakBolumu("tr.euronews.com", "", [m])]}, [])
        self.assertEqual(ceviriler.ozetler[m.url], TR_OZET)
        self.assertIn(TR_ILK, gonderilen)  # gruplama için İngilizcesi hâlâ ilk cümlelerden

    def test_turkce_ozet_denetimi_duzeltme_yazar_baslik_atilir(self):
        m = tr_makale()
        c = Cevirmen({}, lambda x: "G " + x, 10, bekleme=0)
        c.yz_ozeti_kaydet(m.url, TR_UZUN, TR_OZET)
        duzgun = TR_OZET.replace("yalnız bıraktı", "tek başına bıraktı")
        girdiler = []

        def cagir(girdi):
            girdiler.append(girdi)
            return {k: {"tur": "ozet", "neden": "x", "tr_ozet": f"{TR_BASLIK}\n\n{duzgun}"} for k in girdi}
        with contextlib.redirect_stdout(io.StringIO()):
            sayac = ceviri_denetcisi.denetle(c, [(m.url, m.baslik, m.ozet, m.uzun)], cagir=cagir, turkce=True)
            ceviri_denetcisi.denetle(c, [(m.url, m.baslik, m.ozet, m.uzun)], cagir=cagir, turkce=True)
        self.assertEqual(sayac["duzeltilen"], 1)
        self.assertEqual(list(girdiler[0].values())[0], {"baslik": TR_BASLIK, "metin": TR_UZUN, "ozet": TR_OZET})
        self.assertEqual(c.yz_ozeti(m.url, TR_UZUN), duzgun)  # başlık kopyası atıldı
        self.assertEqual(len(girdiler), 1)  # ikinci kez sorulmadı

    def test_turkce_denetim_yabanci_kaynaga_dokunmaz(self):
        c = Cevirmen({}, lambda x: "G " + x, 10, bekleme=0)
        m = makale()
        c.yz_ozeti_kaydet(m.url, UZUN, OZET)
        cagri = []
        with contextlib.redirect_stdout(io.StringIO()):
            ceviri_denetcisi.denetle(c, [(m.url, m.baslik, m.ozet, "")], cagir=lambda g: cagri.append(g) or {}, turkce=True)
        self.assertEqual(cagri, [])


# 22.10.2026, Al Jazeera: cevap (Cambridge Analytica) metnin ilk cümlesinde
# olduğu hâlde genel talimatla yazılan özette yoktu.
SORU_BASLIK = "‘Facebook’s wrongdoing’: Why has Meta been fined $25bn in New Mexico?"
SORU_UZUN = ("The tech giant has been accused of misleading users regarding data privacy linked to the Cambridge"
             " Analytica scandal. A judge in New Mexico has ordered Meta Platforms to pay the US state $25bn.")
SORU_OZET = ("Meta, Cambridge Analytica skandalıyla bağlantılı olarak kullanıcıları veri gizliliği konusunda"
             " yanılttığı için New Mexico'da 25 milyar dolar cezaya çarptırıldı.")


class SoruBasligi(unittest.TestCase):
    def test_soru_mu(self):
        self.assertTrue(Cevirmen.soru_mu(SORU_BASLIK))
        self.assertTrue(Cevirmen.soru_mu("‘At what cost?’: Southeast Asia starts to rethink AI data centre boom"))
        self.assertFalse(Cevirmen.soru_mu(BASLIK))

    def test_soru_basliklari_ayri_istekte_ek_talimatla_gider(self):
        c = Cevirmen({}, lambda m: "G " + m, 10, bekleme=0)
        soru = Makale("aljazeera.com", SORU_BASLIK, "https://a/1", "x", "", "", uzun=SORU_UZUN)
        talimatlar = []

        def sahte(model, parca, talimat):
            talimatlar.append((talimat, [v["baslik"] for v in parca.values()]))
            return {k: (SORU_OZET if v["baslik"] == SORU_BASLIK else OZET) for k, v in parca.items()}
        with mock.patch.object(gemini_ceviri, "kullanilabilir_mi", return_value=True), \
             mock.patch.object(gemini_ceviri, "toplu_cevir", side_effect=lambda girdi, cagir: cagir("m", girdi)), \
             mock.patch.object(gemini_ozet, "_cagir", side_effect=sahte), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(gemini_ozet.ozetle(c, [makale(), soru]), 2)
        self.assertEqual(len(talimatlar), 2)
        (genel, b1), (ozel, b2) = talimatlar
        self.assertEqual((b1, b2), ([BASLIK], [SORU_BASLIK]))
        self.assertNotIn(gemini_ozet.SORU_EKI, genel)
        self.assertTrue(ozel.endswith(gemini_ozet.SORU_EKI))
        self.assertEqual(c.yz_ozeti("https://a/1", SORU_UZUN, soru=True), SORU_OZET)
        self.assertEqual(c.yz_ozeti("https://s/1", UZUN), OZET)

    def test_eski_genel_ozet_soru_basliginda_yeniden_yazilir(self):
        # Ek talimattan önce kaydedilmiş özet geçersiz; soru olmayan haberinki geçerli kalır.
        c = Cevirmen({}, lambda m: "G " + m, 10, bekleme=0)
        c.yz_ozeti_kaydet("https://a/1", SORU_UZUN, OZET)
        self.assertIsNone(c.yz_ozeti("https://a/1", SORU_UZUN, soru=True))
        istekler = []
        soru = Makale("aljazeera.com", SORU_BASLIK, "https://a/1", "x", "", "", uzun=SORU_UZUN)
        with contextlib.redirect_stdout(io.StringIO()):
            gemini_ozet.ozetle(c, [soru], cagir=lambda model, parca: istekler.append(parca) or
                               {k: SORU_OZET for k in parca})
        self.assertEqual(len(istekler), 1)
        self.assertEqual(c.yz_ozeti("https://a/1", SORU_UZUN, soru=True), SORU_OZET)


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
