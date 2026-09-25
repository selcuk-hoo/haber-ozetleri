"""Makale gövdesinden özet üretimi ve kaynağa özgü özet temizliği."""

import re

_AY = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"

# Kaynağa özgü özet temizliği. Her kural, canlı sitedeki özetlerde o
# kaynakta görülen bir kalıptan yazıldı; bir kaynak sayfa düzenini
# değiştirirse sadece kendi bloğu düzenlenir, bir kaynağın kuralı
# başkasının metnine dokunmaz. Değişiklikten sonra tests/test_ozet.py
# çalıştırılır (her kural için gerçek bir örnek var).
#   sil      : metnin her yerinden silinir (başlık kırpılmadan önce)
#   bas      : başlık kırpıldıktan sonra metnin başında kalırsa silinir
#   kes      : bu kalıptan itibaren metnin geri kalanı atılır
#   cumle_at : bu kalıbı içeren cümle özetten çıkarılır (harf büyüklüğü fark etmez)
#   baslik_sonu : başlığın sonundaki kaynak adı ("… | TechCrunch"); başlıktan
#                 silinir (kaynak adı kartta zaten yazıyor)
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
        # Video olmayan sayfalara da gömülen video blokları.
        "sil": [r"Video Ad Feedback\s*"],
        "kes": [r"Latest Videos\b", r"\d{1,2}:\d{2} • Source:"],
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
    "variety.com": {
        # Metnin arasına gömülü "Popular on Variety" kutusu başlığı.
        "sil": [r"\s*Popular on Variety\b"],
    },
    "scmp.com": {
        "sil": [r"\bAdvertisement\s+", r"\d+-MIN READ(\d+-MIN)?\s*(\d+\s+)?(Listen\s+)?"],
        # Sesli okuma oynatıcısı: "Select Voice Select Speed 1x AI-generated voice"
        "kes": [r"Select Voice Select Speed"],
        # Okur mektubu sayfalarındaki "mektup gönderin" çağrısı.
        "cumle_at": [r"Letter to the Editor", r"Feel strongly about these letters", r"Submissions should not exceed"],
    },
    "techcrunch.com": {
        "baslik_sonu": [r"\s*\|\s*TechCrunch\s*$"],
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
        "sil": [r"(?:\b[A-Z][A-Za-z'’-]+ (?:[A-Z]\. )?[A-Z][A-Za-z'’-]+ (?:(?:Scientific|Senior|Chief|Lead|Associate|Managing|Contributing|Science|News) Editor|[Cc]ontributing [Ww]riter)\b\s*)+"],
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
        "cumle_at": [r"may earn a commission", r"affiliate links", r"reflect our own independent opinions"],
    },
    "eater.com": {
        # Pre Shift bülteni tanıtımı ve satış ortaklığı notu.
        "cumle_at": [r"\bour newsletter\b", r"^Subscribe\b", r"may earn a commission", r"See our ethics statement"],
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
        }
    return derlenmis


_DERLENMIS_KURALLAR = _kurallari_derle(KAYNAK_KURALLARI)
_KURALSIZ = {"sil": [], "bas": [], "kes": None, "cumle_at": None, "baslik_sonu": []}


def basligi_temizle(baslik: str, kaynak: str) -> str:
    for kalip in _DERLENMIS_KURALLAR.get(kaynak, _KURALSIZ)["baslik_sonu"]:
        baslik = kalip.sub("", baslik)
    return baslik.strip()


def _tirnaklari_esitle(metin: str) -> str:
    return metin.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


# Birçok kaynakta (Al Jazeera, BBC, SCMP, ScienceDaily, France24…) gövde
# metni başlığın aynısıyla başlıyor; özette başlık iki kez görünmesin.
# Başlık, metnin ilk cümlesinin başı da olabiliyor (Bon Appétit "Karak
# Chai" → "Karak chai (strong tea…"): bu yüzden karşılaştırma büyük/küçük
# harfe duyarlı ve başlıktan sonra cümle devam ediyorsa (küçük harf, "(",
# virgül…) kırpılmıyor; ayrı bir başlık satırı büyük harf, rakam, tırnak
# ya da tire ile devam eder.
def _basliktan_arindir(metin: str, baslik: str, bastaki_etiketler: list[re.Pattern]) -> str:
    baslik = re.sub(r"\s+", " ", baslik).strip()
    if baslik and _tirnaklari_esitle(metin).startswith(_tirnaklari_esitle(baslik)):
        kalan = metin[len(baslik):].lstrip()
        if not kalan or re.match(r"[A-Z0-9\"“‘'\-–—|:]", kalan):
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
    duz = re.sub(r"\s+", " ", metin).strip()
    for kalip in kurallar["sil"]:
        duz = kalip.sub("", duz)
    duz = _basliktan_arindir(duz.strip(), baslik, kurallar["bas"])
    if kurallar["kes"]:
        kesim = kurallar["kes"].search(duz)
        if kesim:
            duz = duz[: kesim.start()]
    duz = duz.strip()
    if not duz:
        return ""
    parcalar = [p.strip() for p in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"“(])', duz) if p.strip()]
    if kurallar["cumle_at"]:
        parcalar = [p for p in parcalar if not kurallar["cumle_at"].search(p)]
    return " ".join(parcalar[:k]).strip()
