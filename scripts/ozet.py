"""Makale gövdesinden özet üretimi ve kaynağa özgü özet temizliği."""

import re

_AY = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"

# Kaynağa özgü özet temizliği. Her kural, canlı sitedeki özetlerde o
# kaynakta görülen bir kalıptan yazıldı; bir kaynak sayfa düzenini
# değiştirirse sadece kendi bloğu düzenlenir, bir kaynağın kuralı
# başkasının metnine dokunmaz. Değişiklikten sonra tests/test_ozet.py
# çalıştırılır (her kural için gerçek bir örnek var).
#   sil      : metnin her yerinden silinir (başlık kırpılmadan önce); kalıpta
#              "kalan" adlı grup varsa o kısım bırakılır
#   bas      : başlık kırpıldıktan sonra metnin başında kalırsa silinir
#   kes      : bu kalıptan itibaren metnin geri kalanı atılır
#   cumle_at : bu kalıbı içeren cümle özetten çıkarılır (harf büyüklüğü fark etmez)
#   baslik_sonu : başlığın sonundaki kaynak adı ("… | TechCrunch"); başlıktan
#                 silinir (kaynak adı kartta zaten yazıyor)
#   etiket_at : yayıncının sayfa etiketlerinden (bkz. besleme.sayfa_etiketleri)
#              biri bu kalıba uyan haber hiç alınmaz. Reklam, indirim, etkinlik
#              gibi "türü" belli yazılar için başlık kalıbından güvenilir:
#              yazar hangi kelimeyi seçerse seçsin etiket aynı.
#   haber_at : başlığı bu kalıba uyan haber hiç alınmaz (etiketin yedeği;
#              etiketi olmayan yazılar ve arşiv için); harf büyüklüğü fark etmez
#   birak    : başlığı bu kalıba uyan haber etiket_at/haber_at'a rağmen alınır
#   ilk_satir_at : metnin ilk satırı (boşluklar birleştirilmeden önce) bu
#              kalıba uyarsa atılır (Africanews'ün "Libya" gibi ülke etiketi)
#   ara_baslik_at : metnin içinde başlıkla aynı olan satır ve ardından gelen
#              satır bu kalıba uyarsa o da (alt başlık) atılır (The Verge)
KAYNAK_KURALLARI: dict[str, dict[str, list[str]]] = {
    "bbc.co.uk": {
        # Sayfadaki başlık satırı " - Published" ile bitiyor; meta
        # başlıktan farklı yazılabildiği için bu işaretten tanınıyor.
        "sil": [r"^.{0,250}?\s-\s(?:Published|Updated)\s+"],
        "bas": [r"Published|Updated"],
        # Sayfa sonu konu listesi ve metne gömülü "ilgili haberler":
        # " - Could AI wipe out humans? - Published5 days ago - …"
        "kes": [r"Related topics\b", r"\s-\s(?:(?!\s-\s).){5,200}?\s-\sPublished\s?\d"],
        "cumle_at": [r"^Watch:"],
    },
    "cnn.com": {
        # "… | CNN", "… | CNN Politics", "… | CNN Business"
        "baslik_sonu": [r"\s*\|\s*CNN(?:\s+[A-Z][A-Za-z&]*)*\s*$"],
        # Video olmayan sayfalara da gömülen video blokları (yukarıda).
        "kes": [r"Latest Videos\b", r"\d{1,2}:\d{2} • Source:"],
        # Günün haberlerinin derlemesi ("Grim mortgage milestone, brawling
        # seniors, gut instinct: Catch up on the day’s stories").
        "haber_at": [r"Catch up on the day[’']s stories"],
        # Canlı yayın sayfalarının başındaki "Here's the latest •" başlığı.
        "sil": [r"Video Ad Feedback\s*", r"^Here[’']s the latest\s*•?\s*"],
        # Hassas haberlerin başındaki yardım hattı notu.
        "cumle_at": [
            r"^EDITOR[’']S NOTE", r"^Help is available if you", r"call or text 988",
            r"International Association for Suicide Prevention", r"Befrienders Worldwide",
        ],
    },
    "aa.com.tr": {
        # Muhabir adı ve tarih satırı:
        # "Merve Gül Aydoğan Ağlarcı 24 September 2026•Update: 24 September 2026 US President…"
        "sil": [rf"^[^.!?]{{0,150}}?\d{{1,2}} {_AY} \d{{4}}\s*•\s*Update:\s*\d{{1,2}} {_AY} \d{{4}}\s*"],
        # Etkinlik haberlerindeki kendi tanıtımı: "Anadolu Agency is the
        # event’s global communications partner."
        "cumle_at": [r"Anadolu Agency is the \w+[’']s (?:global )?communications partner"],
        # Protokol haberleri: "Turkish foreign minister meets …", "Erdogan
        # receives …", "… discuss bilateral ties … in phone call", "…
        # wraps up New York visit". 7 günde Gündem'e giren AA haberlerinin
        # çoğu bu türdendi. Açıklama ve karar haberleri ("Erdogan says…",
        # "… calls for reform of Customs Union") kalır.
        "haber_at": [
            r"\b(?:meets|receives|hosts|attends|chairs|wraps up|bids farewell)\b",
            r"\bhold(?:s|ing)? (?:phone |bilateral )?talks\b",
            r"\bdiscuss(?:es|ed)? (?:bilateral|ties|regional issues)\b",
            r"\bphone (?:call|conversation)\b",
            r"\b(?:minister|president|chief|speaker|envoy|delegation) (?:to visit|visits)\b",
            r"\b(?:congratulates|condoles|offers condolences)\b",
            r"^WRAP-UP\b",
        ],
    },
    "aljazeera.com": {
        "sil": [
            # Canlı blog sayfaları: başlığın önündeki etiket, videodaki ışık
            # uyarısı ve tarih satırı.
            r"^Live updates(?:Live updates)?,?\s*",
            r"(?:\blive\s+)?This video may contain light patterns[^.]*\.\s*",
            r"Published On \d{1,2} [A-Z][a-z]{2} \d{4}\s*(?:-\s*)?",
        ],
        "bas": [r"NewsFeed"],
        # Metne gömülü "Recommended Stories list of 3 items - list 1 of 3…"
        # listesi. Son önerilen başlıkla metnin devamı arasında ayraç yok
        # ("…Al-Aqsa Mosque The demolition…"); bu yüzden listeyi içeren
        # cümle bütünüyle atılıyor, yerini sonraki cümle dolduruyor.
        "cumle_at": [r"Recommended Stories list of"],
    },
    "dw.com": {
        # Sayfadaki başlık (meta başlıktan farklı olabiliyor) + tarih:
        # "… Oleshky September 23, 2026 A man sends…". Yıldan sonra virgül
        # olmaması, cümle içindeki "On September 23, 2026, …"dan ayırıyor.
        "sil": [rf"^[^.!?]{{15,200}}?\s{_AY} \d{{1,2}}, \d{{4}}\s+(?=[A-Z\"“‘'])"],
        "bas": [rf"{_AY} \d{{1,2}}, \d{{4}}"],
    },
    "france24.com": {
        "sil": [
            # Gömülü YouTube oynatıcısının yerine gelen uyarı.
            r"To display this content from YouTube, you must enable advertisement tracking and audience measurement\.\s*",
            r"One of your browser extensions seems to be blocking the video player from loading\.\s*",
            r"To watch this content, you may need to disable it on this site\.\s*",
            # Başlık (+ "Africa" gibi bölüm adı) ve tarih/süre satırı:
            # "… Issued on: Modified: …", "… Issued on: 14:30 min From the
            # show Reading time 1 min …". Sayfadaki başlık meta başlıktan
            # farklı olabildiği için bu işaretten tanınıyor.
            r"^.{0,250}?\bIssued on:\s*(?:Modified:\s*)?(?:\d{1,2}:\d{2}\s*min\s*)?"
            r"(?:From the show\s*)?(?:Reading time \d+ min\s*)?",
        ],
    },
    "scmp.com": {
        "sil": [r"\bAdvertisement\s+", r"\d+-MIN READ(\d+-MIN)?\s*(\d+\s+)?(Listen\s+)?"],
        # Sesli okuma oynatıcısı: "Select Voice Select Speed 1x AI-generated voice"
        "kes": [r"Select Voice Select Speed"],
        # Okur mektubu sayfalarındaki "mektup gönderin" çağrısı.
        "cumle_at": [r"Letter to the Editor", r"Feel strongly about these letters", r"Submissions should not exceed"],
    },
    "tr.euronews.com": {
        # Kendi etkinlik ve yayın tanıtımları ("Euronews zirvesi için
        # Brüksel'de buluşuyor", "Bugün Brüksel'den canlı izleyin"), magazin
        # (Taylor Swift'in VMA rekoru) ve yaşam tarzı ("Gen Alpha argoları").
        # "kültür ajandası" etiketi kullanılmıyor: Van Gölü'ndeki yapılar,
        # Pera Müzesi sergisi gibi kültür yazılarının çoğunda var.
        "etiket_at": [r"^euronews$", r"^magazin dünyas[ıi]$", r"^lifestyle$"],
        "haber_at": [r"canlı izleyin", r"^Avrupa[’']da bu hafta", r"^Kültür seçkisi\b"],
    },
    "bbc.com/turkce": {
        "baslik_sonu": [r"\s+-\s+BBC News(?: Türkçe)?\s*$"],
        # Sayfadaki başlık (meta başlıktan farklı) ve künye: "… - Yazan,
        # Stephanie Hegarty - Unvan, BBC Dünya Servisi - Bildirdiği yer,
        # İstanbul - Yayın tarihi - Okuma süresi 6 dk Ashlee Sellars, …".
        "sil": [r"^.{0,600}?Okuma süresi \d+ dk\s*",
                r"^.{0,300}?-\s*Yazan,.{0,250}?-\s*Yayın tarihi\s*(?:-\s*Güncelleme[^-]{0,40})?"],
        # Görsel altı yazıları: "Görsel kaynağı, Getty Images Görsel altı
        # yazısı, …".
        "cumle_at": [r"Görsel kaynağı,", r"Görsel altı yazısı,"],
    },
    "t24.com.tr": {
        "baslik_sonu": [r"\s*\|\s*T24\s*$"],
        # Metin künyeyle başlıyor: "Haberler 30 Eylül 2026 13:28 Güncelleme:
        # 30 Eylül 2026 13:29 T24 Video Sakarya’nın Karasu ilçesinde…".
        # Başlangıçtaki etiket bilinen bölüm adlarıyla sınırlı: "Toplantı 1
        # Ekim 2026 10:00'da başladı" gibi sıradan bir cümleye dokunmasın.
        "sil": [r"^(?:Haberler|Dünya|Ekonomi|Gündem|Siyaset|Türkiye|Yaşam|Kültür Sanat|Bilim Teknoloji) "
                r"\d{1,2} [A-ZÇĞİÖŞÜa-zçğıöşü]+ \d{4} \d{2}:\d{2}"
                r"(?: Güncelleme: \d{1,2} [A-ZÇĞİÖŞÜa-zçğıöşü]+ \d{4} \d{2}:\d{2})?(?: T24 Video)?\s*"],
        # Gömülü videonun boş sayfası ("- YouTube").
        "haber_at": [r"^\W*YouTube\W*$"],
    },
    "dw.com/tr": {
        # Sayfadaki başlık ve tarih: "İsrail'e giden uçakta kaçırılma alarmı:
        # Nedeni pilot kavgası 30 Eylül 2026 Birleşik Arap Emirlikleri'nin …"
        "sil": [r"^.{0,250}?\b\d{1,2} (?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık) \d{4}\s+"],
    },
    "africanews.com": {
        "baslik_sonu": [r"\s*\|\s*Africanews\s*$"],
        # Metnin ilk satırı ülke etiketi: "Libya\nPublic school teachers…",
        # "Democratic Republic Of Congo\nA Congolese politician…".
        "ilk_satir_at": [r"^[A-Z][\w'’.-]*(?: [\w'’.-]+){0,4}$"],
    },
    "mercopress.com": {
        # Falkland Adaları'nın yerel haberleri (meclis üyelerinin ziyaretleri,
        # balıkçı teknesi kaza raporları): beslemenin yarıya yakını.
        "haber_at": [r"\bFalklands?\b", r"\bMalvinas\b", r"\bPort Stanley\b", r"\bIslanders\b"],
    },
    "aeon.co": {
        "baslik_sonu": [r"\s*\|\s*Aeon (?:Essays|Videos|Ideas|Psyche)\s*$"],
        # Denemelerin başındaki sesli okuma satırı: "Listen to this essay 30
        # minute listen William came to me…"
        "sil": [r"^.{0,300}?Listen to this essay\s*\d+\s*minute listen\s*"],
    },
    "lithub.com": {
        # Liste ve derleme yazıları: "The 12 Best Book Covers of September",
        # "20 great books out in paperback this month", günlük bülten.
        "etiket_at": [r"^best book covers of the month$", r"^book covers$"],
        "haber_at": [
            r"\bBest Book Covers\b", r"\bbooks? out (?:in paperback )?this (?:week|month)\b",
            r"^\d+ (?:great|best|new|must-read)\b.*\bbooks?\b", r"^Lit Hub (?:Daily|Weekly)\b",
            r"\bMost Anticipated Books\b", r"\bBest Reviewed (?:Fiction|Nonfiction|Books|Poetry)\b",
        ],
        "sil": [r"\*?\s*Article continues after advertisement\s*"],
        "cumle_at": [r"first appeared in Lit Hub", r"sign up here", r"Brought to you by Book Marks"],
        # Metin başlık ve alt başlık satırlarıyla başlıyor; alt başlık cümle
        # değil ("Ryan Chapman on the Recent Story Collection A Wooded Shore")
        # ve metne yapışıyordu. Noktalama ile bitmeyen ilk satırlar atılıyor.
        "ilk_satir_at": [r"^(?!.*[.!?][”\"’']?$).{3,250}$"],
    },
    "techcrunch.com": {
        "baslik_sonu": [r"\s*\|\s*TechCrunch\s*$"],
        # Sitenin kendi etkinlikleri ("TechCrunch Disrupt", "Startup Battlefield
        # 200", "TechCrunch Founder Summit", "StrictlyVC"): bilet/katılımcı
        # duyuruları ve yarışmacı girişim tanıtımları. Yatırım turu haberleri
        # "Fundraising". 10 günlük 200 yazıda 35 etkinlik + 6 yatırım turu
        # yazısını ayırıyor; haftalık bülten "TechCrunch Mobility" kalıyor.
        "etiket_at": [
            r"disrupt|summit|sessions|battlefield|strictlyvc|\bexpo\b|conference|\bevents?\b",
            r"^fundraising$",
        ],
        # Milyar dolarlık tur ya da değerleme haberi kalır.
        "birak": [r"\$\d+(?:\.\d+)?\s?(?:B|billion|T|trillion)\b"],
        "haber_at": [
            # Sitenin kendi konferans ve etkinlik duyuruları.
            r"\bDisrupt 20\d\d\b", r"\bStrictlyVC\b", r"\bStartup Battlefield\b", r"\bside events?\b",
            r"\bTechCrunch (?:Sessions|All Stage|Events?)\b",
            # Milyon dolarlık yatırım turları ("X raises $34.5M"); milyar
            # dolarlıklar (OpenAI, Anthropic…) kalır.
            r"^(?=.*\$\d+(?:\.\d+)?\s?(?:M|million)\b)(?=.*\b(?:rais\w*|secur\w*|lands?|nabs?|bags?|snags?|round|fund\w*|seed|valuation|invest\w*|Series [A-Z])\b)",
        ],
    },
    "restofworld.org": {
        # Şirket adının üzerine gelince açılan tanıtım balonu metne
        # karışıyor: "AlibabaAlibabaAlibaba, founded in 1999 by … Tmall.READ
        # MORE had launched". Ad bir kez kalır.
        "sil": [r"(?P<kalan>\b[A-Z][\w&.'’ -]{1,40}?)(?P=kalan)(?P=kalan)[^\n]{0,500}?READ MORE"],
    },
    "theverge.com": {
        # İndirim ve kampanya haberleri: sayfada "good-deals"/"shopping",
        # beslemede "Deals"/"Verge Shopping" etiketli.
        # Ürün incelemeleri ("The Ace Ultra are what Sonos headphones should
        # be"): sayfada "reviews" etiketli; haber değil, uzun değerlendirme.
        # Bir konunun bütün gelişmelerini toplayan sayfalar ("All the latest
        # news on …", "pagetype:stream") haber değil, günlerce güncellenen
        # başlık listesi.
        "etiket_at": [r"^(?:good-deals|deals|shopping|verge[ -]shopping|reviews|pagetype:stream)$"],
        # Metnin ortasında başlık ve alt başlık bir kez daha geçiyor: "… on
        # web traffic.\nGoogle reportedly tests paying publishers for AI
        # search results\nAround 100 publishers have joined …\nDigiday first
        # reported …"; ikisi de atılır.
        "ara_baslik_at": [r"^.{1,300}$"],
        "haber_at": [
            r"(?:\bhalf|\bhundreds|\$\d+|\b\d+\s?%|\b\d+ percent)\s+off\b", r"\bPrime (?:Day|Big Deal)",
            r"\bBlack Friday\b", r"\bCyber Monday\b", r"\bbest\b.*\bdeals?\b", r"\blowest price\b", r"\bon sale\b",
        ],
    },
    "themoscowtimes.com": {
        "baslik_sonu": [r"\s+[-–—]\s+The Moscow Times\s*$"],
    },
    "phys.org": {
        # Editör künyesi: "Gaby Clark Scientific Editor Robert Egan Senior
        # Editor A simplified cosmological model…". Başlıktan (bazen de bir
        # giriş cümlesinden) sonra geldiği için metnin başına bağlı değil;
        # düz metindeki bir "Editor" kelimesini yememek için ad soyad +
        # unvan kalıbının tamamı aranıyor.
        "sil": [r"(?:\b[A-Z][A-Za-z'’-]+ (?:[A-Z]\. )?[A-Z][A-Za-z'’-]+ (?:(?:Scientific|Senior|Chief|Lead|Associate|Managing|Contributing|Science|News|Deputy) Editor|[Cc]ontributing [Ww]riter)\b\s*)+"],
        # Üniversitelerin eğitim ve ekonomi araştırmaları (okul başarısı,
        # piyasa anketleri): Bilim sekmesinde yeri yok.
        "etiket_at": [r"^(?:education|economics & business)$"],
    },
    "arstechnica.com": {
        # Kapak görselinin altı yazısı ve künyesi metnin başında iki kez:
        # "A close-up view of a SpaceX Falcon 9 rocket … in 2021. Credit:
        # SpaceX A close-up view … in 2021. Credit: SpaceX For two decades…".
        # Aynı yazı + künye tekrarı arandığı için sıradan metne dokunmaz.
        "sil": [r"^(?P<yazi>.{20,400}?) Credit: (?P<kunye>.{1,80}?) (?P=yazi) Credit: (?P=kunye) "],
    },
    "quantamagazine.org": {
        "baslik_sonu": [r"\s*\|\s*Quanta Magazine\s*$"],
        # Metin başlık satırıyla, ardından "Introduction" ya da fotoğrafçı
        # adıyla ("Xavi Bou") başlıyor: noktalamayla bitmeyen kısa satırlar.
        "ilk_satir_at": [r"^(?!.*[.!?][”\"’']?$).{3,250}$"],
    },
    "theguardian.com": {
        # Tarif yazılarında metin, giriş paragrafından sonra süre/porsiyon
        # satırı ve malzeme listesiyle devam ediyor: "Prep 10 min Soak 2 hr
        # Cook 25 min Serves 6 200g coarse cornmeal…"; özet orada kesilir.
        # Karşılaştırma yazılarında ("the best supermarket cheesecake")
        # puan listesi: "Best overall: Waitrose No 1 … ★★★★☆".
        "kes": [r"\b(?:Prep|Cook) \d+ ?(?:min|hr)", r"\b(?:Serves|Makes) \d+\b", r"\bBest overall:"],
        # Tarif derlemelerinin başındaki fotoğraf altı ("Mandy Yin’s chicken
        # and squash curry (pictured top) Curry runs…") ve okur sorusu
        # köşesindeki imza ("… a no-no? Sally, by email People sure…").
        "sil": [r"^[^.!?]{0,120}?\(pictured(?: top| above| below)?\)\s*", r"\s*\(pictured(?: top| above| below)?\)",
                r"(?<=[.!?] )[A-Z][a-z]+(?: [A-Z][a-z]+)?, (?:by|via) email\s+"],
        # Başlık sonundaki dizi/köşe adı: "How to make cornbread – recipe |
        # Felicity Cloake's masterclass", "Belgian buns recipe | The sweet spot"
        "baslik_sonu": [r"\s+\|\s+[^|]{1,60}$"],
        # Gezi bölümünün İngiltere içi tatil yazıları (kır evleri, küçük
        # oteller, okurların gün gezisi önerileri): Türk okura uzak.
        # Etiket yalnız gezi yazılarında var; kültür ve yemek yazılarına
        # dokunmaz.
        "etiket_at": [r"^(?:united kingdom|england|scotland|wales|northern ireland) holidays$",
                      # Kültür beslemesinde /film/ ve /culture/ altından gelen TV
                      # yazıları: gerçeklik şovu belgeseli, reklam filmi eleştirisi,
                      # gece kuşağı şovlarının özeti (TV bölümü zaten atlanıyor).
                      r"^(?:television|television & radio|reality tv|late-night tv roundup)$",
                      # Broadway ve West End müzikalleri ("Wicked'ın yıldızları en
                      # sevdikleri şarkıları seçiyor").
                      r"^musicals$"],
    },
    "sciencedaily.com": {
        # "- Date: - Sept 23, 2026 - Source: - PLOS - Summary: -"
        # Özet kutusu ile tam metin arasındaki paylaş butonları: "… - Share: …"
        "sil": [r"-?\s*Date:\s*-.*?-\s*Source:\s*-.*?-\s*Summary:\s*-\s*", r"-\s*Share:\s*"],
    },
    "sciencenews.org": {
        # "This is a human-written story voiced by AI. Got feedback? Take our
        # survey . (See our AI policy here .)" — alt başlığa yapışık geldiği
        # için cümle olarak değil parça parça siliniyor.
        "sil": [
            r"This is a human-written story voiced by AI\.\s*",
            r"Got feedback\?\s*Take our survey\s*\.?\s*",
            r"\(See our AI policy here\s*\.?\)\s*",
        ],
    },
    "lonelyplanet.com": {
        "baslik_sonu": [r"\s+[-–—]\s+Lonely Planet\s*$"],
        "cumle_at": [r"may earn a commission", r"affiliate links", r"reflect our own independent opinions",
                     r"Lonely Planet app"],
    },
    "saveur.com": {
        # Tarifin başındaki "- Serves2–4 - Time25 minutes" satırı ve
        # sonundaki "Ingredients - Kosher salt - 1 lb. …" listesi.
        "sil": [r"\s*-\s*Serves\s*[\d–-]+\s*-\s*Time\s*[\d½¼¾–-]+\s*(?:minutes?|hours?|hrs?|mins?)\b"],
        "kes": [r"\bIngredients\s+-\s"],
    },
    "eater.com": {
        # Pre Shift bülteni tanıtımı ve satış ortaklığı notu.
        "cumle_at": [r"\bour newsletter\b", r"^Subscribe\b", r"may earn a commission", r"See our ethics statement",
                     r"\binstallment of our series\b.*\bpresented by\b"],
    },
}


