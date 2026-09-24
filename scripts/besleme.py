"""Kaynaklardan haber adreslerini ve makale metinlerini çekme."""

import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin

import feedparser
import trafilatura
from courlan import get_hostinfo, normalize_url
from trafilatura.feeds import FeedParameters, determine_feed, find_feed_urls
from trafilatura.sitemaps import find_robots_sitemaps, sitemap_search

# Sayfası çekilmeden atlanan adresler: video/ses oynatıcı sayfaları.
# trafilatura bunlardan haber metni yerine "Video Ad Feedback … Latest
# Videos 11 videos …" gibi başka videoların listesini çıkarıyor (CNN
# /video/, Al Jazeera /video/newsfeed/, BBC /videos/, iPlayer, Sounds).
ATLANAN_ADRES = re.compile(r"/(videos?|iplayer|sounds)/")


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
# Önce adresi doğrudan bir besleme gibi okumayı dener (aa.com.tr/en/
# rss/... gibi gerçek feed URL'leri için bu yeterli); adres anasayfa
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


# trafilatura bazı sayfalarda (ör. Anadolu Ajansı) og:image etiketi
# olduğu hâlde görsel döndürmüyor; o zaman sayfanın paylaşım görseli
# (og:image, yoksa twitter:image) doğrudan okunur.
_PAYLASIM_GORSELI = [
    re.compile(rf'<meta[^>]+(?:property|name)=["\']{ad}["\'][^>]*content=["\']([^"\']+)', re.I)
    for ad in ("og:image", "twitter:image")
] + [
    re.compile(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']{ad}["\']', re.I)
    for ad in ("og:image", "twitter:image")
]


def _paylasim_gorseli(html: str, url: str) -> str:
    for kalip in _PAYLASIM_GORSELI:
        eslesme = kalip.search(html)
        if eslesme:
            return urljoin(url, eslesme.group(1).strip().replace("&amp;", "&"))
    return ""


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
        gorsel = (veri.get("image") or "").strip() or _paylasim_gorseli(indirilen, url)
        tarih = (veri.get("date") or "").strip()
        return {"baslik": baslik, "govde": govde, "gorsel": gorsel, "tarih": tarih}
    except Exception as hata:  # noqa: BLE001 - tek bir haberin hatası taramayı durdurmasın
        print(f"makale alınamadı ({url}): {hata}", file=sys.stderr)
        return None
