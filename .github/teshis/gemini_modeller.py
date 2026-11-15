"""Geçici teşhis: Gemini API'nin model listesi (kota yemez, yalnız ListModels)."""
import json
import os
import urllib.request

anahtar = os.environ.get("GEMINI_API_KEY", "")
if not anahtar:
    print("[TESHIS] anahtar yok")
    raise SystemExit(0)
modeller, jeton = [], ""
while True:
    adres = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200" + (f"&pageToken={jeton}" if jeton else "")
    istek = urllib.request.Request(adres, headers={"x-goog-api-key": anahtar})
    veri = json.loads(urllib.request.urlopen(istek, timeout=30).read())
    modeller += veri.get("models", [])
    jeton = veri.get("nextPageToken", "")
    if not jeton:
        break
print(f"[TESHIS] toplam {len(modeller)} model")
for m in sorted(modeller, key=lambda m: m["name"]):
    if "generateContent" not in m.get("supportedGenerationMethods", []):
        continue
    print(f"[TESHIS] {m['name'].removeprefix('models/')} | {m.get('displayName','')} | v={m.get('version','')} "
          f"| girdi={m.get('inputTokenLimit')} çıktı={m.get('outputTokenLimit')} | düşünme={m.get('thinking')}")