def _kurallari_derle(kurallar: dict[str, dict[str, list[str]]]) -> dict[str, dict]:
    derlenmis = {}
    for kaynak, k in kurallar.items():
        derlenmis[kaynak] = {
            "sil": [re.compile(p) for p in k.get("sil", [])],
            "bas": [re.compile(rf"^(?:[-–—|:]\s*)?(?:{p})\s+") for p in k.get("bas", [])],
            "kes": re.compile("|".join(k["kes"])) if k.get("kes") else None,
            "cumle_at": re.compile("|".join(k["cumle_at"]), re.IGNORECASE) if k.get("cumle_at") else None,
            "baslik_sonu": [re.compile(p) for p in k.get("baslik_sonu", [])],
            "haber_at": re.compile("|".join(f"(?:{p})" for p in k["haber_at"]), re.IGNORECASE) if k.get("haber_at") else None,
            "etiket_at": re.compile("|".join(f"(?:{p})" for p in k["etiket_at"]), re.IGNORECASE) if k.get("etiket_at") else None,
            "birak": re.compile("|".join(f"(?:{p})" for p in k["birak"])) if k.get("birak") else None,
            "ilk_satir_at": re.compile("|".join(f"(?:{p})" for p in k["ilk_satir_at"])) if k.get("ilk_satir_at") else None,
            "ara_baslik_at": re.compile("|".join(f"(?:{p})" for p in k["ara_baslik_at"])) if k.get("ara_baslik_at") else None,
        }
    return derlenmis


