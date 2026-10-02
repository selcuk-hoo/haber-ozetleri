"""GEÇİCİ teşhis: Gemini olay süzgeci. Gevşek algoritmanın aday grupları
her modele BİR istekte gider; model aynı olayı anlatanları seçer. Anahtar
loga yazılmaz."""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "scripts")
import haber_uret  # noqa: E402
import olaylar  # noqa: E402
from ayarlar import KAYNAKLAR, TURKCE_KAYNAKLAR  # noqa: E402
from ceviri import onbellegi_yukle  # noqa: E402
from model import KaynakBolumu  # noqa: E402
from takip import Takip  # noqa: E402

MODELLER = ["gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-3.1-flash-lite"]


def gemini(model: str, sistem: str, metin: str) -> dict:
    govde = {"systemInstruction": {"parts": [{"text": sistem}]},
             "contents": [{"role": "user", "parts": [{"text": metin}]}],
             "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
    istek = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(govde).encode(),
        headers={"x-goog-api-key": os.environ.get("GEMINI_API_KEY", ""), "Content-Type": "application/json"})
    bas = time.time()
    try:
        with urllib.request.urlopen(istek, timeout=120) as yanit:
            cevap = json.loads(yanit.read())
    except urllib.error.HTTPError as hata:
        try:
            h = json.loads(hata.read()).get("error", {})
        except Exception:  # noqa: BLE001
            h = {}
        print(f"[TESHIS] {model}: HTTP {hata.code} {h.get('message', '')[:200]}", flush=True)
        for ayrinti in h.get("details", []):
            if "QuotaFailure" in ayrinti.get("@type", ""):
                print(f"[TESHIS]    {json.dumps(ayrinti, ensure_ascii=False)[:500]}", flush=True)
        return {}
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {model}: {type(hata).__name__}", flush=True)
        return {}
    u = cevap.get("usageMetadata", {})
    print(f"[TESHIS] {model} ({cevap.get('modelVersion')}): {time.time() - bas:.1f} sn, girdi "
          f"{u.get('promptTokenCount')}, çıktı {u.get('candidatesTokenCount')}, düşünme {u.get('thoughtsTokenCount')}",
          flush=True)
    metin = "".join(p.get("text", "") for p in cevap["candidates"][0]["content"]["parts"] if not p.get("thought"))
    try:
        return json.loads(metin[metin.index("{"):metin.rindex("}") + 1])
    except ValueError:
        print(f"[TESHIS] JSON okunamadı: {metin[:300]!r}", flush=True)
        return {}


onbellek = onbellegi_yukle(Path("dist/ceviri.json"))
bolumler = [KaynakBolumu(ad, adres, haber_uret.kaynak_haberleri(kat, ad, adres, Takip({}, datetime.now(timezone.utc))))
            for kat, ad, adres in KAYNAKLAR if kat == "Gündem"]
kategoriler = {"Gündem": bolumler}
ingilizceler = {}
for b in bolumler:
    for m in b.makaleler:
        k = onbellek.get(m.url, {})
        if m.kaynak in TURKCE_KAYNAKLAR and k.get("eb") and k.get("eo"):
            ingilizceler[m.url] = (k["eb"], k["eo"])
haberler = [m for b in bolumler for m in b.makaleler if m.kaynak not in TURKCE_KAYNAKLAR or m.url in ingilizceler]
kimlik = {m.url: f"h{i}" for i, m in enumerate(haberler)}
url_kimlik = {v: k for k, v in kimlik.items()}
haber = {m.url: m for m in haberler}


def kisa(m):
    b, o = ingilizceler.get(m.url, (m.baslik, m.ozet))
    return f"{kimlik[m.url]} [{m.kaynak}] {b} — {olaylar.ilk_cumleler(o, 1)[:300]}"


def grupla(esik, isim):
    olaylar.ESIK, olaylar.EN_AZ_ORTAK_ISIM = esik, isim
    return [[oncu] + [m.url for m in d] for (_, oncu), d in
            olaylar.olaylari_grupla(kategoriler, ingilizceler, TURKCE_KAYNAKLAR).items()]


siki, gevsek = grupla(0.30, 2), grupla(0.12, 1)
for ad, gs in (("SIKI (bugünkü)", siki), ("GEVŞEK adaylar", gevsek)):
    print(f"[TESHIS] ===== {ad}: {len(gs)} grup")
    for g in gs:
        print("[TESHIS]   ---")
        for u in g:
            print(f"[TESHIS]   {kisa(haber[u])[:160]}")

SUZ = """Sen bir haber sitesinin editörüsün. Bir algoritma benzer görünen haberleri aday
gruplar halinde topladı (kimlik [kaynak] başlık — ilk cümle). Her aday grupta
aynı somut olayı anlatan haberleri belirle; olayı farklı olanları çıkar. Bir
aday birden fazla olaya bölünebilir.
Aynı olay: aynı gelişme, açıklama, saldırı, karar ya da toplantı. Yalnız aynı
genel konu (ör. "Ukrayna savaşı", "Gazze", "ABD seçimleri") YETMEZ; farklı
gelişme ayrı olaydır. Bir olayda her kaynaktan en fazla bir haber. Emin
değilsen birleştirme. Açıklama yazma, yalnız JSON döndür.
Yalnız 2 ve daha fazla haberli olayları döndür: {"olaylar": [["h1", "h7"], ...]}"""
adaylar = "\n\n".join(f"Aday {i}:\n" + "\n".join(kisa(haber[u]) for u in g) for i, g in enumerate(gevsek))

for model in MODELLER:
    cevap = gemini(model, SUZ, adaylar)
    gs = []
    for g in cevap.get("olaylar", []):
        uyeler = [url_kimlik[k] for k in dict.fromkeys(g) if k in url_kimlik]
        if len({haber[u].kaynak for u in uyeler}) > 1:
            gs.append(uyeler)
    print(f"[TESHIS] ===== {model}: {len(gs)} olay")
    for g in gs:
        print("[TESHIS]   ---")
        for u in g:
            print(f"[TESHIS]   {kisa(haber[u])[:160]}")
    time.sleep(15)
