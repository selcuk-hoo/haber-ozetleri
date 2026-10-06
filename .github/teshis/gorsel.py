"""GEÇİCİ: paylaşım görselinin weserv üzerinden gelme süresi ([TESHIS] satırları)."""
import html, re, subprocess, time, urllib.parse, urllib.request
subprocess.run(["git", "fetch", "-q", "origin", "gh-pages"], check=True)
t = subprocess.run(["git", "show", "origin/gh-pages:index.html"], capture_output=True, text=True, check=True).stdout
satirlar = []
for m in re.finditer(r"<article[^>]*>.*?</article>", t, re.S):
    a = m.group(0)
    kat = html.unescape((re.search(r'data-kategori="([^"]*)"', a) or [None, "?"])[1])
    kay = (re.search(r'data-kaynak="([^"]*)"', a) or [None, "?"])[1]
    img = re.search(r'<img[^>]*src="([^"]+)"', a)
    if img and (kat == "Sanat & Kültür" or kay in ("bbc.co.uk", "aljazeera.com")):
        satirlar.append((kat, kay, html.unescape(img.group(1))))
gorulen = set()
for kat, kay, url in satirlar:
    if (kat, kay) in gorulen and kat != "Sanat & Kültür":
        continue
    gorulen.add((kat, kay))
    adres = "https://images.weserv.nl/?w=720&we&url=" + urllib.parse.quote(re.sub(r"^https?://", "", url), safe="")
    bas = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(adres, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as y:
            veri = y.read()
            sonuc = f"{y.status} {y.headers.get('Content-Type')} {len(veri)//1024} KB"
    except Exception as h:  # noqa: BLE001
        sonuc = f"HATA {h!r}"[:160]
    print(f"[TESHIS] {time.time()-bas:5.1f} sn | {kat} / {kay} | {sonuc} | {url[:110]}")