_DERLENMIS_KURALLAR = _kurallari_derle(KAYNAK_KURALLARI)
_KURALSIZ = {"sil": [], "bas": [], "kes": None, "cumle_at": None, "baslik_sonu": [], "haber_at": None,
             "etiket_at": None, "birak": None, "ilk_satir_at": None, "ara_baslik_at": None}


def basligi_temizle(baslik: str, kaynak: str) -> str:
    for kalip in _DERLENMIS_KURALLAR.get(kaynak, _KURALSIZ)["baslik_sonu"]:
        baslik = kalip.sub("", baslik)
    return baslik.strip()


def haber_ayiklanir_mi(kaynak: str) -> bool:
    kurallar = _DERLENMIS_KURALLAR.get(kaynak, _KURALSIZ)
    return kurallar["haber_at"] is not None or kurallar["etiket_at"] is not None


# Etiketi etiket_at'a ya da başlığı haber_at'a uyan haber alınmaz (başlığı
# birak'a uyan hariç). Arşiv kayıtlarında etiket yok; yalnız başlığa bakılır.
def atlanacak_mi(baslik: str, kaynak: str, etiketler: list[str] | tuple = ()) -> bool:
    kurallar = _DERLENMIS_KURALLAR.get(kaynak, _KURALSIZ)
    if kurallar["birak"] and kurallar["birak"].search(baslik):
        return False
    if kurallar["etiket_at"] and any(kurallar["etiket_at"].search(e) for e in etiketler):
        return True
    return bool(kurallar["haber_at"] and kurallar["haber_at"].search(baslik))


