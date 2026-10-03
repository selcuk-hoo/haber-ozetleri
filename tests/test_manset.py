"""Manşet (scripts/manset.py) testleri. Claude'a gidilmiyor; puanlama ve
derleme sahte fonksiyonla.

Çalıştırma: python -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import manset  # noqa: E402
import sayfa  # noqa: E402
from model import Ceviriler, KaynakBolumu, Makale  # noqa: E402

# 3 Ekim 05:30 UTC = 08:30 Türkiye saati: son baskı 3 Ekim 08:00 (sabah).
SABAH = datetime(2026, 10, 3, 5, 30, tzinfo=timezone.utc)
AKSAM = datetime(2026, 10, 3, 14, 10, tzinfo=timezone.utc)  # 17:10 TR


def m(kaynak, baslik, ozet="The report gives details. More follows in the text today."):
    return Makale(kaynak, baslik, f"https://{kaynak}/{abs(hash(baslik))}", ozet, "", "2026-10-02T10:00:00+0000")


# Yerel ama çok yazılan olay (03.10.2026: Christa Pike) ve gerçekten önemli olay (G7).
A, B, C = m("aljazeera.com", "Pike execution stabbed"), m("bbc.co.uk", "Pike stab survives"), m("dw.com/tr", "Pike bıçak")
D, E = m("aa.com.tr", "G7 agrees oil release"), m("npr.org", "G7 to release oil")


def kategoriler(*makaleler):
    return {"Gündem": [KaynakBolumu("x", "", list(makaleler))]}


def gruplar(*gruplar_):
    return {("Gündem", g[0].url): list(g[1:]) for g in gruplar_}


def sahte_uret(cagrilar, dusuk=("stab", "bıçak")):
    """Puanlamada içinde `dusuk` kelimesi geçen olaylara her kıstasta 2,
    ötekilere 8 verir; derlemede her olaya bir derleme yazar."""
    def uret(sistem, girdi):
        cagrilar.append((sistem, girdi))
        bloklar = re.split(r"\n\n(?=Olay g)", girdi)
        if sistem == manset.PUAN_TALIMATI:
            def p(blok):
                n = 2 if any(k in blok for k in dusuk) else 8
                return {**{k: n for k in manset.KISTASLAR}, "gerekce": "g"}
            return json.dumps({f"g{i}": p(b) for i, b in enumerate(bloklar)})
        return "```json\n" + json.dumps({
            f"g{i}": {"baslik": f"Başlık {i}", "ozet": "Al Jazeera'ya göre G7 anlaştı ve petrol salınacak. " * 2}
            for i in range(len(bloklar))}, ensure_ascii=False) + "\n```"
    return uret


def derlemeler(cagrilar):
    return [g for s, g in cagrilar if s == manset.TALIMAT]


class Baski(unittest.TestCase):
    def test_baski_ani_ve_etiketi(self):
        self.assertEqual(manset.baski_ani(SABAH).isoformat(), "2026-10-03T08:00:00+03:00")
        self.assertEqual(manset.baski_ani(AKSAM).isoformat(), "2026-10-03T17:00:00+03:00")
        gece = datetime(2026, 10, 3, 2, 0, tzinfo=timezone.utc)  # 05:00 TR
        self.assertEqual(manset.baski_ani(gece).isoformat(), "2026-10-02T17:00:00+03:00")
        self.assertEqual(manset.etiket({"baski": "2026-10-03T08:00:00+03:00"}), "3 Ekim · sabah baskısı")
        self.assertEqual(manset.etiket({"baski": "2026-10-02T17:00:00+03:00"}), "2 Ekim · akşam baskısı")


class Kayit(unittest.TestCase):
    def test_gruplar_birlesir_ilk_gorulme_korunur(self):
        kayit = {}
        tum = kategoriler(A, B, C, D, E)
        manset.olaylari_kaydet(kayit, gruplar([A, B]), tum, SABAH)
        manset.olaylari_kaydet(kayit, gruplar([A, B, C], [D, E]), tum, SABAH + timedelta(hours=1))
        olaylar = sorted(kayit["olaylar"], key=lambda o: len(o["uyeler"]))
        self.assertEqual([len(o["uyeler"]) for o in olaylar], [2, 3])
        self.assertEqual(olaylar[1]["ilk"], SABAH.isoformat())
        self.assertEqual(olaylar[1]["son"], (SABAH + timedelta(hours=1)).isoformat())

    def test_baska_kategori_alinmaz_eskiler_duser(self):
        eski = (SABAH - timedelta(days=4)).isoformat()
        kayit = {"olaylar": [{"ilk": eski, "son": eski, "uyeler": []}], "denemeler": {eski: 1}}
        tum = {"Teknoloji": [KaynakBolumu("x", "", [A, B])]}
        manset.olaylari_kaydet(kayit, {("Teknoloji", A.url): [B]}, tum, SABAH)
        self.assertEqual(kayit, {"olaylar": [], "denemeler": {}})

    def test_adaylar_son_24_saat_en_az_iki_kaynak(self):
        def olay(saat_once, kaynaklar):
            an = (SABAH - timedelta(hours=saat_once)).isoformat()
            return {"ilk": an, "son": an, "uyeler": [{"kaynak": k} for k in kaynaklar]}
        olaylar = [olay(2, "ab"), olay(5, "abc"), olay(30, "abcd"), olay(1, "a")]
        secilen = manset.adaylar(olaylar, manset.baski_ani(SABAH))
        self.assertEqual([len(o["uyeler"]) for o in secilen], [3, 2])


class Puanlama(unittest.TestCase):
    def test_agirlikli_ortalama(self):
        self.assertAlmostEqual(sum(manset.MANSET_AGIRLIKLAR.values()), 1)
        p = {"etki": 8, "kalicilik": 6, "donum": 4, "eylem": 10, "turkiye": 0}
        self.assertAlmostEqual(manset.puan(p), round(8 * .32 + 6 * .27 + 4 * .18 + 10 * .13, 2))
        # Türkiye'ye yakınlık %10.
        self.assertAlmostEqual(manset.puan({**p, "turkiye": 10}) - manset.puan(p), 1.0)

    def test_cevap_sinirlanir_eksik_olay_none(self):
        olay = {"uyeler": [manset._uye(A), manset._uye(B)]}
        cevap = json.dumps({"g0": {"etki": 14, "kalicilik": -3, "donum": "5", "eylem": 5, "turkiye": 0,
                                   "gerekce": "yerel"}, "g1": {"etki": 5}})
        sonuc = manset.puanla([olay, olay], lambda s, g: cevap)
        self.assertEqual((sonuc[0]["etki"], sonuc[0]["kalicilik"], sonuc[0]["gerekce"]), (10, 0, "yerel"))
        self.assertIsNone(sonuc[1])
        with self.assertRaises(ValueError):
            manset.puanla([olay], lambda s, g: '{"g0": {}}')


class Derleme(unittest.TestCase):
    def olay(self):
        return {"uyeler": [manset._uye(D), manset._uye(E)]}

    def test_cevap_ayiklanir_kaynaklar_baglanir(self):
        cagrilar = []
        sonuc = manset.derle([self.olay()], sahte_uret(cagrilar))
        self.assertEqual(sonuc[0]["baslik"], "Başlık 0")
        self.assertEqual([k["ad"] for k in sonuc[0]["kaynaklar"]], ["aa.com.tr", "npr.org"])
        self.assertIn("[aa.com.tr] G7 agrees oil release", cagrilar[0][1])

    def test_kullanilamayan_cevap_hata(self):
        for cevap in ("Üzgünüm", '{"g0": {"baslik": "", "ozet": "kısa"}}', '{"g5": {}}'):
            with self.assertRaises(ValueError):
                manset.derle([self.olay()], lambda s, g, c=cevap: c)


class Guncelle(unittest.TestCase):
    def guncelle(self, kayit, ozet, simdi, gruplar_, tum, **kw):
        with contextlib.redirect_stderr(io.StringIO()):
            return manset.guncelle(kayit, ozet, simdi, gruplar_, tum, **kw)

    def test_cok_yazilan_ama_yerel_olay_manset_olmaz(self):
        kayit, cagrilar = {}, []
        ozet = self.guncelle(kayit, None, SABAH, gruplar([A, B, C], [D, E]), kategoriler(A, B, C, D, E),
                             uret=sahte_uret(cagrilar))
        self.assertEqual(ozet["baski"], "2026-10-03T08:00:00+03:00")
        self.assertEqual([len(o["kaynaklar"]) for o in ozet["olaylar"]], [2])
        self.assertEqual(ozet["olaylar"][0]["puan"], 8.0)
        self.assertEqual(sorted(p["puan"] for p in ozet["puanlar"]), [2.0, 8.0])
        self.assertEqual(derlemeler(cagrilar)[0].count("Olay g"), 1)
        self.assertEqual(manset.gosterilecek(ozet, SABAH), ozet)

    def test_ayni_baski_yeniden_hazirlanmaz_sonraki_baski_hazirlanir(self):
        kayit, cagrilar = {}, []
        tum = kategoriler(D, E)
        ozet = self.guncelle(kayit, None, SABAH, gruplar([D, E]), tum, uret=sahte_uret(cagrilar))
        ozet2 = self.guncelle(kayit, ozet, SABAH + timedelta(hours=1), gruplar([D, E]), tum, uret=sahte_uret(cagrilar))
        self.assertIs(ozet2, ozet)
        self.assertEqual(len(cagrilar), 2)  # puanlama + derleme
        aksam = self.guncelle(kayit, ozet, AKSAM, gruplar([D, E]), tum, uret=sahte_uret(cagrilar))
        self.assertEqual(aksam["baski"], "2026-10-03T17:00:00+03:00")
        self.assertEqual(len(cagrilar), 4)
        # Denemede zorla ve yöntem (sürüm) değişince yeniden hazırlanır.
        self.guncelle(kayit, aksam, AKSAM, {}, tum, zorla=True, uret=sahte_uret(cagrilar))
        eski = {k: v for k, v in aksam.items() if k != "surum"}
        self.guncelle(kayit, eski, AKSAM, {}, tum, uret=sahte_uret(cagrilar))
        self.assertEqual(len(cagrilar), 8)

    def test_esigi_gecen_yoksa_manset_yok_derleme_yapilmaz(self):
        cagrilar = []
        ozet = self.guncelle({}, None, SABAH, gruplar([A, B, C]), kategoriler(A, B, C), uret=sahte_uret(cagrilar))
        self.assertEqual(ozet["olaylar"], [])
        self.assertEqual(derlemeler(cagrilar), [])
        self.assertIsNone(manset.gosterilecek(ozet, SABAH))

    def test_en_fazla_uc_olay(self):
        olaylar_ = [[m(f"k{i}.com", f"Olay {i} G7"), m(f"l{i}.com", f"Olay {i} G7")] for i in range(5)]
        tum = kategoriler(*[x for g in olaylar_ for x in g])
        ozet = self.guncelle({}, None, SABAH, gruplar(*olaylar_), tum, uret=sahte_uret([]))
        self.assertEqual(len(ozet["olaylar"]), manset.MANSET_EN_FAZLA)

    def test_kapali_ise_claude_cagrilmaz(self):
        cagrilar = []
        ozet = self.guncelle({}, None, SABAH, gruplar([D, E]), kategoriler(D, E), kapali=True, uret=sahte_uret(cagrilar))
        self.assertIsNone(ozet)
        self.assertEqual(cagrilar, [])

    def test_hata_olursa_manset_yok_en_fazla_uc_deneme(self):
        def hata(sistem, girdi):
            raise RuntimeError("limit")

        kayit = {}
        for i in range(5):
            ozet = self.guncelle(kayit, None, SABAH + timedelta(minutes=i * 5), gruplar([D, E]), kategoriler(D, E),
                                 uret=hata)
        self.assertIsNone(ozet)
        self.assertEqual(kayit["denemeler"], {"2026-10-03T08:00:00+03:00": manset.EN_FAZLA_DENEME})

    def test_eski_baski_36_saate_kadar_gosterilir(self):
        ozet = {"baski": "2026-10-03T08:00:00+03:00", "olaylar": [{"baslik": "b", "ozet": "o", "kaynaklar": []}]}
        self.assertEqual(manset.gosterilecek(ozet, SABAH + timedelta(hours=30)), ozet)
        self.assertIsNone(manset.gosterilecek(ozet, SABAH + timedelta(hours=40)))
        self.assertIsNone(manset.gosterilecek(None, SABAH))

    def test_dosya_gidis_donus(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "x.json"
            manset.kaydet(yol, {"baski": "x"})
            self.assertEqual(manset.yukle(yol), {"baski": "x"})
            self.assertEqual(manset.yukle(Path(d) / "yok.json"), {})


class Sayfa(unittest.TestCase):
    OZET = {"baski": "2026-10-03T08:00:00+03:00", "olaylar": [
        {"baslik": "G7 <anlaştı>", "ozet": "Metin.", "kaynaklar": [{"ad": "bbc.co.uk", "url": "https://b/1"}]}]}

    def sayfa(self, ozet):
        haber = m("bbc.co.uk", "Başlık")
        ceviri = Ceviriler({haber.url: "Başlık"}, {haber.url: "Özet."})
        return sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "", [haber])]}, ceviri=ceviri, manset=ozet)

    def test_manset_en_soldaki_sekme_sayfa_gundemle_acilir(self):
        html = self.sayfa(self.OZET)
        nav = re.search(r'<div class="kategori-nav">(.*?)</div>', html).group(1)
        self.assertTrue(nav.startswith('<button type="button" class="kategori-buton manset-buton" data-kategori="Manşet"'))
        self.assertIn('class="kategori-buton aktif" data-kategori="Gündem"', nav)
        self.assertIn('<section class="manset" id="manset" data-kategori="Manşet" hidden>', html)
        self.assertIn('<h2 data-etiket="3 Ekim · sabah baskısı"></h2>', html)
        self.assertIn("<h3>G7 &lt;anlaştı&gt;</h3>", html)
        self.assertIn('<a href="https://b/1" target="_blank" rel="noopener">bbc.co.uk</a>', html)

    def test_manset_yoksa_ya_da_ingilizce_sayfada_sekme_yok(self):
        self.assertNotIn('data-kategori="Manşet"', self.sayfa(None))
        haber = m("bbc.co.uk", "Başlık")
        ingilizce = sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "", [haber])]}, manset=self.OZET)
        self.assertNotIn('data-kategori="Manşet"', ingilizce)


if __name__ == "__main__":
    unittest.main()
