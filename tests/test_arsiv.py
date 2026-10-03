""""Older news" arşivinin (scripts/arsiv.py) ve sayfadaki listesinin testleri.

Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sayfa  # noqa: E402
from arsiv import arsivi_guncelle, arsivi_kaydet, arsivi_yukle, eski_haberler  # noqa: E402
from model import ArsivKaydi, KaynakBolumu, Makale  # noqa: E402

SIMDI = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)


def makale(url: str, tarih: str, baslik: str = "Başlık", kaynak: str = "bbc.co.uk") -> Makale:
    return Makale(kaynak, baslik, url, "Özet.", "", tarih)


def kayit(url: str, tarih: str, kategori: str = "Gündem", kaynak: str = "bbc.co.uk", eklendi: str = "") -> ArsivKaydi:
    return ArsivKaydi(kategori, kaynak, "Eski başlık", url, tarih, False, eklendi or tarih)


class ArsivGuncelleme(unittest.TestCase):
    def test_sayfadakiler_eklenir_eskiler_korunur(self):
        onceki = [kayit("https://x/eski", "2026-09-22T08:00:00+0000")]
        kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", [makale("https://x/yeni", "2026-09-24T10:00:00+0000")])]}
        arsiv = arsivi_guncelle(onceki, kategoriler, SIMDI)
        self.assertEqual([k.url for k in arsiv], ["https://x/yeni", "https://x/eski"])

    def test_yedi_gunden_eskiler_duser(self):
        onceki = [
            kayit("https://x/6gun", "2026-09-18T13:00:00+0000"),
            kayit("https://x/8gun", "2026-09-16T12:00:00+0000"),
        ]
        arsiv = arsivi_guncelle(onceki, {}, SIMDI)
        self.assertEqual([k.url for k in arsiv], ["https://x/6gun"])

    def test_tarihsiz_haberin_suresi_eklenme_anina_gore(self):
        onceki = [
            kayit("https://x/yeni", "", eklendi="2026-09-23T12:00:00+0000"),
            kayit("https://x/eski", "", eklendi="2026-09-10T12:00:00+0000"),
        ]
        arsiv = arsivi_guncelle(onceki, {}, SIMDI)
        self.assertEqual([k.url for k in arsiv], ["https://x/yeni"])

    def test_tekrar_gorulen_haber_guncellenir_eklenme_ani_korunur(self):
        onceki = [kayit("https://x/a", "2026-09-23T08:00:00+0000", eklendi="2026-09-23T08:30:00+0000")]
        kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", [makale("https://x/a", "2026-09-23T08:00:00+0000", "Yeni başlık")])]}
        (k,) = arsivi_guncelle(onceki, kategoriler, SIMDI)
        self.assertEqual((k.baslik, k.eklendi), ("Yeni başlık", "2026-09-23T08:30:00+0000"))

    def test_eski_haberler_sayfadakileri_ve_kaldirilan_kaynaklari_disarida_birakir(self):
        arsiv = [
            kayit("https://x/sayfada", "2026-09-24T10:00:00+0000"),
            kayit("https://x/dustu", "2026-09-23T10:00:00+0000"),
            kayit("https://x/kaldirildi", "2026-09-23T09:00:00+0000", kaynak="eskikaynak.com"),
        ]
        kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", [makale("https://x/sayfada", "2026-09-24T10:00:00+0000")])]}
        self.assertEqual([k.url for k in eski_haberler(arsiv, kategoriler)], ["https://x/dustu"])

    def test_kaydet_yukle_ve_bozuk_dosya(self):
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / "arsiv.json"
            kayitlar = [kayit("https://x/a", "2026-09-23T10:00:00+0000")]
            arsivi_kaydet(yol, kayitlar)
            self.assertEqual(arsivi_yukle(yol), kayitlar)
            yol.write_text("bozuk", encoding="utf-8")
            self.assertEqual(arsivi_yukle(yol), [])
            self.assertEqual(arsivi_yukle(Path(klasor) / "yok.json"), [])


    def test_eski_haberlerde_ayni_haberin_ikinci_adresi_gosterilmez(self):
        # TechCrunch aynı haberi yazım hatası düzeltilmiş ikinci bir
        # adresle de yayımlıyor; DW aynı yazıyı iki adresle veriyor.
        def k(url, baslik, tarih, kaynak="techcrunch.com"):
            return ArsivKaydi("Teknoloji", kaynak, baslik, url, tarih, False, tarih)
        arsiv = [
            k("https://x/1", "OpenAI reportedly in talks to raise $30B round at $1.4T valuation", "2026-09-23T19:52:00+0000"),
            k("https://x/2", "OpenAI repotedly in talks to raise $30B round at $1.4T valuation", "2026-09-23T19:50:00+0000"),
            # Başka kaynaktaki aynı başlık ayrı haberdir (olaylar.py birleştirir).
            k("https://y/1", "OpenAI reportedly in talks to raise $30B round at $1.4T valuation",
              "2026-09-23T18:00:00+0000", kaynak="theverge.com"),
            # Sayfadaki kartın eski kopyası.
            k("https://x/3", "Anthropic releases Sonnet 5.5, a cheaper work partner", "2026-09-23T10:00:00+0000"),
            # Benzer kalıplı ama ayrı haber.
            k("https://x/4", "OpenAI launches Dots, its bubbly agentic avatar", "2026-09-23T09:00:00+0000"),
        ]
        kategoriler = {"Teknoloji": [
            KaynakBolumu("techcrunch.com", "", [makale(
                "https://x/5", "2026-09-23T11:00:00+0000", "Anthropic releases Sonnet 5.5, a much cheaper work partner",
                kaynak="techcrunch.com")]),
            KaynakBolumu("theverge.com", "", []),
        ]}
        self.assertEqual([k.url for k in eski_haberler(arsiv, kategoriler)], ["https://x/1", "https://y/1", "https://x/4"])


class ArsivSayfasi(unittest.TestCase):
    def test_gunlere_ayrilir_ve_sayilar_veride(self):
        kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", [])]}
        eski = [
            kayit("https://x/b", "2026-09-23T21:30:00+0000"),  # TR: 24 Eylül 00:30
            kayit("https://x/a", "2026-09-23T10:00:00+0000"),  # TR: 23 Eylül 13:00
        ]
        html = sayfa.sayfa_olustur(kategoriler, eski)
        self.assertIn('var KATEGORI_VERISI = {"Gündem": [["bbc.co.uk", 0, 2, 0]]};', html)
        # Gün başlıkları Türkçe ve lang="tr" (büyük harfte "İ" doğru çıksın).
        self.assertLess(html.index('<h2 lang="tr" data-etiket="Perşembe, 24 Eylül">'),
                        html.index('<h2 lang="tr" data-etiket="Çarşamba, 23 Eylül">'))
        self.assertIn('<a href="https://x/b" target="_blank" rel="noopener">Eski başlık</a>', html)
        self.assertIn('<span class="arsiv-bilgi" data-etiket="00:30 · bbc.co.uk"></span>', html)
        self.assertIn('data-gorunum="eski"', html)

    def test_turkce_sayfada_liste_ayri_dosyada(self):
        from model import Ceviriler
        haber = Makale("bbc.co.uk", "Başlık", "https://x/yeni", "Özet.", "", "2026-09-24T10:00:00+0000")
        kategoriler = {"Gündem": [KaynakBolumu("bbc.co.uk", "", [haber])]}
        ceviri = Ceviriler({haber.url: "Başlık"}, {haber.url: "Özet."})
        eski = [kayit("https://x/a", "2026-09-23T10:00:00+0000")]
        with tempfile.TemporaryDirectory() as d:
            html = sayfa.sayfa_olustur(kategoriler, eski, ceviri, arsiv_klasoru=Path(d))
            parca = (Path(d) / sayfa.ARSIV_PARCASI).read_text(encoding="utf-8")
        self.assertRegex(html, r'<div class="arsiv" id="arsiv" data-kaynak="eski\.html\?v=[0-9]+" hidden>')
        self.assertNotIn("https://x/a", html)
        self.assertIn('<a href="https://x/a" target="_blank" rel="noopener">Eski başlık</a>', parca)
        # İngilizce (yedek) sayfada liste sayfada kalır (translate.goog çevirsin).
        with tempfile.TemporaryDirectory() as d:
            ingilizce = sayfa.sayfa_olustur(kategoriler, eski, arsiv_klasoru=Path(d))
        self.assertIn("https://x/a", ingilizce)


if __name__ == "__main__":
    unittest.main()


class EtiketleAyiklanan(unittest.TestCase):
    def test_etiketle_atlanan_yazinin_adresi_kaydedilir(self):
        # Arşiv kayıtlarında etiket yok; etiketiyle atlanan yazı (Guardian'ın
        # İngiltere içi gezi yazısı) arşivden adresiyle çıkarılır.
        from unittest import mock

        import haber_uret
        from takip import Takip

        ingiltere = "https://www.theguardian.com/travel/2026/sep/27/15-great-cottages-uk"
        helsinki = "https://www.theguardian.com/travel/2026/sep/28/helsinki-subterranean-city"
        sayfalar = {
            ingiltere: {"baslik": "15 great cottages", "govde": "Cosy cottages. Log fires.", "gorsel": "",
                        "tarih": "2026-09-27T06:00:00+0000", "etiketler": ["travel", "united kingdom holidays"]},
            helsinki: {"baslik": "Helsinki’s subterranean city", "govde": "Dive in. Swim below.", "gorsel": "",
                       "tarih": "2026-09-28T06:00:00+0000", "etiketler": ["travel", "finland holidays"]},
        }
        ayiklanan: set[str] = set()
        with mock.patch.object(haber_uret, "besleme_ogeleri", return_value=([ingiltere, helsinki], {})), \
             mock.patch.object(haber_uret, "makale_getir", side_effect=lambda url: sayfalar[url]), \
             mock.patch.object(haber_uret, "_cok_eski_mi", return_value=False):
            makaleler = haber_uret.kaynak_haberleri("Gezi", "theguardian.com", "https://x/rss", Takip({}, SIMDI),
                                                    ayiklanan)
        self.assertEqual([m.url for m in makaleler], [helsinki])
        self.assertIn(ingiltere, ayiklanan)
        self.assertNotIn(helsinki, ayiklanan)


class KaynakSayisi(unittest.TestCase):
    def test_kategoriye_ozel_sayi(self):
        # SCMP Gündem'de 6, Sanat & Kültür'de kategori/genel sayı.
        from unittest import mock

        import haber_uret
        from takip import Takip

        urls = [f"https://www.scmp.com/news/china/article/{i}" for i in range(20)]
        sayfa_ = {"baslik": "", "govde": "First. Second.", "gorsel": "", "tarih": "", "etiketler": []}

        konular = ["Beijing trade", "Tokyo floods", "Manila election", "Seoul defectors", "Jakarta budget",
                   "Hanoi exports", "Delhi smog", "Taipei chips", "Bangkok protests", "Dhaka garments",
                   "Kathmandu quake", "Colombo debt", "Kabul aid", "Yangon junta", "Ulaanbaatar mining",
                   "Phnom Penh casinos", "Vientiane dams", "Karachi port", "Busan shipyard", "Osaka expo"]

        def getir(url):
            return dict(sayfa_, baslik=f"{konular[int(url.rsplit('/', 1)[1])]} dominate regional headlines")

        with mock.patch.object(haber_uret, "besleme_ogeleri", return_value=(urls, {})), \
             mock.patch.object(haber_uret, "makale_getir", side_effect=getir):
            gundem = haber_uret.kaynak_haberleri("Gündem", "scmp.com", "https://x", Takip({}, SIMDI))
            sanat = haber_uret.kaynak_haberleri("Sanat & Kültür", "scmp.com", "https://x", Takip({}, SIMDI))
        self.assertEqual(len(gundem), 6)
        self.assertEqual(len(sanat), haber_uret.N)
