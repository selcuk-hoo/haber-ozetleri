"""Piyasa sekmesi (29.10.2026, kullanıcının isteği): dolar, euro, gram/çeyrek/tam
altın, BIST 100 ve Brent petrol; ayrıca günlük ortalamaların kalıcı kaydı.

Yapay zekâ yok, her saatlik çalıştırmada birkaç HTTP isteği. Kaynaklar
(GitHub'ın sunucusunda denendi, 29.10.2026; resmi değil, ücretsiz):
- Truncgil today.json (v3): dolar, euro, gram/çeyrek/tam altın (alış ve satış,
  günlük değişim; serbest piyasa kurları, TCMB'nin iş günü 15:30 kuru değil).
- Yahoo Finance chart API: BIST 100 (XU100.IS), Brent (BZ=F); Truncgil'in
  dolar ve euro için yedeği (USDTRY=X, EURTRY=X).
Bir kaynak çökerse önceki değer kalır (sayfada saati görünür); ~3 saat hiçbir
şey alınamazsa sağlık uyarısı gelir. TCMB today.xml (resmi dolar/euro) denendi,
altını yok; gerekirse dolar/euro yedeği olur.

Günlük ortalama: her enstrüman için, kaynağın verdiği zaman damgası
değişmişse (piyasa kapalıyken aynı değer tekrar sayılmasın) o günün
istatistiğine bir örnek eklenir: n, ort, min, max, ilk, son (alış; satış da
varsa ayrıca). Türkiye saatine göre gün. piyasa_gunluk.json hiç silinmez
(yılda ~250 KB); grafik için (sonra) kaynak.
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ayarlar import TR_SAATI

UA = {"User-Agent": "Mozilla/5.0 (compatible; haber-ozetleri)"}
ZAMAN_ASIMI = 25
BAYAT_SURE = timedelta(hours=3)  # hiçbir kaynaktan veri alınamadı: sağlık sinyali
ESKI_SURE = timedelta(hours=3)  # enstrümanın değeri bu kadar eskiyse saati yazılır
SICRAMA = 0.25  # önceki değerden %25'ten fazla farklı yeni değer (bozuk veri) alınmaz

TRUNCGIL = "https://finans.truncgil.com/v3/today.json"
TRUNCGIL_ANAHTAR = {"usd": "USD", "eur": "EUR", "gram": "gram-altin", "ceyrek": "ceyrek-altin", "tam": "tam-altin"}
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{simge}?interval=1d&range=5d"
YAHOO_SIMGE = {"bist100": "XU100.IS", "brent": "BZ=F"}
YAHOO_YEDEK = {"usd": "USDTRY=X", "eur": "EURTRY=X"}

# Sayfadaki sıra: (grup, [(kod, görünen ad, birim öneki, birim soneki, ondalık)])
GRUPLAR = (
    ("Döviz (alış / satış)", (("usd", "Dolar", "", " ₺", 4), ("eur", "Euro", "", " ₺", 4))),
    ("Altın (alış / satış)", (("gram", "Gram altın", "", " ₺", 2), ("ceyrek", "Çeyrek altın", "", " ₺", 2),
                              ("tam", "Tam altın", "", " ₺", 2))),
    ("Borsa ve petrol", (("bist100", "BIST 100", "", " puan", 2), ("brent", "Brent petrol", "$", "", 2))),
)
KODLAR = [k for _, e in GRUPLAR for k, *_ in e]


def sayi_tr(metin) -> float:
    """"49,8316" → 49.8316, "6.449,49" → 6449.49, "$4.025,11" → 4025.11, "%-1,03" → -1.03."""
    if isinstance(metin, (int, float)):
        return float(metin)
    s = str(metin).replace("$", "").replace("%", "").replace("₺", "").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def _al(adres: str) -> str:
    istek = urllib.request.Request(adres, headers=UA)
    with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as yanit:
        return yanit.read().decode("utf-8", "replace")


def truncgil(getir=_al) -> dict[str, dict]:
    veri = json.loads(getir(TRUNCGIL))
    zaman = datetime.strptime(veri["Update_Date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=TR_SAATI).isoformat()
    sonuc = {}
    for kod, anahtar in TRUNCGIL_ANAHTAR.items():
        k = veri.get(anahtar)
        if not isinstance(k, dict):
            continue
        sonuc[kod] = {"alis": sayi_tr(k["Buying"]), "satis": sayi_tr(k["Selling"]),
                      "degisim": sayi_tr(k["Change"]) if k.get("Change") not in (None, "") else None,
                      "zaman": zaman, "kaynak": "Truncgil"}
    return sonuc


def yahoo(simge: str, getir=_al) -> dict:
    sonuc = json.loads(getir(YAHOO.format(simge=simge)))["chart"]["result"][0]
    meta = sonuc["meta"]
    fiyat = float(meta["regularMarketPrice"])
    kapanislar = [c for c in (sonuc.get("indicators", {}).get("quote") or [{}])[0].get("close", []) if c is not None]
    # Son çubuk bugünün (ya da son işlem gününün) çubuğu; öncekisi önceki kapanış.
    degisim = None
    if len(kapanislar) >= 2 and kapanislar[-2]:
        degisim = (fiyat - kapanislar[-2]) / kapanislar[-2] * 100
    zaman = datetime.fromtimestamp(int(meta["regularMarketTime"]), tz=timezone.utc).astimezone(TR_SAATI)
    return {"alis": fiyat, "satis": None, "degisim": degisim, "zaman": zaman.isoformat(), "kaynak": "Yahoo Finance"}


def topla(getir=_al) -> dict[str, dict]:
    """{kod: gözlem}; alınamayan kod yok. Kaynak hataları yutulur (loga yazılır)."""
    sonuc: dict[str, dict] = {}
    try:
        sonuc.update(truncgil(getir))
    except Exception as hata:  # noqa: BLE001 - bir kaynak düşerse ötekiler sürer
        print(f"Piyasa: Truncgil alınamadı ({hata!r})", file=sys.stderr)
    for kod, simge in {**YAHOO_SIMGE, **{k: s for k, s in YAHOO_YEDEK.items() if k not in sonuc}}.items():
        try:
            sonuc[kod] = yahoo(simge, getir)
        except Exception as hata:  # noqa: BLE001
            print(f"Piyasa: Yahoo {simge} alınamadı ({hata!r})", file=sys.stderr)
    return sonuc


def _makul_mu(yeni: dict, eski: dict | None) -> bool:
    if not (yeni["alis"] > 0):
        return False
    if eski and eski.get("alis"):
        return abs(yeni["alis"] / eski["alis"] - 1) <= SICRAMA
    return True


def _istatistik(onceki: dict | None, deger: float) -> dict:
    if not onceki:
        return {"n": 1, "ort": round(deger, 4), "min": deger, "max": deger, "ilk": deger, "son": deger, "t": deger}
    t = onceki["t"] + deger
    n = onceki["n"] + 1
    return {"n": n, "ort": round(t / n, 4), "min": min(onceki["min"], deger), "max": max(onceki["max"], deger),
            "ilk": onceki["ilk"], "son": deger, "t": t}


def guncelle(kayit: dict, gunluk: dict, gozlemler: dict[str, dict], simdi: datetime) -> tuple[dict, dict]:
    """kayit: önceki piyasa.json, gunluk: piyasa_gunluk.json. Yeni hâlleri döndürür."""
    degerler = dict(kayit.get("degerler", {}))
    gun = simdi.astimezone(TR_SAATI).date().isoformat()
    gunluk = {"gunler": dict(gunluk.get("gunler", {}))}
    bugun = dict(gunluk["gunler"].get(gun, {}))
    alinan = 0
    for kod in KODLAR:
        g = gozlemler.get(kod)
        if not g:
            continue
        if not _makul_mu(g, degerler.get(kod)):
            print(f"Piyasa: {kod} değeri makul değil, atlandı ({g['alis']})", file=sys.stderr)
            continue
        alinan += 1
        yeni_zaman = g["zaman"] != (degerler.get(kod) or {}).get("zaman")
        degerler[kod] = g
        if yeni_zaman:
            gunun = dict(bugun.get(kod, {}))
            gunun["alis"] = _istatistik(gunun.get("alis"), g["alis"])
            if g.get("satis"):
                gunun["satis"] = _istatistik(gunun.get("satis"), g["satis"])
            bugun[kod] = gunun
    if bugun:
        gunluk["gunler"][gun] = bugun
    zaman = simdi.isoformat() if alinan else kayit.get("zaman", "")
    bayat = (not zaman) or (simdi - datetime.fromisoformat(zaman) > BAYAT_SURE)
    print(f"Piyasa: {alinan}/{len(KODLAR)} değer alındı"
          + ("; " + ", ".join(f"{k} {degerler[k]['alis']:g}" for k in KODLAR if k in degerler)))
    return {"zaman": zaman, "bayat": bayat, "degerler": degerler}, gunluk


def yukle(yol: Path, varsayilan: dict) -> dict:
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else varsayilan
    except (FileNotFoundError, json.JSONDecodeError):
        return varsayilan


def kaydet(yol: Path, kayit: dict) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(kayit, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def sayi_yaz(deger: float, ondalik: int) -> str:
    """49.8316 → "49,8316", 41570.74 → "41.570,74" (Türkçe yazım)."""
    s = f"{deger:,.{ondalik}f}"
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")
