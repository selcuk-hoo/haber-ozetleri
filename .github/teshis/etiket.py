"""GEÇİCİ: Yemek ve Gezi haberlerinin sayfa etiketleri ([TESHIS] satırları)."""
import html, re, subprocess, sys
sys.path.insert(0, "scripts")
from besleme import makale_getir
subprocess.run(["git", "fetch", "-q", "origin", "gh-pages"], check=True)
t = subprocess.run(["git", "show", "origin/gh-pages:index.html"], capture_output=True, text=True, check=True).stdout
n = 0
for m in re.finditer(r"<article[^>]*>.*?</article>", t, re.S):
    a = m.group(0)
    kat = html.unescape((re.search(r'data-kategori="([^"]*)"', a) or [0, "?"])[1])
    if kat not in ("Yemek", "Gezi"):
        continue
    kay = (re.search(r'data-kaynak="([^"]*)"', a) or [0, "?"])[1]
    u = re.search(r'href="([^"]+)"[^>]*class="[^"]*src', a) or re.search(r'href="(https?://[^"]+)"', a)
    if not u or "euronews" in kay:
        continue
    url = html.unescape(u.group(1))
    s = makale_getir(url)
    n += 1
    print(f"[TESHIS] {kat}/{kay} | {(s or {}).get('baslik', 'ALINAMADI')[:70]} | {(s or {}).get('etiketler')}")
print(f"[TESHIS] {n} sayfa")
