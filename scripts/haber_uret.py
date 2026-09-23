#!/usr/bin/env python3
"""haber_ham.sh'nin toplu/otomatik sürümü.

Yerel Chromium açma ve canlı yenileme yok; GitHub Actions'ta çalışıp
statik bir HTML üretir. Sayfa lang="en" işaretlenir, tarayıcı Türkçeye
çevirmeyi önerir (haber_ham.sh ile aynı fikir).

Gereksinim: trafilatura (pip install trafilatura)
"""

import html
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from courlan import get_hostinfo, normalize_url
import feedparser
import trafilatura
from trafilatura.feeds import FeedParameters, determine_feed, find_feed_urls
from trafilatura.sitemaps import find_robots_sitemaps, sitemap_search

TR_SAATI = ZoneInfo("Europe/Istanbul")

# Her kayıt: (kategori, kaynak adı, besleme/anasayfa adresi). Sayfa
# kategoriye göre sekmelere ayrılır; her sekmenin kendi "All + kaynak"
# filtresi vardır (bkz. sayfa_olustur).
KAYNAKLAR = [
    # /rss/turkiye "Türkiye" etiketli dar bir alt besleme, günde 1-2
    # haber veriyordu; anasayfaya geçildi ki genel dailysabah.com akışı
    # (besleme_ogeleri anasayfadan duyurulan gerçek beslemeyi bulup
    # tarihe göre sıralıyor) kullanılsın.
    ("Gündem", "dailysabah.com", "https://www.dailysabah.com/"),
    ("Gündem", "cnn.com", "https://www.cnn.com/"),
    ("Gündem", "bbc.co.uk", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Gündem", "aljazeera.com", "https://www.aljazeera.com/"),
    ("Gündem", "dw.com", "https://rss.dw.com/rdf/rss-en-world"),
    ("Gündem", "france24.com", "https://www.france24.com/en/rss"),
    ("Gündem", "themoscowtimes.com", "https://www.themoscowtimes.com/rss/news"),
    # Uzakdoğu bakış açısı için: SCMP'nin tam besleme adresi bilinmediği
    # için (diğer anasayfa kaynakları gibi) anasayfadan duyurulan gerçek
    # besleme besleme_ogeleri tarafından otomatik keşfedilip kullanılıyor.
    ("Gündem", "scmp.com", "https://www.scmp.com/"),
    # Bilim ve Teknoloji ayrı sekmelere bölündü: kitleleri farklı
    # (biri araştırma/keşif, diğeri ürün/şirket haberleri). TechCrunch,
    # Verge ile aynı büyük şirket duyurularını (ör. OpenAI, Apple)
    # işleyebildiği için haberlerin tekrar tekrar çıkma riski var —
    # bilinçli olarak kabul edildi.
    ("Teknoloji", "bbc.co.uk", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("Teknoloji", "theverge.com", "https://www.theverge.com/rss/index.xml"),
    ("Teknoloji", "techcrunch.com", "https://techcrunch.com/feed/"),
    # ScienceDaily ve Science News'ün doğrudan besleme adresleri web
    # aramasıyla bulundu, gerçek çalıştırmada ikisi de 10'ar haber verdi.
    # Bilim Teknik (TÜBİTAK) denendi ama besleme bulunamadı (0 sonuç),
    # kaldırıldı.
    ("Bilim", "sciencedaily.com", "https://www.sciencedaily.com/rss/all.xml"),
    ("Bilim", "sciencenews.org", "https://www.sciencenews.org/feed"),
    ("Sanat & Kültür", "bbc.co.uk", "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
    ("Sanat & Kültür", "theguardian.com", "https://www.theguardian.com/culture/rss"),
    # Japan Times'ın görselleri translate.goog üzerinden açılan çeviri
    # sürümünde yüklenmiyordu (görsel adresinin kendisi doğru ve
    # ulaşılabilir, ama Google'ın çeviri proxy'si üçüncü taraf CDN'sinden
    # görseli aktaramıyor) — kullanıcı görselleri kaybetmek yerine
    # kaynağı değiştirmeyi tercih etti. SCMP zaten Gündem'de kullanılıyor
    # ve sorunsuz çalışıyor; aynı domain'in kültür/yaşam tarzı sayfası
    # kullanıldı.
    ("Sanat & Kültür", "scmp.com", "https://www.scmp.com/lifestyle/arts-culture"),
    ("Gezi", "cntraveler.com", "https://www.cntraveler.com/"),
    ("Gezi", "lonelyplanet.com", "https://www.lonelyplanet.com/"),
    ("Yemek", "bonappetit.com", "https://www.bonappetit.com/feed/rss"),
    ("Yemek", "eater.com", "https://www.eater.com/"),
    # Bon Appétit ve Eater çoğunlukla Amerikan restoran sahnesi/tarif
    # geliştirme odaklı; Saveur dünya mutfaklarına ve yemek kültürüne
    # daha geniş bakan bir dergi olduğu için eklendi.
    ("Yemek", "saveur.com", "https://www.saveur.com/feed/"),
]

N = 10  # kaynak başına haber sayısı
# Teknoloji'de sadece 2 kaynak var (BBC + The Verge), bu yüzden N=10 ile
# sekme çok hızlı tazeleniyor/tükeniyor gibi görünüyordu; o kategoride
# kaynak başına daha fazla haber tutulur.
KATEGORI_SAYISI = {"Teknoloji": 15}
K = 5  # özet cümle sayısı
# Eater/Saveur gibi kaynakların beslemeleri arada 2021-2024'ten kalma
# "evergreen" tarif/rehber içerikleri de karıştırıyor; bunlar tarihe göre
# doğru sıralanıyor ama bir haber sitesinde yıllar öncesine ait içerik
# görünmesi istenmiyor, bu yüzden bu eşikten eski haberler hiç sayfaya
# eklenmiyor.
ESKI_HABER_ESIGI = timedelta(days=30)
SITE_URL = "https://selcuk-hoo.github.io/haber-ozetleri/"
CIKTI = Path(__file__).resolve().parent.parent / "dist" / "index.html"
# html2canvas satır içi gömülü: translate.goog (otomatik Türkçe çeviri)
# üçüncü taraf bir CDN'den yüklenen <script src="..."> etiketini düzgün
# proxy'lemiyor, bu yüzden "Paylaş" butonu çeviri sürümünde hiç
# çalışmıyordu. Kütüphane depoda vendor'lanıp sayfanın kendi
# <script>'ine gömülerek bu proxy sorunu tamamen atlanıyor.
HTML2CANVAS_DOSYASI = Path(__file__).resolve().parent / "vendor" / "html2canvas.min.js"

# CNN, Al Jazeera gibi gerçek bir RSS beslemesi olmayan (anasayfadan
# otomatik keşifle veya site haritasından çekilen) kaynaklarda ne sayfada
# ne beslemede tarih bulunabiliyor. Bu dosya, öyle bir makaleyi ilk kez
# gördüğümüz anı url'e göre kalıcı olarak saklar; sonraki çalıştırmalarda
# gerçek tarih hâlâ yoksa bu "ilk görülme" zamanı yedek olarak kullanılır
# (bkz. uret()). Sadece main'de commit'lenir (workflow'a bakın) — gerçek
# yayın saati DEĞİL, sırf sıralama ve "en azından bir saat göster" için.
ILK_GORULME_DOSYASI = Path(__file__).resolve().parent / "ilk_gorulme.json"


def kacir(metin: str) -> str:
    return html.escape(metin, quote=False)


# Metnin ilk k cümlesini tek paragraf olarak döner. haber_ham.sh'deki
# ilk_cumleler() ile aynı mantık: [.!?] + boşluk + büyük harf/tırnak sınırı.
def ilk_cumleler(metin: str, k: int) -> str:
    duz = re.sub(r"\s+", " ", metin).strip()
    if not duz:
        return ""
    parcalar = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"“(])', duz)
    parcalar = [p for p in parcalar if p.strip()]
    return " ".join(parcalar[:k]).strip()


def besleme_listesi(feed_url: str, n: int) -> list[str]:
    try:
        urls = find_feed_urls(feed_url)[:n]
    except Exception as hata:  # noqa: BLE001 - tek bir kaynağın hatası taramayı durdurmasın
        print(f"besleme alınamadı ({feed_url}): {hata}", file=sys.stderr)
        return []
    if urls:
        return urls

    try:
        _, baseurl = get_hostinfo(feed_url)
    except Exception as hata:  # noqa: BLE001
        print(f"adres çözümlenemedi ({feed_url}): {hata}", file=sys.stderr)
        return []

    if feed_url.rstrip("/") != baseurl.rstrip("/"):
        # Konuya özel bir alt sayfa (ör. /technology) besleme vermiyorsa site
        # geneli haritasına düşmek yanlış konudaki haberleri karıştırabilir
        # (genel site haritası konu ayrımı yapmaz) — bu durumda boş dönüp o
        # kaynağı bu bölüm için atla.
        return []

    # Anasayfa düzeyinde bir adres (ör. CNN gibi genel "Gündem" kaynağı) ve
    # besleme bulunamadıysa site haritasından dene. Genel site haritası
    # taraması (sitemap_search) haber sitelerinde video/galeri gibi haber
    # olmayan sayfaları da karıştırabiliyor (CNN'de olduğu gibi: robots.txt'te
    # video.xml, gallery.xml vs. de listeleniyor ve karışık geliyordu).
    # robots.txt'te adında "news" geçen özel bir site haritası varsa (CNN'in
    # sitemap/news.xml'i gibi; Google News formatı, sadece güncel haberleri
    # listeler) onu tercih et.
    try:
        adaylar = find_robots_sitemaps(baseurl)
    except Exception as hata:  # noqa: BLE001
        print(f"robots.txt site haritası bulunamadı ({feed_url}): {hata}", file=sys.stderr)
        adaylar = []
    haber_haritasi = next((a for a in adaylar if "news" in a.lower()), None)
    try:
        if haber_haritasi:
            return sitemap_search(haber_haritasi, max_sitemaps=1)[:n]
        return sitemap_search(feed_url, max_sitemaps=5)[:n]
    except Exception as hata:  # noqa: BLE001
        print(f"site haritası alınamadı ({feed_url}): {hata}", file=sys.stderr)
        return []


# Tek bir adresi doğrudan feedparser ile ayrıştırıp (zaman, url,
# iso_tarih) üçlülerini feedparser'ın verdiği <pubDate>/<updated> alanına
# göre YENİDEN ESKİYE açıkça sıralı döner. Beslemenin kendi (varsayılan
# olarak kronolojik olması beklenen) sırasına güvenilmiyor, çünkü
# find_feed_urls'ın döndürdüğü linkler ALFABETİK sıraya dizili (bkz.
# besleme_ogeleri üstündeki not) — burada o sıralamaya hiç bulaşmadan
# kendi tarihe dayalı sıralamamızı yapıyoruz. Adres gerçek bir besleme
# değilse (feedparser hiç girdi bulamazsa) boş liste döner.
def _feedparser_girdileri(feed_url: str) -> list[tuple[datetime | None, str, str]]:
    try:
        ayristirilan = feedparser.parse(feed_url)
    except Exception as hata:  # noqa: BLE001
        print(f"besleme okunamadı ({feed_url}): {hata}", file=sys.stderr)
        return []

    ogeler: list[tuple[datetime | None, str, str]] = []
    for oge in ayristirilan.get("entries", []):
        url = oge.get("link")
        if not url:
            continue
        # find_feed_urls'ın linkleri courlan ile temizleyip (izleme
        # parametreleri gibi) döndürdüğü davranışla tutarlı olsun diye
        # (ör. BBC'nin ?at_medium=RSS&at_campaign=... eklediği linkler)
        # burada da aynı normalizasyon uygulanıyor; makale_getir'e giden
        # url ile burada üretilen tarih haritasının anahtarları
        # örtüşmezse tarih hiç eşleşmez.
        try:
            url = normalize_url(url)
        except Exception:  # noqa: BLE001
            pass
        parcalanmis = oge.get("published_parsed") or oge.get("updated_parsed")
        if parcalanmis:
            zaman = datetime(*parcalanmis[:6], tzinfo=timezone.utc)
            iso_tarih = zaman.strftime("%Y-%m-%dT%H:%M:%S%z")
        else:
            zaman = None
            iso_tarih = ""
        ogeler.append((zaman, url, iso_tarih))

    ogeler.sort(key=lambda o: o[0] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return ogeler


# Anasayfa düzeyindeki bir adresten (CNN, Al Jazeera gibi) <link
# rel="alternate"> etiketiyle duyurulan gerçek besleme adaylarını bulur.
# find_feed_urls de (besleme_listesi'nin kullandığı fallback) tam olarak
# bunu kendi içinde yapıyor (determine_feed ile) — ama bulduğu besleme
# öğelerini alfabetik sıralayıp döndürüyor. Burada sadece ADAY besleme
# adreslerini çıkarıp _feedparser_girdileri'ne besliyoruz ki tarihe göre
# doğru sıralanabilsin.
def _anasayfa_besleme_adaylari(url: str) -> list[str]:
    try:
        domain, baseurl = get_hostinfo(url)
    except Exception:  # noqa: BLE001
        return []
    if domain is None:
        return []
    try:
        indirilen = trafilatura.fetch_url(url)
    except Exception:  # noqa: BLE001
        return []
    if not indirilen:
        return []
    try:
        return determine_feed(indirilen, FeedParameters(baseurl, domain, url, False, None))
    except Exception:  # noqa: BLE001
        return []


# Verilen adresteki en yeni n haberin url'ini ve tarihini döndürür.
# Önce adresi doğrudan bir besleme gibi okumayı dener (dailysabah.com/
# rss/turkiye gibi gerçek feed URL'leri için bu yeterli); adres anasayfa
# düzeyindeyse (CNN, Al Jazeera gibi, gerçek bir besleme değilse) o
# sayfadan duyurulan besleme adaylarını bulup ilk sonuç vereni kullanır.
# İkisi de boşsa çağıran taraf (uret()) besleme_listesi'ndeki site
# haritası fallback'ine düşer (orada tarih bilgisi olmaz, ilk görülme
# mekanizması devreye girer).
def besleme_ogeleri(feed_url: str, n: int) -> tuple[list[str], dict[str, str]]:
    ogeler = _feedparser_girdileri(feed_url)
    if not ogeler:
        for aday in _anasayfa_besleme_adaylari(feed_url):
            ogeler = _feedparser_girdileri(aday)
            if ogeler:
                break

    if not ogeler:
        return [], {}

    urls = [url for _, url, _ in ogeler[:n]]
    tarihler = {url: t for _, url, t in ogeler if t}
    return urls, tarihler


# with_metadata ile title, image (og:image) ve date (article:published_time
# gibi etiketlerden, saat/saat dilimiyle birlikte) doğrudan ayrıştırılmış
# olarak gelir. CLI'nin --json çıktısında saat dilimi biçimini kontrol
# edemediğimiz için Python API'sini kullanıyoruz.
def makale_getir(url: str) -> dict | None:
    try:
        indirilen = trafilatura.fetch_url(url)
        if not indirilen:
            return None

        belge = trafilatura.bare_extraction(
            indirilen,
            url=url,
            with_metadata=True,
            date_extraction_params={
                # extensive_search=False: sayfa metninden "tahmin" etmeye
                # çalışmasın, sadece article:published_time gibi güvenilir
                # meta etiketlerine dayansın (yanlış saat riskini azaltır).
                "extensive_search": False,
                "original_date": True,
                "outputformat": "%Y-%m-%dT%H:%M:%S%z",
            },
        )
        if belge is None:
            return None

        veri = belge.as_dict()
        govde = (veri.get("text") or "").strip()
        if not govde:
            return None

        baslik = (veri.get("title") or "").strip() or url
        gorsel = (veri.get("image") or "").strip()
        tarih = (veri.get("date") or "").strip()
        return {"baslik": baslik, "govde": govde, "gorsel": gorsel, "tarih": tarih}
    except Exception as hata:  # noqa: BLE001 - tek bir haberin hatası taramayı durdurmasın
        print(f"makale alınamadı ({url}): {hata}", file=sys.stderr)
        return None


# Saat dilimi bilgisi varsa (article:published_time gibi etiketlerden
# geldiyse) Türkiye saatine çevirip saatiyle gösterir; kaynakta sadece
# tarih varsa (saat bilgisi yoksa) yalnızca tarihi gösterir.
# trafilatura/htmldate saat dilimi bulamadığında saati "T00:00:00" olarak
# dolduruyor (offsetsiz) — bu, saati bilinmiyor demek, gece yarısı demek
# değil. Üç biçim de denenir; saat dilimi olmayanlarda saat gösterilmez.
_TARIH_BICIMLERI = ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")


def _tarihi_ayristir(ham: str) -> datetime | None:
    for bicim in _TARIH_BICIMLERI:
        try:
            return datetime.strptime(ham, bicim)
        except ValueError:
            continue
    return None


def tarihi_bicimlendir(ham: str) -> str:
    zaman = _tarihi_ayristir(ham)
    if zaman is None:
        return ham
    if zaman.tzinfo is not None:
        yerel = zaman.astimezone(TR_SAATI)
        return yerel.strftime("%d.%m · %H:%M")
    return zaman.strftime("%d.%m")


# Sıralama için: ayrıştırılabilen tarihler karşılaştırılabilir olsun diye
# UTC'ye sabitlenir; ayrıştırılamayan/boş tarihler en eskiymiş gibi
# davranıp listenin sonuna düşer.
def _sira_anahtari(tarih: str) -> datetime:
    zaman = _tarihi_ayristir(tarih)
    if zaman is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return zaman if zaman.tzinfo else zaman.replace(tzinfo=timezone.utc)


# Sayfa tarihi ile besleme tarihinden GÜVENİLİR olanı seçer; ikisi de
# güvenilir değilse boş döner (çağıran taraf bu durumda ilk görülme
# zamanına düşer, bkz. uret()). Sayfa tarihi boş DEĞİLSE bile saat dilimi
# taşımıyor olabilir — htmldate, sayfada bulduğu ama saati belirsiz bir
# tarihi "T00:00:00" ile dolduruyor (bkz. _TARIH_BICIMLERI üstündeki not).
# Bu saatsiz/yer tutucu değer CNN, Al Jazeera gibi anasayfa kaynaklarında
# sıkça çıkıyor ve bir haberin gerçekte ne zaman yayınlandığına dair
# güvenilir bir sinyal değil (bazen sayfadaki alakasız bir tarih, bazen
# eski bir "son güncelleme" olabiliyor). Bu yüzden sadece saat dilimli
# (gerçekten ayrıştırılmış) tarihler "güvenilir" sayılır: sayfa tarihi
# saat dilimliyse ona güvenilir; değilse besleme'nin (her zaman saat
# dilimli üretilen) tarihi kullanılır; o da yoksa boş dönülür.
def _guvenilir_tarih(sayfa_tarihi: str, besleme_tarihi: str) -> str:
    sayfa_zaman = _tarihi_ayristir(sayfa_tarihi) if sayfa_tarihi else None
    if sayfa_zaman is not None and sayfa_zaman.tzinfo is not None:
        return sayfa_tarihi
    return besleme_tarihi


def ilk_gorulmeleri_yukle() -> dict[str, str]:
    try:
        return json.loads(ILK_GORULME_DOSYASI.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# Sadece bu çalıştırmada gerçekten karşılaşılan url'ler (gorulen_urller)
# saklanır; bir makale artık hiçbir kaynağın ilk N haberi arasında değilse
# (sitede de görünmüyor) kaydı burada da düşer. Bu, dosyanın kaynak sayısı
# × N ile sınırlı kalmasını sağlar, sınırsız büyümez.
def ilk_gorulmeleri_kaydet(harita: dict[str, str], gorulen_urller: set[str]) -> None:
    guncel = {url: tarih for url, tarih in harita.items() if url in gorulen_urller}
    ILK_GORULME_DOSYASI.write_text(
        json.dumps(guncel, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


STIL = """
  :root{
    --bg:#fbfaf8; --card:#fff; --ink:#1c1b19; --soft:#6f6b66;
    --line:#e6e2dc; --accent:#8a5a2b; --warn:#9a5b2a; --warnbg:#fdf3e7;
    --shadow:0 1px 2px rgba(28,27,25,.05);
  }
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){
      --bg:#15151a; --card:#1d1d23; --ink:#e9e7e3; --soft:#a29e98;
      --line:#2d2d35; --accent:#d69a5e; --warn:#d69a5e; --warnbg:#26201a;
      --shadow:none;
    }
  }
  :root[data-theme="dark"]{
    --bg:#15151a; --card:#1d1d23; --ink:#e9e7e3; --soft:#a29e98;
    --line:#2d2d35; --accent:#d69a5e; --warn:#d69a5e; --warnbg:#26201a;
    --shadow:none;
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth; scroll-padding-top:4.5rem}
  body{
    margin:0; background:var(--bg); color:var(--ink);
    font:1rem/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    padding:0 16px; -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:46rem; margin:0 auto; padding:2.4rem 0 5rem}
  h1{font-size:1.65rem; margin:0 0 .35rem; letter-spacing:-.015em}
  .meta{color:var(--soft); font-size:.88rem; margin:0 0 1.6rem}
  .kaynak-cubugu{
    position:sticky; top:0; z-index:5;
    background:color-mix(in srgb, var(--bg) 88%, transparent);
    backdrop-filter:saturate(1.4) blur(8px);
    padding:.75rem 0; border-bottom:1px solid var(--line);
    margin-bottom:1.6rem; display:flex; align-items:center;
    flex-wrap:wrap; gap:.7rem;
  }
  .top-buton{
    all:unset; cursor:pointer; color:var(--soft); font-size:.83rem;
    white-space:nowrap; transition:color .15s;
  }
  .top-buton:hover{color:var(--accent)}
  /* Gerçek bir <select> değil, buton + liste ile kurulmuş kendi açılır
     menümüz: Google Çeviri (translate.goog) sayfadaki <select>/<form>
     elemanlarını "form" sayıp engelliyor ("Bu formu desteklemiyor"
     uyarısı) — bu yüzden native select yerine düz buton/liste kullanılıyor. */
  .kaynak-sarici{position:relative}
  .kaynak-secici-buton{
    all:unset; font-size:.83rem; color:var(--ink); background:var(--card);
    border:1px solid var(--line); border-radius:6px; padding:.3rem .6rem;
    cursor:pointer; display:inline-flex; align-items:center; gap:.4rem;
    max-width:14rem;
  }
  .kaynak-secici-buton:hover{border-color:var(--accent)}
  .kaynak-secici-buton .ok{font-size:.7em; opacity:.7}
  .kaynak-secici-liste{
    all:unset; position:absolute; top:calc(100% + .3rem); left:0; z-index:6;
    display:flex; flex-direction:column;
    min-width:11rem; max-height:16rem; overflow-y:auto;
    background:var(--card); border:1px solid var(--line); border-radius:8px;
    box-shadow:0 4px 16px rgba(0,0,0,.12); padding:.35rem;
  }
  .kaynak-secici-liste[hidden]{display:none}
  .kaynak-secici-liste li{
    list-style:none; padding:.4rem .6rem; border-radius:5px;
    font-size:.85rem; color:var(--ink); cursor:pointer; white-space:nowrap;
  }
  .kaynak-secici-liste li:hover{background:var(--bg)}
  .kaynak-secici-liste li[aria-selected="true"]{color:var(--accent); font-weight:700}
  .izgara{display:grid; grid-template-columns:1fr; gap:.75rem; align-items:start}
  :root[data-duzen="liste"] .izgara{grid-template-columns:1fr !important}
  @media (min-width:640px){
    .wrap{max-width:52rem}
    .izgara{grid-template-columns:repeat(2, 1fr)}
  }
  @media (min-width:900px){
    .wrap{max-width:70rem}
  }
  @media (min-width:1200px){
    .wrap{max-width:78rem}
    .izgara{grid-template-columns:repeat(3, 1fr)}
  }
  article{
    background:var(--card); border:1px solid var(--line);
    border-radius:11px; padding:1.05rem 1.2rem 1.1rem;
    box-shadow:var(--shadow); transition:border-color .15s, transform .15s;
  }
  article:hover{border-color:var(--accent); transform:translateY(-1px)}
  article h3{
    margin:0 0 .35rem; font-size:1rem; line-height:1.35; font-weight:700;
    text-transform:uppercase; letter-spacing:.02em;
  }
  article h3 a{color:var(--ink); text-decoration:none}
  article h3 a:hover{color:var(--accent)}
  article img{
    display:block; width:100%; aspect-ratio:16/9; object-fit:cover;
    border-radius:8px; margin:0 0 1.1rem; background:var(--line);
  }
  article .tarih{margin:0 0 1.1rem; color:var(--soft); font-size:.78rem; letter-spacing:.02em}
  article .tarih.tahmini{cursor:help; border-bottom:1px dotted var(--soft); display:inline-block}
  article summary{
    cursor:pointer; display:inline-flex; align-items:center; gap:.3rem;
    color:var(--accent); font-weight:700; font-size:.82rem;
    text-transform:uppercase; letter-spacing:.04em; list-style:none;
  }
  article summary::-webkit-details-marker{display:none}
  article summary::after{content:"\\2304"; font-size:1rem; transition:transform .15s}
  article details[open] summary::after{transform:rotate(180deg)}
  article details p{margin:.7rem 0 0; color:var(--ink); opacity:.85; font-size:.97rem}
  .dinle, .paylas{
    display:inline-flex; align-items:center; gap:.35rem; margin:.75rem .5rem 0 0;
    padding:.35rem .7rem; border:1px solid var(--line); border-radius:6px;
    background:none; color:var(--accent); font-size:.78rem; font-weight:600;
    letter-spacing:.02em; cursor:pointer; font-family:inherit;
  }
  .dinle:hover, .paylas:hover{border-color:var(--accent)}
  .paylas:disabled{opacity:.6; cursor:default}
  .src{
    display:inline-block; margin-top:.75rem; font-size:.77rem;
    color:var(--soft); text-decoration:none; letter-spacing:.01em;
  }
  .src:hover{color:var(--accent)}
  .bos{
    background:var(--warnbg); border:1px solid var(--line);
    border-left:3px solid var(--warn);
    border-radius:8px; padding:.85rem 1rem; font-size:.9rem; color:var(--warn);
  }
  footer{
    margin-top:3rem; padding-top:1.2rem; border-top:1px solid var(--line);
    color:var(--soft); font-size:.8rem;
  }
  .cevir{
    display:inline-flex; align-items:center; gap:.35rem;
    color:var(--accent); text-decoration:none; font-weight:600;
  }
  .cevir:hover{text-decoration:underline}
  .tema-buton{
    display:inline-flex; align-items:center; gap:.35rem; margin-left:.5rem;
    padding:.3rem .65rem; border:1px solid var(--line); border-radius:6px;
    background:none; color:var(--soft); font-size:.78rem; font-weight:600;
    letter-spacing:.02em; cursor:pointer; font-family:inherit;
  }
  .tema-buton:hover{border-color:var(--accent); color:var(--accent)}
  .tema-buton:disabled{opacity:.4; cursor:default; border-color:var(--line); color:var(--soft)}
  .kategori-nav{display:flex; flex-wrap:wrap; gap:.5rem; margin:0 0 1.4rem}
  .kategori-buton{
    all:unset; cursor:pointer; padding:.4rem .95rem; border-radius:999px;
    border:1px solid var(--line); color:var(--soft); font-size:.85rem;
    font-weight:600; transition:color .15s, border-color .15s, background .15s;
  }
  .kategori-buton:hover{border-color:var(--accent); color:var(--accent)}
  .kategori-buton.aktif{background:var(--accent); border-color:var(--accent); color:#fff}
  @media (max-width:520px){
    .wrap{padding-top:1.4rem} h1{font-size:1.35rem}
    article{padding:.9rem 1rem}
  }
"""


# Paylaş butonlarının etiketi: metin, bir SVG'nin içinde CSS maskesi
# olarak çiziliyor — sayfada gerçek bir metin düğümü olmadığı için
# translate.goog butona dokunmayı yutamıyor, maske olduğu için de renk
# (currentColor) temayla birlikte değişiyor. textLength, farklı cihaz
# fontlarında metnin kutuya hep aynı genişlikte sığmasını sağlıyor.
def _etiket_maskesi(sinif: str, metin: str, metin_genisligi: int) -> str:
    genislik = 19 + metin_genisligi + 1
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {genislik} 16'>"
        "<g fill='none' stroke='black' stroke-width='2.2' stroke-linecap='round' "
        "stroke-linejoin='round' transform='translate(0 1) scale(.583)'>"
        "<path d='M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7'/>"
        "<polyline points='16 6 12 2 8 6'/><line x1='12' y1='2' x2='12' y2='15'/></g>"
        f"<text x='19' y='12.5' textLength='{metin_genisligi}' "
        "font-family='Helvetica,Arial,Roboto,sans-serif' font-size='12.5' "
        f"font-weight='600'>{metin}</text></svg>"
    )
    adres = "data:image/svg+xml," + urllib.parse.quote(svg)
    return (
        f".{sinif}{{width:{genislik}px;"
        f"-webkit-mask-image:url(\"{adres}\");mask-image:url(\"{adres}\")}}"
    )


PAYLAS_STIL = (
    ".paylas-satiri .paylas{margin-top:.5rem}"
    ".etiket-resmi{display:block;height:16px;background-color:currentColor;"
    "-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;"
    "-webkit-mask-size:100% 100%;mask-size:100% 100%}"
    + _etiket_maskesi("etiket-ozet", "Özeti paylaş", 72)
    + _etiket_maskesi("etiket-orijinal", "Orijinal metni paylaş", 120)
    + _etiket_maskesi("etiket-kopyalandi", "Bağlantı kopyalandı", 116)
)


def sayfa_olustur(kategoriler: dict[str, list[tuple[str, str, list[tuple[str, str, str, str, str, bool]]]]]) -> str:
    kategori_adlari = list(kategoriler.keys())
    ilk_kategori = kategori_adlari[0] if kategori_adlari else ""

    # Kategori sekmeleri: hangisine tıklanırsa JS o kategorinin kartlarını
    # gösterip kaynak filtre düğmelerini (aşağıdaki KATEGORI_VERISI'nden)
    # yeniden kurar.
    kategori_nav_dugmeleri = []
    for i, kat in enumerate(kategori_adlari):
        aktif = " aktif" if i == 0 else ""
        kategori_nav_dugmeleri.append(
            f'<button type="button" class="kategori-buton{aktif}" data-kategori="{kacir(kat)}">{kacir(kat)}</button>'
        )
    kategori_nav = "".join(kategori_nav_dugmeleri)

    # (kategori adı) -> [[kaynak adı, haber sayısı], ...] — JS'nin aktif
    # kategoriye göre kaynak filtre düğmelerini kurması için.
    kategori_kaynak_verisi = {
        kat: [[ad, len(makaleler)] for ad, _, makaleler in bolumler] for kat, bolumler in kategoriler.items()
    }

    toplam = 0
    kartlar = []
    bos_mesajlari = []
    for kat, bolumler in kategoriler.items():
        # Bir kategori içindeki tüm kaynakların haberlerini tek listede
        # birleştirip zamana göre (kaynaktan bağımsız) sırala.
        tum_makaleler: list[tuple[str, str, str, str, str, str, bool]] = []
        for ad, feed_url, makaleler in bolumler:
            toplam += len(makaleler)
            if not makaleler:
                # Hiç haberi olmayan kaynak için: o kaynak filtrelendiğinde
                # gösterilecek gizli bir mesaj (JS ile açılır).
                bos_mesajlari.append(
                    f'<p class="bos" data-kategori="{kacir(kat)}" data-kaynak="{kacir(ad)}" hidden>'
                    f"No stories could be retrieved from {kacir(ad)}. <code>{kacir(feed_url)}</code> "
                    f"may not be a valid RSS feed, or the source is temporarily unreachable.</p>"
                )
            for baslik_metin, url, ozet, gorsel, tarih, tahmini in makaleler:
                tum_makaleler.append((ad, baslik_metin, url, ozet, gorsel, tarih, tahmini))
        tum_makaleler.sort(key=lambda m: _sira_anahtari(m[5]), reverse=True)

        for ad, baslik_metin, url, ozet, gorsel, tarih, tahmini in tum_makaleler:
            gorsel_html = (
                f'<img src="{kacir(gorsel)}" alt="" loading="lazy" referrerpolicy="no-referrer">'
                if gorsel
                else ""
            )
            # Kaynak adı başlığın hemen altında da görünsün diye tarih
            # satırına eklendi (kartın altındaki "kaynak →" linki hâlâ
            # duruyor, bu sadece yukarıda da hemen görülebilsin diyedir).
            if tarih:
                # tahmini=True: gerçek yayın saati bulunamadı, gösterilen
                # bizim bu haberi ilk gördüğümüz an (bkz. ilk_gorulmeleri_*).
                # "~" ve title ile gerçek yayın saatiyle karışmasın diye
                # işaretleniyor.
                on_ek = "~" if tahmini else ""
                baslik_ozniteligi = (
                    ' title="İlk görüldüğü an; kaynağın gerçek yayın saati bulunamadı"' if tahmini else ""
                )
                tarih_html = (
                    f'<p class="tarih{" tahmini" if tahmini else ""}"{baslik_ozniteligi}>'
                    f"{on_ek}{kacir(tarihi_bicimlendir(tarih))} &middot; {kacir(ad)}</p>"
                )
            else:
                tarih_html = f'<p class="tarih">{kacir(ad)}</p>'
            # Paylaş butonlarında gerçek metin yok, etiket CSS maskesiyle
            # çizilen bir görsel (bkz. PAYLAS_STIL): translate.goog metin
            # içeren butonlara dokunulduğunda tıklamayı geçirmek yerine
            # kendi çeviri balonunu gösterip tıklamayı yutuyordu.
            # data-url: translate.goog sayfadaki <a href>'leri kendi
            # adreslerine çeviriyor, "Orijinal metni paylaş" haberin gerçek
            # adresine ihtiyaç duyduğu için dokunulmayan bir öznitelikte
            # saklanıyor.
            kartlar.append(
                f"""<article data-kategori="{kacir(kat)}" data-kaynak="{kacir(ad)}" data-url="{kacir(url)}">
  <h3><a href="{kacir(url)}" target="_blank" rel="noopener">{kacir(baslik_metin)}</a></h3>
  {tarih_html}
  {gorsel_html}
  <details>
    <summary>Read more</summary>
    <p>{kacir(ozet)}</p>
  </details>
  <button type="button" class="dinle">&#128266; Listen</button>
  <a class="src" href="{kacir(url)}" target="_blank" rel="noopener">{kacir(ad)} &rarr;</a>
  <div class="paylas-satiri">
    <button type="button" class="paylas paylas-ozet" title="Özeti paylaş" aria-label="Özeti paylaş"><span class="etiket-resmi etiket-ozet"></span></button>
    <button type="button" class="paylas paylas-orijinal" title="Orijinal metni paylaş" aria-label="Orijinal metni paylaş"><span class="etiket-resmi etiket-orijinal"></span></button>
  </div>
</article>"""
            )

    icerik = (
        '<div class="izgara" id="izgara">\n' + "\n".join(kartlar) + "\n</div>\n" + "\n".join(bos_mesajlari)
    )

    # Sayfa ilk yüklendiğinde (JS çalışmadan önceki an) sadece ilk kategori
    # görünsün diye — JS zaten aynısını yapıyor ama bu, kısa bir "tüm
    # kategoriler bir anda görünür" titremesini önler.
    ekstra_stil = (
        ".izgara article[data-kategori]{display:none}"
        '.izgara article[data-kategori="' + kacir(ilk_kategori) + '"]{display:block}'
    )

    zaman_metni = datetime.now(timezone.utc).astimezone(TR_SAATI).strftime("%Y-%m-%d %H:%M TRT")
    # Deploy'un gerçekten güncellendiğini görmek için. SHA tek başına yetmiyor:
    # zamanlayıcı aynı commit'i tekrar tekrar çalıştırdığı için commit
    # değişmeden de yeni deploy oluyor. Çalıştırma numarası her seferinde
    # arttığı için eski/yeni kopya ayrımı footer'dan tek bakışta anlaşılır.
    build = os.environ.get("GITHUB_SHA", "local")[:7]
    calistirma = os.environ.get("GITHUB_RUN_NUMBER")
    if calistirma:
        build = f"{build}#{calistirma}"

    # Google arama sonucunda Türkçe çıkması için title/description Türkçe
    # yazılıyor — sayfanın kendisi lang="en" kalıyor (gerçek içerik/otomatik
    # yönlendirme mantığı buna bağlı), ama title/description Google'ın
    # snippet için okuduğu bağımsız metinler; hedef kitle Türkçe olduğu
    # için bu ayrım yaygın ve sorunsuz bir pratik.
    baslik = "World Brief — Dünyadan Haberler, Özetlenmiş"
    aciklama = (
        f"Dünya, bilim, teknoloji, sanat, gezi ve yemek haberleri {len(KAYNAKLAR)} kaynaktan özetlenip "
        f"her yarım saatte bir güncellenir. Şu an {toplam} haber."
    )
    try:
        html2canvas_js = HTML2CANVAS_DOSYASI.read_text(encoding="utf-8")
    except FileNotFoundError:
        html2canvas_js = ""
    html2canvas_etiketi = f"<script>{html2canvas_js}</script>" if html2canvas_js else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="google-site-verification" content="2fw9kal9TSUlQlGZdebXp3fpQ4v1C5x5MSbxnbxlv2E">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%93%B0%3C/text%3E%3C/svg%3E">
<title>{kacir(baslik)}</title>
<meta name="description" content="{kacir(aciklama)}">
<link rel="canonical" href="{SITE_URL}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="World Brief">
<meta property="og:locale" content="tr_TR">
<meta property="og:title" content="{kacir(baslik)}">
<meta property="og:description" content="{kacir(aciklama)}">
<meta property="og:url" content="{SITE_URL}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{kacir(baslik)}">
<meta name="twitter:description" content="{kacir(aciklama)}">
{html2canvas_etiketi}
<style>{STIL}</style>
<style>{PAYLAS_STIL}</style>
<style>{ekstra_stil}</style>
</head>
<body>
<div class="wrap" id="top">
<h1>&#128240; World Brief</h1>
<p class="meta">{zaman_metni} &middot; {toplam} stories &middot; <a id="cevir-linki" class="cevir" href="https://translate.google.com/translate?sl=en&amp;tl=tr" target="_blank" rel="noopener">&#127481;&#127479; Read in Turkish</a> <button type="button" id="tema-buton" class="tema-buton">&#127769; Dark mode</button> <button type="button" id="duzen-buton" class="tema-buton">&#9776; List view</button> <button type="button" id="yazi-kucult-buton" class="tema-buton" title="Decrease text size" aria-label="Decrease text size">A&minus;</button> <button type="button" id="yazi-buyut-buton" class="tema-buton" title="Increase text size" aria-label="Increase text size">A+</button></p>
<div class="kategori-nav">{kategori_nav}</div>
<div class="kaynak-cubugu">
<button type="button" class="top-buton" id="top-buton">&#8593; Top</button>
<div class="kaynak-sarici">
<button type="button" id="kaynak-secici-buton" class="kaynak-secici-buton" aria-haspopup="listbox" aria-expanded="false"><span class="kaynak-secici-etiket">All Sources</span><span class="ok">&#9662;</span></button>
<ul id="kaynak-secici-liste" class="kaynak-secici-liste" role="listbox" hidden></ul>
</div>
</div>
{icerik}
<footer>Generated automatically &middot; {zaman_metni} &middot; build {build}</footer>
</div>
<script>
(function(){{
  var a = document.getElementById('cevir-linki');
  // Zaten translate.goog aynasındaysak (kendi yönlendirmemizden ya da
  // kullanıcının kendi tıklamasından) bunu adres/dilden anlıyoruz.
  var suankiGoog = location.hostname.indexOf('.translate.goog') !== -1;

  // Chrome'un kendi "Sayfayı çevir" özelliğinin kullandığı translate.goog
  // ayna adresi — eski translate.google.com/translate?...&u= proxy'sinden
  // farklı olarak hâlâ güvenilir çalışıyor.
  function cevrilmisAdres() {{
    var host = location.hostname.replace(/-/g, '--').replace(/\./g, '-') + '.translate.goog';
    var ayrac = location.search ? '&' : '?';
    return location.protocol + '//' + host + location.pathname + location.search +
      ayrac + '_x_tr_sl=en&_x_tr_tl=tr&_x_tr_hl=tr&_x_tr_pto=wapp';
  }}

  // translate.goog'un anasayfa adını gerçek adrese çevirir (kodlama:
  // önce her "-" harfi "--" olarak ikizlenir, sonra her "." "-" olur;
  // burada tam tersi uygulanıyor).
  function orijinalAdres() {{
    var kodlanmis = location.hostname.replace(/\.translate\.goog$/, '');
    var host = kodlanmis.split('--').map(function(parca){{ return parca.replace(/-/g, '.'); }}).join('-');
    return location.protocol + '//' + host + location.pathname;
  }}

  if (a) {{
    if (suankiGoog) {{
      a.href = orijinalAdres();
      a.textContent = '🇬🇧 Read in English';
      // Kullanıcı elle İngilizce'ye dönerse bir daha otomatik Türkçeye
      // sürüklenmesin diye tercihi hatırla.
      a.addEventListener('click', function(){{
        try {{ localStorage.setItem('dilTercihi', 'en'); }} catch (e) {{}}
      }});
    }} else {{
      a.href = cevrilmisAdres();
    }}
  }}

  // ?en=1 ile açılırsa otomatik Türkçe yönlendirmesi kalıcı olarak
  // kapatılır. Bazı kurumsal ağlar translate.goog'u "Anonymizer"
  // (proxy) kategorisine sokup engelliyor; bu durumda otomatik
  // yönlendirme kullanıcıyı "Read in English"e tıklamaya fırsat
  // bulamadan doğrudan engellenen sayfaya götürüyordu. Bu adresi bir
  // kez açmak yeterli, tercih localStorage'da kalıcı.
  try {{
    if (new URLSearchParams(location.search).get('en') === '1') {{
      localStorage.setItem('dilTercihi', 'en');
    }}
  }} catch (e) {{}}

  // Tarayıcı dili Türkçeyse (ve kullanıcı elle İngilizce'yi seçmediyse)
  // sayfa ilk yüklenirken otomatik olarak Türkçe çeviriye yönlendir —
  // "Read in Turkish"e tıklamaya gerek kalmadan.
  if (!suankiGoog) {{
    var tercih = null;
    try {{ tercih = localStorage.getItem('dilTercihi'); }} catch (e) {{}}
    if (tercih !== 'en') {{
      var dil = (navigator.language || (navigator.languages && navigator.languages[0]) || '').toLowerCase();
      if (dil.indexOf('tr') === 0) {{
        location.replace(cevrilmisAdres());
      }}
    }}
  }}
}})();

// Karanlık tema düğmesi: sistem tercihinden bağımsız manuel geçiş,
// tercih tarayıcıda (localStorage) hatırlanır.
(function(){{
  var dugme = document.getElementById('tema-buton');
  if (!dugme) return;

  function etiketGuncelle(koyuMu) {{
    dugme.innerHTML = koyuMu ? '&#9728;&#65039; Light mode' : '&#127769; Dark mode';
  }}

  var kayitli = null;
  try {{ kayitli = localStorage.getItem('tema'); }} catch (e) {{}}
  if (kayitli === 'dark' || kayitli === 'light') {{
    document.documentElement.setAttribute('data-theme', kayitli);
  }}

  var sistemKoyu = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  etiketGuncelle(kayitli ? kayitli === 'dark' : sistemKoyu);

  dugme.addEventListener('click', function(){{
    var mevcut = document.documentElement.getAttribute('data-theme');
    var suankiKoyu = mevcut ? mevcut === 'dark' : sistemKoyu;
    var yeni = suankiKoyu ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', yeni);
    etiketGuncelle(yeni === 'dark');
    try {{ localStorage.setItem('tema', yeni); }} catch (e) {{}}
  }});
}})();

// Döşeme/liste düzeni düğmesi: haberleri yan yana kutucuklar (döşeme)
// yerine tek sütun akış olarak göstermeye zorlar. Tercih hatırlanır.
(function(){{
  var dugme = document.getElementById('duzen-buton');
  if (!dugme) return;

  function etiketGuncelle(listeMi) {{
    dugme.innerHTML = listeMi ? '&#9638; Tile view' : '&#9776; List view';
  }}

  var kayitli = null;
  try {{ kayitli = localStorage.getItem('duzen'); }} catch (e) {{}}
  if (kayitli === 'liste') {{
    document.documentElement.setAttribute('data-duzen', 'liste');
  }}
  etiketGuncelle(kayitli === 'liste');

  dugme.addEventListener('click', function(){{
    var suankiListe = document.documentElement.getAttribute('data-duzen') === 'liste';
    var yeni = suankiListe ? 'dosme' : 'liste';
    if (yeni === 'liste') {{
      document.documentElement.setAttribute('data-duzen', 'liste');
    }} else {{
      document.documentElement.removeAttribute('data-duzen');
    }}
    etiketGuncelle(yeni === 'liste');
    try {{ localStorage.setItem('duzen', yeni); }} catch (e) {{}}
  }});
}})();

// Yazı boyutu düğmeleri: tüm sayfa rem birimiyle ölçeklendiği için
// <html>'in kök font-size'ını değiştirmek yeter, her şey orantılı
// büyür/küçülür. Tercih tarayıcıda (localStorage) hatırlanır.
(function(){{
  var kucultDugme = document.getElementById('yazi-kucult-buton');
  var buyutDugme = document.getElementById('yazi-buyut-buton');
  if (!kucultDugme || !buyutDugme) return;

  var ADIMLAR = [80, 90, 100, 110, 120, 130, 140, 150]; // yüzde
  var VARSAYILAN_INDEKS = ADIMLAR.indexOf(100);

  function indeksiBul(yuzde) {{
    var i = ADIMLAR.indexOf(yuzde);
    return i === -1 ? VARSAYILAN_INDEKS : i;
  }}

  function uygula(indeks) {{
    var yuzde = ADIMLAR[indeks];
    document.documentElement.style.fontSize = yuzde === 100 ? '' : yuzde + '%';
    kucultDugme.disabled = indeks === 0;
    buyutDugme.disabled = indeks === ADIMLAR.length - 1;
    try {{ localStorage.setItem('yaziOlcek', String(yuzde)); }} catch (e) {{}}
  }}

  var kayitliYuzde = null;
  try {{ kayitliYuzde = parseInt(localStorage.getItem('yaziOlcek'), 10); }} catch (e) {{}}
  var mevcutIndeks = indeksiBul(kayitliYuzde || 100);
  uygula(mevcutIndeks);

  kucultDugme.addEventListener('click', function(){{
    mevcutIndeks = Math.max(0, mevcutIndeks - 1);
    uygula(mevcutIndeks);
  }});
  buyutDugme.addEventListener('click', function(){{
    mevcutIndeks = Math.min(ADIMLAR.length - 1, mevcutIndeks + 1);
    uygula(mevcutIndeks);
  }});
}})();

// Kategori + kaynak filtresi: üstteki kategori sekmesi hangi konunun
// kartları görünsün onu belirler; altındaki tek "Kaynak" açılır menüsü
// her kategori değişiminde bu kategorinin kaynaklarına göre JS
// tarafından yeniden kurulur (sunucu tarafında bir buton yığını basmak
// yerine — çok sayıda kaynağı olan kategorilerde bu, N ayrı düğme yerine
// tek bir seçiciye sığar). "All Sources" o kategorinin tüm haberlerini
// zamana göre karışık gösterir, bir kaynak seçmek sayfa yeniden
// yüklenmeden sadece onu gösterir.
//
// Bilerek gerçek bir <select> DEĞİL: Google Çeviri (translate.goog)
// sayfadaki <select>/<form> elemanlarını "form" sayıp bir uyarıyla
// engelliyor. Onun yerine düz bir buton + gizli/görünür <ul> listesiyle
// kendi açılır menümüz kuruluyor.
var KATEGORI_VERISI = {json.dumps(kategori_kaynak_verisi, ensure_ascii=False)};
(function(){{
  var izgara = document.getElementById('izgara');
  var seciciButon = document.getElementById('kaynak-secici-buton');
  var seciciListe = document.getElementById('kaynak-secici-liste');
  var topButonu = document.getElementById('top-buton');
  var kategoriButonlari = document.querySelectorAll('.kategori-buton');
  if (!izgara || !seciciButon || !seciciListe || !kategoriButonlari.length) return;

  var aktifKategori = kategoriButonlari[0].dataset.kategori;
  var aktifKaynak = 'all';

  if (topButonu) {{
    topButonu.addEventListener('click', function(){{
      window.scrollTo({{top: 0, behavior: 'smooth'}});
    }});
  }}

  function uygula() {{
    izgara.querySelectorAll('article[data-kategori]').forEach(function(el){{
      var kategoriUyum = el.dataset.kategori === aktifKategori;
      var kaynakUyum = aktifKaynak === 'all' || el.dataset.kaynak === aktifKaynak;
      // '' değil 'block': boş string satır içi stili kaldırır, o zaman
      // sayfanın başındaki "sadece ilk kategori görünsün" CSS kuralı
      // (ekstra_stil) tekrar devreye girip kartı gizler. Satır içi stil
      // her zaman sayfa CSS'inden önceliklidir, bu yüzden açıkça 'block'
      // yazmak gerekiyor.
      el.style.display = (kategoriUyum && kaynakUyum) ? 'block' : 'none';
    }});
    document.querySelectorAll('.bos[data-kategori]').forEach(function(el){{
      var kategoriUyum = el.dataset.kategori === aktifKategori;
      el.hidden = !(kategoriUyum && aktifKaynak !== 'all' && el.dataset.kaynak === aktifKaynak);
    }});
  }}

  function listeyiKapat() {{
    seciciListe.hidden = true;
    seciciButon.setAttribute('aria-expanded', 'false');
  }}

  // Butonun etiketini SADECE textContent ile değiştirmek yerine, o
  // etiketi taşıyan span'ı yepyeni bir span ile değiştiriyoruz. Google
  // Çeviri (translate.goog) sayfayı ilk yüklerken DOM'daki mevcut
  // öğeleri çevirir, sonradan eklenen düğümleri de bir gözlemciyle
  // yakalayıp çevirir — ama var olan bir düğümün textContent'i
  // değiştirildiğinde bunu fark etmez (yalnızca ekleme/çıkarma
  // izliyor). innerHTML ile kurulan <li> seçenekleri tam olarak bu
  // yüzden çevriliyordu; buton etiketi ise düz metin ataması olduğu
  // için çevrilmeden İngilizce kalıyordu. Etiketi bağımsız bir span
  // yapıp her güncellemede yepyeni bir span ile değiştirmek, <li>'lerle
  // aynı "yeni düğüm" davranışını taklit ediyor.
  function etiketiGuncelle(metin) {{
    var eskiEtiket = seciciButon.querySelector('.kaynak-secici-etiket');
    var yeniEtiket = document.createElement('span');
    yeniEtiket.className = 'kaynak-secici-etiket';
    yeniEtiket.textContent = metin;
    eskiEtiket.replaceWith(yeniEtiket);
  }}

  function kaynakSeciciKur(butonuSifirla) {{
    var kaynaklar = KATEGORI_VERISI[aktifKategori] || [];
    var kategoriToplami = kaynaklar.reduce(function(acc, k){{ return acc + k[1]; }}, 0);
    var html = '<li role="option" aria-selected="true" data-filtre="all">All Sources (' + kategoriToplami + ')</li>';
    kaynaklar.forEach(function(k){{
      html += '<li role="option" aria-selected="false" data-filtre="' + k[0] + '">' + k[0] + ' (' + k[1] + ')</li>';
    }});
    seciciListe.innerHTML = html;
    // İlk yüklemede butonun etiketine hiç DOKUNMA: sunucudan gelen
    // "All Sources" span'ı sayfanın ilk taramasında zaten Google
    // tarafından çevrilmiş olur. Kategori değişince filtre gerçekten
    // "all"a sıfırlandığı için orada etiketiGuncelle ile güncellemek
    // gerekiyor (yeni bir span olduğundan Google bunu da yakalar).
    if (butonuSifirla) {{
      etiketiGuncelle('All Sources');
    }}
    listeyiKapat();
  }}

  seciciButon.addEventListener('click', function(olay){{
    olay.stopPropagation();
    var acikMi = !seciciListe.hidden;
    if (acikMi) {{
      listeyiKapat();
    }} else {{
      seciciListe.hidden = false;
      seciciButon.setAttribute('aria-expanded', 'true');
    }}
  }});

  seciciListe.addEventListener('click', function(olay){{
    var secenek = olay.target.closest('[data-filtre]');
    if (!secenek) return;
    aktifKaynak = secenek.dataset.filtre;
    etiketiGuncelle(secenek.textContent);
    seciciListe.querySelectorAll('[data-filtre]').forEach(function(li){{
      li.setAttribute('aria-selected', li === secenek ? 'true' : 'false');
    }});
    listeyiKapat();
    uygula();
  }});

  document.addEventListener('click', function(olay){{
    if (!seciciListe.hidden && !seciciListe.contains(olay.target) && olay.target !== seciciButon) {{
      listeyiKapat();
    }}
  }});

  kategoriButonlari.forEach(function(buton){{
    buton.addEventListener('click', function(){{
      aktifKategori = buton.dataset.kategori;
      aktifKaynak = 'all';
      kategoriButonlari.forEach(function(b){{ b.classList.toggle('aktif', b === buton); }});
      kaynakSeciciKur(true);
      uygula();
    }});
  }});

  kaynakSeciciKur();
  uygula();
}})();

// Sesli okuma: tarayıcının yerleşik Web Speech API'si, sunucu/API yok.
(function(){{
  if (!('speechSynthesis' in window)) {{
    document.querySelectorAll('.dinle').forEach(function(b){{ b.style.display = 'none'; }});
    return;
  }}

  function sifirla(buton) {{
    buton.dataset.playing = '0';
    buton.innerHTML = '&#128266; Listen';
  }}

  // Google'ın translate.goog aynasında sayfanın görünen metni zaten
  // Türkçeye çevrilmiş olarak geliyor; bu durumda ekrandaki metni okuyup
  // Türkçe sesle seslendiriyoruz. Normal sayfada İngilizce okunuyor.
  var turkceMi = location.hostname.indexOf('translate.goog') !== -1;

  // Sadece .lang ayarlamak yetmiyor — bazı tarayıcılar yine de varsayılan
  // (genelde İngilizce) sesi kullanıp metni yanlış telaffuzla okuyor.
  // Uygun dildeki gerçek sesi (voice) elle seçmek gerekiyor. Ses listesi
  // bazı tarayıcılarda asenkron yükleniyor, bu yüzden voiceschanged de
  // dinleniyor.
  var sesListesi = speechSynthesis.getVoices();
  speechSynthesis.onvoiceschanged = function(){{ sesListesi = speechSynthesis.getVoices(); }};

  function sesSec(dilOneki) {{
    for (var i = 0; i < sesListesi.length; i++) {{
      if (sesListesi[i].lang && sesListesi[i].lang.toLowerCase().indexOf(dilOneki) === 0) {{
        return sesListesi[i];
      }}
    }}
    return null;
  }}

  document.addEventListener('click', function(olay){{
    var buton = olay.target.closest('.dinle');
    if (!buton) return;

    var calaniydi = buton.dataset.playing === '1';
    speechSynthesis.cancel();
    document.querySelectorAll('.dinle').forEach(sifirla);
    if (calaniydi) return;

    var kart = buton.closest('article');
    var baslikEl = kart.querySelector('h3');
    var ozetEl = kart.querySelector('details p');
    var metin = (baslikEl ? baslikEl.textContent : '') + '. ' + (ozetEl ? ozetEl.textContent : '');

    var konusma = new SpeechSynthesisUtterance(metin);
    var ses = sesSec(turkceMi ? 'tr' : 'en');
    if (ses) konusma.voice = ses;
    konusma.lang = turkceMi ? 'tr-TR' : 'en-US';
    konusma.onend = function(){{ sifirla(buton); }};
    konusma.onerror = function(){{ sifirla(buton); }};
    buton.dataset.playing = '1';
    buton.innerHTML = '&#9209; Stop';
    speechSynthesis.speak(konusma);
  }});
}})();

// Kart paylaşımı: başlık/görsel/özet/kaynağı tek bir PNG'ye çevirip
// (mümkünse) yerel paylaşım penceresini açar, değilse indirir. Kartın
// görseli çoğu kaynakta CORS izni olmayan üçüncü taraf bir sunucudan
// geldiği için doğrudan html2canvas ile çizilemiyor; bu yüzden SADECE
// bu ekran görüntüsü için images.weserv.nl üzerinden CORS izinli bir
// kopyası isteniyor — sayfanın normal gösterdiği görsel bundan
// etkilenmiyor, sadece bu tek seferlik render için kullanılıyor.
(function(){{
  if (typeof html2canvas === 'undefined') {{
    document.querySelectorAll('.paylas-ozet').forEach(function(b){{ b.style.display = 'none'; }});
    return;
  }}

  function corsGorseli(url) {{
    return 'https://images.weserv.nl/?url=' + encodeURIComponent(url.replace(/^https?:\\/\\//, ''));
  }}

  document.addEventListener('click', function(olay){{
    var buton = olay.target.closest('.paylas-ozet');
    if (!buton || buton.disabled) return;

    var kart = buton.closest('article');
    var orijinalGorsel = kart.querySelector('img');
    var kopya = kart.cloneNode(true);
    kopya.querySelectorAll('.dinle, .paylas-satiri').forEach(function(b){{ b.remove(); }});
    var detay = kopya.querySelector('details');
    if (detay) detay.open = true;

    // Kart ekrandaki genişliğiyle (geniş masaüstü pencerelerinde 700px'i
    // geçebiliyor) yakalanınca metin, paylaşılan görsel telefonda
    // büyütülüp bakıldığında bir satıra çok fazla karakter sığdığı için
    // ufak/okunaksız kalıyordu. Kart burada sabit, telefon ekranı
    // genişliğine yakın bir genişliğe (satır başına ~37 karakter hedefi,
    // ilk denemedeki ~40'tan kullanıcı isteğiyle %10 azaltıldı) zorlanıyor;
    // yazı tipi rem cinsinden sabit olduğundan metin bu dar kutuda daha
    // az karaktere sığıp daha büyük/okunur görünüyor.
    var PAYLASIM_GENISLIGI = 346;

    var sarici = document.createElement('div');
    sarici.style.cssText = 'position:fixed; left:-9999px; top:0; width:' + PAYLASIM_GENISLIGI + 'px;';
    sarici.appendChild(kopya);
    document.body.appendChild(sarici);

    var gorselHazir = Promise.resolve();
    var kopyaGorsel = kopya.querySelector('img');
    if (kopyaGorsel && orijinalGorsel) {{
      // html2canvas ne CSS aspect-ratio'yu ne de object-fit:cover'ı
      // destekliyor; sadece kutu boyutunu zorlamak (bir önceki deneme)
      // görseli kırpmadan olduğu gibi ya da kendi doğal boyutunda
      // çiziyor, bu yüzden hâlâ ince-uzun çıkıyordu. Kırpma/ölçekleme
      // burada elle bir canvas'a "cover" mantığıyla çizilip html2canvas'a
      // ZATEN doğru piksel oranında bir görsel veriliyor — html2canvas'ın
      // sadece düz bir resmi olduğu gibi çizmesi yetiyor. Hedef kutu,
      // kopyanın YENİ (sabit genişlikli) haldeki kendi boyutundan
      // okunuyor ki 16/9 oranı PAYLASIM_GENISLIGI'ne göre doğru çıksın.
      var hedefGenislik = kopyaGorsel.offsetWidth;
      var hedefYukseklik = kopyaGorsel.offsetHeight;
      kopyaGorsel.style.width = hedefGenislik + 'px';
      kopyaGorsel.style.height = hedefYukseklik + 'px';
      gorselHazir = new Promise(function(tamam){{
        var zamanAsimi = setTimeout(function(){{ kopyaGorsel.remove(); tamam(); }}, 6000);
        var yukleyici = new Image();
        yukleyici.crossOrigin = 'anonymous';
        yukleyici.onload = function(){{
          clearTimeout(zamanAsimi);
          try {{
            var canvas = document.createElement('canvas');
            canvas.width = hedefGenislik;
            canvas.height = hedefYukseklik;
            var olcek = Math.max(hedefGenislik / yukleyici.naturalWidth, hedefYukseklik / yukleyici.naturalHeight);
            var cizilenGenislik = yukleyici.naturalWidth * olcek;
            var cizilenYukseklik = yukleyici.naturalHeight * olcek;
            canvas.getContext('2d').drawImage(
              yukleyici,
              (hedefGenislik - cizilenGenislik) / 2,
              (hedefYukseklik - cizilenYukseklik) / 2,
              cizilenGenislik, cizilenYukseklik
            );
            // .decode() burada bazı tarayıcılarda hiç sonuçlanmıyor
            // (muhtemelen ekran dışına taşınmış/henüz yerleşimi
            // tamamlanmamış bir öğe için); data: URI zaten senkron
            // olarak hazır olduğundan beklemeye gerek yok.
            kopyaGorsel.src = canvas.toDataURL('image/jpeg', 0.92);
            tamam();
            return;
          }} catch (e) {{
            kopyaGorsel.remove();
          }}
          tamam();
        }};
        yukleyici.onerror = function(){{
          clearTimeout(zamanAsimi);
          kopyaGorsel.remove();
          tamam();
        }};
        yukleyici.src = corsGorseli(orijinalGorsel.currentSrc || orijinalGorsel.src);
      }});
    }}

    // Bekleme sırasında buton sadece soluklaşıyor (.paylas:disabled);
    // etikete metin yazılmıyor ki translate.goog'a çevirecek bir şey
    // verilmesin.
    buton.disabled = true;

    function birak() {{
      sarici.remove();
      buton.disabled = false;
    }}

    gorselHazir.then(function(){{
      return html2canvas(kopya, {{
        backgroundColor: getComputedStyle(document.body).backgroundColor,
        useCORS: true,
        scale: 2,
      }});
    }}).then(function(canvas){{
      return new Promise(function(tamam){{ canvas.toBlob(tamam, 'image/png'); }});
    }}).then(function(blob){{
      birak();
      if (!blob) return;

      var baslikEl = kart.querySelector('h3');
      var dosya = new File([blob], 'world-brief.png', {{ type: 'image/png' }});

      if (navigator.canShare && navigator.canShare({{ files: [dosya] }})) {{
        navigator.share({{ files: [dosya], title: baslikEl ? baslikEl.textContent : 'World Brief' }}).catch(function(){{}});
        return;
      }}

      var indirmeLinki = document.createElement('a');
      indirmeLinki.href = URL.createObjectURL(blob);
      indirmeLinki.download = 'world-brief.png';
      document.body.appendChild(indirmeLinki);
      indirmeLinki.click();
      indirmeLinki.remove();
      setTimeout(function(){{ URL.revokeObjectURL(indirmeLinki.href); }}, 30000);
    }}).catch(function(hata){{
      birak();
      console.error('Paylaşım görseli oluşturulamadı:', hata);
    }});
  }});
}})();

// "Orijinal metni paylaş": haberin iki bağlantısını birlikte paylaşır —
// translate.goog üzerinden Türkçe çevirisi ve kaynaktaki orijinali.
// Yalnız orijinal gönderildiğinde bazı sayfalar alıcının Chrome'unda
// Türkçeye çevrilemedi; yalnız çeviri gönderilse translate.goog'u
// engelleyen ağlarda (ör. kullanıcının iş yeri) hiç açılmaz. Çeviri
// adresi sayfanın kendi "Read in Turkish" bağlantısındaki
// (cevrilmisAdres) kuralla kuruluyor. Paylaşım penceresi yoksa metin
// panoya kopyalanıyor.
(function(){{
  function ceviriAdresi(url) {{
    var u = new URL(url);
    var host = u.hostname.replace(/-/g, '--').replace(/\\./g, '-') + '.translate.goog';
    var ayrac = u.search ? '&' : '?';
    return u.protocol + '//' + host + u.pathname + u.search + ayrac +
      '_x_tr_sl=en&_x_tr_tl=tr&_x_tr_hl=tr&_x_tr_pto=wapp' + u.hash;
  }}

  function kopyalandiGoster(buton) {{
    var etiket = buton.querySelector('.etiket-resmi');
    etiket.classList.add('etiket-kopyalandi');
    clearTimeout(buton._zamanlayici);
    buton._zamanlayici = setTimeout(function(){{ etiket.classList.remove('etiket-kopyalandi'); }}, 2000);
  }}

  function panoyaKopyala(buton, metin) {{
    var kopya = (navigator.clipboard && navigator.clipboard.writeText)
      ? navigator.clipboard.writeText(metin)
      : Promise.reject(new Error('pano yok'));
    kopya.then(function(){{ kopyalandiGoster(buton); }}, function(){{
      window.prompt('Bağlantıyı kopyalayın:', metin);
    }});
  }}

  document.addEventListener('click', function(olay){{
    var buton = olay.target.closest('.paylas-orijinal');
    if (!buton) return;
    var kart = buton.closest('article');
    var adres = kart.dataset.url;
    if (!adres) return;
    var baslikEl = kart.querySelector('h3');
    var baslik = baslikEl ? baslikEl.textContent.trim() : '';
    var turkce;
    try {{ turkce = ceviriAdresi(adres); }} catch (e) {{ turkce = null; }}
    // Bağlantılar ayrı bir url alanı yerine metnin içinde: url verilince
    // bazı uygulamalar onu metnin başına ya da sonuna kendisi ekliyor,
    // hangisinin Türkçe hangisinin orijinal olduğu karışıyor.
    var metin = baslik + '\\n\\n' +
      (turkce ? 'Türkçe: ' + turkce + '\\n\\n' : '') +
      'Orijinal: ' + adres;

    if (navigator.share) {{
      navigator.share({{ title: baslik, text: metin }}).catch(function(hata){{
        if (hata && hata.name === 'AbortError') return;
        panoyaKopyala(buton, metin);
      }});
      return;
    }}
    panoyaKopyala(buton, metin);
  }});
}})();
</script>
</body>
</html>
"""


def uret() -> None:
    kategoriler: dict[str, list[tuple[str, str, list[tuple[str, str, str, str, str, bool]]]]] = {}
    ilk_gorulme_haritasi = ilk_gorulmeleri_yukle()
    gorulen_urller: set[str] = set()

    for kategori, ad, feed_url in KAYNAKLAR:
        sayi = KATEGORI_SAYISI.get(kategori, N)
        urls, besleme_tarih_haritasi = besleme_ogeleri(feed_url, sayi)
        if not urls:
            # Gerçek bir besleme yok (anasayfa/site haritası kaynağı,
            # ör. CNN, Al Jazeera) — mevcut otomatik keşif/site haritası
            # yoluna düş. besleme_tarih_haritasi zaten boş.
            urls = besleme_listesi(feed_url, sayi)
        makaleler = []

        for url in urls:
            sonuc = makale_getir(url)
            if sonuc is None:
                continue
            ozet = ilk_cumleler(sonuc["govde"], K)
            if not ozet:
                continue
            try:
                normalize_edilmis_url = normalize_url(url)
            except Exception:  # noqa: BLE001
                normalize_edilmis_url = url
            gorulen_urller.add(normalize_edilmis_url)

            tarih = _guvenilir_tarih(sonuc["tarih"], besleme_tarih_haritasi.get(normalize_edilmis_url, ""))
            tahmini = False
            if not tarih:
                # Ne sayfada ne beslemede tarih bulunamadı (CNN, Al Jazeera
                # gibi gerçek RSS'i olmayan kaynaklarda görülüyor). Bu
                # makaleyi daha önce görmüşsek o an kullanılır; ilk kezse
                # şimdi kaydedilir. Gerçek yayın saati değil, sadece bizim
                # ilk fark ettiğimiz an — bkz. tarih_html'deki "~" işareti.
                onceki = ilk_gorulme_haritasi.get(normalize_edilmis_url)
                if not onceki:
                    onceki = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
                    ilk_gorulme_haritasi[normalize_edilmis_url] = onceki
                tarih = onceki
                tahmini = True

            zaman = _tarihi_ayristir(tarih)
            if zaman is not None and zaman.tzinfo is not None:
                if datetime.now(timezone.utc) - zaman > ESKI_HABER_ESIGI:
                    continue

            makaleler.append((sonuc["baslik"], url, ozet, sonuc["gorsel"], tarih, tahmini))

        makaleler.sort(key=lambda m: _sira_anahtari(m[4]), reverse=True)
        kategoriler.setdefault(kategori, []).append((ad, feed_url, makaleler))
        print(f"{kategori} / {ad}: {len(makaleler)} haber")

    ilk_gorulmeleri_kaydet(ilk_gorulme_haritasi, gorulen_urller)

    toplam = sum(len(makaleler) for bolumler in kategoriler.values() for _, _, makaleler in bolumler)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(sayfa_olustur(kategoriler), encoding="utf-8")

    # Google'ın siteyi taraması ve indekslemesi için: robots.txt taramaya
    # izin verip sitemap'in yerini bildiriyor, sitemap.xml de (site tek
    # sayfa olduğu için) o tek url'i lastmod'uyla listeliyor. dist/ her
    # çalıştırmada sıfırdan üretilip gh-pages'e yazıldığından (bkz.
    # workflow) bu dosyalar da her seferinde burada tazelenmesi gerekiyor.
    simdi_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (CIKTI.parent / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8"
    )
    (CIKTI.parent / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>{SITE_URL}</loc>\n"
        f"    <lastmod>{simdi_iso}</lastmod>\n"
        "    <changefreq>hourly</changefreq>\n"
        "  </url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )

    print(f"Bitti: {CIKTI} ({toplam} haber)")


if __name__ == "__main__":
    uret()
