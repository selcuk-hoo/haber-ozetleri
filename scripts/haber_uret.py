#!/usr/bin/env python3
"""haber_ham.sh'nin toplu/otomatik sürümü.

Yerel Chromium açma ve canlı yenileme yok; GitHub Actions'ta çalışıp
statik bir HTML üretir. Sayfa lang="en" işaretlenir, tarayıcı Türkçeye
çevirmeyi önerir (haber_ham.sh ile aynı fikir).

Gereksinim: trafilatura (pip install trafilatura)
"""

import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import trafilatura
from trafilatura.feeds import find_feed_urls

TR_SAATI = ZoneInfo("Europe/Istanbul")

KAYNAKLAR = [
    ("dailysabah.com", "https://www.dailysabah.com/rss/turkiye"),
    ("bbc.co.uk", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("aljazeera.com", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("dw.com", "https://rss.dw.com/rdf/rss-en-world"),
    ("france24.com", "https://www.france24.com/en/rss"),
    ("themoscowtimes.com", "https://www.themoscowtimes.com/rss/news"),
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
        return find_feed_urls(feed_url)[:n]
    except Exception as hata:  # noqa: BLE001 - tek bir kaynağın hatası taramayı durdurmasın
        print(f"besleme alınamadı ({feed_url}): {hata}", file=sys.stderr)
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
                "extensive_search": True,
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
def tarihi_bicimlendir(ham: str) -> str:
    for bicim in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            zaman = datetime.strptime(ham, bicim)
        except ValueError:
            continue
        if zaman.tzinfo is not None:
            yerel = zaman.astimezone(TR_SAATI)
            return yerel.strftime("%b %d, %Y · %H:%M TRT")
        return zaman.strftime("%b %d, %Y")
    return ham


# Sıralama için: ayrıştırılabilen tarihler karşılaştırılabilir olsun diye
# UTC'ye sabitlenir; ayrıştırılamayan/boş tarihler en eskiymiş gibi
# davranıp listenin sonuna düşer.
def _sira_anahtari(tarih: str) -> datetime:
    for bicim in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            zaman = datetime.strptime(tarih, bicim)
        except ValueError:
            continue
        return zaman if zaman.tzinfo else zaman.replace(tzinfo=timezone.utc)
    return datetime.min.replace(tzinfo=timezone.utc)


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
  nav a{
    color:var(--soft); text-decoration:none; font-size:.83rem;
    white-space:nowrap; transition:color .15s;
  }
  nav a:hover{color:var(--accent)}
  @media (min-width:900px){
    .wrap{margin-left:13rem; margin-right:2rem}
    nav{
      position:fixed; top:0; left:0; bottom:0; z-index:5;
      width:11rem; flex-direction:column; align-items:flex-start;
      flex-wrap:nowrap; overflow-y:auto;
      padding:2.4rem 1.2rem; margin-bottom:0; gap:.7rem;
      background:var(--bg); backdrop-filter:none;
      border-bottom:none; border-right:1px solid var(--line);
    }
  }
  h2{
    font-size:.78rem; text-transform:uppercase; letter-spacing:.1em;
    color:var(--soft); font-weight:600;
    margin:2.5rem 0 .9rem; padding-bottom:.4rem;
    border-bottom:1px solid var(--line);
    display:flex; justify-content:space-between; align-items:baseline; gap:1rem;
  }
  h2 .adet{text-transform:none; letter-spacing:0; font-weight:400; opacity:.8}
  article{
    background:var(--card); border:1px solid var(--line);
    border-radius:11px; padding:1.05rem 1.2rem 1.1rem; margin-bottom:.75rem;
    box-shadow:var(--shadow); transition:border-color .15s, transform .15s;
  }
  article:hover{border-color:var(--accent); transform:translateY(-1px)}
  article h3{
    margin:0 0 1.1rem; font-size:1rem; line-height:1.35; font-weight:700;
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
  @media (max-width:520px){
    .wrap{padding-top:1.4rem} h1{font-size:1.35rem}
    article{padding:.9rem 1rem}
  }
"""


def sayfa_olustur(bolumler: list[tuple[str, str, list[tuple[str, str, str, str, str]]]], toplam: int, k: int) -> str:
    nav = '<a href="#top">Home</a>' + "".join(
        f'<a href="#{kacir(ad)}">{kacir(ad)}</a>' for ad, _, _ in bolumler
    )

    bolum_parcalari = []
    for ad, feed_url, makaleler in bolumler:
        baslik_html = f'<h2 id="{kacir(ad)}">{kacir(ad)}<span class="adet">{len(makaleler)} stories</span></h2>'

        if not makaleler:
            bolum_parcalari.append(
                baslik_html
                + f'\n<p class="bos">No stories could be retrieved from this source. '
                f'<code>{kacir(feed_url)}</code> may not be a valid RSS feed, or the source is temporarily unreachable.</p>\n'
            )
            continue

        kartlar = []
        for baslik_metin, url, ozet, gorsel, tarih in makaleler:
            gorsel_html = (
                f'<img src="{kacir(gorsel)}" alt="" loading="lazy" referrerpolicy="no-referrer">'
                if gorsel
                else ""
            )
            tarih_html = (
                f'<p class="tarih">{kacir(tarihi_bicimlendir(tarih))}</p>' if tarih else ""
            )
            kartlar.append(
                f"""<article>
  <h3><a href="{kacir(url)}" target="_blank" rel="noopener">{kacir(baslik_metin)}</a></h3>
  {gorsel_html}
  {tarih_html}
  <details>
    <summary>Read more</summary>
    <p>{kacir(ozet)}</p>
  </details>
  <a class="src" href="{kacir(url)}" target="_blank" rel="noopener">{kacir(ad)} &rarr;</a>
</article>"""
            )
        bolum_parcalari.append(baslik_html + "\n" + "\n".join(kartlar) + "\n")

    zaman_metni = datetime.now(timezone.utc).astimezone(TR_SAATI).strftime("%Y-%m-%d %H:%M TRT")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%93%B0%3C/text%3E%3C/svg%3E">
<title>World Brief</title>
<style>{STIL}</style>
</head>
<body>
<div class="wrap" id="top">
<h1>&#128240; World Brief</h1>
<p class="meta">{zaman_metni} &middot; {toplam} stories &middot; <a id="cevir-linki" class="cevir" href="https://translate.google.com/translate?sl=en&amp;tl=tr" target="_blank" rel="noopener">&#127481;&#127479; Read in Turkish</a></p>
<nav>{nav}</nav>
{''.join(bolum_parcalari)}
<footer>Generated automatically &middot; {zaman_metni}</footer>
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
</script>
</body>
</html>
"""


def uret() -> None:
    bolumler = []
    toplam = 0

    for ad, feed_url in KAYNAKLAR:
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
        toplam += len(makaleler)
        bolumler.append((ad, feed_url, makaleler))
        print(f"{ad}: {len(makaleler)} haber")

    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(sayfa_olustur(bolumler, toplam, K), encoding="utf-8")
    print(f"Bitti: {CIKTI} ({toplam} haber)")


if __name__ == "__main__":
    uret()
