"""GEÇİCİ teşhis: Google Çeviri / Gemini Flash / Gemini Flash-Lite / Sonnet
karşılaştırması (Gündem, Teknoloji, Bilim). Anahtar loga yazılmaz."""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "scripts")
import claude_ceviri  # noqa: E402
import haber_uret  # noqa: E402
from ceviri import Cevirmen, onbellegi_yukle  # noqa: E402
from takip import Takip  # noqa: E402

ANAHTAR = os.environ.get("GEMINI_API_KEY", "")
print(f"[TESHIS] anahtar var mı: {bool(ANAHTAR)}")

ROL = "haber yazılarını (dünya gündemi, teknoloji ve bilim)"
ALAN = """- Kişi, şirket, ürün, marka ve yayın adlarını çevirme. Ülke, şehir ve kurum
  adlarının Türkçede yerleşik biçimini kullan (the Kremlin → Kremlin, the
  State Department → ABD Dışişleri Bakanlığı, Kyiv → Kiev).
- Unvanları Türk basınındaki gibi yaz (Prime Minister → Başbakan, Secretary
  of State → Dışişleri Bakanı).
- Bilim ve teknoloji terimlerinin Türkçede yerleşik karşılığını kullan;
  yerleşik karşılığı olmayan teknik terimleri özgün haliyle bırak.
- Haber dilini koru: tarafsız, açık, kısa cümleler."""
SISTEM = claude_ceviri.SISTEM_KALIBI.format(rol=ROL, alan=ALAN)
ISTEK = "Aşağıdaki JSON nesnesindeki metinleri kurallara göre Türkçeye çevir."

# --- Örnekler: önbellekte Google çevirisi olan gerçek haberler ---
onbellek = onbellegi_yukle(Path("dist/ceviri.json"))
KAYNAKLAR = [
    ("Gündem", "bbc.co.uk"), ("Gündem", "aljazeera.com"), ("Gündem", "themoscowtimes.com"),
    ("Gündem", "france24.com"), ("Gündem", "africanews.com"), ("Gündem", "cnn.com"),
    ("Teknoloji", "theverge.com"), ("Teknoloji", "arstechnica.com"), ("Teknoloji", "restofworld.org"),
    ("Bilim", "sciencedaily.com"), ("Bilim", "phys.org"), ("Bilim", "quantamagazine.org"),
]
adresler = {(k, a): u for k, a, u in haber_uret.KAYNAKLAR}
ornekler = []  # (kimlik, kategori, kaynak, İngilizce, Google)
for kat, ad in KAYNAKLAR:
    if (kat, ad) not in adresler:
        print(f"[TESHIS] kaynak yok: {kat} / {ad}")
        continue
    makaleler = haber_uret.kaynak_haberleri(kat, ad, adresler[(kat, ad)], Takip({}, datetime.now(timezone.utc)))
    alinan = 0
    for m in makaleler:
        k = onbellek.get(m.url, {})
        if (k.get("bh") == Cevirmen._tr_ozeti(m.baslik) and k.get("oh") == Cevirmen._tr_ozeti(m.ozet)
                and k.get("bk") != "c" and k.get("ok") != "c"):
            n = len(ornekler) // 2
            ornekler.append((f"b{n}", kat, ad, m.baslik, k["b"]))
            ornekler.append((f"o{n}", kat, ad, m.ozet, k["o"]))
            alinan += 1
            if alinan == 2:
                break
    print(f"[TESHIS] {kat} / {ad}: {len(makaleler)} haber, {alinan} örnek")
metinler = {kimlik: en for kimlik, _, _, en, _ in ornekler}
print(f"[TESHIS] toplam {len(metinler)} metin")


