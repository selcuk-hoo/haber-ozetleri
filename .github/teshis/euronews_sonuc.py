# Geçici: üretilen sayfada Euronews Türkçe kartları ve birleştiği gruplar.
import html, re
h = open("dist/index.html", encoding="utf-8").read()
kartlar = re.findall(r'<article [^>]*>.*?</article>', h, re.S)
tr = [k for k in kartlar if 'data-dil="tr"' in k]
print(f"[TESHIS] Euronews kartı: {len(tr)}")
for k in tr:
    b = html.unescape(re.search(r"<h3><a[^>]*>(.*?)</a>", k, re.S).group(1))
    o = html.unescape(re.search(r"<details>.*?<p>(.*?)</p>", k, re.S).group(1))
    print(f"[TESHIS]  {'(grupta) ' if 'data-grupta' in k else ''}{b}\n[TESHIS]     {o[:220]}")
for k in kartlar:
    if 'class="ilgili"' in k and ("tr.euronews.com" in k):
        b = html.unescape(re.search(r"<h3><a[^>]*>(.*?)</a>", k, re.S).group(1))
        ilgili = re.search(r'<details class="ilgili".*?</details>', k, re.S).group(0)
        print(f"[TESHIS] GRUP: {b}\n[TESHIS]     {html.unescape(re.sub(r'<[^>]+>', ' | ', ilgili))[:400]}")
