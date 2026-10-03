"""Dünün özetleri (scripts/dun_ozeti.py) testleri. Claude'a gidilmiyor;
derleme fonksiyonu sahte.

Çalıştırma: python -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import dun_ozeti  # noqa: E402
import sayfa  # noqa: E402
from model import Ceviriler, KaynakBolumu, Makale  # noqa: E402

# 03.10.2026 02:00 Türkiye saati (UTC+3) = 02.10 23:00 UTC: Türkiye günü 3 Ekim.
BUGUN = datetime(2026, 10, 2, 23, 0, tzinfo=timezone.utc)
YARIN = BUGUN + timedelta(days=1)


def m(kaynak, baslik, ozet="Pilot recounts the attack in a call. More details follow in the report today."):
    return Makale(kaynak, baslik, f"https://{kaynak}/{abs(hash(baslik))}", ozet, "", "2026-10-02T10:00:00+0000")


A, B, C = m("aljazeera.com", "Pilot recounts stabbing"), m("bbc.co.uk", "Flydubai captain stabbed"), m("dw.com/tr", "Kokpitte bıçaklanma")
D, E = m("aa.com.tr", "Seoul summons envoy"), m("npr.org", "Seoul warns Ukraine")
F, G = m("t24.com.tr", "Bakan açıkladı"), m("bbc.co.uk", "Minister speaks")


def kategoriler(*makaleler):
    return {"Gündem": [KaynakBolumu("x", "", list(makaleler))]}


def gruplar(*gruplar_):
    return {("Gündem", g[0].url): list(g[1:]) for g in gruplar_}


def sahte_uret(cagrilar):
    def uret(sistem, girdi):
        cagrilar.append(girdi)
        n = girdi.count("Olay g")
        return "```json\n" + json.dumps({
            f"g{i}": {"baslik": f"Başlık {i}", "ozet": "Pilot Smit Machchhar, Al Jazeera'ya göre ucağın düştüğünü sandı. " * 2}
            for i in range(n)}, ensure_ascii=False) + "\n```"
    return uret


class Kayit(unittest.TestCase):
    def test_gruplar_birlesir_kaynak_buyur(self):
        kayit = {}
        tum = kategoriler(A, B, C, D, E)
        dun_ozeti.olaylari_kaydet(kayit, gruplar([A, B]), tum, BUGUN)
        dun_ozeti.olaylari_kaydet(kayit, gruplar([A, B, C], [D, E]), tum, BUGUN + timedelta(hours=1))
        olaylar = kayit["gunler"]["2026-10-03"]
        self.assertEqual(sorted(len(o["uyeler"]) for o in olaylar), [2, 3])

    def test_baska_kategori_ve_eski_gunler(self):
        kayit = {"gunler": {"2026-09-20": [{"uyeler": []}]}, "denemeler": {"2026-09-20": 1}}
        tum = {"Teknoloji": [KaynakBolumu("x", "", [A, B])]}
        dun_ozeti.olaylari_kaydet(kayit, {("Teknoloji", A.url): [B]}, tum, BUGUN)
        self.assertEqual(kayit["gunler"], {"2026-10-03": []})
        self.assertEqual(kayit["denemeler"], {})

    def test_secim_en_cok_kaynaklilar(self):
        olaylar = [{"uyeler": [{"kaynak": "a"}, {"kaynak": "b"}]},
                   {"uyeler": [{"kaynak": "a"}, {"kaynak": "b"}, {"kaynak": "c"}]},
                   {"uyeler": [{"kaynak": "a"}]}]
        sec = dun_ozeti.secim(olaylar, 2)
        self.assertEqual([len(o["uyeler"]) for o in sec], [3, 2])


class Derleme(unittest.TestCase):
    def olay(self):
        return {"uyeler": [dun_ozeti._uye(A), dun_ozeti._uye(B)]}

    def test_cevap_ayiklanir_kaynaklar_baglanir(self):
        cagrilar = []
        sonuc = dun_ozeti.derle([self.olay()], sahte_uret(cagrilar))
        self.assertEqual(sonuc[0]["baslik"], "Başlık 0")
        self.assertEqual([k["ad"] for k in sonuc[0]["kaynaklar"]], ["aljazeera.com", "bbc.co.uk"])
        self.assertIn("[aljazeera.com] Pilot recounts stabbing", cagrilar[0])

    def test_kullanilamayan_cevap_hata(self):
        for cevap in ("Üzgünüm", '{"g0": {"baslik": "", "ozet": "kısa"}}', '{"g5": {}}'):
            with self.assertRaises(ValueError):
                dun_ozeti.derle([self.olay()], lambda s, g, c=cevap: c)


class Guncelle(unittest.TestCase):
    def guncelle(self, kayit, ozet, simdi, gruplar_, tum, **kw):
        with contextlib.redirect_stderr(io.StringIO()):
            return dun_ozeti.guncelle(kayit, ozet, simdi, gruplar_, tum, **kw)

    def test_ilk_kurulumda_gorulenler_dun_sayilir(self):
        kayit, cagrilar = {}, []
        ozet = self.guncelle(kayit, None, BUGUN, gruplar([A, B, C]), kategoriler(A, B, C), uret=sahte_uret(cagrilar))
        self.assertEqual(ozet["gun"], "2026-10-02")
        self.assertEqual(len(cagrilar), 1)
        self.assertEqual(kayit["denemeler"], {"2026-10-02": 1})

    def test_ayni_gun_ikinci_calistirmada_yeniden_derlenmez(self):
        kayit, cagrilar = {}, []
        ozet = self.guncelle(kayit, None, BUGUN, gruplar([A, B]), kategoriler(A, B), uret=sahte_uret(cagrilar))
        ozet2 = self.guncelle(kayit, ozet, BUGUN + timedelta(hours=1), gruplar([A, B]), kategoriler(A, B),
                              uret=sahte_uret(cagrilar))
        self.assertEqual(ozet2, ozet)
        self.assertEqual(len(cagrilar), 1)

    def test_yeni_gun_onceki_gunun_en_cok_kaynaklilarini_derler(self):
        kayit, cagrilar = {"gunler": {"2026-10-01": []}}, []
        tum = kategoriler(A, B, C, D, E, F, G)
        self.guncelle(kayit, None, BUGUN, gruplar([A, B, C], [D, E], [F, G]), tum, kapali=True)
        ozet = self.guncelle(kayit, None, YARIN, {}, tum, uret=sahte_uret(cagrilar))
        # 3 Ekim'in olayları 4 Ekim sabahı derlenir: en çok kaynaklı 2 olay.
        self.assertEqual(ozet["gun"], "2026-10-03")
        self.assertEqual([len(o["kaynaklar"]) for o in ozet["olaylar"]], [3, 2])
        self.assertEqual(cagrilar[0].count("Olay g"), 2)

    def test_kapali_ise_claude_cagrilmaz(self):
        cagrilar = []
        ozet = self.guncelle({}, None, BUGUN, gruplar([A, B]), kategoriler(A, B), kapali=True, uret=sahte_uret(cagrilar))
        self.assertIsNone(ozet)
        self.assertEqual(cagrilar, [])

    def test_hata_olursa_kutu_yok_en_fazla_uc_deneme(self):
        def hata(sistem, girdi):
            raise RuntimeError("limit")

        kayit = {}
        for i in range(5):
            ozet = self.guncelle(kayit, None, BUGUN + timedelta(hours=i * 0.1), gruplar([A, B]), kategoriler(A, B),
                                 uret=hata)
        self.assertIsNone(ozet)
        self.assertEqual(kayit["denemeler"], {"2026-10-02": dun_ozeti.EN_FAZLA_DENEME})

    def test_eski_ozet_uc_gune_kadar_gosterilir(self):
        eski = {"gun": "2026-10-03", "olaylar": [{"baslik": "b", "ozet": "o" * 80, "kaynaklar": []}]}
        kayit = {"gunler": {"2026-10-04": []}}
        simdi = BUGUN + timedelta(days=2)  # TR günü 5 Ekim, dün olay yok
        self.assertEqual(self.guncelle(kayit, eski, simdi, {}, kategoriler()), eski)
        self.assertIsNone(self.guncelle(kayit, eski, simdi + timedelta(days=3), {}, kategoriler()))

    def test_dosya_gidis_donus(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "x.json"
            dun_ozeti.kaydet(yol, {"gun": "2026-10-02"})
            self.assertEqual(dun_ozeti.yukle(yol), {"gun": "2026-10-02"})
            self.assertEqual(dun_ozeti.yukle(Path(d) / "yok.json"), {})


class Sayfa(unittest.TestCase):
    OZET = {"gun": "2026-10-02", "olaylar": [
        {"baslik": "Pilot <anlattı>", "ozet": "Metin.", "kaynaklar": [{"ad": "bbc.co.uk", "url": "https://b/1"}]}]}

    def sayfa(self, dun):
        haber = m("bbc.co.uk", "Başlık")
        ceviri = Ceviriler({haber.url: "Başlık"}, {haber.url: "Özet."})
        return sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "", [haber])]}, ceviri=ceviri, dun_ozeti=dun)

    def test_kutu_turkce_sayfada_gundem_basinda(self):
        html = self.sayfa(self.OZET)
        self.assertIn('<section class="dun-ozeti" id="dun-ozeti" data-kategori="Gündem">', html)
        self.assertIn('<h2 data-etiket="Dünün özetleri · 2 Ekim"></h2>', html)
        self.assertIn("<h3>Pilot &lt;anlattı&gt;</h3>", html)
        self.assertIn('<a href="https://b/1" target="_blank" rel="noopener">bbc.co.uk</a>', html)
        self.assertLess(html.index('id="dun-ozeti"'), html.index('id="izgara"'))

    def test_ozet_yoksa_ya_da_ingilizce_sayfada_kutu_yok(self):
        self.assertNotIn('id="dun-ozeti"', self.sayfa(None))
        haber = m("bbc.co.uk", "Başlık")
        ingilizce = sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "", [haber])]}, dun_ozeti=self.OZET)
        self.assertNotIn('id="dun-ozeti"', ingilizce)


if __name__ == "__main__":
    unittest.main()