# --- Gemini ---
def gemini_istek(yol: str, govde: dict | None = None) -> dict:
    istek = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/" + yol,
        data=json.dumps(govde).encode() if govde is not None else None,
        headers={"x-goog-api-key": ANAHTAR, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(istek, timeout=180) as yanit:
        return json.loads(yanit.read())


modeller = []
try:
    sayfa = gemini_istek("models?pageSize=200")
    adlar = [m["name"].removeprefix("models/") for m in sayfa.get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    print(f"[TESHIS] modeller: {[a for a in adlar if 'gemini' in a]}")
    for takma in ("gemini-flash-latest", "gemini-flash-lite-latest"):
        if takma in adlar:
            modeller.append(takma)
    if not modeller:
        def surum(a):
            return [int(x) for x in re.findall(r"\d+", a.split("-")[1])] if re.match(r"gemini-\d", a) else [0]
        for tur in (r"^gemini-[\d.]+-flash$", r"^gemini-[\d.]+-flash-lite$"):
            uyan = sorted((a for a in adlar if re.match(tur, a)), key=surum)
            if uyan:
                modeller.append(uyan[-1])
except urllib.error.HTTPError as hata:
    print(f"[TESHIS] model listesi HTTP {hata.code}: {hata.read()[:400]!r}")
except Exception as hata:  # noqa: BLE001
    print(f"[TESHIS] model listesi alınamadı: {type(hata).__name__}")
print(f"[TESHIS] denenecek modeller: {modeller}")


def gemini_cevir(model: str, parca: dict[str, str]) -> tuple[dict[str, str], dict, float]:
    bas = time.time()
    cevap = gemini_istek(f"models/{model}:generateContent", {
        "systemInstruction": {"parts": [{"text": SISTEM}]},
        "contents": [{"role": "user", "parts": [{"text": ISTEK + "\n\n" + json.dumps(parca, ensure_ascii=False)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    })
    sure = time.time() - bas
    metin = "".join(p.get("text", "") for p in cevap["candidates"][0]["content"]["parts"] if not p.get("thought"))
    return claude_ceviri.cevabi_ayikla(metin), cevap.get("usageMetadata", {}), sure


sonuclar: dict[str, dict[str, str]] = {}
kimlikler = list(metinler)
for model in modeller:
    sonuclar[model] = {}
    for i in range(0, len(kimlikler), 12):
        parca = {k: metinler[k] for k in kimlikler[i:i + 12]}
        try:
            cevap, kullanim, sure = gemini_cevir(model, parca)
            sonuclar[model].update(cevap)
            print(f"[TESHIS] {model} parça {i // 12}: {len(cevap)}/{len(parca)} metin, {sure:.1f} sn, kullanım {kullanim}")
        except urllib.error.HTTPError as hata:
            print(f"[TESHIS] {model} parça {i // 12}: HTTP {hata.code}: {hata.read()[:400]!r}")
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] {model} parça {i // 12}: {type(hata).__name__}: {str(hata)[:300]}")
        time.sleep(8)

# --- Sonnet (referans) ---
sonuclar["sonnet"] = {}
if claude_ceviri.kullanilabilir_mi():
    for i in range(0, len(kimlikler), 12):
        parca = {k: metinler[k] for k in kimlikler[i:i + 12]}
        try:
            sonuclar["sonnet"].update(claude_ceviri._cagir(parca, SISTEM))
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] sonnet parça {i // 12}: {type(hata).__name__}: {str(hata)[:300]}")
    print(f"[TESHIS] sonnet: {len(sonuclar['sonnet'])} metin; {claude_ceviri.kullanim_ozeti()}")

# --- Yan yana ---
etiket = {m: ("F" if "lite" not in m else "L") for m in modeller}
etiket["sonnet"] = "S"
for kimlik, kat, ad, en, google in ornekler:
    print(f"[TESHIS] ===== {kimlik} {kat} / {ad}")
    print(f"[TESHIS] EN: {en}")
    print(f"[TESHIS] G : {google}")
    for model, cev in sonuclar.items():
        print(f"[TESHIS] {etiket[model]} : {cev.get(kimlik, '(yok)')}")