def _tirnaklari_esitle(metin: str) -> str:
    return metin.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


# Birçok kaynakta (Al Jazeera, BBC, SCMP, ScienceDaily, France24…) gövde
# metni başlığın aynısıyla başlıyor; özette başlık iki kez görünmesin.
# Başlık, metnin ilk cümlesinin başı da olabiliyor (ör. "Karak
# Chai" → "Karak chai (strong tea…"): bu yüzden karşılaştırma büyük/küçük
# harfe duyarlı ve başlıktan sonra cümle devam ediyorsa (küçük harf, "(",
# virgül…) kırpılmıyor; ayrı bir başlık satırı büyük harf, rakam, tırnak
# ya da tire ile devam eder.
def _basliktan_arindir(metin: str, baslik: str, bastaki_etiketler: list[re.Pattern]) -> str:
    baslik = re.sub(r"\s+", " ", baslik).strip()
    if baslik and _tirnaklari_esitle(metin).startswith(_tirnaklari_esitle(baslik)):
        kalan = metin[len(baslik):].lstrip()
        if not kalan or re.match(r"[A-ZÇĞİÖŞÜ0-9\"“‘'\-–—|:]", kalan):
            metin = kalan
    metin = metin.lstrip(" -–—|:")
    degisti = True
    while degisti:
        degisti = False
        for etiket in bastaki_etiketler:
            yeni = etiket.sub("", metin, count=1)
            if yeni != metin:
                metin, degisti = yeni, True
    return metin


