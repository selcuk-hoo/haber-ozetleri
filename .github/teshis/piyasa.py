"""GEÇİCİ: döviz, altın, BIST 100 ve Brent için ücretsiz kaynaklar çalışıyor mu?"""
import json
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; haber-ozetleri)"}


def al(ad, adres, uzunluk=400):
    try:
        istek = urllib.request.Request(adres, headers=UA)
        with urllib.request.urlopen(istek, timeout=25) as y:
            govde = y.read().decode("utf-8", "replace")
        print(f"[TESHIS] ### {ad}: HTTP {y.status}, {len(govde)} harf")
        return govde
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] ### {ad}: HATA {hata!r}")
        return None


# 1) TCMB: resmi gösterge kurlar
g = al("TCMB today.xml", "https://www.tcmb.gov.tr/kurlar/today.xml")
if g:
    import re
    print("[TESHIS] TCMB tarih:", re.search(r'Tarih="([^"]+)"', g).group(1) if re.search(r'Tarih="([^"]+)"', g) else "?")
    print("[TESHIS] TCMB kodlar:", re.findall(r'CurrencyCode="(\w+)"', g))
    for kod in ("USD", "EUR", "XAU"):
        m = re.search(rf'<Currency[^>]*CurrencyCode="{kod}".*?</Currency>', g, re.S)
        print(f"[TESHIS] TCMB {kod}:", re.sub(r"\s+", " ", m.group(0))[:300] if m else "yok")

# 2) Truncgil: piyasa kurları (gram, çeyrek, tam altın dahil olabilir)
for ad, adres in (("Truncgil v4", "https://finans.truncgil.com/v4/today.json"),
                  ("Truncgil v3", "https://finans.truncgil.com/v3/today.json"),
                  ("Truncgil v2", "https://finans.truncgil.com/today.json")):
    g = al(ad, adres)
    if not g:
        continue
    try:
        d = json.loads(g)
    except Exception as hata:  # noqa: BLE001
        print("[TESHIS]  json değil:", repr(hata)[:100], g[:150].replace("\n", " "))
        continue
    anahtarlar = list(d)
    print(f"[TESHIS]  {len(anahtarlar)} anahtar: {anahtarlar[:80]}")
    for k in anahtarlar:
        ku = str(k).upper()
        if any(w in ku for w in ("USD", "EUR", "GRA", "CEYREK", "TAM", "BIST", "BRENT", "ONS", "XU100", "GOLD")) and len(str(k)) < 30:
            print(f"[TESHIS]  {k}: {json.dumps(d[k], ensure_ascii=False)[:230]}")
    if "Update_Date" in d or "Meta_Data" in d:
        print("[TESHIS]  meta:", json.dumps(d.get("Meta_Data", d.get("Update_Date")), ensure_ascii=False)[:200])

# 3) Yahoo Finance (resmi olmayan): BIST 100, Brent, USD/TRY
for ad, simge in (("Yahoo XU100", "XU100.IS"), ("Yahoo Brent", "BZ=F"), ("Yahoo USDTRY", "USDTRY=X"),
                  ("Yahoo EURTRY", "EURTRY=X"), ("Yahoo ons altın", "GC=F")):
    g = al(ad, f"https://query1.finance.yahoo.com/v8/finance/chart/{simge}?interval=1d&range=5d")
    if g:
        try:
            r = json.loads(g)["chart"]["result"][0]
            print("[TESHIS]  ", simge, r["meta"].get("regularMarketPrice"), r["meta"].get("regularMarketTime"),
                  r["meta"].get("exchangeName"), r["meta"].get("currency"))
        except Exception as hata:  # noqa: BLE001
            print("[TESHIS]  ayrıştırılamadı", repr(hata)[:100], g[:150])

# 4) Stooq CSV
for ad, simge in (("Stooq BIST100", "xu100"), ("Stooq ^XU100", "^xu100"), ("Stooq Brent", "cb.f"),
                  ("Stooq USDTRY", "usdtry"), ("Stooq ons altın", "xauusd")):
    g = al(ad, f"https://stooq.com/q/l/?s={simge}&f=sd2t2ohlcv&h&e=csv")
    if g:
        print("[TESHIS]  ", g.strip().replace("\n", " | ")[:200])

# 5) Frankfurter (AMB referans kurları) ve ücretsiz altın ons API
g = al("Frankfurter", "https://api.frankfurter.dev/v1/latest?base=USD&symbols=TRY,EUR")
if g:
    print("[TESHIS]  ", g[:200])
g = al("gold-api XAU", "https://api.gold-api.com/price/XAU")
if g:
    print("[TESHIS]  ", g[:300])
