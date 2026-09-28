# Geçici teşhis: Euronews Türkçe beslemesi ve özet kalitesi.
import sys
sys.path.insert(0, "scripts")
from besleme import besleme_ogeleri, makale_getir, _anasayfa_besleme_adaylari
from ozet import ozet_olustur

for adres in ["https://tr.euronews.com/rss", "https://tr.euronews.com/rss?level=theme&name=news", "https://tr.euronews.com/"]:
    urls, tarihler = besleme_ogeleri(adres, 12)
    print(f"\n[TESHIS] === {adres}: {len(urls)} öğe")
    if adres.endswith("/"):
        print("[TESHIS] adaylar:", _anasayfa_besleme_adaylari(adres))
    for u in urls:
        print(f"[TESHIS]  {tarihler.get(u, '-')[:25]} | {u}")
    if urls:
        break

for u in urls[:8]:
    s = makale_getir(u)
    print(f"\n[TESHIS] ----- {u}")
    if s is None:
        print("[TESHIS] makale_getir=None")
        continue
    print("[TESHIS] BAŞLIK:", s["baslik"])
    print("[TESHIS] GÖRSEL:", s.get("gorsel"))
    print("[TESHIS] HAM:", " ".join(s["govde"].split())[:900])
    print("[TESHIS] ÖZET:", ozet_olustur(s["govde"], s["baslik"], 5, "tr.euronews.com"))
