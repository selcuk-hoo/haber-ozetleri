"""Gemini çevirisi (scripts/gemini_ceviri.py) testleri. Gemini'ye
gidilmiyor; çağrı yerine sahte fonksiyon veriliyor.

Çalıştırma: python -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import gemini_ceviri  # noqa: E402
import haber_uret  # noqa: E402
import saglik  # noqa: E402
from ceviri import Cevirmen  # noqa: E402
from gemini_ceviri import GeminiHatasi  # noqa: E402
from model import ArsivKaydi, KaynakBolumu, Makale  # noqa: E402

ILK, YEDEK = gemini_ceviri.MODELLER


class Temel(unittest.TestCase):
    def setUp(self):
        gemini_ceviri.durum.update(denendi=False, hata=None)

    def cevir(self, metinler, cagir):
        with contextlib.redirect_stderr(io.StringIO()):
            return gemini_ceviri.toplu_cevir(metinler, cagir, bekleme=0)


class TopluCeviri(Temel):
    def test_parcalar_halinde_cevrilir(self):
        cagrilar = []

        def cagir(model, parca):
            cagrilar.append((model, len(parca)))
            return {k: "TR " + v for k, v in parca.items()}

        metinler = {f"o{i}": f"text {i}" for i in range(gemini_ceviri.PARCA_BOYU + 3)}
        sonuc = self.cevir(metinler, cagir)
        self.assertEqual(cagrilar, [(ILK, gemini_ceviri.PARCA_BOYU), (ILK, 3)])
        self.assertEqual(sonuc["o0"], "TR text 0")
        self.assertIsNone(gemini_ceviri.durum["hata"])

    def test_kota_dolunca_yedek_modele_gecilir(self):
        cagrilar = []

        def cagir(model, parca):
            cagrilar.append(model)
            if model == ILK:
                raise GeminiHatasi(429, "You exceeded your current quota")
            return {k: "TR " + v for k, v in parca.items()}

        metinler = {f"o{i}": f"text {i}" for i in range(gemini_ceviri.PARCA_BOYU + 3)}
        sonuc = self.cevir(metinler, cagir)
        self.assertEqual(len(sonuc), len(metinler))
        # Kotası dolan modele sonraki parçada yeniden gidilmez.
        self.assertEqual(cagrilar, [ILK, YEDEK, YEDEK])
        self.assertIsNone(gemini_ceviri.durum["hata"])

    def test_yogunlukta_ayni_model_bir_kez_daha_denenir(self):
        cagrilar = []

        def cagir(model, parca):
            cagrilar.append(model)
            if len(cagrilar) == 1:
                raise GeminiHatasi(503, "This model is currently experiencing high demand.")
            return {k: "TR " + v for k, v in parca.items()}

        self.assertEqual(self.cevir({"b0": "Title"}, cagir), {"b0": "TR Title"})
        self.assertEqual(cagrilar, [ILK, ILK])

    def test_hepsi_basarisizsa_kalanlar_google_a(self):
        def cagir(model, parca):
            raise GeminiHatasi(429, "quota")

        self.assertEqual(self.cevir({"b0": "Title", "o0": "Text."}, cagir), {})
        self.assertTrue(gemini_ceviri.durum["denendi"])
        self.assertTrue(gemini_ceviri.durum["hata"])

    def test_bozuk_json_parcayi_boler(self):
        def cagir(model, parca):
            if len(parca) > 1:
                raise ValueError("Expecting ',' delimiter")
            return {k: "TR " + v for k, v in parca.items()}

        sonuc = self.cevir({"b0": "One", "b1": "Two", "b2": "Three"}, cagir)
        self.assertEqual(sonuc, {"b0": "TR One", "b1": "TR Two", "b2": "TR Three"})
        self.assertIsNone(gemini_ceviri.durum["hata"])

    def test_calistirma_basina_sinir(self):
        gonderilen = []

        def cagir(model, parca):
            gonderilen.extend(parca)
            return {k: "TR " + v for k, v in parca.items()}

        metinler = {f"o{i}": "x" for i in range(gemini_ceviri.CALISTIRMA_BASINA_METIN + 10)}
        self.cevir(metinler, cagir)
        self.assertEqual(len(gonderilen), gemini_ceviri.CALISTIRMA_BASINA_METIN)


class Istek(Temel):
    def test_anahtar_adrese_degil_basliga(self):
        istekler = []

        class Yanit(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def urlopen(istek, timeout):
            istekler.append(istek)
            metin = json.dumps({"b0": "Başlık"}, ensure_ascii=False)
            return Yanit(json.dumps({"candidates": [{"content": {"parts": [{"text": metin}]}}],
                                     "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5}}).encode())

        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "GIZLI-ANAHTAR"}), \
             mock.patch("urllib.request.urlopen", side_effect=urlopen):
            sonuc = gemini_ceviri._cagir(ILK, {"b0": "Title"}, "talimat")
        self.assertEqual(sonuc, {"b0": "Başlık"})
        istek = istekler[0]
        self.assertNotIn("GIZLI-ANAHTAR", istek.full_url)
        self.assertEqual(istek.get_header("X-goog-api-key"), "GIZLI-ANAHTAR")
        govde = json.loads(istek.data)
        self.assertEqual(govde["generationConfig"]["responseMimeType"], "application/json")
        self.assertIn("Title", govde["contents"][0]["parts"][0]["text"])

    def test_haberlerin_talimati_kesinlik_kaydini_korur(self):
        import claude_ceviri
        for kat in ("Gündem", "Teknoloji", "Bilim"):
            self.assertIn(kat, claude_ceviri.ALANLAR)
        self.assertIn("reportedly", claude_ceviri.sistem("Gündem"))


class UretimeBaglanti(Temel):
    def makale(self, url="https://b/1", baslik="Flight diverted", ozet="A plane landed."):
        return Makale("bbc.co.uk", baslik, url, ozet, "", "")

    def test_gemini_cevirisi_onbellege_yazilir_google_a_gidilmez(self):
        google = mock.Mock(side_effect=lambda m: "GOOGLE " + m)
        cevirmen = Cevirmen({}, google, 10, bekleme=0)
        m = self.makale()
        eski = ArsivKaydi("Gündem", "bbc.co.uk", "Old news", "https://b/eski", "", False, "")
        gonderilen = {}

        def toplu(metinler, kategori=""):
            gonderilen[kategori] = sorted(metinler.values())
            return {k: "GEMINI " + v for k, v in metinler.items()}

        with mock.patch.object(gemini_ceviri, "kullanilabilir_mi", return_value=True), \
             mock.patch.object(gemini_ceviri, "toplu_cevir", side_effect=toplu), \
             contextlib.redirect_stdout(io.StringIO()):
            haber_uret.gemini_ile_cevir(cevirmen, [("Gündem", m)], [eski])
        self.assertEqual(gonderilen, {"Gündem": ["A plane landed.", "Flight diverted", "Old news"]})
        cevirmen.baslik(m.url, m.baslik)
        cevirmen.ozet(m.url, m.ozet)
        cevirmen.baslik(eski.url, eski.baslik)
        google.assert_not_called()
        self.assertEqual(cevirmen.ceviriler.basliklar[m.url], "GEMINI Flight diverted")
        self.assertEqual(cevirmen.onbellek[m.url]["bk"], "g")
        self.assertEqual(cevirmen.gemini, 3)

    def test_google_cevirisi_olan_metin_yeniden_cevrilmez(self):
        m = self.makale()
        cevirmen = Cevirmen({}, lambda metin: "GOOGLE " + metin, 10, bekleme=0)
        cevirmen.baslik(m.url, m.baslik)
        cevirmen.ozet(m.url, m.ozet)
        toplu = mock.Mock()
        with mock.patch.object(gemini_ceviri, "kullanilabilir_mi", return_value=True), \
             mock.patch.object(gemini_ceviri, "toplu_cevir", toplu):
            haber_uret.gemini_ile_cevir(cevirmen, [("Gündem", m)], [])
        toplu.assert_not_called()

    def test_gemini_cevirmezse_google(self):
        m = self.makale()
        cevirmen = Cevirmen({}, lambda metin: "GOOGLE " + metin, 10, bekleme=0)
        with mock.patch.object(gemini_ceviri, "kullanilabilir_mi", return_value=True), \
             mock.patch.object(gemini_ceviri, "toplu_cevir", return_value={}), \
             contextlib.redirect_stdout(io.StringIO()):
            haber_uret.gemini_ile_cevir(cevirmen, [("Gündem", m)], [])
        cevirmen.baslik(m.url, m.baslik)
        self.assertEqual(cevirmen.ceviriler.basliklar[m.url], "GOOGLE Flight diverted")

    def test_anahtar_yoksa_google_ve_saglik_sinyali(self):
        m = self.makale()
        cevirmen = Cevirmen({}, lambda metin: "GOOGLE " + metin, 10, bekleme=0)
        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": ""}), contextlib.redirect_stdout(io.StringIO()):
            haber_uret.gemini_ile_cevir(cevirmen, [("Gündem", m)], [])
        self.assertTrue(gemini_ceviri.durum["hata"])
        self.assertIn("GEMINI_API_KEY", saglik.aciklama("gemini"))

    def test_turkce_kaynak_gemini_ye_gitmez(self):
        dw = Makale("dw.com/tr", "Türkçe başlık", "https://d/1", "Türkçe özet.", "", "")
        bbc = self.makale()
        kategoriler = {"Gündem": [KaynakBolumu("dw.com/tr", "", [dw]), KaynakBolumu("bbc.co.uk", "", [bbc])]}
        gonderilen = []
        with mock.patch.dict("os.environ", {"CEVIRI_KAPALI": "1"}), \
             mock.patch.object(haber_uret, "onbellegi_yukle", return_value={}), \
             mock.patch.object(haber_uret, "onbellegi_kaydet"), \
             mock.patch.object(haber_uret, "claude_ile_cevir"), \
             mock.patch.object(haber_uret, "gemini_ile_cevir",
                               side_effect=lambda c, ms, eski, **_: gonderilen.extend((k, m.kaynak) for k, m in ms)), \
             contextlib.redirect_stdout(io.StringIO()):
            haber_uret.cevir(kategoriler, [])
        self.assertEqual(gonderilen, [("Gündem", "bbc.co.uk")])


if __name__ == "__main__":
    unittest.main()
