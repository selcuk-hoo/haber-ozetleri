"""Piyasa sekmesi (scripts/piyasa.py) testleri. Ağa gidilmiyor.

Çalıştırma: python -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import piyasa  # noqa: E402
import sayfa  # noqa: E402
from model import Ceviriler, KaynakBolumu, Makale  # noqa: E402

SIMDI = datetime(2026, 10, 29, 12, 45, tzinfo=timezone.utc)  # 15:45 Türkiye

# 29.10.2026'da GitHub'ın sunucusunda alınan gerçek biçimler (kısaltılmış).
TRUNCGIL = {
    "Update_Date": "2026-10-29 15:30:03",
    "USD": {"Buying": "49,8316", "Type": "Currency", "Selling": "49,8438", "Change": "%0,00"},
    "EUR": {"Buying": "55,6417", "Type": "Currency", "Selling": "55,6534", "Change": "%0,14"},
    "ons": {"Buying": "$4.025,11", "Type": "Gold", "Selling": "$4.025,73", "Change": "%-1,03"},
    "gram-altin": {"Buying": "6.449,49", "Type": "Gold", "Selling": "6.450,49", "Change": "%-1,03"},
    "ceyrek-altin": {"Buying": "10.392,68", "Type": "Gold", "Selling": "10.632,48", "Change": "%0,00"},
    "tam-altin": {"Buying": "41.570,74", "Type": "Gold", "Selling": "42.399,85", "Change": "%0,00"},
}


def yahoo_cevabi(fiyat, kapanislar, zaman=1793277262):
    return json.dumps({"chart": {"result": [{
        "meta": {"regularMarketPrice": fiyat, "regularMarketTime": zaman},
        "indicators": {"quote": [{"close": kapanislar}]}}]}})


def sahte_getir(truncgil=TRUNCGIL, yahoo_hata=()):
    def getir(adres):
        if "truncgil" in adres:
            if truncgil is None:
                raise OSError("503")
            return json.dumps(truncgil)
        for simge in yahoo_hata:
            if simge in adres:
                raise OSError("429")
        if "XU100" in adres:
            return yahoo_cevabi(11165.44, [10900.0, 11000.0, None, 11165.44])
        if "BZ=F" in adres:
            return yahoo_cevabi(110.66, [108.0, 110.0, 110.66])
        if "USDTRY" in adres:
            return yahoo_cevabi(49.8347, [49.7, 49.8, 49.8347])
        if "EURTRY" in adres:
            return yahoo_cevabi(55.6493, [55.5, 55.6, 55.6493])
        raise AssertionError(adres)
    return getir


class Sayilar(unittest.TestCase):
    def test_turkce_sayi_okunur_ve_yazilir(self):
        self.assertEqual(piyasa.sayi_tr("49,8316"), 49.8316)
        self.assertEqual(piyasa.sayi_tr("6.449,49"), 6449.49)
        self.assertEqual(piyasa.sayi_tr("$4.025,11"), 4025.11)
        self.assertEqual(piyasa.sayi_tr("%-1,03"), -1.03)
        self.assertEqual(piyasa.sayi_yaz(49.8316, 4), "49,8316")
        self.assertEqual(piyasa.sayi_yaz(41570.74, 2), "41.570,74")


class Kaynaklar(unittest.TestCase):
    def test_truncgil_ve_yahoo_ayrisir(self):
        g = piyasa.topla(sahte_getir())
        self.assertEqual(set(g), {"usd", "eur", "gram", "ceyrek", "tam", "bist100", "brent"})
        self.assertEqual((g["gram"]["alis"], g["gram"]["satis"], g["gram"]["degisim"]), (6449.49, 6450.49, -1.03))
        self.assertEqual(g["tam"]["alis"], 41570.74)
        self.assertEqual(g["usd"]["zaman"], "2026-10-29T15:30:03+03:00")
        # Yahoo: değişim, son çubuk (bugün) ile bir öncekinin farkı; boş çubuk atlanır.
        self.assertAlmostEqual(g["bist100"]["degisim"], (11165.44 - 11000.0) / 11000.0 * 100)
        self.assertIsNone(g["bist100"]["satis"])

    def test_truncgil_dusunce_dolar_euro_yahoodan_altin_eski_kalir(self):
        with contextlib.redirect_stderr(io.StringIO()):
            g = piyasa.topla(sahte_getir(truncgil=None))
        self.assertEqual(set(g), {"usd", "eur", "bist100", "brent"})
        self.assertEqual(g["usd"]["kaynak"], "Yahoo Finance")

    def test_yahoo_dusunce_ote_kodlar_gelir(self):
        with contextlib.redirect_stderr(io.StringIO()):
            g = piyasa.topla(sahte_getir(yahoo_hata=("XU100",)))
        self.assertNotIn("bist100", g)
        self.assertIn("brent", g)


class Kayit(unittest.TestCase):
    def guncelle(self, kayit, gunluk, g, simdi):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return piyasa.guncelle(kayit, gunluk, g, simdi)

    def test_gunluk_ortalama_ve_ayni_zaman_damgasi_tekrar_sayilmaz(self):
        g = piyasa.topla(sahte_getir())
        kayit, gunluk = self.guncelle({}, {}, g, SIMDI)
        gun = gunluk["gunler"]["2026-10-29"]
        self.assertEqual(gun["gram"]["alis"]["n"], 1)
        self.assertEqual(gun["gram"]["satis"]["ort"], 6450.49)
        self.assertNotIn("satis", gun["bist100"])
        # Aynı kaynak zamanı: örnek eklenmez.
        kayit, gunluk = self.guncelle(kayit, gunluk, g, SIMDI + timedelta(hours=1))
        self.assertEqual(gunluk["gunler"]["2026-10-29"]["gram"]["alis"]["n"], 1)
        # Yeni zaman damgası: ortalama, min, max, ilk, son güncellenir.
        yeni = json.loads(json.dumps(TRUNCGIL))
        yeni["Update_Date"] = "2026-10-29 16:30:03"
        yeni["gram-altin"]["Buying"] = "6.500,00"
        kayit, gunluk = self.guncelle(kayit, gunluk, piyasa.topla(sahte_getir(yeni)), SIMDI + timedelta(hours=2))
        g_ist = gunluk["gunler"]["2026-10-29"]["gram"]["alis"]
        self.assertEqual((g_ist["n"], g_ist["min"], g_ist["max"], g_ist["ilk"], g_ist["son"]),
                         (2, 6449.49, 6500.0, 6449.49, 6500.0))
        self.assertAlmostEqual(g_ist["ort"], (6449.49 + 6500.0) / 2, places=2)

    def test_gun_turkiye_saatine_gore_degisir_eski_gunler_kalir(self):
        g = piyasa.topla(sahte_getir())
        kayit, gunluk = self.guncelle({}, {}, g, datetime(2026, 10, 29, 20, 30, tzinfo=timezone.utc))  # 23:30 TR
        yeni = json.loads(json.dumps(TRUNCGIL))
        yeni["Update_Date"] = "2026-10-30 00:10:00"
        kayit, gunluk = self.guncelle(kayit, gunluk, piyasa.topla(sahte_getir(yeni)),
                                      datetime(2026, 10, 29, 21, 15, tzinfo=timezone.utc))  # 00:15 TR
        self.assertEqual(sorted(gunluk["gunler"]), ["2026-10-29", "2026-10-30"])

    def test_bozuk_deger_ve_sicrama_alinmaz_eski_deger_kalir(self):
        g = piyasa.topla(sahte_getir())
        kayit, gunluk = self.guncelle({}, {}, g, SIMDI)
        bozuk = json.loads(json.dumps(TRUNCGIL))
        bozuk["Update_Date"] = "2026-10-29 16:30:03"
        bozuk["gram-altin"]["Buying"] = "64,49"  # %99 düşüş: virgül kayması
        bozuk["EUR"]["Buying"] = "0,00"
        kayit, gunluk = self.guncelle(kayit, gunluk, piyasa.topla(sahte_getir(bozuk)), SIMDI + timedelta(hours=1))
        self.assertEqual(kayit["degerler"]["gram"]["alis"], 6449.49)
        self.assertEqual(kayit["degerler"]["eur"]["alis"], 55.6417)

    def test_hic_veri_alinamazsa_onceki_kalir_uc_saat_sonra_bayat(self):
        kayit, gunluk = self.guncelle({}, {}, piyasa.topla(sahte_getir()), SIMDI)
        self.assertFalse(kayit["bayat"])
        kayit2, _ = self.guncelle(kayit, gunluk, {}, SIMDI + timedelta(hours=2))
        self.assertFalse(kayit2["bayat"])
        self.assertEqual(kayit2["zaman"], kayit["zaman"])
        kayit3, _ = self.guncelle(kayit2, gunluk, {}, SIMDI + timedelta(hours=4))
        self.assertTrue(kayit3["bayat"])
        self.assertEqual(kayit3["degerler"]["usd"]["alis"], 49.8316)

    def test_dosya_gidis_gelis(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "piyasa.json"
            self.assertEqual(piyasa.yukle(yol, {}), {})
            piyasa.kaydet(yol, {"zaman": "x", "degerler": {}})
            self.assertEqual(piyasa.yukle(yol, {})["zaman"], "x")


class Sayfa(unittest.TestCase):
    def sayfa(self, kayit, turkce=True):
        m = Makale("bbc.co.uk", "Title", "https://b/1", "Summary.", "", "2026-10-29T10:00:00+0000")
        ceviri = Ceviriler(basliklar={m.url: "Başlık"}, ozetler={m.url: "Özet."}) if turkce else None
        return sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "", [m])]}, [], ceviri, piyasa=kayit)

    def kayit(self, g=None):
        with contextlib.redirect_stdout(io.StringIO()):
            return piyasa.guncelle({}, {}, g or piyasa.topla(sahte_getir()), SIMDI)[0]

    def test_sekme_ve_degerler(self):
        html = self.sayfa(self.kayit())
        self.assertIn('id="piyasa" data-kategori="Piyasa"', html)
        self.assertIn('class="kategori-buton piyasa-buton"', html)
        # Başlıkta kaynakların en yeni zamanı (Yahoo 15:34), çekim anı (15:45) değil.
        self.assertIn("Piyasa · 29 Ekim 15:34 itibarıyla", html)
        self.assertIn("49,8316 ₺", html)
        self.assertIn("6.449,49 ₺", html)
        self.assertIn("6.450,49 ₺", html)  # satış
        self.assertIn("41.570,74 ₺", html)
        self.assertIn("11.165,44 puan", html)
        self.assertIn("$110,66", html)
        self.assertIn('<span class="piyasa-degisim piyasa-azal">▼ %1,03</span>', html)
        self.assertIn('<span class="piyasa-degisim piyasa-art">▲ %0,14</span>', html)
        self.assertIn("yatırım tavsiyesi değildir", html)

    def test_sekme_yalniz_turkce_sayfada_ve_veri_varsa(self):
        self.assertNotIn('id="piyasa"', self.sayfa(self.kayit(), turkce=False))
        self.assertNotIn('id="piyasa"', self.sayfa({}))
        self.assertNotIn('id="piyasa"', self.sayfa(None))

    def test_eski_deger_kendi_zamanini_yazar_bayat_uyarisi(self):
        g = piyasa.topla(sahte_getir())
        g["bist100"]["zaman"] = "2026-10-27T18:10:00+03:00"  # iki gün önceki kapanış
        kayit = self.kayit(g)
        html = self.sayfa(dict(kayit, bayat=True))
        self.assertIn("27 Ekim 18:10", html)
        self.assertIn("ulaşılamıyor", html)
        self.assertNotIn("ulaşılamıyor", self.sayfa(kayit))


if __name__ == "__main__":
    unittest.main()
