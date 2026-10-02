"""Olay süzgeci (scripts/olay_suzgeci.py) testleri. Gemini'ye gidilmiyor;
aday ve temkinli gruplar sahte, Gemini cevabı sahte fonksiyonla.

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
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import olay_suzgeci  # noqa: E402
from model import KaynakBolumu, Makale  # noqa: E402

SIMDI = datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc)


def m(kaynak, baslik, saat):
    return Makale(kaynak, baslik, f"https://{kaynak}/{abs(hash(baslik))}", baslik + ".", "", saat)


# 02.10.2026 Gündem'inden: iki kaynak aynı olayı anlatıyor, üçüncüsü yalnız
# aynı konuda (Gazze); temkinli algoritma FAO ile Kızılay'ı birleştirmişti.
SEUL = m("bbc.co.uk", "Seoul warns 'further action' if Ukraine does not apologise", "2026-10-02T07:00:00+0000")
SEUL2 = m("dw.com", "Why is South Korea so angry with Ukraine over North Korean prisoners?", "2026-10-02T06:00:00+0000")
FAO = m("aljazeera.com", "FAO official says he lost his job for criticising Israeli policies in Gaza",
        "2026-10-02T05:00:00+0000")
KIZILAY = m("aa.com.tr", "Turkish Red Crescent helps elderly Gaza man walk again", "2026-10-02T04:00:00+0000")
SEUL3 = m("aa.com.tr", "Seoul summons Ukrainian envoy over POW disclosure", "2026-10-02T03:00:00+0000")
HEPSI = [SEUL, SEUL2, FAO, KIZILAY]


def kategoriler(makaleler):
    bolumler = {}
    for x in makaleler:
        bolumler.setdefault(x.kaynak, KaynakBolumu(x.kaynak, "", [])).makaleler.append(x)
    return {"Gündem": list(bolumler.values())}


def sahte_gruplama(gevsek, siki):
    """olaylar.olaylari_grupla yerine: eşik verilirse gevşek adaylar, yoksa
    temkinli gruplar ({(kat, öncü): [diğerleri]})."""
    def grupla(kategoriler, ingilizceler=None, turkce_kaynaklar=(), esik=None, en_az_ortak_isim=None):
        gruplar = gevsek if esik is not None else siki
        return {("Gündem", g[0].url): g[1:] for g in gruplar}
    return mock.patch.object(olay_suzgeci.olaylar, "olaylari_grupla", side_effect=grupla)


class Gruplama(unittest.TestCase):
    def grupla(self, makaleler, kararlar, sor):
        with contextlib.redirect_stderr(io.StringIO()):
            return olay_suzgeci.grupla(kategoriler(makaleler), {}, set(), kararlar, sor, SIMDI)

    def test_gemini_ayni_konu_farkli_olayi_ayirir_karar_saklanir(self):
        sor = mock.Mock(return_value=[[[SEUL.url, SEUL2.url]], []])
        kararlar = {}
        with sahte_gruplama(gevsek=[[SEUL, SEUL2], [FAO, KIZILAY]], siki=[[SEUL, SEUL2], [FAO, KIZILAY]]):
            gruplar = self.grupla(HEPSI, kararlar, sor)
            self.assertEqual(gruplar, {("Gündem", SEUL.url): [SEUL2]})
            self.assertEqual(sor.call_count, 1)
            # Aynı adaylar sonraki çalıştırmada yeniden sorulmaz.
            sor2 = mock.Mock()
            self.assertEqual(self.grupla(HEPSI, kararlar, sor2), gruplar)
            sor2.assert_not_called()
        self.assertEqual(len(kararlar), 2)

    def test_uyesi_azalan_aday_eski_karardan(self):
        kararlar = {}
        sor = mock.Mock(return_value=[[[SEUL.url, SEUL2.url, SEUL3.url]]])
        with sahte_gruplama(gevsek=[[SEUL, SEUL2, SEUL3]], siki=[]):
            self.grupla([SEUL, SEUL2, SEUL3], kararlar, sor)
        # SEUL3 sayfadan düştü: aday küçüldü ama sorulmaz.
        sor2 = mock.Mock()
        with sahte_gruplama(gevsek=[[SEUL, SEUL2]], siki=[]):
            gruplar = self.grupla([SEUL, SEUL2], kararlar, sor2)
        sor2.assert_not_called()
        self.assertEqual(gruplar, {("Gündem", SEUL.url): [SEUL2]})

    def test_yeni_uye_gelince_yeniden_sorulur(self):
        kararlar = {}
        with sahte_gruplama(gevsek=[[SEUL, SEUL2]], siki=[]):
            self.grupla([SEUL, SEUL2], kararlar, mock.Mock(return_value=[[[SEUL.url, SEUL2.url]]]))
        sor = mock.Mock(return_value=[[[SEUL.url, SEUL2.url, SEUL3.url]]])
        with sahte_gruplama(gevsek=[[SEUL, SEUL2, SEUL3]], siki=[]):
            gruplar = self.grupla([SEUL, SEUL2, SEUL3], kararlar, sor)
        sor.assert_called_once()
        self.assertEqual(gruplar, {("Gündem", SEUL.url): [SEUL2, SEUL3]})

    def test_gemini_yoksa_ya_da_cevap_vermezse_temkinli_algoritma(self):
        for sor in (None, mock.Mock(return_value=None)):
            kararlar = {}
            with sahte_gruplama(gevsek=[[SEUL, SEUL2], [FAO, KIZILAY]], siki=[[FAO, KIZILAY]]):
                gruplar = self.grupla(HEPSI, kararlar, sor)
            self.assertEqual(gruplar, {("Gündem", FAO.url): [KIZILAY]})
            self.assertEqual(kararlar, {})

    def test_ayni_kaynaktan_ikinci_haber_alinmaz(self):
        sor = mock.Mock(return_value=[[[SEUL.url, KIZILAY.url, SEUL3.url]]])
        with sahte_gruplama(gevsek=[[SEUL, KIZILAY, SEUL3]], siki=[]):
            gruplar = self.grupla([SEUL, KIZILAY, SEUL3], {}, sor)
        self.assertEqual(gruplar, {("Gündem", SEUL.url): [KIZILAY]})


class GeminiSor(unittest.TestCase):
    def test_kimlikler_adaylara_eslenir(self):
        istekler = []

        def uret(model, talimat, metin):
            istekler.append((model, metin))
            return json.dumps({"olaylar": [["h0", "h1"], ["h3", "h2"], ["h9"]]})

        sonuc = olay_suzgeci.gemini_sor([[SEUL, SEUL2], [FAO, KIZILAY]], {}, uret)
        self.assertEqual(sonuc, [[[SEUL.url, SEUL2.url]], [[KIZILAY.url, FAO.url]]])
        self.assertEqual(istekler[0][0], olay_suzgeci.MODELLER[0])
        self.assertIn("h0 [bbc.co.uk] Seoul warns", istekler[0][1])

    def test_olay_tek_adayda_kalir(self):
        sonuc = olay_suzgeci.gemini_sor([[SEUL, SEUL2], [FAO, KIZILAY]], {},
                                        lambda *a: '{"olaylar": [["h0", "h2"]]}')
        self.assertEqual(sonuc, [[[SEUL.url]], []])

    def test_model_hata_verirse_siradaki_hepsi_olmazsa_none(self):
        cagrilar = []

        def uret(model, talimat, metin):
            cagrilar.append(model)
            if model == olay_suzgeci.MODELLER[0]:
                raise RuntimeError("HTTP 429")
            return '{"olaylar": []}'

        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(olay_suzgeci.gemini_sor([[SEUL, SEUL2]], {}, uret), [[]])
            self.assertEqual(cagrilar, list(olay_suzgeci.MODELLER[:2]))

            def hep_hata(*a):
                raise RuntimeError("HTTP 503")

            self.assertIsNone(olay_suzgeci.gemini_sor([[SEUL, SEUL2]], {}, hep_hata))


class Kayit(unittest.TestCase):
    def test_eski_kararlar_duser(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "olay_kararlari.json"
            kararlar = {
                "yeni": {"urller": [], "olaylar": [], "zaman": SIMDI.isoformat()},
                "eski": {"urller": [], "olaylar": [], "zaman": (SIMDI - timedelta(days=4)).isoformat()},
            }
            olay_suzgeci.kararlari_kaydet(yol, kararlar, SIMDI)
            self.assertEqual(set(olay_suzgeci.kararlari_yukle(yol)), {"yeni"})
            self.assertEqual(olay_suzgeci.kararlari_yukle(Path(d) / "yok.json"), {})


if __name__ == "__main__":
    unittest.main()
