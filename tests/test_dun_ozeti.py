"""Dünün özetleri (scripts/dun_ozeti.py) testleri. Claude'a gidilmiyor;
derleme fonksiyonu sahte.

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

import dun_ozeti  # noqa: E402
import sayfa  # noqa: E402
from model import Ceviriler, KaynakBolumu, Makale  # noqa: E402

# 03.10.2026 02:00 Türkiye saati (UTC+3) = 02.10 23:00 UTC: Türkiye günü 3 Ekim.
BUGUN = datetime(2026, 10, 2, 23, 0, tzinfo=timezone.utc)
YARIN = BUGUN + timedelta(days=1)


def m(kaynak, baslik, ozet="Pilot recounts the attack in a call. More details follow in the report today."):
    return Makale(kaynak, baslik, f"https://{kaynak}/{abs(hash(baslik))}", ozet, "", "2026-10-02T10:00:00+0000")


A, B, C = m("aljazeera.com", "Pilot recounts stabbing"), m("bbc.co.uk", "Flydubai Pilot stabbed"), m("dw.com/tr", "Pilot bıçaklandı")
D, E = m("aa.com.tr", "G7 agrees oil release"), m("npr.org", "G7 to release oil")
F, G = m("t24.com.tr", "Bakan açıkladı"), m("bbc.co.uk", "Minister speaks")


def kategoriler(*makaleler):
    return {"Gündem": [KaynakBolumu("x", "", list(makaleler))]}


def gruplar(*gruplar_):
    return {("Gündem", g[0].url): list(g[1:]) for g in gruplar_}


def sahte_uret(cagrilar, dusuk=("stab", "bıçak")):
    """Puanlamada içinde `dusuk` kelimesi geçen olaylara 2, ötekilere 8
    verir; derlemede her olaya bir derleme yazar."""
    def uret(sistem, girdi):
        cagrilar.append((sistem, girdi))
        bloklar = re.split(r"\n\n(?=Olay g)", girdi)
        if sistem == dun_ozeti.PUAN_TALIMATI:
            def p(blok):
                n = 2 if any(k in blok for k in dusuk) else 8
                return {"etki": n, "kalicilik": n, "donum": n, "eylem": n, "turkiye": n, "gerekce": "g"}
            return json.dumps({f"g{i}": p(b) for i, b in enumerate(bloklar)})
        return "```json\n" + json.dumps({
            f"g{i}": {"baslik": f"Başlık {i}", "ozet": "Al Jazeera'ya göre G7 anlaştı ve petrol salınacak. " * 2}
            for i in range(len(bloklar))}, ensure_ascii=False) + "\n```"
    return uret


def derlemeler(cagrilar):
    return [g for s, g in cagrilar if s == dun_ozeti.TALIMAT]


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

    def test_adaylar_en_az_iki_kaynakli_cok_kaynaklilar_once(self):
        olaylar = [{"uyeler": [{"kaynak": "a"}, {"kaynak": "b"}]},
                   {"uyeler": [{"kaynak": "a"}, {"kaynak": "b"}, {"kaynak": "c"}]},
                   {"uyeler": [{"kaynak": "a"}]}]
        self.assertEqual([len(o["uyeler"]) for o in dun_ozeti.adaylar(olaylar)], [3, 2])
        self.assertEqual(len(dun_ozeti.adaylar(olaylar, 1)), 1)


class Puanlama(unittest.TestCase):
    def test_agirlikli_ortalama(self):
        self.assertAlmostEqual(sum(dun_ozeti.DUN_OZETI_AGIRLIKLAR.values()), 1)
        p = {"etki": 8, "kalicilik": 6, "donum": 4, "eylem": 10, "turkiye": 0}
        self.assertAlmostEqual(dun_ozeti.puan(p), round(8 * .30 + 6 * .25 + 4 * .17 + 10 * .13, 2))
        # Türkiye'ye yakınlık %15.
        self.assertAlmostEqual(dun_ozeti.puan({**p, "turkiye": 10}) - dun_ozeti.puan(p), 1.5)

    def test_cevap_sinirlanir_eksik_olay_none(self):
        olay = {"uyeler": [dun_ozeti._uye(A), dun_ozeti._uye(B)]}
        cevap = json.dumps({"g0": {"etki": 14, "kalicilik": -3, "donum": "5", "eylem": 5, "turkiye": 0,
                                   "gerekce": "yerel"}, "g1": {"etki": 5}})
        sonuc = dun_ozeti.puanla([olay, olay], lambda s, g: cevap)
        self.assertEqual((sonuc[0]["etki"], sonuc[0]["kalicilik"], sonuc[0]["gerekce"]), (10, 0, "yerel"))
        self.assertIsNone(sonuc[1])
        with self.assertRaises(ValueError):
            dun_ozeti.puanla([olay], lambda s, g: '{"g0": {}}')


class Derleme(unittest.TestCase):
    def olay(self):
        return {"uyeler": [dun_ozeti._uye(A), dun_ozeti._uye(B)]}

    def test_cevap_ayiklanir_kaynaklar_baglanir(self):
        cagrilar = []
        sonuc = dun_ozeti.derle([self.olay()], sahte_uret(cagrilar))
        self.assertEqual(sonuc[0]["baslik"], "Başlık 0")
        self.assertEqual([k["ad"] for k in sonuc[0]["kaynaklar"]], ["aljazeera.com", "bbc.co.uk"])
        self.assertIn("[aljazeera.com] Pilot recounts stabbing", cagrilar[0][1])

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
        ozet = self.guncelle(kayit, None, BUGUN, gruplar([D, E]), kategoriler(D, E), uret=sahte_uret(cagrilar))
        self.assertEqual(ozet["gun"], "2026-10-02")
        self.assertEqual(len(ozet["olaylar"]), 1)
        self.assertEqual(len(cagrilar), 2)  # puanlama + derleme
        self.assertEqual(kayit["denemeler"], {"2026-10-02": 1})

    def test_cok_yazilan_ama_yerel_olay_esigi_gecemez(self):
        # 03.10.2026: Christa Pike'ın infazı 4 kaynakta, G7 kararı 2'de;
        # kaynak sayısı değil puan belirler.
        kayit, cagrilar = {"gunler": {"2026-10-01": []}}, []
        tum = kategoriler(A, B, C, D, E)
        self.guncelle(kayit, None, BUGUN, gruplar([A, B, C], [D, E]), tum, kapali=True)
        ozet = self.guncelle(kayit, None, YARIN, {}, tum, uret=sahte_uret(cagrilar))
        self.assertEqual(ozet["gun"], "2026-10-03")
        self.assertEqual([len(o["kaynaklar"]) for o in ozet["olaylar"]], [2])
        self.assertEqual(ozet["olaylar"][0]["puan"], 8.0)
        self.assertEqual(sorted(p["puan"] for p in ozet["puanlar"]), [2.0, 8.0])
        self.assertEqual(derlemeler(cagrilar)[0].count("Olay g"), 1)

    def test_esigi_gecen_yoksa_kutu_yok_derleme_yapilmaz(self):
        cagrilar = []
        ozet = self.guncelle({}, None, BUGUN, gruplar([A, B, C]), kategoriler(A, B, C), uret=sahte_uret(cagrilar))
        self.assertEqual(ozet["olaylar"], [])
        self.assertEqual(derlemeler(cagrilar), [])
        self.assertIsNone(dun_ozeti.gosterilecek(ozet, BUGUN))
        # Aynı gün yeniden sorulmaz.
        self.guncelle({"gunler": {"2026-10-02": []}}, ozet, BUGUN, {}, kategoriler(), uret=sahte_uret(cagrilar))
        self.assertEqual(len(cagrilar), 1)

    def test_en_fazla_uc_olay_puana_gore(self):
        olaylar_ = [[m(f"k{i}.com", f"Olay {i} G7"), m(f"l{i}.com", f"Olay {i} G7")] for i in range(5)]
        tum = kategoriler(*[x for g in olaylar_ for x in g])
        ozet = self.guncelle({}, None, BUGUN, gruplar(*olaylar_), tum, uret=sahte_uret([]))
        self.assertEqual(len(ozet["olaylar"]), dun_ozeti.DUN_OZETI_EN_FAZLA)

    def test_ayni_gun_ikinci_calistirmada_yeniden_derlenmez(self):
        kayit, cagrilar = {}, []
        ozet = self.guncelle(kayit, None, BUGUN, gruplar([D, E]), kategoriler(D, E), uret=sahte_uret(cagrilar))
        ozet2 = self.guncelle(kayit, ozet, BUGUN + timedelta(hours=1), gruplar([D, E]), kategoriler(D, E),
                              uret=sahte_uret(cagrilar))
        self.assertIs(ozet2, ozet)
        self.assertEqual(len(cagrilar), 2)
        # Denemede zorla: yeniden puanlanır.
        self.guncelle(kayit, ozet, BUGUN, {}, kategoriler(D, E), zorla=True, uret=sahte_uret(cagrilar))
        self.assertEqual(len(cagrilar), 4)
        # Eski yöntemle (sürümsüz) hazırlanmış özet yeniden hazırlanır.
        eski = {k: v for k, v in ozet.items() if k != "surum"}
        self.guncelle(kayit, eski, BUGUN, {}, kategoriler(D, E), uret=sahte_uret(cagrilar))
        self.assertEqual(len(cagrilar), 6)

    def test_kapali_ise_claude_cagrilmaz(self):
        cagrilar = []
        ozet = self.guncelle({}, None, BUGUN, gruplar([D, E]), kategoriler(D, E), kapali=True, uret=sahte_uret(cagrilar))
        self.assertIsNone(ozet)
        self.assertEqual(cagrilar, [])

    def test_hata_olursa_kutu_yok_en_fazla_uc_deneme(self):
        def hata(sistem, girdi):
            raise RuntimeError("limit")

        kayit = {}
        for i in range(5):
            ozet = self.guncelle(kayit, None, BUGUN + timedelta(hours=i * 0.1), gruplar([D, E]), kategoriler(D, E),
                                 uret=hata)
        self.assertIsNone(ozet)
        self.assertEqual(kayit["denemeler"], {"2026-10-02": dun_ozeti.EN_FAZLA_DENEME})

    def test_eski_ozet_uc_gune_kadar_gosterilir(self):
        eski = {"gun": "2026-10-03", "olaylar": [{"baslik": "b", "ozet": "o" * 80, "kaynaklar": []}]}
        simdi = BUGUN + timedelta(days=2)  # TR günü 5 Ekim
        self.assertEqual(dun_ozeti.gosterilecek(eski, simdi), eski)
        self.assertIsNone(dun_ozeti.gosterilecek(eski, simdi + timedelta(days=3)))
        self.assertIsNone(dun_ozeti.gosterilecek(None, simdi))

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
