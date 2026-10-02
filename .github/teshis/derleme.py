"""GEÇİCİ teşhis: Gündem derleme prototipi (B): gevşek aday gruplar tek
istekte Gemini'ye; Gemini aynı olayı anlatanları süzer ve her olay için
derleme yazar. Zincirde olmayan bir modelle (canlı çevirinin hakkı
harcanmasın). Anahtar loga yazılmaz."""

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

MODEL = "gemini-3.8-flash"
kullanim = {"istek": 0, "girdi": 0, "cikti": 0}


def gemini(sistem: str, metin: str) -> dict:
    """Bu sürüm Claude Sonnet'le (Gemini'nin ücretsiz kotası doldu)."""
    import subprocess
    komut = ["claude", "-p", "Aşağıdaki aday grupları talimata göre işle.", "--output-format", "json",
             "--tools", "", "--max-turns", "1", "--no-session-persistence", "--system-prompt", sistem,
             "--model", "sonnet"]
    bas = time.time()
    sonuc = subprocess.run(komut, input=metin, capture_output=True, text=True, timeout=600,
                           cwd=os.environ.get("RUNNER_TEMP") or None)
    if sonuc.returncode != 0:
        print(f"[TESHIS] claude hata {sonuc.returncode}: {sonuc.stderr[-300:]}", flush=True)
        return {}
    zarf = json.loads(sonuc.stdout)
    u = zarf.get("usage") or {}
    kullanim["istek"] += 1
    kullanim["girdi"] += int(u.get("input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0)
    kullanim["cikti"] += int(u.get("output_tokens") or 0)
    print(f"[TESHIS] istek: {time.time() - bas:.1f} sn, {u}", flush=True)
    metin = zarf.get("result") or ""
    try:
        return json.loads(metin[metin.index("{"):metin.rindex("}") + 1])
    except ValueError as hata:
        print(f"[TESHIS] JSON okunamadı: {hata}; {metin[:300]!r}", flush=True)
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

# --- (B) Gevşek adaylar → tek istekte süzme + derleme ---
adaylar = "\n\n".join(
    f"Aday {i}:\n" + "\n".join(f"{kimlik[u]} [{haber[u].kaynak}] {en(haber[u])[0]}\n{en(haber[u])[1]}" for u in g)
    for i, g in enumerate(gevsek))
cevap = gemini(
    """Sen bir Türk haber sitesinin editörüsün. Bir algoritma benzer görünen haberleri aday gruplar halinde
topladı (kimlik [kaynak] başlık, ardından özet; İngilizce).

1) Her aday grupta aynı somut olayı anlatan haberleri belirle; olayı farklı
olanları çıkar. Bir aday birden fazla olaya bölünebilir.
""" + KURAL + """

2) İki ya da daha fazla haberli her olay için Türkçe bir derleme yaz:
- "baslik": tarafsız, bilgi eklemeyen bir haber başlığı.
- "ozet": 4-6 cümle. Olayın ne olduğunu anlat; kaynaklar farklı bilgi, rakam
  ya da vurgu veriyorsa kaynağını belirterek göster ("Al Jazeera'ya göre…",
  "Moscow Times ise … yazdı"). Tek kaynağa dayanan iddiayı o kaynağa bağla.
Kurallar: yalnız metinlerde olan bilgiyi kullan, yorum ve tahmin ekleme; sayı,
isim ve tarihleri değiştirme; "reportedly", "allegedly" gibi kesinlik
kayıtlarını koru; kişi, kurum ve yayın adlarını çevirme.

JSON döndür: {"olaylar": [{"haberler": ["h1", "h7"], "baslik": "...", "ozet": "..."}, ...]}""",
    adaylar)
olay_listesi = cevap.get("olaylar", [])
print(f"[TESHIS] ===== (B) tek istek: {len(olay_listesi)} olay")
for o in olay_listesi:
    uyeler = [url_kimlik[k] for k in dict.fromkeys(o.get("haberler", [])) if k in url_kimlik]
    print("[TESHIS] -----")
    for u in uyeler:
        m = haber[u]
        print(f"[TESHIS] KAYNAK {kimlik[u]} [{m.kaynak}] {en(m)[0]}")
        print(f"[TESHIS]   {en(m)[1][:700]}")
    print(f"[TESHIS] DERLEME BAŞLIK: {o.get('baslik')}")
    print(f"[TESHIS] DERLEME ÖZET: {o.get('ozet')}")

print(f"[TESHIS] kullanım: {kullanim}")
