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

        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(claude_ceviri.toplu_cevir({"b0": "Title"}, cagir), {})

    def test_bozuk_cevapta_parca_bolunup_yeniden_denenir(self):
        # Gerçek hata: çeviride kaçmamış tırnak ("Expecting ',' delimiter").
        cagrilar = []

        def cagir(parca):
            cagrilar.append(len(parca))
            if "o2" in parca:
                return claude_ceviri.cevabi_ayikla('{"o2": "Adı "Lezzet" olan"}')
            return {k: "TR " + v for k, v in parca.items()}

        metinler = {f"o{i}": f"text {i}" for i in range(4)}
        with contextlib.redirect_stderr(io.StringIO()):
            sonuc = claude_ceviri.toplu_cevir(metinler, cagir)
        self.assertEqual(sonuc, {"o0": "TR text 0", "o1": "TR text 1", "o3": "TR text 3"})
        self.assertEqual(cagrilar, [4, 2, 2, 1, 1])

    def test_cevapta_olmayan_ya_da_fazladan_kimlik_alinmaz(self):
        sonuc = claude_ceviri.toplu_cevir({"b0": "A", "b1": "B"}, lambda p: {"b0": "Ç", "x9": "?"})
        self.assertEqual(sonuc, {"b0": "Ç"})


class Talimat(unittest.TestCase):
    def test_kategoriye_gore_talimat(self):
        self.assertIn("yemek ve mutfak", claude_ceviri.sistem("Yemek"))
        self.assertIn("Venedik", claude_ceviri.sistem("Gezi"))
        self.assertNotIn("Venedik", claude_ceviri.sistem("Yemek"))
        self.assertIn("İlyada", claude_ceviri.sistem("Sanat & Kültür"))
        # Tanımsız kategori de çalışır; ortak kurallar her talimatta.
        for kategori in ("Yemek", "Gezi", "Bilim"):
            self.assertIn("JSON", claude_ceviri.sistem(kategori))
            self.assertIn("Hiçbir şey ekleme", claude_ceviri.sistem(kategori))


class Kullanim(unittest.TestCase):
    def test_cli_cevabindaki_kullanim_toplanir(self):
        with mock.patch.dict(claude_ceviri.kullanim, {"cagri": 0, "girdi": 0, "onbellek": 0, "cikti": 0, "maliyet": 0.0}):
            claude_ceviri.kullanimi_ekle({"usage": {"input_tokens": 900, "cache_creation_input_tokens": 100,
                                                    "cache_read_input_tokens": 50, "output_tokens": 700},
                                          "total_cost_usd": 0.0125})
            claude_ceviri.kullanimi_ekle({"result": "{}"})  # usage yoksa da bozulmaz
            self.assertEqual(claude_ceviri.kullanim_ozeti(),
                             "2 çağrı, 1000 girdi + 50 önbellekten okunan + 700 çıktı token (API karşılığı ~$0.013)")


