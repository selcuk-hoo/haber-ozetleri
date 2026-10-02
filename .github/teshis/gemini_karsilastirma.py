"""GEÇİCİ teşhis: aynı 48 metin (gemini_ornekler.json) Gemini Flash
sürümleriyle; 503'te bekleyip yeniden dener. Anahtar loga yazılmaz."""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, "scripts")
import claude_ceviri  # noqa: E402

ANAHTAR = os.environ.get("GEMINI_API_KEY", "")
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

ornekler = json.loads(Path(".github/teshis/gemini_ornekler.json").read_text(encoding="utf-8"))
metinler = {o["kimlik"]: o["en"] for o in ornekler}
MODELLER = ["gemini-flash-latest", "gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-lite-latest"]


def cevir(model: str, parca: dict[str, str]):
    govde = {
        "systemInstruction": {"parts": [{"text": SISTEM}]},
        "contents": [{"role": "user", "parts": [{"text": ISTEK + "\n\n" + json.dumps(parca, ensure_ascii=False)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    istek = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(govde).encode(), headers={"x-goog-api-key": ANAHTAR, "Content-Type": "application/json"})
    bas = time.time()
    with urllib.request.urlopen(istek, timeout=180) as yanit:
        cevap = json.loads(yanit.read())
    metin = "".join(p.get("text", "") for p in cevap["candidates"][0]["content"]["parts"] if not p.get("thought"))
    return claude_ceviri.cevabi_ayikla(metin), cevap.get("usageMetadata", {}), cevap.get("modelVersion"), time.time() - bas


sonuclar: dict[str, dict[str, str]] = {}
kimlikler = list(metinler)
for model in MODELLER:
    sonuclar[model] = {}
    for i in range(0, len(kimlikler), 12):
        parca = {k: metinler[k] for k in kimlikler[i:i + 12]}
        for bekleme in (20, 60, None):
            try:
                cev, kul, surum, sure = cevir(model, parca)
                sonuclar[model].update(cev)
                print(f"[TESHIS] {model} ({surum}) parça {i // 12}: {len(cev)}/{len(parca)}, {sure:.1f} sn, "
                      f"girdi {kul.get('promptTokenCount')} çıktı {kul.get('candidatesTokenCount')} "
                      f"düşünme {kul.get('thoughtsTokenCount')}")
                break
            except urllib.error.HTTPError as hata:
                print(f"[TESHIS] {model} parça {i // 12}: HTTP {hata.code}: {hata.read()[:200]!r}")
                if hata.code not in (429, 500, 503) or bekleme is None:
                    break
                time.sleep(bekleme)
            except Exception as hata:  # noqa: BLE001
                print(f"[TESHIS] {model} parça {i // 12}: {type(hata).__name__}: {str(hata)[:200]}")
                break
        time.sleep(5)
    print(f"[TESHIS] {model}: {len(sonuclar[model])}/{len(metinler)} metin")

for o in ornekler:
    print(f"[TESHIS] ===== {o['kimlik']}")
    for model, cev in sonuclar.items():
        print(f"[TESHIS] {model}: {cev.get(o['kimlik'], '(yok)')}")