# Gövde metninden başlık tekrarı ve kaynağın kalıntıları (KAYNAK_KURALLARI)
# temizlenip ilk k cümle tek paragraf olarak döner. Cümle sınırı:
# [.!?] + boşluk + büyük harf/tırnak. Temizlik kesmeden önce yapıldığı
# için atılan cümlelerin yerini sonraki cümleler dolduruyor.
def ozet_olustur(metin: str, baslik: str, k: int, kaynak: str) -> str:
    kurallar = _DERLENMIS_KURALLAR.get(kaynak, _KURALSIZ)
    # En fazla ilk üç satır (başlık, alt başlık, etiket) kurala uydukça atılır.
    # Başlık satırı "?" ile bitse de (Quanta: "… What Does That Mean for
    # Reality?") başlık olduğu için atılır, sonraki satırlara geçilir.
    duz_baslik = _tirnaklari_esitle(re.sub(r"\s+", " ", baslik).strip())
    for _ in range(3):
        if not kurallar["ilk_satir_at"]:
            break
        ilk, _, kalan = metin.strip().partition("\n")
        ilk = ilk.strip()
        if not (kalan and (kurallar["ilk_satir_at"].search(ilk) or _tirnaklari_esitle(ilk) == duz_baslik)):
            break
        metin = kalan
    if kurallar["ara_baslik_at"] and duz_baslik:
        satirlar = metin.split("\n")
        kalanlar = []
        i = 0
        while i < len(satirlar):
            if _tirnaklari_esitle(satirlar[i].strip()) == duz_baslik:
                i += 1
                if i < len(satirlar) and kurallar["ara_baslik_at"].search(satirlar[i].strip()):
                    i += 1
                continue
            kalanlar.append(satirlar[i])
            i += 1
        metin = "\n".join(kalanlar)
    duz = re.sub(r"\s+", " ", metin).strip()
    for kalip in kurallar["sil"]:
        # Kalıpta "kalan" adlı grup varsa o kısım metinde bırakılır.
        duz = kalip.sub(r"\g<kalan>" if "kalan" in kalip.groupindex else "", duz)
    duz = _basliktan_arindir(duz.strip(), baslik, kurallar["bas"])
    if kurallar["kes"]:
        kesim = kurallar["kes"].search(duz)
        if kesim:
            duz = duz[: kesim.start()]
    duz = duz.strip()
    if not duz:
        return ""
    parcalar = [p.strip() for p in re.split(r'(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9"“(])', duz) if p.strip()]
    # Liste numarası tek başına cümle sayılıyor ("… here are the films. 1.
    # Digger …"); özete "1." diye bir cümle girmesin.
    parcalar = [p for p in parcalar if not re.fullmatch(r"\d{1,2}\.", p)]
    if kurallar["cumle_at"]:
        parcalar = [p for p in parcalar if not kurallar["cumle_at"].search(p)]
    # Giriş (spot) cümlesi metnin içinde bir kez daha geçebiliyor (ör.
    # Euronews); aynı cümle özette ikinci kez yer almasın.
    # Neredeyse aynısı da (spot ile metnin ilk cümlesi, France 24: "Israel's
    # Prime Minister Benjamin Netanyahu said that one pilot had allegedly
    # stabbed…" / "Israeli Prime Minister Benjamin Netanyahu said Wednesday
    # that one of the pilots…") ikinci kez alınmaz.
    gorulen: set[str] = set()
    tekil: list[str] = []
    kelimeler: list[set[str]] = []
    for p in parcalar:
        anahtar = _tirnaklari_esitle(p).lower()
        if anahtar in gorulen:
            continue
        k_p = _icerik_kelimeleri(p)
        if any(_yakin_tekrar(k_p, k_o) for k_o in kelimeler):
            continue
        gorulen.add(anahtar)
        tekil.append(p)
        kelimeler.append(k_p)
    return " ".join(tekil[:k]).strip()


_BOS_KELIMELER = set("""the and that with for from this said says was were has have had are its his her their they them
but not will would which who whom into after about also been more than when what where while there these those being
over under our your you she him one two then just very can could may might should shall did does ile ve bir bu için
olarak daha gibi ancak çok kadar sonra olan""".split())


def _icerik_kelimeleri(cumle: str) -> set[str]:
    # İlk 5 harf: "Israel/Israeli", "pilot/pilots" aynı sayılsın.
    return {w[:5] for w in re.findall(r"[a-zçğıöşü0-9]{3,}", cumle.lower()) if w not in _BOS_KELIMELER}


def _yakin_tekrar(a: set[str], b: set[str]) -> bool:
    kucuk = min(len(a), len(b))
    return kucuk >= 7 and len(a & b) / kucuk >= 0.6
