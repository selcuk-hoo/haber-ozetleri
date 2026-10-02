"""GEÇİCİ teşhis: Gemini ücretsiz kota yoklaması. Her modele tek, küçük
istek; hata olursa Google'ın kota ayrıntısı (metrik, sınır) yazdırılır.
Anahtar loga yazılmaz."""

import json
import os
import time
import urllib.error
import urllib.request

MODELLER = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-lite-latest", "gemini-flash-latest",
            "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash"]

for model in MODELLER:
    govde = {"contents": [{"role": "user", "parts": [{"text": "Translate to Turkish: Good morning"}]}]}
    istek = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(govde).encode(),
        headers={"x-goog-api-key": os.environ.get("GEMINI_API_KEY", ""), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(istek, timeout=60) as yanit:
            cevap = json.loads(yanit.read())
        print(f"[TESHIS] {model}: TAMAM ({cevap.get('modelVersion')})", flush=True)
    except urllib.error.HTTPError as hata:
        try:
            hata_json = json.loads(hata.read()).get("error", {})
        except Exception:  # noqa: BLE001
            hata_json = {}
        print(f"[TESHIS] {model}: HTTP {hata.code} {hata_json.get('status')}: {hata_json.get('message', '')[:600]}",
              flush=True)
        for ayrinti in hata_json.get("details", []):
            print(f"[TESHIS]    {json.dumps(ayrinti, ensure_ascii=False)[:600]}", flush=True)
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {model}: {type(hata).__name__}", flush=True)
    time.sleep(3)
