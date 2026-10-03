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


def m(kaynak, baslik, ozet="The report gives details. More follows in the text today.", gorsel=""):
    return Makale(kaynak, baslik, f"https://{kaynak}/{abs(hash(baslik))}", ozet, gorsel, "2026-10-02T10:00:00+0000")


# Yerel ama çok yazılan olay (03.10.2026: Christa Pike) ve gerçekten önemli olay (G7).
A, B, C = m("aljazeera.com", "Pike execution stabbed"), m("bbc.co.uk", "Pike stab survives"), m("dw.com/tr", "Pike bıçak")
D, E = m("aa.com.tr", "G7 agrees oil release"), m("npr.org", "G7 to release oil", gorsel="https://npr.org/g7.jpg")
# Tek kaynaklı Türkiye haberi (gruba girmemiş).
F = m("t24.com.tr", "Meclis yargı paketini kabul etti")


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
        if sistem in (manset.PUAN_TALIMATI, manset.TR_PUAN_TALIMATI):
            kistaslar = manset.KISTASLAR if sistem == manset.PUAN_TALIMATI else manset.TR_KISTASLAR

            def p(blok):
                n = 2 if any(k in blok for k in dusuk) else 8
                # Türkiye talimatında G7 haberi "Türkiye haberi değil".
                cevap = {**{k: n for k in kistaslar}, "gerekce": "g"}
                if sistem == manset.TR_PUAN_TALIMATI:
                    cevap["turkiye_haberi"] = "G7" not in blok
                return cevap
            return json.dumps({f"g{i}": p(b) for i, b in enumerate(bloklar)})
        return "```json\n" + json.dumps({
            f"g{i}": {"baslik": f"Başlık {i}", "ozet": "Al Jazeera'ya göre G7 anlaştı ve petrol salınacak. " * 2}
            for i in range(len(bloklar))}, ensure_ascii=False) + "\n```"
    return uret


def derlemeler(cagrilar):
    return [g for s, g in cagrilar if s == manset.TALIMAT]


