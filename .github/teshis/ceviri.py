"""GEÇİCİ teşhis: aynı 10 haber özetinin Google (gtx), opus-mt ve NLLB çevirileri."""
import html, json, re, subprocess, time, urllib.parse, urllib.request

s = subprocess.run(["git", "show", "FETCH_HEAD:index.html"], capture_output=True, text=True).stdout
kartlar = re.findall(r'<article data-kategori="([^"]*)" data-kaynak="([^"]*)"[^>]*>(.*?)</article>', s, re.S)
istek = {"Gündem": 3, "Teknoloji": 2, "Bilim": 2, "Sanat &amp; Kültür": 1, "Gezi": 1, "Yemek": 1}
secilen, kaynaklar = [], set()
for kat, ad, govde in kartlar:
    if istek.get(kat, 0) > 0 and ad not in kaynaklar:
        baslik = html.unescape(re.search(r"<h3><a[^>]*>(.*?)</a>", govde, re.S).group(1))
        ozet = html.unescape(re.search(r"<details>.*?<p>(.*?)</p>", govde, re.S).group(1))
        secilen.append({"kategori": html.unescape(kat), "kaynak": ad, "baslik": baslik, "ozet": ozet})
        istek[kat] -= 1; kaynaklar.add(ad)
print(len(secilen), "haber seçildi")

def cumleler(metin):
    return [c for c in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"“(])', metin) if c.strip()]

# 1) Google (gtx): tarayıcı çevirisinin kullandığı ücretsiz uç nokta
def google(metin):
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(
        {"client": "gtx", "sl": "en", "tl": "tr", "dt": "t", "q": metin})
    veri = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read())
    return "".join(p[0] for p in veri[0] if p[0])

t = time.time()
for h in secilen:
    try:
        h["google_baslik"] = google(h["baslik"]); h["google_ozet"] = google(h["ozet"])
    except Exception as e:
        h["google_baslik"] = h["google_ozet"] = f"HATA: {e}"
print(f"google: {time.time()-t:.1f} sn")

from transformers import pipeline  # noqa: E402

def model_ile(ad, **kw):
    t = time.time()
    cevir = pipeline("translation", model=ad, device=-1, **kw)
    yukleme = time.time() - t
    t = time.time()
    for h in secilen:
        parcalar = [h["baslik"]] + cumleler(h["ozet"])
        cikti = [c["translation_text"] for c in cevir(parcalar, batch_size=8, max_length=400)]
        h[ad + "_baslik"] = cikti[0]; h[ad + "_ozet"] = " ".join(cikti[1:])
    print(f"{ad}: yükleme {yukleme:.0f} sn, çeviri {time.time()-t:.0f} sn")

model_ile("Helsinki-NLP/opus-mt-tc-big-en-tr")
model_ile("facebook/nllb-200-distilled-600M", src_lang="eng_Latn", tgt_lang="tur_Latn")
print("===JSON===" + json.dumps(secilen, ensure_ascii=False) + "===SON===")
