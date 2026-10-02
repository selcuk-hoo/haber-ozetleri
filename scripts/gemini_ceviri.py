"""Gemini ile çeviri (Gündem, Teknoloji, Bilim: sitenin haberlerinin çoğu).

Google Çeviri haber metinlerinde anlam hataları yapıyordu: "Democrats are
challenging in states they usually lose" → "Demokratlar … zorlanıyor"
(tersi), "Lee said on X" → "X hakkındaki", şarkı adı "September" →
"Eylül". 48 gerçek metinde (02.10.2026) puanlar: Google ~6,5, Gemini 2.5
Flash ~7,5, Sonnet ~8,5. Sonnet bu hacimde (günde ~500 haber) aboneliğin
haftalık limitinin yarısını tüketirdi; Gemini'nin ücretsiz katmanı yetiyor.

Google AI Studio'dan alınan anahtar GEMINI_API_KEY gizli değişkenindedir;
istekte başlıkla gider (adrese yazılmaz, hata mesajlarında görünmez).
Anahtar loga yazdırılmaz. Ücretsiz katmanda Google gönderilen metinleri
ürünlerini geliştirmek için kullanabilir; metinler zaten yayımlanmış haber
özetleri.

Talimat Claude'unkiyle aynı (claude_ceviri.sistem: ortak kurallar +
kategoriye özgü rol). JSON girdi → JSON çıktı, PARCA_BOYU'luk parçalar.

Zincir: MODELLER sırayla denenir. En yeni Flash ücretsiz katmanda sık sık
"yoğun" (503) ve "kota aşıldı" (429) veriyordu; 2.5 Flash 48/48 metni
hatasız çevirdi, Flash-Lite yedek. Hepsi başarısız olursa kalanlar Google
Çeviri'ye, o da durursa Claude yedeğine gider (bkz. haber_uret.cevir).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

import claude_ceviri

MODELLER = ("gemini-2.5-flash", "gemini-flash-lite-latest")
PARCA_BOYU = 24  # bir istekteki metin sayısı (12 haberin başlık + özeti)
ZAMAN_ASIMI = 90  # sn, bir istek için
# Bir çalıştırmada en fazla bu kadar metin (ücretsiz katmanın günlük istek
# hakkını korumak için; kalanlar Google'a).
CALISTIRMA_BASINA_METIN = 240
# Geçici yoğunlukta (503/500) aynı modelle bir kez daha denemeden önce.
YOGUNLUK_BEKLEMESI = 10
ADRES = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ISTEK = "Aşağıdaki JSON nesnesindeki metinleri kurallara göre Türkçeye çevir."

# Bu çalıştırmadaki kullanım (loga yazılır) ve sağlık takibi (saglik.py).
kullanim = {"cagri": 0, "girdi": 0, "cikti": 0}
durum: dict = {"denendi": False, "hata": None}


class GeminiHatasi(RuntimeError):
    def __init__(self, kod: int, mesaj: str):
        super().__init__(f"HTTP {kod}: {mesaj}")
        self.kod = kod


def kullanilabilir_mi() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def kullanim_ozeti() -> str:
    k = kullanim
    return f"{k['cagri']} istek, {k['girdi']} girdi + {k['cikti']} çıktı token"


def _cagir(model: str, girdi: dict[str, str], sistem_metni: str) -> dict[str, str]:
    ayar: dict = {"responseMimeType": "application/json", "temperature": 0.2}
    if "2.5" in model:
        # Çeviri için "düşünme" gereksiz; süre ve kota harcar.
        ayar["thinkingConfig"] = {"thinkingBudget": 0}
    govde = {
        "systemInstruction": {"parts": [{"text": sistem_metni}]},
        "contents": [{"role": "user", "parts": [{"text": ISTEK + "\n\n" + json.dumps(girdi, ensure_ascii=False)}]}],
        "generationConfig": ayar,
    }
    istek = urllib.request.Request(
        ADRES.format(model=model), data=json.dumps(govde).encode("utf-8"),
        headers={"x-goog-api-key": os.environ.get("GEMINI_API_KEY", ""), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as yanit:
            cevap = json.loads(yanit.read())
    except urllib.error.HTTPError as hata:
        try:
            mesaj = json.loads(hata.read()).get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            mesaj = ""
        raise GeminiHatasi(hata.code, mesaj[:500]) from None
    kullanim["cagri"] += 1
    u = cevap.get("usageMetadata") or {}
    kullanim["girdi"] += int(u.get("promptTokenCount") or 0)
    kullanim["cikti"] += int(u.get("candidatesTokenCount") or 0)
    adaylar = cevap.get("candidates") or []
    if not adaylar:
        raise ValueError(f"cevapta aday yok: {str(cevap.get('promptFeedback'))[:200]}")
    parcalar = (adaylar[0].get("content") or {}).get("parts") or []
    metin = "".join(p.get("text", "") for p in parcalar if not p.get("thought"))
    return claude_ceviri.cevabi_ayikla(metin)


def toplu_cevir(metinler: dict[str, str], cagir=None, kategori: str = "",
                bekleme: float = YOGUNLUK_BEKLEMESI) -> dict[str, str]:
    """{kimlik: İngilizce} → {kimlik: Türkçe}. Bir model hata verirse
    (kota, yoğunluk, zaman aşımı) sıradakine geçilir; hepsi tükenirse
    kalanlar sonuçta yer almaz (Google'a kalır). cagir(model, parca)."""
    if cagir is None:
        sistem_metni = claude_ceviri.sistem(kategori)
        cagir = lambda model, parca: _cagir(model, parca, sistem_metni)  # noqa: E731
    sonuc: dict[str, str] = {}
    modeller = list(MODELLER)
    kimlikler = list(metinler)[:CALISTIRMA_BASINA_METIN]
    for i in range(0, len(kimlikler), PARCA_BOYU):
        parca = {k: metinler[k] for k in kimlikler[i:i + PARCA_BOYU]}
        durum["denendi"] = True
        yeniden_denendi = False
        while modeller:
            model = modeller[0]
            try:
                sonuc.update(claude_ceviri._parcayi_cevir(parca, lambda p: cagir(model, p), "Gemini"))
                break
            except Exception as hata:  # noqa: BLE001 - Gemini olmazsa Google var
                if isinstance(hata, GeminiHatasi) and hata.kod in (500, 503) and not yeniden_denendi:
                    yeniden_denendi = True
                    time.sleep(bekleme)
                    continue
                print(f"Gemini ({model}) çeviremedi ({hata!r}); "
                      + (f"{modeller[1]} deneniyor" if len(modeller) > 1 else "kalanlar Google'a kalıyor"),
                      file=sys.stderr)
                modeller.pop(0)
                yeniden_denendi = False
        if not modeller:
            durum["hata"] = "bütün modeller başarısız"
            break
    return sonuc
