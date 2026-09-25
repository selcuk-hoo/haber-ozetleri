"""Özet temizliği (KAYNAK_KURALLARI) testleri.

Her örnek, canlı sitedeki özetlerde görülmüş gerçek bir kalıntıdan
kısaltılarak alındı. Bir kaynağın kuralı değiştiğinde ya da yeni kural
eklendiğinde buraya o kaynaktan bir örnek eklenir.

Çalıştırma: python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ayarlar import KAYNAKLAR  # noqa: E402
from besleme import ATLANAN_ADRES  # noqa: E402
from ozet import KAYNAK_KURALLARI, basligi_temizle, ozet_olustur  # noqa: E402


def ozet(metin: str, baslik: str, kaynak: str, k: int = 5) -> str:
    return ozet_olustur(metin, baslik, k, kaynak)


class KaynakKurallari(unittest.TestCase):
    def test_bbc_farkli_yazilmis_baslik_satiri(self):
        self.assertEqual(
            ozet(
                "Residents eating garden weeds in Russian-occupied city cut off from food and water"
                ' - Published "Two more civilians died last night," says Halia. She is trapped in the city.',
                "Oleshky: Residents eating garden weeds in Russian-occupied city cut off from food and water",
                "bbc.co.uk",
            ),
            '"Two more civilians died last night," says Halia. She is trapped in the city.',
        )

    def test_bbc_ayni_baslik_ve_published(self):
        self.assertEqual(
            ozet(
                "Harvey Weinstein sentenced to 15 years in prison - Published Disgraced producer Harvey"
                " Weinstein has been sentenced. More text.",
                "Harvey Weinstein sentenced to 15 years in prison",
                "bbc.co.uk",
            ),
            "Disgraced producer Harvey Weinstein has been sentenced. More text.",
        )

    def test_bbc_ilgili_haberler_listesi_kesilir(self):
        self.assertEqual(
            ozet(
                "Gemini found public information online. Experts disagree. - Why are there concerns AI"
                " could threaten humanity, and how real are they? - Published6 days ago - Could AI wipe"
                " out humans? - Published5 days ago",
                "Gemini hacked three companies",
                "bbc.co.uk",
            ),
            "Gemini found public information online. Experts disagree.",
        )

    def test_bbc_related_topics_kesilir(self):
        self.assertEqual(
            ozet(
                "The BBC's Tabby Wilson is in Sydney. Related topics - AustraliaUpdates from your News"
                " topics will appear in My News.",
                "X",
                "bbc.co.uk",
            ),
            "The BBC's Tabby Wilson is in Sydney.",
        )

    def test_bbc_watch_cumlesi_atilir(self):
        self.assertEqual(
            ozet("Watch: The arms race in space. The RAF chief has warned of a threat.", "X", "bbc.co.uk"),
            "The RAF chief has warned of a threat.",
        )

    def test_cnn_video_blogu(self):
        self.assertEqual(
            ozet(
                "Navarro says voters feel betrayed. 2:43 • Source: CNN Politics of the Day 11 videos"
                " Video Ad Feedback Judge says he'll make a ruling",
                "X",
                "cnn.com",
            ),
            "Navarro says voters feel betrayed.",
        )

    def test_cnn_yardim_hatti_notu(self):
        self.assertEqual(
            ozet(
                "EDITOR’S NOTE: This story contains discussion of suicide. Help is available if you or"
                " someone you know is struggling with suicidal thoughts or mental health matters. In the"
                " US, call or text 988 for help. The International Association for Suicide Prevention and"
                " Befrienders Worldwide have contact information for crisis centers around the world."
                " Eight US Navy personnel attempted suicide, according to a letter.",
                "Eight sailors",
                "cnn.com",
            ),
            "Eight US Navy personnel attempted suicide, according to a letter.",
        )

    def test_aa_muhabir_ve_tarih_satiri(self):
        self.assertEqual(
            ozet(
                "Merve Gül Aydoğan Ağlarcı 24 September 2026•Update: 24 September 2026 US President Donald"
                " Trump and Chinese President Xi Jinping began talks on Thursday. The meeting followed a ceremony.",
                "Trump, Xi hold closed-door bilateral talks at White House",
                "aa.com.tr",
            ),
            "US President Donald Trump and Chinese President Xi Jinping began talks on Thursday. The meeting"
            " followed a ceremony.",
        )

    def test_aa_cumle_icindeki_tarih_korunur(self):
        metin = "Talks began on 24 September 2026 in Ankara. Officials met again."
        self.assertEqual(ozet(metin, "Talks", "aa.com.tr"), metin)

    def test_aljazeera_baslik_ve_newsfeed(self):
        self.assertEqual(
            ozet(
                "Spain’s Sanchez warns of far-right threat NewsFeed Spanish Prime Minister spoke. More.",
                "Spain’s Sanchez warns of far-right threat",
                "aljazeera.com",
            ),
            "Spanish Prime Minister spoke. More.",
        )

    def test_aljazeera_onerilen_haberler_listesi(self):
        # Son önerilen başlık metnin devamına yapışık; o cümle bütünüyle atılır.
        self.assertEqual(
            ozet(
                "Bulldozers uprooted olive groves. Farmers were preparing the harvest. Recommended Stories"
                " list of 3 items - list 1 of 3Israeli campaign moves on - list 2 of 3How Israel dismantles"
                " life - list 3 of 3Palestine weekly: Violent disruptions The demolition started on Monday."
                " He said they were steadfast.",
                "They uprooted it all",
                "aljazeera.com",
            ),
            "Bulldozers uprooted olive groves. Farmers were preparing the harvest. He said they were steadfast.",
        )

    def test_aljazeera_canli_blog(self):
        self.assertEqual(
            ozet(
                "Live updatesLive updates, Iran war live: Tehran says it won’t be bullied Rezaei says the US"
                " has a deadline. live This video may contain light patterns or images that could trigger"
                " seizures or cause discomfort for people with visual sensitivities. Published On 24 Sep 2026"
                " - In a defiant UN address, Pezeshkian rebuked a US threat.",
                "Iran war live: Tehran says it won’t be bullied",
                "aljazeera.com",
            ),
            "Rezaei says the US has a deadline. In a defiant UN address, Pezeshkian rebuked a US threat.",
        )

    def test_france24_youtube_uyarisi_ve_tarih_satiri(self):
        self.assertEqual(
            ozet(
                "Tigray rebels seize airports Africa To display this content from YouTube, you must enable"
                " advertisement tracking and audience measurement. One of your browser extensions seems to be"
                " blocking the video player from loading. To watch this content, you may need to disable it on"
                " this site. Issued on: 14:30 min From the show Reading time 1 min In tonight's edition, 11"
                " are killed. Also, TPLF fighters take over the airport.",
                "Tigray rebels seize airports",
                "france24.com",
            ),
            "In tonight's edition, 11 are killed. Also, TPLF fighters take over the airport.",
        )

    def test_france24_metin_sonundaki_youtube_uyarisi(self):
        self.assertEqual(
            ozet(
                "Zelensky told the UN General Assembly on Wednesday. To display this content from YouTube,"
                " you must enable advertisement tracking and audience measurement. One of your browser"
                " extensions seems to be blocking the video player from loading. To watch this content, you"
                " may need to disable it on this site.",
                "Putin using citizens from 47 countries",
                "france24.com",
            ),
            "Zelensky told the UN General Assembly on Wednesday.",
        )

    def test_dw_baslik_ve_tarih(self):
        self.assertEqual(
            ozet(
                "Warnings of famine grow in Ukrainian town of Oleshky September 23, 2026 A man sends a"
                " photo. Second.",
                "Famine threatens Ukrainian town of Oleshky",
                "dw.com",
            ),
            "A man sends a photo. Second.",
        )

    def test_dw_cumle_icindeki_tarih_korunur(self):
        metin = "On September 23, 2026, the council voted. It passed."
        self.assertEqual(ozet(metin, "Council vote", "dw.com"), metin)

    def test_scmp_reklam_baslik_ve_okuma_suresi(self):
        self.assertEqual(
            ozet(
                "Advertisement Big picture or big deals? What the summit holds The focus may be about"
                " optics, observers say 4-MIN READ4-MIN 1 Listen With the balance of power shifting,"
                " talks began. Second.",
                "Big picture or big deals? What the summit holds",
                "scmp.com",
            ),
            "The focus may be about optics, observers say With the balance of power shifting, talks"
            " began. Second.",
        )

    def test_scmp_sesli_okuma_satiri_kesilir(self):
        self.assertEqual(
            ozet(
                "Fendi showed sheer dresses. Advertisement Select Voice Select Speed 1x AI-generated voice",
                "X",
                "scmp.com",
            ),
            "Fendi showed sheer dresses.",
        )

    def test_scmp_mektup_cagrisi(self):
        self.assertEqual(
            ozet(
                "Feel strongly about these letters, or any other aspects of the news? Share your views by"
                " emailing us your Letter to the Editor or filling in this form. Submissions should not"
                " exceed 400 words. As policymakers gathered, attention focused on AI.",
                "X",
                "scmp.com",
            ),
            "As policymakers gathered, attention focused on AI.",
        )

    def test_sciencedaily_tarih_kaynak_blogu(self):
        self.assertEqual(
            ozet(
                "More REM sleep linked to lower risk of 83 diseases Tracking sleep revealed links. - Date:"
                " - September 23, 2026 - Source: - PLOS - Summary: - A large study suggests a link.",
                "More REM sleep linked to lower risk of 83 diseases",
                "sciencedaily.com",
            ),
            "Tracking sleep revealed links. A large study suggests a link.",
        )

    def test_sciencedaily_paylas_butonlari(self):
        self.assertEqual(
            ozet(
                "Arctic melt season stalls The melt season is 40 days longer. Clouds may explain the pause."
                " - Share: For most of the satellite record, the season kept getting longer.",
                "Arctic melt season stalls",
                "sciencedaily.com",
            ),
            "The melt season is 40 days longer. Clouds may explain the pause. For most of the satellite"
            " record, the season kept getting longer.",
        )

    def test_physorg_editor_kunyesi(self):
        self.assertEqual(
            ozet("Gaby Clark Scientific Editor Robert Egan Senior Editor A simplified model suggests decoherence"
                 " can suppress tunneling. The vacuum is not always so empty.", "Cosmic lockdown", "phys.org"),
            "A simplified model suggests decoherence can suppress tunneling. The vacuum is not always so empty.",
        )
        self.assertEqual(
            ozet("Robert Egan Senior Editor The age-adjusted suicide rate increased. It then plateaued.", "x", "phys.org"),
            "The age-adjusted suicide rate increased. It then plateaued.",
        )
        # Canlıdaki gerçek hal: gövde başlıkla başlıyor, künye ondan sonra
        self.assertEqual(
            ozet("Cosmic lockdown: How the environment can isolate quantum fields Gaby Clark Scientific Editor"
                 " Robert Egan Senior Editor A simplified model suggests decoherence. It works.",
                 "Cosmic lockdown: How the environment can isolate quantum fields", "phys.org"),
            "A simplified model suggests decoherence. It works.",
        )
        self.assertEqual(
            ozet("Storm season Andrew Zinin Lead Editor The Pacific has seen storms. More are coming.", "Storm season",
                 "phys.org"),
            "The Pacific has seen storms. More are coming.",
        )
        # Metnin ortasında, bir giriş cümlesinden sonra
        self.assertEqual(
            ozet("Policy shift Rules must change, says a forum. Sadie Harley Scientific Editor Robert Egan Senior"
                 " Editor Governments act slowly.", "Policy shift", "phys.org"),
            "Rules must change, says a forum. Governments act slowly.",
        )
        # Künye olmayan "editor" geçen cümle korunur
        self.assertEqual(
            ozet("X Jane Doe, a senior editor at Nature, disagreed. The Editor said no.", "X", "phys.org"),
            "Jane Doe, a senior editor at Nature, disagreed. The Editor said no.",
        )

    def test_variety_popular_kutusu(self):
        self.assertEqual(
            ozet("Their films are entertaining takes on serious subjects.” Popular on Variety “This is the same"
                 " here,” added Pösö.", "Halima", "variety.com"),
            "Their films are entertaining takes on serious subjects.” “This is the same here,” added Pösö.",
        )

    def test_sciencenews_yapay_zeka_seslendirme_notu(self):
        self.assertEqual(
            ozet(
                "Will the U.S. megadrought ever end? A controversial new hypothesis suggests “No” This is"
                " a human-written story voiced by AI. Got feedback? Take our survey . (See our AI policy"
                " here .) Kearny, Ariz., is a town on the brink.",
                "Will the U.S. megadrought ever end?",
                "sciencenews.org",
            ),
            "A controversial new hypothesis suggests “No” Kearny, Ariz., is a town on the brink.",
        )

    def test_lonelyplanet_komisyon_notu(self):
        self.assertEqual(
            ozet(
                "Lonely Planet may earn a commission from affiliate links on our site. All recommendations"
                " and reviews reflect our own independent opinions. Real New Yorkers know that fall is"
                " the best season.",
                "Fall in New York City",
                "lonelyplanet.com",
            ),
            "Real New Yorkers know that fall is the best season.",
        )

    def test_eater_bulten_tanitimi(self):
        self.assertEqual(
            ozet(
                "The owner talks branding. This excerpt was originally published in Pre Shift, our"
                " newsletter for the hospitality industry. Subscribe for more first-person accounts,"
                " advice, and interviews. This is the first installment.",
                "Hoy Is Bringing Night-Market Energy to NYC",
                "eater.com",
            ),
            "The owner talks branding. This is the first installment.",
        )


class BaslikSonu(unittest.TestCase):
    def test_kaynak_adi_silinir(self):
        for baslik, kaynak, beklenen in [
            ("McDonald’s is spending billions to make major changes | CNN Business", "cnn.com",
             "McDonald’s is spending billions to make major changes"),
            ("Australia confirms F-35 fighter jet parts were diverted | CNN", "cnn.com",
             "Australia confirms F-35 fighter jet parts were diverted"),
            ("YouTube is making comments more fun | TechCrunch", "techcrunch.com", "YouTube is making comments more fun"),
            ("Czech Man Jailed 13 Days for Red Square Protest - The Moscow Times", "themoscowtimes.com",
             "Czech Man Jailed 13 Days for Red Square Protest"),
            ("20 things to know before visiting French Polynesia - Lonely Planet", "lonelyplanet.com",
             "20 things to know before visiting French Polynesia"),
        ]:
            with self.subTest(kaynak=kaynak):
                self.assertEqual(basligi_temizle(baslik, kaynak), beklenen)

    def test_basligin_parcasi_korunur(self):
        # Tire/iki nokta sonrası başlığın kendisi; başka kaynakta dokunulmaz.
        self.assertEqual(basligi_temizle("Who is skipping the UN General Assembly — and why", "dw.com"),
                         "Who is skipping the UN General Assembly — and why")
        self.assertEqual(basligi_temizle("Live updates: CNN, MS NOW and Politico allowed back", "cnn.com"),
                         "Live updates: CNN, MS NOW and Politico allowed back")


class OrtakDavranis(unittest.TestCase):
    def test_baslik_cumlenin_basiysa_kirpilmaz(self):
        metin = "Karak chai (strong tea in Hindi) is a style of masala chai. Second."
        self.assertEqual(ozet(metin, "Karak Chai", "bonappetit.com"), metin)

    def test_baslik_tekrari_her_kaynakta_kirpilir(self):
        self.assertEqual(
            ozet("Turkey to hand over base Turkey will hand over the base. More.", "Turkey to hand over base",
                 "france24.com"),
            "Turkey will hand over the base. More.",
        )

    def test_kural_baska_kaynaga_dokunmaz(self):
        metin = "Headline here - Published Body starts. More."
        self.assertEqual(ozet(metin, "X", "theguardian.com"), metin)

    def test_cumle_sayisi_k_ile_sinirli(self):
        self.assertEqual(ozet("A one. B two. C three. D four.", "X", "dw.com", k=2), "A one. B two.")

    def test_bos_metin(self):
        self.assertEqual(ozet("", "X", "bbc.co.uk"), "")

    def test_video_sayfalari_atlanir(self):
        self.assertTrue(ATLANAN_ADRES.search("https://www.cnn.com/2026/09/23/politics/video/x"))
        self.assertTrue(ATLANAN_ADRES.search("https://www.aljazeera.com/video/newsfeed/2026/9/24/x"))
        self.assertTrue(ATLANAN_ADRES.search("https://www.bbc.co.uk/iplayer/episode/m0032301"))
        self.assertFalse(ATLANAN_ADRES.search("https://www.bbc.co.uk/news/articles/c4g"))
        self.assertFalse(ATLANAN_ADRES.search(
            "https://www.scmp.com/news/china/article/3368596/video-us-military-adjusting-red-carpet"))

    def test_kural_anahtarlari_gercek_kaynak_adlari(self):
        # Yazım hatalı bir anahtar ("bbc.com" gibi) sessizce hiç uygulanmazdı.
        kaynaklar = {ad for _, ad, _ in KAYNAKLAR}
        self.assertEqual(set(KAYNAK_KURALLARI) - kaynaklar, set())


if __name__ == "__main__":
    unittest.main()
