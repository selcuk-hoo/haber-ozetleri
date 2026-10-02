"""GEÇİCİ teşhis: Gündem'de olay gruplama ve derleme kutusu prototipi.

Karşılaştırılanlar: bugünkü sıkı gruplama, gevşek aday gruplama,
(A) Gemini'nin tüm sayfayı gruplaması, (B) gevşek adaylar + Gemini süzgeci,
ve 5 grup için Gemini derlemesi. Anahtar loga yazılmaz."""

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

MODEL = "gemini-2.5-flash"
kullanim = {"istek": 0, "girdi": 0, "cikti": 0}


def gemini(sistem: str, metin: str) -> dict:
    govde = {
        "systemInstruction": {"parts": [{"text": sistem}]},
        "contents": [{"role": "user", "parts": [{"text": metin}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1,
                             "thinkingConfig": {"thinkingBudget": 0}},
    }
    istek = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(govde).encode(),
        headers={"x-goog-api-key": os.environ.get("GEMINI_API_KEY", ""), "Content-Type": "application/json"})
    for deneme in range(3):
        bas = time.time()
        try:
            with urllib.request.urlopen(istek, timeout=120) as yanit:
                cevap = json.loads(yanit.read())
            u = cevap.get("usageMetadata", {})
            kullanim["istek"] += 1
            kullanim["girdi"] += u.get("promptTokenCount", 0)
            kullanim["cikti"] += u.get("candidatesTokenCount", 0)
            print(f"[TESHIS] istek: {time.time() - bas:.1f} sn, girdi {u.get('promptTokenCount')} "
                  f"çıktı {u.get('candidatesTokenCount')}", flush=True)
            metin = "".join(p.get("text", "") for p in cevap["candidates"][0]["content"]["parts"])
            return json.loads(metin[metin.index("{"):metin.rindex("}") + 1])
        except urllib.error.HTTPError as hata:
            print(f"[TESHIS] HTTP {hata.code}: {hata.read()[:300]!r}", flush=True)
            time.sleep(15)
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] hata: {type(hata).__name__}: {str(hata)[:200]}", flush=True)
            time.sleep(5)
    return {}


# --- Gündem haberleri (sayfadaki gibi) ---
onbellek = onbellegi_yukle(Path("dist/ceviri.json"))
bolumler = []
for kat, ad, adres in KAYNAKLAR:
    if kat != "Gündem":
        continue
    ms = haber_uret.kaynak_haberleri(kat, ad, adres, Takip({}, datetime.now(timezone.utc)))
    bolumler.append(KaynakBolumu(ad, adres, ms))
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


def en(m):
    return ingilizceler.get(m.url, (m.baslik, m.ozet))


def satir(m):
    return f"{m.kaynak} | {en(m)[0]}"


print(f"[TESHIS] Gündem: {len(haberler)} haber (Türkçe kaynaklardan {len(ingilizceler)} İngilizcesiyle)")


def gruplar_yaz(ad, gruplar):
    uye = sum(len(g) for g in gruplar)
    print(f"[TESHIS] ===== {ad}: {len(gruplar)} grup, {uye} haber")
    for g in sorted(gruplar, key=len, reverse=True):
        print("[TESHIS]   ---")
        for u in g:
            print(f"[TESHIS]   {kimlik[u]} {satir(haber[u])[:150]}")


def algoritma(esik, isim):
    olaylar.ESIK, olaylar.EN_AZ_ORTAK_ISIM = esik, isim
    sonuc = olaylar.olaylari_grupla(kategoriler, ingilizceler, TURKCE_KAYNAKLAR)
    return [[oncu] + [m.url for m in digerleri] for (_, oncu), digerleri in sonuc.items()]


siki = algoritma(0.30, 2)
gruplar_yaz("Bugünkü sıkı gruplama (0.30, 2 isim)", siki)
gevsek = algoritma(0.12, 1)
gruplar_yaz("Gevşek adaylar (0.12, 1 isim)", gevsek)

