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
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from courlan import get_hostinfo
import trafilatura
from trafilatura.feeds import find_feed_urls
from trafilatura.sitemaps import find_robots_sitemaps, sitemap_search

TR_SAATI = ZoneInfo("Europe/Istanbul")

# Her kayıt: (kategori, kaynak adı, besleme/anasayfa adresi). Sayfa
# kategoriye göre sekmelere ayrılır; her sekmenin kendi "All + kaynak"
# filtresi vardır (bkz. sayfa_olustur).
KAYNAKLAR = [
    ("Gündem", "dailysabah.com", "https://www.dailysabah.com/rss/turkiye"),
    ("Gündem", "cnn.com", "https://www.cnn.com/"),
    ("Gündem", "bbc.co.uk", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Gündem", "aljazeera.com", "https://www.aljazeera.com/"),
    ("Gündem", "dw.com", "https://rss.dw.com/rdf/rss-en-world"),
    ("Gündem", "france24.com", "https://www.france24.com/en/rss"),
    ("Gündem", "themoscowtimes.com", "https://www.themoscowtimes.com/rss/news"),
    ("Bilim & Teknoloji", "bbc.co.uk", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("Sanat & Kültür", "bbc.co.uk", "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"),
    # Gezi: mevcut 7 kaynağın gezi/travel alt sayfalarıyla 5 farklı deneme
    # (BBC Travel, CNN, Daily Sabah, DW, France24) hepsi 0 sonuç verdi —
    # bu genel haber/siyaset kaynakları gezi konusunda güvenilir besleme
    # sunmuyor. Onun yerine gezi konusunda uzmanlaşmış bir kaynak eklendi;
    # anasayfa düzeyinde olduğu için besleme bulunamazsa site haritası
    # yedeği de devreye girebiliyor (CNN'de işe yarayan mekanizmanın aynısı).
    ("Gezi", "cntraveler.com", "https://www.cntraveler.com/"),
]

N = 10  # kaynak başına haber sayısı
K = 5  # özet cümle sayısı
CIKTI = Path(__file__).resolve().parent.parent / "dist" / "index.html"


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
    font:16px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    padding:0 16px; -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:46rem; margin:0 auto; padding:2.4rem 0 5rem}
  h1{font-size:1.65rem; margin:0 0 .35rem; letter-spacing:-.015em}
  .meta{color:var(--soft); font-size:.88rem; margin:0 0 1.6rem}
  nav{
    position:sticky; top:0; z-index:5;
    background:color-mix(in srgb, var(--bg) 88%, transparent);
    backdrop-filter:saturate(1.4) blur(8px);
    padding:.75rem 0; border-bottom:1px solid var(--line);
    margin-bottom:1.6rem; display:flex; flex-wrap:wrap; gap:.35rem .85rem;
  }
  .filtre-buton{
    all:unset; cursor:pointer; color:var(--soft); font-size:.83rem;
    white-space:nowrap; transition:color .15s;
    display:inline-flex; align-items:baseline; gap:.3rem;
  }
  .filtre-buton:hover{color:var(--accent)}
  .filtre-buton.aktif{color:var(--accent); font-weight:700}
  .filtre-buton .adet{font-size:.8em; opacity:.75}
  .izgara{display:grid; grid-template-columns:1fr; gap:.75rem; align-items:start}
  :root[data-duzen="liste"] .izgara{grid-template-columns:1fr !important}
  @media (min-width:640px){
    .wrap{max-width:52rem}
    .izgara{grid-template-columns:repeat(2, 1fr)}
  }
  @media (min-width:900px){
    .wrap{margin-left:13rem; margin-right:2rem; max-width:70rem}
    nav{
      position:fixed; top:0; left:0; bottom:0; z-index:5;
      width:11rem; flex-direction:column; align-items:flex-start;
      flex-wrap:nowrap; overflow-y:auto;
      padding:2.4rem 1.2rem; margin-bottom:0; gap:.7rem;
      background:var(--bg); backdrop-filter:none;
      border-bottom:none; border-right:1px solid var(--line);
    }
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
  article summary{
    cursor:pointer; display:inline-flex; align-items:center; gap:.3rem;
    color:var(--accent); font-weight:700; font-size:.82rem;
    text-transform:uppercase; letter-spacing:.04em; list-style:none;
  }
  article summary::-webkit-details-marker{display:none}
  article summary::after{content:"\\2304"; font-size:1rem; transition:transform .15s}
  article details[open] summary::after{transform:rotate(180deg)}
  article details p{margin:.7rem 0 0; color:var(--ink); opacity:.85; font-size:.97rem}
  .dinle{
    display:inline-flex; align-items:center; gap:.35rem; margin:.75rem .5rem 0 0;
    padding:.35rem .7rem; border:1px solid var(--line); border-radius:6px;
    background:none; color:var(--accent); font-size:.78rem; font-weight:600;
    letter-spacing:.02em; cursor:pointer; font-family:inherit;
  }
  .dinle:hover{border-color:var(--accent)}
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


def sayfa_olustur(kategoriler: dict[str, list[tuple[str, str, list[tuple[str, str, str, str, str]]]]]) -> str:
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
        tum_makaleler: list[tuple[str, str, str, str, str, str]] = []
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
            for baslik_metin, url, ozet, gorsel, tarih in makaleler:
                tum_makaleler.append((ad, baslik_metin, url, ozet, gorsel, tarih))
        tum_makaleler.sort(key=lambda m: _sira_anahtari(m[5]), reverse=True)

        for ad, baslik_metin, url, ozet, gorsel, tarih in tum_makaleler:
            gorsel_html = (
                f'<img src="{kacir(gorsel)}" alt="" loading="lazy" referrerpolicy="no-referrer">'
                if gorsel
                else ""
            )
            tarih_html = f'<p class="tarih">{kacir(tarihi_bicimlendir(tarih))}</p>' if tarih else ""
            kartlar.append(
                f"""<article data-kategori="{kacir(kat)}" data-kaynak="{kacir(ad)}">
  <h3><a href="{kacir(url)}" target="_blank" rel="noopener">{kacir(baslik_metin)}</a></h3>
  {tarih_html}
  {gorsel_html}
  <details>
    <summary>Read more</summary>
    <p>{kacir(ozet)}</p>
  </details>
  <button type="button" class="dinle">&#128266; Listen</button>
  <a class="src" href="{kacir(url)}" target="_blank" rel="noopener">{kacir(ad)} &rarr;</a>
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
    # Deploy'un gerçekten güncellendiğini görmek için: her commit'te değişen
    # kısa git SHA. GitHub Actions bunu otomatik sağlıyor (GITHUB_SHA).
    build = os.environ.get("GITHUB_SHA", "local")[:7]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%93%B0%3C/text%3E%3C/svg%3E">
<title>World Brief</title>
<style>{STIL}</style>
<style>{ekstra_stil}</style>
</head>
<body>
<div class="wrap" id="top">
<h1>&#128240; World Brief</h1>
<p class="meta">{zaman_metni} &middot; {toplam} stories &middot; <a id="cevir-linki" class="cevir" href="https://translate.google.com/translate?sl=en&amp;tl=tr" target="_blank" rel="noopener">&#127481;&#127479; Read in Turkish</a> <button type="button" id="tema-buton" class="tema-buton">&#127769; Dark mode</button> <button type="button" id="duzen-buton" class="tema-buton">&#9776; List view</button></p>
<div class="kategori-nav">{kategori_nav}</div>
<nav id="kaynak-nav"></nav>
{icerik}
<footer>Generated automatically &middot; {zaman_metni} &middot; build {build}</footer>
</div>
<script>
(function(){{
  var a = document.getElementById('cevir-linki');
  if (!a) return;
  // Chrome'un kendi "Sayfayı çevir" özelliğinin kullandığı translate.goog
  // ayna adresi — eski translate.google.com/translate?...&u= proxy'sinden
  // farklı olarak hâlâ güvenilir çalışıyor.
  var host = location.hostname.replace(/-/g, '--').replace(/\./g, '-') + '.translate.goog';
  var ayrac = location.search ? '&' : '?';
  a.href = location.protocol + '//' + host + location.pathname + location.search +
    ayrac + '_x_tr_sl=en&_x_tr_tl=tr&_x_tr_hl=tr&_x_tr_pto=wapp';
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

// Kategori + kaynak filtresi: üstteki kategori sekmesi hangi konunun
// kartları görünsün onu belirler; sekmenin altındaki nav ("All" + kaynak
// düğmeleri) her kategori değişiminde bu kategorinin kaynaklarına göre JS
// tarafından yeniden kurulur (sunucu tarafında hepsini önceden basmak
// yerine). "All" o kategorinin tüm haberlerini zamana göre karışık
// gösterir, bir kaynağa tıklamak sayfa yeniden yüklenmeden sadece onu
// gösterir.
var KATEGORI_VERISI = {json.dumps(kategori_kaynak_verisi, ensure_ascii=False)};
(function(){{
  var izgara = document.getElementById('izgara');
  var kaynakNav = document.getElementById('kaynak-nav');
  var kategoriButonlari = document.querySelectorAll('.kategori-buton');
  if (!izgara || !kaynakNav || !kategoriButonlari.length) return;

  var aktifKategori = kategoriButonlari[0].dataset.kategori;
  var aktifKaynak = 'all';

  function uygula() {{
    izgara.querySelectorAll('article[data-kategori]').forEach(function(el){{
      var kategoriUyum = el.dataset.kategori === aktifKategori;
      var kaynakUyum = aktifKaynak === 'all' || el.dataset.kaynak === aktifKaynak;
      el.style.display = (kategoriUyum && kaynakUyum) ? '' : 'none';
    }});
    document.querySelectorAll('.bos[data-kategori]').forEach(function(el){{
      var kategoriUyum = el.dataset.kategori === aktifKategori;
      el.hidden = !(kategoriUyum && aktifKaynak !== 'all' && el.dataset.kaynak === aktifKaynak);
    }});
  }}

  function kaynakNavKur() {{
    var kaynaklar = KATEGORI_VERISI[aktifKategori] || [];
    var kategoriToplami = kaynaklar.reduce(function(acc, k){{ return acc + k[1]; }}, 0);
    var html = '<a href="#top" class="filtre-buton">&#8593; Top</a>';
    html += '<button type="button" class="filtre-buton aktif" data-filtre="all">All<span class="adet">' +
      kategoriToplami + '</span></button>';
    kaynaklar.forEach(function(k){{
      html += '<button type="button" class="filtre-buton" data-filtre="' + k[0] + '">' + k[0] +
        '<span class="adet">' + k[1] + '</span></button>';
    }});
    kaynakNav.innerHTML = html;
    kaynakNav.querySelectorAll('.filtre-buton[data-filtre]').forEach(function(buton){{
      buton.addEventListener('click', function(){{
        aktifKaynak = buton.dataset.filtre;
        kaynakNav.querySelectorAll('.filtre-buton[data-filtre]').forEach(function(b){{
          b.classList.toggle('aktif', b === buton);
        }});
        uygula();
      }});
    }});
  }}

  kategoriButonlari.forEach(function(buton){{
    buton.addEventListener('click', function(){{
      aktifKategori = buton.dataset.kategori;
      aktifKaynak = 'all';
      kategoriButonlari.forEach(function(b){{ b.classList.toggle('aktif', b === buton); }});
      kaynakNavKur();
      uygula();
    }});
  }});

  kaynakNavKur();
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
</script>
</body>
</html>
"""


def uret() -> None:
    kategoriler: dict[str, list[tuple[str, str, list[tuple[str, str, str, str, str]]]]] = {}

    for kategori, ad, feed_url in KAYNAKLAR:
        urls = besleme_listesi(feed_url, N)
        makaleler = []

        for url in urls:
            sonuc = makale_getir(url)
            if sonuc is None:
                continue
            ozet = ilk_cumleler(sonuc["govde"], K)
            if not ozet:
                continue
            makaleler.append((sonuc["baslik"], url, ozet, sonuc["gorsel"], sonuc["tarih"]))

        makaleler.sort(key=lambda m: _sira_anahtari(m[4]), reverse=True)
        kategoriler.setdefault(kategori, []).append((ad, feed_url, makaleler))
        print(f"{kategori} / {ad}: {len(makaleler)} haber")

    toplam = sum(len(makaleler) for bolumler in kategoriler.values() for _, _, makaleler in bolumler)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(sayfa_olustur(kategoriler), encoding="utf-8")
    print(f"Bitti: {CIKTI} ({toplam} haber)")


if __name__ == "__main__":
    uret()
