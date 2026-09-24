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

import torch  # noqa: E402
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # noqa: E402

def model_ile(ad, kaynak_dil=None, hedef_dil=None):
    t = time.time()
    tok = AutoTokenizer.from_pretrained(ad, **({"src_lang": kaynak_dil} if kaynak_dil else {}))
    model = AutoModelForSeq2SeqLM.from_pretrained(ad).eval()
    yukleme = time.time() - t
    ek = {"forced_bos_token_id": tok.convert_tokens_to_ids(hedef_dil)} if hedef_dil else {}
    t = time.time()
    for h in secilen:
        parcalar = [h["baslik"]] + cumleler(h["ozet"])
        girdi = tok(parcalar, return_tensors="pt", padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            cikti = model.generate(**girdi, max_new_tokens=400, num_beams=4, **ek)
        metin = tok.batch_decode(cikti, skip_special_tokens=True)
        h[ad + "_baslik"] = metin[0]; h[ad + "_ozet"] = " ".join(metin[1:])
    print(f"{ad}: yükleme {yukleme:.0f} sn, çeviri {time.time()-t:.0f} sn")

try:
    model_ile("Helsinki-NLP/opus-mt-tc-big-en-tr")
except Exception as e:
    print("opus-mt HATA:", repr(e))
try:
    model_ile("facebook/nllb-200-distilled-600M", "eng_Latn", "tur_Latn")
except Exception as e:
    print("nllb HATA:", repr(e))
print("===JSON===" + json.dumps(secilen, ensure_ascii=False) + "===SON===")