KURAL = """Aynı somut olayı anlatan haberler bir gruptur: aynı gelişme, aynı açıklama,
aynı saldırı, aynı karar, aynı toplantı. Yalnız aynı genel konu (ör. "Ukrayna
savaşı", "Gazze", "ABD seçimleri") YETMEZ; farklı gün ya da farklı gelişme
ayrı olaydır. Bir grupta her kaynaktan en fazla bir haber olur. Emin değilsen
gruplama."""

# --- (A) Gemini tüm sayfayı gruplar ---
liste = "\n".join(f"{kimlik[m.url]}: {satir(m)} — {olaylar.ilk_cumleler(en(m)[1], 1)[:300]}" for m in haberler)
cevap = gemini(
    "Sen bir haber sitesinin editörüsün. Haber listesindeki haberleri olaylara göre grupla.\n" + KURAL
    + '\nYalnız 2 ve daha fazla haberli grupları döndür: {"gruplar": [["h1", "h7"], ...]}',
    liste)
a = [[url_kimlik[k] for k in g if k in url_kimlik] for g in cevap.get("gruplar", [])]
a = [g for g in a if len(g) > 1]
gruplar_yaz("(A) Gemini tüm sayfayı grupladı", a)

# --- (B) Gevşek adaylar + Gemini süzgeci ---
adaylar = "\n\n".join(
    f"Aday {i}:\n" + "\n".join(f"{kimlik[u]}: {satir(haber[u])} — {olaylar.ilk_cumleler(en(haber[u])[1], 1)[:300]}"
                               for u in g)
    for i, g in enumerate(gevsek))
cevap = gemini(
    "Sen bir haber sitesinin editörüsün. Bir algoritma benzer görünen haberleri aday gruplar halinde topladı. "
    "Her aday grupta aynı olayı anlatan haberleri belirle; olayı farklı olanları çıkar. Bir aday grup birden "
    "fazla olaya bölünebilir.\n" + KURAL
    + '\nYalnız 2 ve daha fazla haberli grupları döndür: {"gruplar": [["h1", "h7"], ...]}',
    adaylar)
b = [[url_kimlik[k] for k in g if k in url_kimlik] for g in cevap.get("gruplar", [])]
b = [g for g in b if len(g) > 1]
gruplar_yaz("(B) Gevşek adaylar + Gemini süzgeci", b)

# --- Derleme: B'nin en büyük 5 grubu ---
secilen = sorted(b, key=len, reverse=True)[:5]
girdi = "\n\n".join(
    f"Grup g{i}:\n" + "\n".join(f"[{haber[u].kaynak}] {en(haber[u])[0]}\n{en(haber[u])[1]}" for u in g)
    for i, g in enumerate(secilen))
cevap = gemini(
    """Sen bir Türk haber sitesinin editörüsün. Her grupta aynı olayı anlatan farklı kaynakların haberleri var
(İngilizce). Her grup için Türkçe tek bir derleme yaz:
- "baslik": tarafsız, bilgi eklemeyen bir haber başlığı.
- "ozet": 4-6 cümle. Olayın ne olduğunu anlat; kaynaklar farklı bilgi, rakam
  ya da vurgu veriyorsa kaynağını belirterek göster ("Al Jazeera'ya göre…",
  "Moscow Times ise … yazdı"). Tek kaynağa dayanan iddiayı o kaynağa bağla.
Kurallar: yalnız metinlerde olan bilgiyi kullan, yorum ve tahmin ekleme; sayı,
isim ve tarihleri değiştirme; "reportedly", "allegedly" gibi kesinlik
kayıtlarını koru; kişi, kurum ve yayın adlarını çevirme.
JSON döndür: {"g0": {"baslik": "...", "ozet": "..."}, ...}""",
    girdi)
for i, g in enumerate(secilen):
    d = cevap.get(f"g{i}", {})
    print(f"[TESHIS] ===== Derleme g{i} ({len(g)} kaynak)")
    for u in g:
        m = haber[u]
        print(f"[TESHIS] KAYNAK [{m.kaynak}] {en(m)[0]}")
        print(f"[TESHIS]   {en(m)[1][:900]}")
    print(f"[TESHIS] DERLEME BAŞLIK: {d.get('baslik')}")
    print(f"[TESHIS] DERLEME ÖZET: {d.get('ozet')}")

print(f"[TESHIS] kullanım: {kullanim}")
