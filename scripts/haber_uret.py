#!/usr/bin/env python3
"""haber_ham.sh'nin toplu/otomatik sürümü.

Yerel Chromium açma ve canlı yenileme yok; GitHub Actions'ta çalışıp
statik bir HTML üretir. Sayfa lang="en" işaretlenir, tarayıcı Türkçeye
çevirmeyi önerir (haber_ham.sh ile aynı fikir).

Gereksinim: trafilatura (pip install trafilatura)
"""

import html
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

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
        sonuc = subprocess.run(
            ["trafilatura", "--feed", feed_url, "--list"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        satirlar = [s.strip() for s in sonuc.stdout.splitlines() if s.strip()]
        return satirlar[:n]
    except Exception as hata:  # noqa: BLE001 - tek bir kaynağın hatası taramayı durdurmasın
        print(f"besleme alınamadı ({feed_url}): {hata}", file=sys.stderr)
        return []


# trafilatura -u çıktısı: ilk satır başlık, geri kalanı gövde metni
# (yayın tarihi/atıf satırları ve "Related topics" sonrası ayıklanır).
def makale_getir(url: str) -> tuple[str, str] | None:
    try:
        sonuc = subprocess.run(
            ["trafilatura", "-u", url],
            capture_output=True,
            text=True,
            timeout=60,
        )
        raw = sonuc.stdout.strip()
        if not raw:
            return None

        satirlar = raw.splitlines()
        baslik = satirlar[0].strip() if satirlar else url

        govde_satirlari = []
        for satir in satirlar[1:]:
            if satir.startswith("- Published") or satir.startswith("- Attribution"):
                continue
            if satir.startswith("Related topics"):
                break
            govde_satirlari.append(satir)

        govde = " ".join(s for s in govde_satirlari if s.strip())
        if not govde.strip():
            return None
        return (baslik or url, govde)
    except Exception as hata:  # noqa: BLE001
        print(f"makale alınamadı ({url}): {hata}", file=sys.stderr)
        return None


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
  article h3{font-size:1.05rem; line-height:1.38; margin:0 0 .5rem; font-weight:600}
  article h3 a{color:var(--ink); text-decoration:none}
  article h3 a:hover{color:var(--accent)}
  article p{margin:0; color:var(--ink); opacity:.85; font-size:.97rem}
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
  @media (max-width:520px){
    .wrap{padding-top:1.4rem} h1{font-size:1.35rem}
    article{padding:.9rem 1rem}
  }
"""


def sayfa_olustur(bolumler: list[tuple[str, str, list[tuple[str, str, str]]]], toplam: int, k: int) -> str:
    nav = "".join(f'<a href="#{kacir(ad)}">{kacir(ad)}</a>' for ad, _, _ in bolumler)

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
        for baslik_metin, url, ozet in makaleler:
            kartlar.append(
                f"""<article>
  <h3><a href="{kacir(url)}" target="_blank" rel="noopener">{kacir(baslik_metin)}</a></h3>
  <p>{kacir(ozet)}</p>
  <a class="src" href="{kacir(url)}" target="_blank" rel="noopener">{kacir(ad)} &rarr;</a>
</article>"""
            )
        bolum_parcalari.append(baslik_html + "\n" + "\n".join(kartlar) + "\n")

    zaman_metni = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>News digest</title>
<style>{STIL}</style>
</head>
<body>
<div class="wrap">
<h1>News digest</h1>
<p class="meta">{zaman_metni} &middot; first {k} sentences &middot; no AI, no model &middot; {toplam} stories</p>
<nav>{nav}</nav>
{''.join(bolum_parcalari)}
<footer>Generated automatically &middot; {zaman_metni}</footer>
</div>
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
            baslik, govde = sonuc
            ozet = ilk_cumleler(govde, K)
            if not ozet:
                continue
            makaleler.append((baslik, url, ozet))

        toplam += len(makaleler)
        bolumler.append((ad, feed_url, makaleler))
        print(f"{ad}: {len(makaleler)} haber")

    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(sayfa_olustur(bolumler, toplam, K), encoding="utf-8")
    print(f"Bitti: {CIKTI} ({toplam} haber)")


if __name__ == "__main__":
    uret()
