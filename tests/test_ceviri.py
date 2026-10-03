"""Sunucu tarafı çeviri (scripts/ceviri.py) ve Türkçe sayfa üretimi testleri.

Google'a gidilmiyor; çevirmen yerine sahte bir fonksiyon veriliyor.
Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sayfa  # noqa: E402
from ceviri import Cevirmen, onbellegi_kaydet, onbellegi_yukle  # noqa: E402
from model import ArsivKaydi, Ceviriler, KaynakBolumu, Makale  # noqa: E402


class SahteCevirmen:
    def __init__(self, hata_sonrasi=None):
        self.cagrilar = []
        self.hata_sonrasi = hata_sonrasi

    def __call__(self, metin):
        if self.hata_sonrasi is not None and len(self.cagrilar) >= self.hata_sonrasi:
            raise OSError("429 Too Many Requests")
        self.cagrilar.append(metin)
        return "TR " + metin


def cevirmen(onbellek=None, sahte=None, sinir=100):
    return Cevirmen(onbellek if onbellek is not None else {}, sahte or SahteCevirmen(), sinir, bekleme=0)


class YerlesikAdlar(unittest.TestCase):
    def test_oman_ve_omanyali_duzelir(self):
        from ceviri import yerlesik_adlari_duzelt as d
        self.assertEqual(d("BAE'li müfettişler Omanyalı Flydubai yardımcı pilotunun saldırısı"),
                         "BAE'li müfettişler Ummanlı Flydubai yardımcı pilotunun saldırısı")
        self.assertEqual(d("Oman'da yasaklandı; Oman, Suudi Arabistan ile görüştü. Omanlı pilot."),
                         "Umman'da yasaklandı; Umman, Suudi Arabistan ile görüştü. Ummanlı pilot.")

    def test_sıradan_metne_dokunmaz(self):
        from ceviri import yerlesik_adlari_duzelt as d
        for metin in ("Oman Air uçuşları durdurdu.", "Umman vatandaşı pilot", "Romantik bir gezi", "Woman"):
            self.assertEqual(d(metin), metin)


class Onbellek(unittest.TestCase):
    def test_cevirir_ve_onbellekten_okur(self):
        sahte = SahteCevirmen()
        c = cevirmen(sahte=sahte)
        c.baslik("u1", "Title")
        c.ozet("u1", "Summary.")
        self.assertEqual((c.ceviriler.baslik("u1", "Title"), c.ceviriler.ozet("u1", "Summary.")), ("TR Title", "TR Summary."))
        self.assertTrue(c.ceviriler.cevrildi_mi("u1"))

        ikinci_sahte = SahteCevirmen()
        c2 = cevirmen(c.onbellek, ikinci_sahte)
        c2.baslik("u1", "Title")
        c2.ozet("u1", "Summary.")
        self.assertEqual(ikinci_sahte.cagrilar, [])  # önbellekten geldi
        self.assertEqual(c2.yeni, 0)
        self.assertTrue(c2.ceviriler.cevrildi_mi("u1"))

    def test_gemini_aynen_geri_verirse_kaydedilmez_eski_kayit_yenilenir(self):
        # 03.10.2026: Gemini Ars Technica'nın özetini çevirmeden geri verdi,
        # Türkçe sayfada İngilizce kaldı.
        metin = "On Friday, Amazon committed to donating more than $1 billion."
        c = cevirmen()
        c.claude_kaydet("o", "u1", metin, metin, isaret="g")
        self.assertNotIn("u1", c.onbellek)
        self.assertTrue(c.ceviri_gerekli_mi("o", "u1", metin))
        # Önbellekte kalmış eski bozuk kayıt: yeniden çevrilir (Google'a gider).
        onbellek = {"u1": {"o": metin, "oh": Cevirmen._tr_ozeti(metin), "ok": "g"}}
        sahte = SahteCevirmen()
        c2 = cevirmen(onbellek, sahte)
        self.assertTrue(c2.ceviri_gerekli_mi("o", "u1", metin))
        c2.ozet("u1", metin)
        self.assertEqual(sahte.cagrilar, [metin])
        self.assertEqual(c2.ceviriler.ozet("u1", ""), "TR " + metin)
        # Google'ın aynı kalan çevirisi (tek kelimelik ad) bozuk sayılmaz.
        onbellek = {"u2": {"b": "Nvidia", "bh": Cevirmen._tr_ozeti("Nvidia")}}
        self.assertFalse(cevirmen(onbellek).ceviri_gerekli_mi("b", "u2", "Nvidia"))

    def test_ingilizce_metin_degisince_yeniden_cevrilir(self):
        c = cevirmen()
        c.ozet("u1", "Old summary.")
        sahte = SahteCevirmen()
        c2 = cevirmen(c.onbellek, sahte)
        c2.ozet("u1", "Updated summary.")
        self.assertEqual(sahte.cagrilar, ["Updated summary."])
        self.assertEqual(c2.ceviriler.ozet("u1", ""), "TR Updated summary.")

    def test_yenisi_alinamazsa_onceki_ceviri_kullanilir(self):
        c = cevirmen()
        c.ozet("u1", "Old summary.")
        c2 = cevirmen(c.onbellek, SahteCevirmen(hata_sonrasi=0))
        c2.ozet("u1", "Updated summary.")
        c2.baslik("u2", "Brand new")
        self.assertEqual(c2.ceviriler.ozet("u1", ""), "TR Old summary.")
        self.assertEqual(c2.eskimis, 1)
        self.assertNotIn("u2", c2.ceviriler.basliklar)
        # Önbellekteki kayıt değişmedi: sonraki çalıştırma yeniden dener
        sahte = SahteCevirmen()
        cevirmen(c2.onbellek, sahte).ozet("u1", "Updated summary.")
        self.assertEqual(sahte.cagrilar, ["Updated summary."])

    def test_gecici_hatadan_sonra_tekrar_dener(self):
        class IkiKezHata(SahteCevirmen):
            def __init__(self):
                super().__init__()
                self.hata = 2

            def __call__(self, metin):
                if self.hata:
                    self.hata -= 1
                    raise OSError("429 Too Many Requests")
                return super().__call__(metin)

        c = cevirmen(sahte=IkiKezHata())
        c.baslik("u1", "Title")
        self.assertFalse(c.durdu)
        self.assertEqual(c.ceviriler.baslik("u1", ""), "TR Title")

    def test_turkce_kaynak_cevrilmeden_girer_ingilizcesi_gruplama_icin(self):
        sahte = SahteCevirmen()
        c = Cevirmen({}, SahteCevirmen(), 100, bekleme=0, ingilizceye_cevir=sahte)
        c.turkce_kaynak("u1", "Başlık", "Birinci cümle. İkinci cümle. Üçüncü cümle.")
        self.assertEqual(c.ceviriler.baslik("u1", ""), "Başlık")
        self.assertEqual(c.ceviriler.ozet("u1", ""), "Birinci cümle. İkinci cümle. Üçüncü cümle.")
        self.assertTrue(c.ceviriler.cevrildi_mi("u1"))
        self.assertEqual(c.ceviriler.ingilizceler["u1"], ("TR Başlık", "TR Birinci cümle. İkinci cümle."))
        # İkinci çalıştırma önbellekten
        ikinci = SahteCevirmen()
        c2 = Cevirmen(c.onbellek, SahteCevirmen(), 100, bekleme=0, ingilizceye_cevir=ikinci)
        c2.turkce_kaynak("u1", "Başlık", "Birinci cümle. İkinci cümle. Üçüncü cümle.")
        self.assertEqual(ikinci.cagrilar, [])
        self.assertIn("u1", c2.ceviriler.ingilizceler)

    def test_turkce_kaynak_google_yoksa_da_gosterilir(self):
        c = Cevirmen({}, SahteCevirmen(), 100, bekleme=0, ingilizceye_cevir=SahteCevirmen(hata_sonrasi=0))
        c.turkce_kaynak("u1", "Başlık", "Cümle.")
        self.assertTrue(c.ceviriler.cevrildi_mi("u1"))
        self.assertNotIn("u1", c.ceviriler.ingilizceler)

    def test_cagri_siniri(self):
        c = cevirmen(sinir=3)
        for i in range(5):
            c.baslik(f"u{i}", f"Title {i}")
        self.assertEqual(len(c.ceviriler.basliklar), 3)
        self.assertEqual(c.ceviriler.baslik("u4", "Title 4"), "Title 4")  # İngilizce kaldı

    def test_hata_olunca_durur(self):
        sahte = SahteCevirmen(hata_sonrasi=2)
        c = cevirmen(sahte=sahte)
        for i in range(5):
            c.baslik(f"u{i}", f"Title {i}")
        self.assertTrue(c.durdu)
        self.assertEqual(len(c.ceviriler.basliklar), 2)
        self.assertEqual(len(sahte.cagrilar), 2)  # durduktan sonra Google'a gidilmedi

    def test_kaydet_budar_ve_yukler(self):
        c = cevirmen()
        c.baslik("tut", "A")
        c.baslik("at", "B")
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "ceviri.json"
            onbellegi_kaydet(yol, c.onbellek, {"tut"})
            self.assertEqual(set(onbellegi_yukle(yol)), {"tut"})
            yol.write_text("bozuk", encoding="utf-8")
            self.assertEqual(onbellegi_yukle(yol), {})


def makale(i):
    return Makale("bbc.co.uk", f"Title {i}", f"https://x/{i}", f"Summary {i}.", "", "2026-09-24T12:00:00+0000")


class MarkaAdlari(unittest.TestCase):
    # Google'ın yer tutucuya verdiği gerçek çıktılar (teşhis, 30.09.2026).
    GOOGLE = {
        "The open-source AI platforms vying to become China’s X1Q":
            "Açık kaynaklı yapay zeka platformları Çin'in X1Q'su olmak için yarışıyor",
        "X1Q CEO Amodei to have dinner with Trump at White House":
            "X1Q CEO'su Amodei, Beyaz Saray'da Trump'la akşam yemeği yiyecek",
        "AMD buys Li Fei-Fei’s X1Q for US$8.2b, escalating rivalry with Nvidia":
            "AMD, Li Fei-Fei'nin X1Q'sunu 8,2 milyar dolara satın alarak Nvidia ile rekabeti artırıyor",
        "X1Q's new model beats OpenAI and X2Q rivals in a benchmark":
            "X1Q'nun yeni modeli, kıyaslamada OpenAI ve X2Q rakiplerini geride bırakıyor",
    }

    def cevir(self, metin):
        return self.GOOGLE.get(metin, "DÜZ " + metin)

    def test_ad_korunur_ek_okunusa_gore_cekimlenir(self):
        from markalar import markalari_koruyarak
        for ingilizce, beklenen in [
            ("The open-source AI platforms vying to become China’s Hugging Face",
             "Açık kaynaklı yapay zeka platformları Çin'in Hugging Face'i olmak için yarışıyor"),
            ("Anthropic CEO Amodei to have dinner with Trump at White House",
             "Anthropic CEO'su Amodei, Beyaz Saray'da Trump'la akşam yemeği yiyecek"),
            ("AMD buys Li Fei-Fei’s World Labs for US$8.2b, escalating rivalry with Nvidia",
             "AMD, Li Fei-Fei'nin World Labs'ını 8,2 milyar dolara satın alarak Nvidia ile rekabeti artırıyor"),
            ("Anthropic's new model beats OpenAI and Hugging Face rivals in a benchmark",
             "Anthropic'in yeni modeli, kıyaslamada OpenAI ve Hugging Face rakiplerini geride bırakıyor"),
        ]:
            self.assertEqual(markalari_koruyarak(ingilizce, self.cevir), beklenen)

    def test_ek_cekimi(self):
        from markalar import _ek_cekimle
        self.assertEqual(_ek_cekimle("da", "ik"), "te")  # Anthropic'te
        self.assertEqual(_ek_cekimle("dan", "eys"), "ten")  # Hugging Face'ten
        self.assertEqual(_ek_cekimle("da", "labz"), "da")  # World Labs'da
        self.assertEqual(_ek_cekimle("yla", "örld"), "le")  # Rest of World'le
        self.assertEqual(_ek_cekimle("ya", "örc"), "e")  # The Verge'e
        self.assertEqual(_ek_cekimle("su", "i"), "si")  # Bon Appétit'si

    def test_sirada_kullanim_korunmaz(self):
        from markalar import markali_mi
        for metin in ["Homemade Apple Butter", "The only thing more unwelcome in the Oval Office",
                      "Signal failure: how years of thin investment", "a rough surface of the moon",
                      "Three takeaways from the summit"]:
            self.assertFalse(markali_mi(metin), metin)
        self.assertTrue(markali_mi("Microsoft’s new Surface Mouse has haptic feedback"))

    def test_yer_tutucu_kaybolursa_duz_cevrilir(self):
        from markalar import markalari_koruyarak
        self.assertEqual(markalari_koruyarak("Hugging Face news", lambda m: "haberler"), "haberler")

    def test_markali_eski_ceviri_bir_kez_yenilenir(self):
        # Koruma gelmeden önce "Antropik" diye çevrilmiş başlık.
        ingilizce = "Anthropic CEO Amodei to have dinner with Trump at White House"
        from ceviri import _ozetle
        onbellek = {"u1": {"b": "Antropik CEO Amodei yemek yiyecek", "bh": _ozetle(ingilizce)}}
        c = Cevirmen(onbellek, self.cevir, 10, bekleme=0)
        c.baslik("u1", ingilizce)
        self.assertEqual(c.ceviriler.basliklar["u1"], "Anthropic CEO'su Amodei, Beyaz Saray'da Trump'la akşam yemeği yiyecek")
        self.assertEqual(c.yeni, 1)
        c2 = Cevirmen(onbellek, self.cevir, 10, bekleme=0)
        c2.baslik("u1", ingilizce)
        self.assertEqual(c2.yeni, 0)


class TurkceSayfa(unittest.TestCase):
    def setUp(self):
        self.makaleler = [makale(i) for i in range(10)]
        self.kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", self.makaleler)]}
        self.eski = [ArsivKaydi("Gündem", "bbc.co.uk", "Old title", "https://x/eski", "2026-09-23T10:00:00+0000", False,
                                "2026-09-23T10:00:00+0000")]

    def ceviriler(self, adet):
        c = Ceviriler()
        for m in self.makaleler[:adet]:
            c.basliklar[m.url] = "Başlık " + m.baslik
            c.ozetler[m.url] = "Özet " + m.ozet
        c.basliklar["https://x/eski"] = "Eski başlık"
        return c

    def test_cevrilmis_sayfa_turkce(self):
        html = sayfa.sayfa_olustur(self.kategoriler, self.eski, self.ceviriler(9))  # %90
        self.assertRegex(html, r'<html lang="tr" translate="no" data-dil="tr" data-uretim="\d+">')
        self.assertIn(">Başlık Title 0</a>", html)
        self.assertIn("<p>Özet Summary 0.</p>", html)
        self.assertIn(">Eski başlık</a>", html)
        self.assertNotIn('id="cevir-linki"', html)
        # Çevirisi alınamamış haber bu yayında hiç gösterilmez (İngilizce
        # kart çıkmaz); bir sonraki çalıştırmada çevrilip gelir.
        self.assertNotIn('data-url="https://x/9"', html)
        self.assertNotIn(">Title 9</a>", html)
        self.assertIn("9 haber", html)

    def test_turkce_kaynak_karti(self):
        tr = Makale("tr.euronews.com", "Türkçe başlık", "https://tr/1", "Türkçe özet.", "", "2026-09-24T12:00:00+0000")
        self.kategoriler["Gündem"].append(KaynakBolumu("tr.euronews.com", "", [tr]))
        c = self.ceviriler(10)
        c.basliklar[tr.url], c.ozetler[tr.url] = tr.baslik, tr.ozet
        html = sayfa.sayfa_olustur(self.kategoriler, self.eski, c)
        self.assertRegex(html, r'<article [^>]*data-url="https://tr/1" data-dil="tr">')
        # İngilizce (yedek) sayfada translate.goog'un dokunmaması için işaretli
        html = sayfa.sayfa_olustur(self.kategoriler, self.eski, Ceviriler())
        self.assertRegex(html, r'<article [^>]*data-url="https://tr/1" data-dil="tr" lang="tr" translate="no">')
        self.assertIn(">Türkçe başlık</a>", html)

    def test_cevirinin_cogu_yoksa_ingilizce_sayfa(self):
        html = sayfa.sayfa_olustur(self.kategoriler, self.eski, self.ceviriler(4))  # %40 < %50
        self.assertRegex(html, r'<html lang="en" data-uretim="\d+">')
        self.assertIn(">Title 0</a>", html)
        self.assertNotIn(">Başlık Title", html)
        self.assertNotIn(">Eski başlık<", html)
        self.assertIn('id="cevir-linki"', html)


if __name__ == "__main__":
    unittest.main()