def tr_puanlamalari(cagrilar):
    return [g for s, g in cagrilar if s == manset.TR_PUAN_TALIMATI]


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
        # Haberin güncel hali (görsel sonradan geldiyse) kayda geçer.
        A2 = Makale(A.kaynak, A.baslik, A.url, A.ozet, "https://a/g.jpg", A.tarih)
        manset.olaylari_kaydet(kayit, gruplar([A2, B]), kategoriler(A2, B), SABAH + timedelta(hours=2))
        uye = next(u for o in kayit["olaylar"] for u in o["uyeler"] if u["url"] == A.url)
        self.assertEqual(uye["gorsel"], "https://a/g.jpg")

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


    def test_gruba_girmemis_turkiye_haberi_tek_olay_olarak_kaydedilir(self):
        kayit = {}
        manset.olaylari_kaydet(kayit, gruplar([D, E]), kategoriler(D, E, F, m("npr.org", "Tek dünya haberi")), SABAH)
        self.assertEqual(sorted(len(o["uyeler"]) for o in kayit["olaylar"]), [1, 2])
        self.assertEqual(next(o for o in kayit["olaylar"] if len(o["uyeler"]) == 1)["uyeler"][0]["url"], F.url)

    def test_tr_adaylari(self):
        kayit = {}
        manset.olaylari_kaydet(kayit, gruplar([A, B, C], [D, E]), kategoriler(A, B, C, D, E, F), SABAH)
        baski = manset.baski_ani(SABAH)
        # Türkçe kaynaklı ya da AA'lı olaylar; dünya manşetine girenler hariç.
        self.assertEqual(len(manset.tr_adaylar(kayit["olaylar"], baski)), 3)
        haric = {D.url}
        adaylar = manset.tr_adaylar(kayit["olaylar"], baski, haric)
        self.assertEqual(sorted(len(o["uyeler"]) for o in adaylar), [1, 3])


    def test_kurumun_kendi_haberi_aday_olmaz(self):
        # 03.10.2026: T24'ün kendi erişim engeli haberleri Türkiye manşetine çıkmıştı.
        def olay(*uyeler):
            an = SABAH.isoformat()
            return {"ilk": an, "son": an, "uyeler": [{"kaynak": k, "baslik": b, "url": f"https://{k}/{b}"}
                                                       for k, b in uyeler]}
        kendi = [olay(("t24.com.tr", "Erişim engeli kararı sonrası T24'e destek ziyaretleri sürüyor")),
                 olay(("t24.com.tr", "T24, erişim engeline örnek kararlarla itiraz etti"))]
        baskasi_da = olay(("t24.com.tr", "T24'e erişim engeli"), ("bbc.com/turkce", "T24'e erişim engeli getirildi"))
        siradan = [olay(("t24.com.tr", "Meclis yargı paketini kabul etti")),
                   olay(("aa.com.tr", "Türkiye, Georgia sign education agreement")),
                   olay(("bbc.com/turkce", "Kripto hırsızlıkları neden artıyor?"))]
        for o in kendi:
            self.assertTrue(manset.kendi_haberi(o))
        for o in [baskasi_da, *siradan]:
            self.assertFalse(manset.kendi_haberi(o))
        adaylar = manset.tr_adaylar(kendi + [baskasi_da] + siradan, manset.baski_ani(SABAH))
        self.assertEqual(len(adaylar), 4)

    def test_sonnet_kendi_haberi_derse_elenir(self):
        olay = {"uyeler": [manset._uye(F)]}
        cevap = json.dumps({"g0": {**{k: 8 for k in manset.TR_KISTASLAR}, "turkiye_haberi": True, "kendi_haberi": True}})
        self.assertEqual(manset.puanla([olay], lambda s, g: cevap, manset.TR_PUAN_TALIMATI,
                                       manset.MANSET_TR_AGIRLIKLAR), [None])


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
        # Görsel: kaynakların haber görsellerinden ilki (AA'nınki boş).
        self.assertEqual(sonuc[0]["gorsel"], "https://npr.org/g7.jpg")

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

    def test_turkiye_manseti_kendi_kistaslariyla(self):
        cagrilar = []
        tum = kategoriler(A, B, C, D, E, F)
        ozet = self.guncelle({}, None, SABAH, gruplar([A, B, C], [D, E]), tum, uret=sahte_uret(cagrilar))
        self.assertEqual([o["tur"] for o in ozet["olaylar"]], ["dunya", "turkiye"])
        self.assertEqual(ozet["olaylar"][1]["kaynaklar"], [{"ad": "t24.com.tr", "url": F.url}])
        # G7 dünya manşetinde; Türkiye puanlamasına gitmez.
        self.assertNotIn("G7", tr_puanlamalari(cagrilar)[0])
        self.assertEqual(sorted(p["puan"] for p in ozet["tr_puanlar"]), [2.0, 8.0])
        self.assertEqual(set(manset.MANSET_TR_AGIRLIKLAR) & set(ozet["tr_puanlar"][0]), set(manset.TR_KISTASLAR))

    def test_turkiye_haberi_olmayan_elenir(self):
        olay = {"uyeler": [manset._uye(D)]}
        sonuc = manset.puanla([olay], sahte_uret([]), manset.TR_PUAN_TALIMATI, manset.MANSET_TR_AGIRLIKLAR)
        self.assertEqual(sonuc, [None])

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

    def test_onceki_baskilar(self):
        def baski(saat, n=1):
            return {"baski": (SABAH - timedelta(hours=saat)).astimezone(manset.TR_SAATI).isoformat(),
                    "olaylar": [{"baslik": f"b{i}", "ozet": "o", "tur": "dunya", "kaynaklar": [], "puan": 7}
                                for i in range(n)]}
        arsiv = manset.arsive_ekle([], baski(9 * 24), SABAH)  # 9 gün önce: düşer
        arsiv = manset.arsive_ekle(arsiv, baski(15), SABAH)
        arsiv = manset.arsive_ekle(arsiv, baski(0, 2), SABAH)
        arsiv = manset.arsive_ekle(arsiv, baski(0, 3), SABAH)  # aynı baskı yeniden: yerine
        arsiv = manset.arsive_ekle(arsiv, {**baski(0), "baski": "x", "olaylar": []}, SABAH)  # boş: eklenmez
        self.assertEqual([len(b["olaylar"]) for b in arsiv], [3, 1])
        self.assertNotIn("puan", arsiv[0]["olaylar"][0])

    def test_dosya_gidis_donus(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "x.json"
            manset.kaydet(yol, {"baski": "x"})
            self.assertEqual(manset.yukle(yol), {"baski": "x"})
            self.assertEqual(manset.yukle(Path(d) / "yok.json"), {})


class Sayfa(unittest.TestCase):
    OZET = {"baski": "2026-10-03T08:00:00+03:00", "olaylar": [
        {"baslik": "G7 <anlaştı>", "ozet": "Metin.", "gorsel": "https://b/g.jpg",
         "kaynaklar": [{"ad": "bbc.co.uk", "url": "https://b/1"}]}]}

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
        self.assertIn('<img src="https://b/g.jpg" alt="" loading="lazy" referrerpolicy="no-referrer">', html)
        self.assertIn('<p class="manset-ust" data-etiket="Manşet · 1 kaynak"></p>', html)
        self.assertIn('<a href="https://b/1" target="_blank" rel="noopener">bbc.co.uk</a>', html)

    def test_turkiye_kutusu_dinle_paylas_onceki_baskilar(self):
        ozet = {"baski": "2026-10-03T17:00:00+03:00", "olaylar": [
            {"baslik": "Meclis", "ozet": "Metin.", "tur": "turkiye", "kaynaklar": [{"ad": "t24.com.tr", "url": "https://t/1"}]}]}
        haber = m("bbc.co.uk", "Başlık")
        ceviri = Ceviriler({haber.url: "Başlık"}, {haber.url: "Özet."})
        html = sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "", [haber])]}, ceviri=ceviri,
                                   manset=ozet, onceki_baskilar=[self.OZET])
        self.assertIn('<article class="manset-kutu manset-turkiye" data-dil="tr">', html)
        self.assertIn('data-etiket="Manşet · Türkiye · 1 kaynak"', html)
        kutu = html[html.index('<article class="manset-kutu'):]
        self.assertLess(kutu.index('class="dinle"'), kutu.index("</article>"))
        self.assertLess(kutu.index('class="paylas paylas-ozet"'), kutu.index("</article>"))
        self.assertIn('<summary data-etiket="Önceki baskılar (1)"></summary>', html)
        self.assertIn('<h4 data-etiket="3 Ekim · sabah baskısı"></h4>', html)
        self.assertIn("<summary>G7 &lt;anlaştı&gt;</summary>", html)
        # Son baskı boşsa da önceki baskılar için sekme kalır.
        bos = sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "", [haber])]}, ceviri=ceviri,
                                  onceki_baskilar=[self.OZET])
        self.assertIn('data-kategori="Manşet" data-baski=""', bos)
        self.assertIn('<h2 data-etiket="Son baskıda manşete giren olay yok"></h2>', bos)

    def test_manset_yoksa_ya_da_ingilizce_sayfada_sekme_yok(self):
        self.assertNotIn('data-kategori="Manşet"', self.sayfa(None))
        haber = m("bbc.co.uk", "Başlık")
        ingilizce = sayfa.sayfa_olustur({"Gündem": [KaynakBolumu("bbc.co.uk", "", [haber])]}, manset=self.OZET)
        self.assertNotIn('data-kategori="Manşet"', ingilizce)


if __name__ == "__main__":
    unittest.main()
