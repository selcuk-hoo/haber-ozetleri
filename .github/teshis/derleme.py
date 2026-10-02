"""GEÇİCİ teşhis: Gemini 3.5 Flash-Lite ile derleme. Olay süzgecinin
gruplarından (canlıdaki gibi) her olay için tek bir Türkçe derleme.
Anahtar loga yazılmaz."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "scripts")
import gemini_ceviri  # noqa: E402
import haber_uret  # noqa: E402
import olay_suzgeci  # noqa: E402
from ayarlar import KAYNAKLAR, TURKCE_KAYNAKLAR  # noqa: E402
from ceviri import onbellegi_yukle  # noqa: E402
from model import KaynakBolumu  # noqa: E402
from takip import Takip  # noqa: E402

onbellek = onbellegi_yukle(Path("dist/ceviri.json"))
bolumler = [KaynakBolumu(ad, adres, haber_uret.kaynak_haberleri(kat, ad, adres, Takip({}, datetime.now(timezone.utc))))
            for kat, ad, adres in KAYNAKLAR if kat == "Gündem"]
kategoriler = {"Gündem": bolumler}
ingilizceler = {}
for b in bolumler:
    for m in b.makaleler:
        k = onbellek.get(m.url, {})
        if m.kaynak in TURKCE_KAYNAKLAR and k.get("eb") and k.get("eo"):
            ingilizceler[m.url] = (k["eb"], k["eo"])

kararlar = olay_suzgeci.kararlari_yukle(Path("dist/olay_kararlari.json"))
gruplar = olay_suzgeci.grupla(kategoriler, ingilizceler, TURKCE_KAYNAKLAR, kararlar, olay_suzgeci.gemini_sor)
print(f"[TESHIS] süzgeç: {olay_suzgeci.ozet()}; {len(gruplar)} grup")
olaylar_ = [[oncu_url] + [m.url for m in d] for (_, oncu_url), d in gruplar.items()]
haber = {m.url: m for b in bolumler for m in b.makaleler}

TALIMAT = """Sen bir Türk haber sitesinin editörüsün. Her olayda aynı olayı anlatan farklı
kaynakların haberleri var (İngilizce ya da Türkçe). Her olay için Türkçe tek bir derleme yaz:
- "baslik": tarafsız, bilgi eklemeyen bir haber başlığı.
- "ozet": 4-6 cümle. Olayın ne olduğunu anlat; kaynaklar farklı bilgi, rakam
  ya da vurgu veriyorsa kaynağını belirterek göster ("Al Jazeera'ya göre…",
  "Moscow Times ise … yazdı"). Tek kaynağa dayanan iddiayı o kaynağa bağla.
Kurallar: yalnız metinlerde olan bilgiyi kullan, yorum ve tahmin ekleme; sayı,
isim ve tarihleri değiştirme; rakamlar zamanla değişmişse (ölü sayısı gibi)
en güncelini esas al, eskisini yazma; "reportedly", "allegedly" gibi kesinlik
kayıtlarını koru ("bildirildi", "iddia edildi"); kişi, kurum ve yayın
adlarını çevirme; ABD başkanı için "ABD Başkanı" de.
Metin içinde tırnak gerekirse “ ” kullan (JSON bozulmasın).
JSON döndür: {"g0": {"baslik": "...", "ozet": "..."}, ...}"""
girdi = "\n\n".join(
    f"Olay g{i}:\n" + "\n".join(f"[{haber[u].kaynak}] {haber[u].baslik}\n{haber[u].ozet}" for u in g)
    for i, g in enumerate(olaylar_))
bas = time.time()
try:
    metin = gemini_ceviri.metin_uret("gemini-flash-lite-latest", TALIMAT, girdi, sicaklik=0.2)
    cevap = json.loads(metin[metin.index("{"):metin.rindex("}") + 1])
except Exception as hata:  # noqa: BLE001
    print(f"[TESHIS] derleme alınamadı: {hata!r}")
    cevap = {}
print(f"[TESHIS] derleme: {time.time() - bas:.1f} sn; kullanım: {gemini_ceviri.kullanim_ozeti()}")
for i, g in enumerate(olaylar_):
    d = cevap.get(f"g{i}", {})
    print(f"[TESHIS] ===== g{i}")
    for u in g:
        m = haber[u]
        print(f"[TESHIS] KAYNAK [{m.kaynak}] {m.baslik}")
        print(f"[TESHIS]   {m.ozet[:900]}")
    print(f"[TESHIS] BAŞLIK: {d.get('baslik')}")
    print(f"[TESHIS] ÖZET: {d.get('ozet')}")