class UretimeBaglanti(unittest.TestCase):
    def makale(self):
        return Makale("bonappetit.com", "Cottage Cheese Meatballs", "https://x/k", "Adding cottage cheese works.", "", "")

    def test_claude_cevirisi_onbellege_yazilir_google_a_gidilmez(self):
        google = mock.Mock(side_effect=lambda m: "GOOGLE " + m)
        cevirmen = Cevirmen({}, google, 10, bekleme=0)
        m = self.makale()
        with mock.patch.object(claude_ceviri, "kullanilabilir_mi", return_value=True), \
             mock.patch.object(claude_ceviri, "toplu_cevir",
                               side_effect=lambda metinler, **_: {k: "CLAUDE " + v for k, v in metinler.items()}):
            with contextlib.redirect_stdout(io.StringIO()):
                haber_uret.claude_ile_cevir(cevirmen, "Yemek", [m])
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

    def test_haric_kaynak_claude_a_gitmez(self):
        # Sanat & Kültür Claude'da, The Art Newspaper Google'da kalıyor.
        from model import KaynakBolumu
        guardian = Makale("theguardian.com", "Renoir and Love review", "https://g/1", "A happy show.", "", "")
        tan = Makale("theartnewspaper.com", "Whitney workers vote to strike", "https://t/1", "They voted.", "", "")
        kategoriler = {"Sanat & Kültür": [KaynakBolumu("theguardian.com", "", [guardian]),
                                          KaynakBolumu("theartnewspaper.com", "", [tan])]}
        gonderilen = []
        with mock.patch.dict("os.environ", {"CEVIRI_KAPALI": "1"}), \
             mock.patch.object(haber_uret, "onbellegi_yukle", return_value={}), \
             mock.patch.object(haber_uret, "onbellegi_kaydet"), \
             mock.patch.object(haber_uret, "claude_ile_cevir",
                               side_effect=lambda c, kat, ms, **_: gonderilen.extend(m.kaynak for m in ms)), \
             mock.patch.object(haber_uret, "gemini_ile_cevir"), \
             contextlib.redirect_stdout(io.StringIO()):
            haber_uret.cevir(kategoriler, [])
        self.assertEqual(gonderilen, ["theguardian.com"])

    def test_google_durunca_eksikler_claude_a(self):
        from model import KaynakBolumu
        eski = Makale("bbc.co.uk", "Old news", "https://b/eski", "Old summary.", "", "2026-09-30T08:00:00+0000")
        yeni = Makale("bbc.co.uk", "Flight diverted", "https://b/yeni", "A plane landed.", "", "2026-09-30T10:00:00+0000")
        kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", [yeni, eski])]}

        def google(metin):
            raise OSError("429 Too Many Requests")

        cevirmen = Cevirmen({"https://b/eski": {}}, google, 10, bekleme=0)
        # Eski haberin çevirisi önbellekte; yenisininki yok, Google da duruyor.
        cevirmen.claude_kaydet("b", eski.url, eski.baslik, "Eski haber")
        cevirmen.claude_kaydet("o", eski.url, eski.ozet, "Eski özet.")
        with contextlib.redirect_stderr(io.StringIO()):
            for m in (yeni, eski):
                cevirmen.baslik(m.url, m.baslik)
                cevirmen.ozet(m.url, m.ozet)
        self.assertTrue(cevirmen.durdu)
        self.assertFalse(cevirmen.ceviriler.cevrildi_mi(yeni.url))
        gonderilen = []

        def toplu(metinler, **_):
            gonderilen.extend(metinler.values())
            return {k: "TR " + v for k, v in metinler.items()}

        with mock.patch.object(claude_ceviri, "kullanilabilir_mi", return_value=True), \
             mock.patch.object(claude_ceviri, "toplu_cevir", side_effect=toplu), \
             contextlib.redirect_stdout(io.StringIO()):
            haber_uret.claude_yedegi(cevirmen, kategoriler)
        self.assertEqual(sorted(gonderilen), ["A plane landed.", "Flight diverted"])
        self.assertTrue(cevirmen.ceviriler.cevrildi_mi(yeni.url))
        self.assertEqual(cevirmen.ceviriler.basliklar[yeni.url], "TR Flight diverted")
        # Önbelleğe yazıldı: sonraki turda Google'a yeniden gitmez.
        self.assertEqual(cevirmen.onbellek[yeni.url]["o"], "TR A plane landed.")

    def test_claude_yoksa_google(self):
        m = self.makale()
        cevirmen = Cevirmen({}, lambda metin: "GOOGLE " + metin, 10, bekleme=0)
        with mock.patch.object(claude_ceviri, "kullanilabilir_mi", return_value=False):
            with contextlib.redirect_stdout(io.StringIO()):
                haber_uret.claude_ile_cevir(cevirmen, "Yemek", [m])
        cevirmen.baslik(m.url, m.baslik)
        self.assertEqual(cevirmen.ceviriler.basliklar[m.url], "GOOGLE Cottage Cheese Meatballs")


if __name__ == "__main__":
    unittest.main()
