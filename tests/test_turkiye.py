"""Türkiye sekmesi (scripts/turkiye.py) testleri. Gemini'ye gidilmiyor.

Çalıştırma: python -m unittest discover -s tests -v
"""

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sayfa  # noqa: E402
import turkiye  # noqa: E402
from model import Ceviriler, KaynakBolumu, Makale  # noqa: E402

SIMDI = datetime(2026, 10, 22, 20, 0, tzinfo=timezone.utc)


def haber(kaynak, kanat, baslik, ozet="", url=None):
    return {"url": url or f"https://{kaynak}/{abs(hash(baslik)) % 10**6}", "baslik": baslik, "ozet": ozet,
            "zaman": SIMDI.isoformat(), "kaynak": kaynak, "ad": kaynak.upper(), "kanat": kanat}


# 22.10.2026 taramasında aynı anda beş gazetede çıkan haber.
SPK = [
    haber("ntv", "merkez", "SPK’dan 48 kişi hakkında suç duyurusu kararı",
          "48 kişi ile 5 şirkete 2 yıl işlem yapma yasağı uygulanacak"),
    haber("hurriyet", "merkez", "SPK’dan kritik karar: 48 kişiye suç duyurusu, 28 kişiye lisans iptali"),
    haber("sabah", "iktidara yakın", "SPK duyurdu! 48 kişiye suç duyurusu ve işlem yasağı"),
    haber("sozcu", "muhalif", "SPK’dan 48 kişi hakkında suç duyurusu kararı"),
]
OBUR = [haber("cumhuriyet", "muhalif", "Manisa Büyükşehir Belediye Başkanı Besim Dutlulu AKP iddiasını yalanladı"),
        haber("haberturk", "merkez", "Ensesinden vurulmuştu... Berber cinayetinde sır perdesi aralandı")]


def dogrulayan(onemsiz=()):
    def uret(model, talimat, girdi):
        if talimat == turkiye.DOGRULAMA:
            cevap, grup = {}, None
            for satir in girdi.splitlines():
                if satir.endswith(":") and satir.startswith("g"):
                    grup = satir[:-1]
                    cevap[grup] = {"olaylar": [{"haberler": [], "turkiye": True, "onemsiz": False}]}
                elif satir.strip().startswith("h"):
                    olay = cevap[grup]["olaylar"][0]
                    olay["haberler"].append(satir.split()[0])
                    if any(k in satir for k in onemsiz):
                        olay["onemsiz"] = True
            return json.dumps(cevap)
        olaylar = [s[:-1] for s in girdi.splitlines() if s.startswith("o") and s.endswith(":")]
        return json.dumps({o: {"baslik": "SPK 48 kişi hakkında suç duyurusunda bulundu",
                               "ozet": "Sermaye Piyasası Kurulu, iki şirketin hisselerinde işlem yapan 48 kişi"
                                       " hakkında suç duyurusunda bulunma kararı aldı."} for o in olaylar})
    return uret


def getir(url):
    return {"govde": "Sermaye Piyasası Kurulu bülteninde karar açıklandı.", "gorsel": "https://g/1.jpg"}


class Kokler(unittest.TestCase):
    def test_ekler_atilir(self):
        self.assertEqual(turkiye.kokler("SPK’dan karar"), {"spk", "karar"})
        self.assertTrue(turkiye.benzer_mi(turkiye.kokler(SPK[0]["baslik"]), turkiye.kokler(SPK[2]["baslik"])))
        self.assertFalse(turkiye.benzer_mi(turkiye.kokler(SPK[0]["baslik"]), turkiye.kokler(OBUR[0]["baslik"])))

    def test_spor_ve_dunya_adresi_atlanir(self):
        self.assertTrue(turkiye.ATLANAN_ADRES.search("https://www.sabah.com.tr/spor/futbol/x"))
        self.assertTrue(turkiye.ATLANAN_BASLIK.search("Süper Loto çekiliş sonuçları belli oldu"))
        self.assertFalse(turkiye.ATLANAN_BASLIK.search(SPK[0]["baslik"]))


