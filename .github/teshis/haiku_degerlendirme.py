"""GEÇİCİ teşhis: Haiku 5.5 çevirilerinin İngilizce asılları (yan yana)."""
import json
import sys

sys.path.insert(0, "scripts")
from ayarlar import K, KATEGORI_OZET_CUMLE  # noqa: E402
from besleme import makale_getir  # noqa: E402
from ozet import basligi_temizle, ozet_olustur  # noqa: E402

for r in json.load(open(".github/teshis/haiku_ornekler.json")):
    s = makale_getir(r["url"])
    if not s:
        print(f"[TESHIS] ALINAMADI {r['url']}")
        continue
    b = basligi_temizle(s["baslik"], r["kaynak"])
    o = ozet_olustur(s["govde"], b, KATEGORI_OZET_CUMLE.get(r["kategori"], K), r["kaynak"])
    print(f"[TESHIS] ==== {r['kategori']} | {r['kaynak']}\n[TESHIS] EN B: {b}\n[TESHIS] TR B: {r['b']}"
          f"\n[TESHIS] EN O: {o}\n[TESHIS] TR O: {r['o']}")
