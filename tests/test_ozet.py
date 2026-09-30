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

    def test_guardian_tarif_malzeme_listesi_kesilir(self):
        self.assertEqual(
            ozet("Cornbread isn’t a loaf in the conventional sense. It is substantial enough to be the main event."
                 " Prep 10 min Soak 2 hr Cook 25 min Serves 6 200g coarse cornmeal 240ml buttermilk.",
                 "How to make cornbread", "theguardian.com"),
            "Cornbread isn’t a loaf in the conventional sense. It is substantial enough to be the main event.",
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

    def test_guardian_dizi_adi_silinir(self):
        self.assertEqual(
            basligi_temizle("How to make cornbread – recipe | Felicity Cloake's masterclass", "theguardian.com"),
            "How to make cornbread – recipe",
        )
        self.assertEqual(basligi_temizle("Sebb's, Glasgow G1: restaurant review", "theguardian.com"),
                         "Sebb's, Glasgow G1: restaurant review")

    def test_basligin_parcasi_korunur(self):
        # Tire/iki nokta sonrası başlığın kendisi; başka kaynakta dokunulmaz.
        self.assertEqual(basligi_temizle("Who is skipping the UN General Assembly — and why", "dw.com"),
                         "Who is skipping the UN General Assembly — and why")
        self.assertEqual(basligi_temizle("Live updates: CNN, MS NOW and Politico allowed back", "cnn.com"),
                         "Live updates: CNN, MS NOW and Politico allowed back")


class OrtakDavranis(unittest.TestCase):
    def test_baslik_cumlenin_basiysa_kirpilmaz(self):
        metin = "Karak chai (strong tea in Hindi) is a style of masala chai. Second."
        self.assertEqual(ozet(metin, "Karak Chai", "eater.com"), metin)

    def test_baslik_tekrari_her_kaynakta_kirpilir(self):
        self.assertEqual(
            ozet("Turkey to hand over base Turkey will hand over the base. More.", "Turkey to hand over base",
                 "france24.com"),
            "Turkey will hand over the base. More.",
        )

    def test_kural_baska_kaynaga_dokunmaz(self):
        metin = "Headline here - Published Body starts. More."
        self.assertEqual(ozet(metin, "X", "theguardian.com"), metin)

    def test_turkce_buyuk_harfle_baslayan_cumleler(self):
        metin = "Toplantı sona erdi. Çarşamba günü yeniden başlayacak. İstanbul'da hava güzel. Şirket açıklama yaptı."
        self.assertEqual(ozet(metin, "X", "tr.euronews.com", k=2), "Toplantı sona erdi. Çarşamba günü yeniden başlayacak.")

    def test_tekrarlanan_giris_cumlesi_bir_kez(self):
        metin = ("“Ölü Deniz” gösterisi nedeniyle hapis cezası talep ediliyor. Komedyen bugün hakim karşısına"
                 " çıkacak. \"Ölü Deniz\" gösterisi nedeniyle hapis cezası talep ediliyor. Duruşma saat 10'da.")
        self.assertEqual(
            ozet(metin, "X", "tr.euronews.com", k=3),
            "“Ölü Deniz” gösterisi nedeniyle hapis cezası talep ediliyor. Komedyen bugün hakim karşısına çıkacak."
            " Duruşma saat 10'da.",
        )

    def test_saveur_sponsorlu_yazi_atlanir(self):
        import re
        from ayarlar import ATLANAN_BOLUMLER
        kalip = ATLANAN_BOLUMLER[("Yemek", "saveur.com")]
        self.assertTrue(re.search(kalip, "https://www.saveur.com/sponsored-post/making-prosciutto-di-parma/"))
        self.assertFalse(re.search(kalip, "https://www.saveur.com/food/sicilian-caponata-recipe/"))

    def test_guardian_kulturde_muzik_tv_yasam_atlanir(self):
        import re
        from ayarlar import ATLANAN_BOLUMLER
        kalip = ATLANAN_BOLUMLER[("Sanat & Kültür", "theguardian.com")]
        for adres, atlanir in [
            ("https://www.theguardian.com/music/2026/sep/28/mtv-vmas-2026", True),
            ("https://www.theguardian.com/tv-and-radio/2026/sep/27/x", True),
            ("https://www.theguardian.com/lifeandstyle/2026/sep/27/eve", True),
            ("https://www.theguardian.com/books/2026/sep/28/range-review", False),
            ("https://www.theguardian.com/stage/2026/sep/27/tru-review", False),
            ("https://www.theguardian.com/artanddesign/2026/sep/28/korea", False),
        ]:
            self.assertEqual(bool(re.search(kalip, adres)), atlanir, adres)

    def test_liste_numarasi_cumle_sayilmaz(self):
        self.assertEqual(
            ozet("Here are the films to watch. 1. Digger Tom Cruise is back. He plays a billionaire.", "X", "x", k=3),
            "Here are the films to watch. Digger Tom Cruise is back. He plays a billionaire.",
        )

    def test_eater_sponsorlu_dizi_notu(self):
        self.assertEqual(
            ozet("Sharing experiences is the way to connect. This is the second installment of our series Getting on the"
                 " Map, presented by Apple Maps. Guest shifts are everywhere.", "Himkok", "eater.com"),
            "Sharing experiences is the way to connect. Guest shifts are everywhere.",
        )

    def test_saveur_porsiyon_ve_malzeme_listesi(self):
        self.assertEqual(
            ozet("Also known as dirty yak, this dish is woven into the city. - Serves2–4 - Time25 minutes Yat gaw mein"
                 " is a Baltimore classic. The ketchup adds punch. Ingredients - Kosher salt - 1 lb. fresh noodles",
                 "Baltimore Yat Gaw Mein", "saveur.com"),
            "Also known as dirty yak, this dish is woven into the city. Yat gaw mein is a Baltimore classic."
            " The ketchup adds punch.",
        )

    def test_guardian_puan_listesi_kesilir(self):
        self.assertEqual(
            ozet("The best ones have a wonderful fattiness. The worst tasted of stale biscuits. Best overall:"
                 " Waitrose No 1 cheesecake ★★★★☆ Dangerously moreish.", "Cheesecake", "theguardian.com"),
            "The best ones have a wonderful fattiness. The worst tasted of stale biscuits.",
        )

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

    def test_techcrunch_etkinlik_reklami_ve_kucuk_yatirim_turu_atilir(self):
        from ozet import atlanacak_mi
        for baslik in [
            "Disrupt 2026 exhibitor program extended until Oct 2",
            "More Ways to Disrupt: New 2026 Side Events from KOTRA, WayFounder, Enterprise Ireland",
            "Next five VCs judging Startup Battlefield 200 at Disrupt 2026",
            "Insurtech Outmarket raises $34.5M just months after prior round",
            "Protego Ventures closes debut $125 million fund for Israeli defense tech",
            "Enveda secures $311M to bring more nature-derived AI drugs into clinical trials",
            "Peak XV ups Surge seed investment ceiling to $5M, unveils 18-startup cohort",
        ]:
            self.assertTrue(atlanacak_mi(baslik, "techcrunch.com"), baslik)
        # Milyar dolarlık turlar, para geçen ama yatırım olmayan haberler
        # ve başka kaynaklar kalır.
        for baslik in [
            "Viral AI agent Instinct raises $1B Series C at a $10B valuation",
            "OpenAI reportedly in talks to raise $30B round at $1.4T valuation",
            "TikTok agrees to pay at least $100M in Alabama settlement",
            "North Korean hackers suspected in $351M crypto theft, the largest so far this year",
            "OpenAI launches Dots, its bubbly agentic avatar",
        ]:
            self.assertFalse(atlanacak_mi(baslik, "techcrunch.com"), baslik)
        self.assertFalse(atlanacak_mi("Insurtech Outmarket raises $34.5M", "bbc.co.uk"))

    def test_restofworld_sirket_tanitim_balonu(self):
        metin = (
            "When Chinese regulators blocked Hugging Face in 2023, it opened a market for domestic alternatives. "
            "AlibabaAlibabaAlibaba, founded in 1999 by Chinese entrepreneur Jack Ma, is one of the most prominent "
            "global e-commerce companies that operates platforms like AliExpress, Taobao, and Tmall.READ MORE had "
            "launched a Hugging Face-like open-model platform, ModelScope, in 2022."
        )
        self.assertEqual(
            ozet(metin, "The open-source AI platforms vying to become China’s Hugging Face", "restofworld.org"),
            "When Chinese regulators blocked Hugging Face in 2023, it opened a market for domestic alternatives. "
            "Alibaba had launched a Hugging Face-like open-model platform, ModelScope, in 2022.",
        )
        # Sıradan metinde yinelenen ad yoksa dokunulmaz.
        sade = "Samsung has more than doubled its market share. Read more about SK Hynix here."
        self.assertEqual(ozet(sade, "Chips", "restofworld.org"), sade)

    def test_etikete_gore_ayiklama(self):
        # Etiketler 30.09.2026 teşhisinden (sayfa etiketi + kategori, küçük harf).
        from besleme import sayfa_etiketleri
        from ozet import atlanacak_mi
        self.assertEqual(
            sayfa_etiketleri({"tags": ["startup battlefield 200,techcrunch disrupt"], "categories": ["Biotech & Health", "Startups"]}),
            ["startup battlefield 200", "techcrunch disrupt", "biotech & health", "startups"],
        )
        tc = "techcrunch.com"
        # Başlıkta hiçbir ipucu yok; yalnız etiket gösteriyor (Disrupt yarışmacısı).
        self.assertTrue(atlanacak_mi("After losing his voice to cancer, this founder is building ‘glasses for voice’", tc,
                                     ["uhura bionics", "startup battlefield 200", "techcrunch disrupt", "biotech & health"]))
        self.assertTrue(atlanacak_mi("TechCrunch Founder Summit 2026: Everything you need to know", tc,
                                     ["techcrunch founder summit", "startups", "venture"]))
        self.assertTrue(atlanacak_mi("Ando wants to take on Slack with a team messaging app", tc,
                                     ["slack", "ando", "ai", "fundraising", "startups"]))
        # Milyar dolarlık tur, haftalık bülten ve sıradan haber kalır.
        self.assertFalse(atlanacak_mi("Viral AI agent Instinct raises $1B Series C at a $10B valuation", tc,
                                      ["instinct", "ai assistant", "ai", "fundraising"]))
        self.assertFalse(atlanacak_mi("TechCrunch Mobility: AV companies pick their lanes", tc,
                                      ["avs", "zoox", "waymo", "techcrunch mobility", "transportation"]))
        self.assertFalse(atlanacak_mi("OpenAI launches GPT-6.1 Sol, says it nearly matches GPT-6 Astra", tc,
                                      ["openai", "openai devday", "ai"]))
        # The Verge: başlıkta "off" yok, etiket indirim diyor.
        self.assertTrue(atlanacak_mi("Sadly, this $1,549 RTX 5070-equipped gaming PC is a very good deal", "theverge.com",
                                     ["theverge", "pagetype:story", "good-deals", "gadgets", "shopping"]))
        self.assertFalse(atlanacak_mi("Googlebooks might be the real deal", "theverge.com",
                                      ["theverge", "pagetype:story", "installer-newsletter", "tech"]))
        # Başka kaynakta bu etiketler bir şey ifade etmez.
        self.assertFalse(atlanacak_mi("Climate summit opens", "bbc.co.uk", ["summit", "fundraising"]))

    def test_guardian_ingiltere_ici_gezi_yazilari(self):
        # Etiketler 30.09.2026 teşhisinden.
        from ozet import atlanacak_mi
        g = "theguardian.com"
        for baslik, etiketler in [
            ("15 great cottages and cabins for an autumn escape in the UK",
             ["cottages", "life and style", "travel", "self-catering", "united kingdom holidays"]),
            ("Kent is having a champagne moment: ‘English wine has gone from a joke to world-class’",
             ["wine holidays", "kent holidays", "england holidays", "united kingdom holidays", "travel"]),
        ]:
            self.assertTrue(atlanacak_mi(baslik, g, etiketler), baslik)
        for baslik, etiketler in [
            ("Taking a deep dive in Helsinki’s subterranean city",
             ["helsinki holidays", "finland holidays", "city breaks", "europe holidays", "travel"]),
            ("£600 for cheese? The Brazilian beach scams that cost visitors dear",
             ["scams", "brazil holidays", "south america holidays", "travel", "uk news", "world news"]),
        ]:
            self.assertFalse(atlanacak_mi(baslik, g, etiketler), baslik)

    def test_gundem_gurultu_bolumleri_atlanir(self):
        # Adresler 30.09.2026 teşhisinden.
        import re
        from ayarlar import ATLANAN_BOLUMLER
        for kaynak, adres, atlanir in [
            ("aljazeera.com", "https://www.aljazeera.com/sports/2026/9/30/nigeria-and-ghana-suffer-afcon-shocks", True),
            ("aljazeera.com", "https://www.aljazeera.com/news/2026/9/30/lebanese-prisoners-on-hunger-strike", False),
            ("cnn.com", "https://www.cnn.com/travel/mountains-of-heaven-ak-suu-transverse", True),
            ("cnn.com", "https://www.cnn.com/2026/09/29/sport/oregon-qb-moore-concussion", True),
            ("cnn.com", "https://www.cnn.com/2026/09/30/economy/trumps-tariffs-are-back-in-court-again", False),
            ("scmp.com", "https://www.scmp.com/news/hong-kong/hong-kong-economy/article/3369312/ip-financing", True),
            ("scmp.com", "https://www.scmp.com/news/hong-kong/politics/article/3369000/national-security-law", False),
            ("scmp.com", "https://www.scmp.com/lifestyle/food-drink/article/3369179/wine-writers-picks", True),
            ("scmp.com", "https://www.scmp.com/native/business/topics/hong-kong-global-hub-talent/article/3369062/x", True),
            ("scmp.com", "https://www.scmp.com/news/china/diplomacy/article/3369303/eu-weighs-trade-powers", False),
            ("france24.com", "https://www.france24.com/en/tv-shows/the-debate/20260929-still-the-same-far-right", True),
            ("france24.com", "https://www.france24.com/en/middle-east/20260930-us-forces-leave-iraq", False),
            ("france24.com", "https://www.france24.com/en/sport/20260928-italy-rebound-in-turkey", True),
            ("bbc.co.uk", "https://www.bbc.co.uk/sport/football/articles/ckddvv5dn4eyo", True),
            ("bbc.co.uk", "https://www.bbc.co.uk/news/articles/c51kx9ze1mdzo", False),
        ]:
            self.assertEqual(bool(re.search(ATLANAN_BOLUMLER[("Gündem", kaynak)], adres)), atlanir, adres)

    def test_aa_protokol_haberleri_atilir(self):
        from ozet import atlanacak_mi
        for baslik in [
            "Turkish foreign minister meets premier of Germany's North Rhine-Westphalia",
            "Turkish President Erdogan receives premier of Germany’s North Rhine-Westphalia state",
            "Turkish, Indonesian presidents discuss bilateral ties, regional issues in phone call",
            "Türkiye, UAE discussed bilateral ties, regional challenges: Turkish foreign minister",
            "Turkish foreign minister attends Mecca defense pact meeting",
            "Turkish army chief to visit Saudi Arabia to attend Mecca defense pact chiefs of staff meeting",
            "WRAP-UP - Turkish President Erdogan wraps up New York visit",
        ]:
            self.assertTrue(atlanacak_mi(baslik, "aa.com.tr"), baslik)
        for baslik in [
            "President Erdogan says Türkiye will not back down from support for Palestinians",
            "German state premier calls for reform of EU-Türkiye Customs Union",
            "Türkiye, Saudi Arabia, Pakistan condemn attacks on Mecca, discuss joint military support",
            "Historic Greek church in central Türkiye set to open to public soon",
            "Türkiye to host global cybersecurity conference to discuss threats, national capabilities",
        ]:
            self.assertFalse(atlanacak_mi(baslik, "aa.com.tr"), baslik)
        # Başka kaynakta aynı kelimeler haberin kendisi olabilir.
        self.assertFalse(atlanacak_mi("Trump meets Xi in Washington", "bbc.co.uk"))

    def test_euronews_ve_cnn_tanitim_derleme(self):
        from ozet import atlanacak_mi
        e = "tr.euronews.com"
        self.assertTrue(atlanacak_mi("Avrupa'nın savunma ve güvenlik liderleri Euronews zirvesi için Brüksel'de buluşuyor", e,
                                     ["euronews", "mark rutte", "zirve", "brüksel"]))
        # "kültür ajandası" etiketli kültür yazıları kalır; magazin gider.
        self.assertFalse(atlanacak_mi("Van Gölü altında gizemli yapılar: Kayıp bir kent bulunmuş olabilir mi?", e,
                                      ["dalgıç", "van gölü", "arkeoloji", "kültür ajandası"]))
        self.assertTrue(atlanacak_mi("Taylor Swift, MTV VMA’larda en çok ödül alan sanatçı rekorunu kırdı", e,
                                     ["pop müziği", "taylor swift", "müzik", "magazin dünyasi", "kültür ajandası"]))
        self.assertTrue(atlanacak_mi("Chud'dan Bop'a: 2026'da en çok aranan Gen Alpha argoları açıklandı", e,
                                     ["viral", "diller", "genç jenerasyon", "lifestyle"]))
        self.assertTrue(atlanacak_mi("Kültür seçkisi: Avrupa’da haftanın öne çıkan kültür etkinlikleri", e))
        self.assertTrue(atlanacak_mi("Euronews Seyahat ve Turizm Zirvesi 2026: Bugün Brüksel'den canlı izleyin", e))
        self.assertTrue(atlanacak_mi("Avrupa’da bu hafta: Görülecek, dinlenecek, izlenecek en iyi etkinlikler", e))
        self.assertFalse(atlanacak_mi("GRECO: Türkiye yolsuzlukla mücadele tavsiyelerinin çoğunu hâlâ uygulamadı", e,
                                      ["adalet", "yargı", "avrupa konseyi"]))
        self.assertTrue(atlanacak_mi("Grim mortgage milestone, brawling seniors, gut instinct: Catch up on the day’s stories",
                                     "cnn.com"))

    def test_bbc_turkce_kunye(self):
        metin = ("Tennessee eyaletinde, 200 yıl sonra ilk kez bir kadın idam edilecek\n  - Yazan, Stephanie Hegarty\n"
                 "  - Unvan, BBC Dünya Servisi\n- Yayın tarihi\n- Okuma süresi 6 dk\n"
                 "Ashlee Sellars, Christa Pike ile hapiste tanıştı. İkisi de gençti.")
        baslik = basligi_temizle("Christa Pike: Tennessee'de 200 yıl sonra idam edilecek ilk kadın - BBC News Türkçe",
                                 "bbc.com/turkce")
        self.assertEqual(baslik, "Christa Pike: Tennessee'de 200 yıl sonra idam edilecek ilk kadın")
        self.assertEqual(ozet(metin, baslik, "bbc.com/turkce"), "Ashlee Sellars, Christa Pike ile hapiste tanıştı. İkisi de gençti.")

    def test_dw_turkce_baslik_ve_tarih(self):
        metin = ("İsrail'e giden uçakta kaçırılma alarmı: Nedeni pilot kavgası\n30 Eylül 2026\n"
                 "Dubai'den Tel Aviv'e giden uçakta alarm verildi. Uçak Suudi Arabistan'a indi.")
        self.assertEqual(ozet(metin, "İsrail'e giden uçaktaki kaçırılma alarmı pilot kavgası çıktı", "dw.com/tr"),
                         "Dubai'den Tel Aviv'e giden uçakta alarm verildi. Uçak Suudi Arabistan'a indi.")

    def test_africanews_ulke_etiketi(self):
        for ulke in ("Libya", "Democratic Republic Of Congo"):
            metin = f"{ulke}\nPublic school teachers are continuing their strike. Demonstrations were held."
            self.assertEqual(ozet(metin, "Libyan teachers extend strike", "africanews.com"),
                             "Public school teachers are continuing their strike. Demonstrations were held.")
        # İlk satır bir cümleyse dokunulmaz.
        metin = "Morocco's king named the first woman premier on Tuesday.\nShe pledged reforms."
        self.assertEqual(ozet(metin, "Morocco appoints premier", "africanews.com"), "Morocco's king named the first woman premier on Tuesday. She pledged reforms.")
        self.assertEqual(basligi_temizle("Libyan teachers extend strike over pay | Africanews", "africanews.com"),
                         "Libyan teachers extend strike over pay")

    def test_guardian_kultur_tv_yazilari(self):
        # Etiketler 30.09.2026 teşhisinden.
        from ozet import atlanacak_mi
        g = "theguardian.com"
        self.assertTrue(atlanacak_mi("SKF advert review – let’s hope this dull AI Greta Garbo is not the future", g,
                                     ["greta garbo", "ai (artificial intelligence)", "television", "culture", "film"]))
        self.assertTrue(atlanacak_mi("Jon Stewart on Trump offering to sell weapons to China", g,
                                     ["late-night tv roundup", "jon stewart", "comedy", "culture"]))
        self.assertFalse(atlanacak_mi("Digger review – Tom Cruise’s loudmouth oil tycoon goes hard", g,
                                      ["film", "drama films", "comedy films", "tom cruise", "culture"]))
        self.assertFalse(atlanacak_mi("Renoir and Love review – ‘The happiest exhibition of the year!’", g,
                                      ["art", "art and design", "culture", "painting", "exhibitions"]))

    def test_aeon_sesli_okuma_satiri(self):
        metin = ("Listen to this essay\n30 minute listen\nWilliam came to me for a third opinion. He was 53 and healthy.")
        baslik = basligi_temizle("We need a better way to describe what is often called ‘cancer’ | Aeon Essays", "aeon.co")
        self.assertEqual(baslik, "We need a better way to describe what is often called ‘cancer’")
        self.assertEqual(ozet(metin, baslik, "aeon.co"), "William came to me for a third opinion. He was 53 and healthy.")

    def test_lithub_liste_yazilari(self):
        from ozet import atlanacak_mi
        l = "lithub.com"
        for baslik in ["The 12 Best Book Covers of September",
                       "Cheever on Cheever! Tracy K. Smith! 20 great books out in paperback this month.",
                       "Lit Hub Daily: September 30, 2026"]:
            self.assertTrue(atlanacak_mi(baslik, l), baslik)
        for baslik in ["A Reticent Eloquence: Colm Tóibín on the Poetry of Thom Gunn",
                       "On the Secret Three-Man Mission Deep in Nazi Europe That Won WWII"]:
            self.assertFalse(atlanacak_mi(baslik, l), baslik)
        self.assertEqual(
            ozet("Today is International Translation Day. This first appeared in Lit Hub’s Literary History newsletter—sign"
                 " up here. Saint Jerome is the patron saint of translators.", "Happy International Translation Day!",
                 "lithub.com"),
            "Today is International Translation Day. Saint Jerome is the patron saint of translators.")

    def test_guardian_muzikal(self):
        from ozet import atlanacak_mi
        self.assertTrue(atlanacak_mi("‘They’ll never bring us dowwwwwwwn!’ Wicked’s stars pick their favourite songs",
                                     "theguardian.com", ["stage", "musicals", "theatre", "culture", "west end"]))
        self.assertFalse(atlanacak_mi("School Girls; Or, The African Mean Girls Play review – comedy makes a near-flawless"
                                      " Broadway debut", "theguardian.com", ["broadway", "stage", "theatre", "comedy"]))

    def test_mercopress_falkland_yereli(self):
        from ozet import atlanacak_mi
        m = "mercopress.com"
        self.assertTrue(atlanacak_mi("Falklands Legislator meets PM Burnham and cabinet members at Liverpool", m))
        self.assertTrue(atlanacak_mi("Chile's defence minister backs trade between Punta Arenas and the Falklands", m))
        self.assertFalse(atlanacak_mi("Lula remark on medical exams sparks controversy five days before the vote", m))

    def test_verge_indirim_haberleri_atilir(self):
        from ozet import atlanacak_mi
        for baslik in [
            "Razer’s low-latency wireless gaming keyboard is almost half off",
            "Dreame’s step-climbing X50 Ultra mopping vacuum is hundreds off",
            "The best early October Prime Day deals happening now",
            "Sony’s WH-1000XM6 headphones are $100 off",
        ]:
            self.assertTrue(atlanacak_mi(baslik, "theverge.com"), baslik)
        for baslik in [
            "Firefox just got a redesign with round tabs, new themes, and Compact Mode",
            "Walmart won’t hike prices based on your shopping history, CEO says",
            "OpenAI DevDay kicks off with protests outside",
        ]:
            self.assertFalse(atlanacak_mi(baslik, "theverge.com"), baslik)

    def test_kural_anahtarlari_gercek_kaynak_adlari(self):
        # Yazım hatalı bir anahtar ("bbc.com" gibi) sessizce hiç uygulanmazdı.
        kaynaklar = {ad for _, ad, _ in KAYNAKLAR}
        self.assertEqual(set(KAYNAK_KURALLARI) - kaynaklar, set())


if __name__ == "__main__":
    unittest.main()