class Zincirleme(unittest.TestCase):
    def test_sik_sozcukler_farkli_olaylari_birlestirmez(self):
        # 22.10.2026: ilk sürüm SPK, fon kanunu ve Alihan Kuriş soruşturmasını tek
        # grupta toplamıştı ("soruşturma", "tutuklama", "son dakika" ortak).
        fon = [haber("sozcu", "muhalif", "Son dakika... Fon kanunu teklifi TBMM'den geçerek yasallaştı"),
               haber("yenisafak", "iktidara yakın", "Fonların tasfiyesi teklifi yasalaştı"),
               haber("trthaber", "kamu", "Fon düzenlemelerini içeren kanun teklifi yasalaştı")]
        kuris = [haber("habertürk", "merkez", "Alihan Kuriş suç örgütüne 19 tutuklama"),
                 haber("hurriyet", "merkez", "Son dakika... Alihan Kuriş suç örgütüne yönelik operasyonda 19 tutuklama"),
                 haber("trthaber", "kamu", "Alihan Kuriş suç örgütü soruşturmasında 19 tutuklama")]
        dolgu = [haber(f"k{i}", "merkez", f"Son dakika soruşturma tutuklama {i}. haber {k}")
                 for i, k in enumerate(["Ankara", "İzmir", "Bursa", "Adana", "Konya", "Van", "Muş", "Rize"])]
        gruplar = turkiye.grupla(SPK + fon + kuris + dolgu)
        for g in gruplar:
            basliklar = " ".join(h["baslik"] for h in g)
            self.assertLessEqual(sum(k in basliklar for k in ("SPK", "Fon", "Kuriş")), 1, basliklar)
        self.assertEqual(len({h["kaynak"] for h in gruplar[0]}), 4)


class Akis(unittest.TestCase):
    def test_grupla_dogrula_derle(self):
        adaylar = turkiye.grupla(SPK + OBUR)
        self.assertEqual(len({h["kaynak"] for h in adaylar[0]}), 4)
        kayit = turkiye.guncelle({}, SPK + OBUR, SIMDI, uret=dogrulayan(), getir=getir)
        self.assertEqual(len(kayit["olaylar"]), 1)
        o = kayit["olaylar"][0]
        self.assertEqual(len(o["kaynaklar"]), 4)
        self.assertTrue(o["ozet"].startswith("Sermaye Piyasası Kurulu"))
        self.assertEqual(o["gorsel"], "https://g/1.jpg")

    def test_onemsiz_ya_da_az_kaynakli_olay_alinmaz(self):
        kayit = turkiye.guncelle({}, SPK, SIMDI, uret=dogrulayan(onemsiz=("SPK",)), getir=getir)
        self.assertEqual(kayit["olaylar"], [])
        kayit = turkiye.guncelle({}, SPK[:2], SIMDI, uret=dogrulayan(), getir=getir)
        self.assertEqual(kayit["olaylar"], [])

    def test_iki_saatten_once_hesaplanmaz_ozet_yalniz_yeni_gazetede_yenilenir(self):
        derlemeler = []

        def uret(model, talimat, girdi):
            if talimat == turkiye.DERLEME:
                derlemeler.append(girdi)
            return dogrulayan()(model, talimat, girdi)
        kayit = turkiye.guncelle({}, SPK[:3], SIMDI, uret=uret, getir=getir)
        self.assertFalse(turkiye.zamani_mi(kayit, SIMDI + timedelta(hours=1)))
        self.assertTrue(turkiye.zamani_mi(kayit, SIMDI + timedelta(hours=2)))
        kayit = turkiye.guncelle(kayit, SPK[:3], SIMDI + timedelta(hours=2), uret=uret, getir=getir)
        self.assertEqual(len(derlemeler), 1)  # aynı gazeteler: özet aynen kaldı
        kayit = turkiye.guncelle(kayit, SPK, SIMDI + timedelta(hours=4), uret=uret, getir=getir)
        self.assertEqual(len(derlemeler), 2)  # Sözcü katıldı: yeniden derlendi
        o = kayit["olaylar"][0]
        self.assertEqual(o["derleme"], (SIMDI + timedelta(hours=4)).isoformat())
        # Özeti yenilenmeyen olayın derleme anı değişmez.
        sonra = turkiye.guncelle(kayit, SPK, SIMDI + timedelta(hours=6), uret=uret, getir=getir)
        self.assertEqual(sonra["olaylar"][0]["derleme"], o["derleme"])
        self.assertEqual(sonra["hesap"], (SIMDI + timedelta(hours=6)).isoformat())
        self.assertEqual(len(kayit["olaylar"][0]["kaynaklar"]), 4)

    def test_gemini_cevap_vermezse_eski_hal_kalir(self):
        onceki = {"hesap": (SIMDI - timedelta(hours=3)).isoformat(), "olaylar": [{"x": 1}], "kararlar": {}}

        def bozuk(model, talimat, girdi):
            raise RuntimeError("503")
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIs(turkiye.guncelle(onceki, SPK, SIMDI, uret=bozuk, getir=getir), onceki)

    def test_ingilizce_derleme_kaydedilmez(self):
        def uret(model, talimat, girdi):
            if talimat == turkiye.DERLEME:
                return json.dumps({"o0": {"baslik": "SPK", "ozet": "The Capital Markets Board filed a criminal"
                                          " complaint against 48 people and banned them from trading for two years."}})
            return dogrulayan()(model, talimat, girdi)
        self.assertEqual(turkiye.guncelle({}, SPK, SIMDI, uret=uret, getir=getir)["olaylar"], [])


