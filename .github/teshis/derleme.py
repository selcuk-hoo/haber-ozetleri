"""GEÇİCİ teşhis: Gündem derleme, iki aşamalı. Gevşek algoritma aday
gruplar üretir; Haiku (ve karşılaştırma için Sonnet) aynı olayı anlatanları
süzer (yalnız başlık + ilk cümle); Sonnet Haiku'nun gruplarından derleme
yazar (Türkçe kaynakların kendi metniyle)."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "scripts")
import haber_uret  # noqa: E402
import olaylar  # noqa: E402
from ayarlar import KAYNAKLAR, TURKCE_KAYNAKLAR  # noqa: E402
from ceviri import onbellegi_yukle  # noqa: E402
from model import KaynakBolumu  # noqa: E402
from takip import Takip  # noqa: E402


def claude(model: str, sistem: str, metin: str) -> dict:
    komut = ["claude", "-p", "Aşağıdaki girdiyi talimata göre işle.", "--output-format", "json", "--tools", "",
             "--max-turns", "1", "--no-session-persistence", "--system-prompt", sistem, "--model", model]
    bas = time.time()
    sonuc = subprocess.run(komut, input=metin, capture_output=True, text=True, timeout=600,
                           cwd=os.environ.get("RUNNER_TEMP") or None)
    if sonuc.returncode != 0:
        print(f"[TESHIS] {model} hata {sonuc.returncode}: {sonuc.stderr[-300:]}", flush=True)
        return {}
    zarf = json.loads(sonuc.stdout)
    u = zarf.get("usage") or {}
    girdi = int(u.get("input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0) \
        + int(u.get("cache_read_input_tokens") or 0)
    print(f"[TESHIS] {model}: {time.time() - bas:.1f} sn, girdi {girdi}, çıktı {u.get('output_tokens')}, "
          f"API karşılığı ${float(zarf.get('total_cost_usd') or 0):.4f}", flush=True)
    yanit = zarf.get("result") or ""
    try:
        return json.loads(yanit[yanit.index("{"):yanit.rindex("}") + 1])
    except ValueError as hata:
        print(f"[TESHIS] JSON okunamadı: {hata}; {yanit[:300]!r}", flush=True)
        return {}


onbellek = onbellegi_yukle(Path("dist/ceviri.json"))
bolumler = []
for kat, ad, adres in KAYNAKLAR:
    if kat == "Gündem":
        bolumler.append(KaynakBolumu(ad, adres, haber_uret.kaynak_haberleri(kat, ad, adres,
                                                                            Takip({}, datetime.now(timezone.utc)))))
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
    # Süzme için: İngilizce başlık + ilk cümle (Türkçe kaynakta İngilizcesi).
    b, o = ingilizceler.get(m.url, (m.baslik, m.ozet))
    return f"{kimlik[m.url]} [{m.kaynak}] {b} — {olaylar.ilk_cumleler(o, 1)[:300]}"


olaylar.ESIK, olaylar.EN_AZ_ORTAK_ISIM = 0.12, 1
gevsek = [[oncu] + [m.url for m in d] for (_, oncu), d in
          olaylar.olaylari_grupla(kategoriler, ingilizceler, TURKCE_KAYNAKLAR).items()]
print(f"[TESHIS] Gündem: {len(haberler)} haber; gevşek adaylar: {len(gevsek)} grup, "
      f"{sum(len(g) for g in gevsek)} haber")

SUZ = """Sen bir haber sitesinin editörüsün. Bir algoritma benzer görünen haberleri aday
gruplar halinde topladı (kimlik [kaynak] başlık — ilk cümle). Her aday grupta
aynı somut olayı anlatan haberleri belirle; olayı farklı olanları çıkar. Bir
aday birden fazla olaya bölünebilir.
Aynı olay: aynı gelişme, açıklama, saldırı, karar ya da toplantı. Yalnız aynı
genel konu (ör. "Ukrayna savaşı", "Gazze", "ABD seçimleri") YETMEZ; farklı
gelişme ayrı olaydır. Bir olayda her kaynaktan en fazla bir haber. Emin
değilsen birleştirme.
Yalnız 2 ve daha fazla haberli olayları döndür: {"olaylar": [["h1", "h7"], ...]}"""
adaylar = "\n\n".join(f"Aday {i}:\n" + "\n".join(kisa(haber[u]) for u in g) for i, g in enumerate(gevsek))


def gruplar(cevap):
    sonuc = []
    for g in cevap.get("olaylar", []):
        uyeler = [url_kimlik[k] for k in dict.fromkeys(g) if k in url_kimlik]
        if len({haber[u].kaynak for u in uyeler}) > 1:
            sonuc.append(uyeler)
    return sonuc


h_gruplar = gruplar(claude("haiku", SUZ, adaylar))
s_gruplar = gruplar(claude("sonnet", SUZ, adaylar))
for ad, gs in (("HAIKU", h_gruplar), ("SONNET", s_gruplar)):
    print(f"[TESHIS] ===== {ad}: {len(gs)} olay")
    for g in gs:
        print("[TESHIS]   ---")
        for u in g:
            print(f"[TESHIS]   {kisa(haber[u])[:170]}")
h_set = {frozenset(g) for g in h_gruplar}
s_set = {frozenset(g) for g in s_gruplar}
print(f"[TESHIS] aynı: {len(h_set & s_set)}, yalnız Haiku: {len(h_set - s_set)}, yalnız Sonnet: {len(s_set - h_set)}")


def tam(m):
    # Derleme için: özgün metin (Türkçe kaynakta Türkçe).
    return f"[{m.kaynak}] {m.baslik}\n{m.ozet}"


girdi = "\n\n".join(f"Olay g{i}:\n" + "\n".join(tam(haber[u]) for u in g) for i, g in enumerate(h_gruplar))
cevap = claude("sonnet", """Sen bir Türk haber sitesinin editörüsün. Her olayda aynı olayı anlatan farklı
kaynakların haberleri var (İngilizce ya da Türkçe). Her olay için Türkçe tek bir derleme yaz:
- "baslik": tarafsız, bilgi eklemeyen bir haber başlığı.
- "ozet": 4-6 cümle. Olayın ne olduğunu anlat; kaynaklar farklı bilgi, rakam
  ya da vurgu veriyorsa kaynağını belirterek göster ("Al Jazeera'ya göre…",
  "Moscow Times ise … yazdı"). Tek kaynağa dayanan iddiayı o kaynağa bağla.
Kurallar: yalnız metinlerde olan bilgiyi kullan, yorum ve tahmin ekleme; sayı,
isim ve tarihleri değiştirme; rakamlar zamanla değişmişse (ölü sayısı gibi)
en güncelini esas al, eskisini yazma; "reportedly", "allegedly" gibi kesinlik
kayıtlarını koru; kişi, kurum ve yayın adlarını çevirme.
JSON döndür: {"g0": {"baslik": "...", "ozet": "..."}, ...}""", girdi)
for i, g in enumerate(h_gruplar):
    d = cevap.get(f"g{i}", {})
    print(f"[TESHIS] ===== Derleme g{i}: {', '.join(haber[u].kaynak for u in g)}")
    print(f"[TESHIS] BAŞLIK: {d.get('baslik')}")
    print(f"[TESHIS] ÖZET: {d.get('ozet')}")