class BirdenCokOlay(unittest.TestCase):
    def test_bir_adaydan_iki_olay(self):
        # 22.10.2026: Gürlek'in iki açıklaması tek adaydaydı, yalnız biri alınıyordu.
        bassavci = [haber(k, kn, f"Bakan Gürlek duyurdu: Başsavcı vekilleri adli işlere katılacak {i}")
                    for i, (k, kn) in enumerate([("cumhuriyet", "muhalif"), ("trthaber", "kamu"),
                                                 ("sabah", "iktidara yakın")])]
        mechul = [haber(k, kn, f"Bakan Gürlek: 71 faili meçhul cinayet aydınlatıldı {i}")
                  for i, (k, kn) in enumerate([("ntv", "merkez"), ("yenisafak", "iktidara yakın"),
                                               ("hurriyet", "merkez"), ("sozcu", "muhalif")])]
        aday = [bassavci + mechul]

        def uret(model, talimat, girdi):
            kim = [s.split()[0] for s in girdi.splitlines() if s.strip().startswith("h")]
            return json.dumps({"g0": {"olaylar": [
                {"haberler": kim[:3], "turkiye": True, "onemsiz": False},
                {"haberler": kim[3:], "turkiye": True, "onemsiz": False}]}})
        olaylar = turkiye.dogrula(aday, {}, uret)
        self.assertEqual([len(o) for o in olaylar], [3, 4])


class Sayfa(unittest.TestCase):
    def test_turkiye_sekmesi(self):
        kayit = turkiye.guncelle({}, SPK, SIMDI, uret=dogrulayan(), getir=getir)
        m = Makale("bbc.co.uk", "Title", "https://b/1", "Summary.", "", "2026-10-22T19:00:00+00:00")
        ceviri = Ceviriler(basliklar={m.url: "Başlık"}, ozetler={m.url: "Özet."})
        html = sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "", [m])]}, [], ceviri, turkiye=kayit)
        self.assertIn('id="turkiye" data-kategori="Türkiye"', html)
        self.assertIn('class="kategori-buton turkiye-buton"', html)
        self.assertIn("Türkiye · 4 gazete · 23:00 derlemesi", html)
        kutu = html[html.index('id="turkiye"'):]
        self.assertLess(kutu.index("<h3>"), kutu.index("<img"))  # görsel başlıktan sonra
        self.assertLess(kutu.index("<img"), kutu.index('class="ozet-metni"'))  # 20:00 UTC = 23:00 Türkiye
        bos = sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "", [m])]}, [], ceviri,
                                  turkiye={"hesap": SIMDI.isoformat(), "olaylar": []})
        self.assertNotIn('id="turkiye"', bos)


if __name__ == "__main__":
    unittest.main()
