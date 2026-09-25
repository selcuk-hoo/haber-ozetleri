"""GEÇİCİ teşhis: yeni kaynaklar (Phys.org, Variety) ve translate.goog'un sunduğu kopya."""
import re, sys, urllib.request
sys.path.insert(0, "scripts")
from ayarlar import KAYNAKLAR
from besleme import besleme_ogeleri, makale_getir
from ozet import basligi_temizle, ozet_olustur

for ad in ("phys.org", "variety.com"):
    adres = [a for _, k, a in KAYNAKLAR if k == ad][0]
    urls, tarihler = besleme_ogeleri(adres, 20)
    print(f"\n== {ad}: {len(urls)} aday, en yeni {tarihler.get(urls[0], '-') if urls else '-'}")
    for u in urls[:4]:
        m = makale_getir(u)
        if not m:
            print("   makale alınamadı:", u); continue
        b = basligi_temizle(m["baslik"], ad)
        print(f"   {tarihler.get(u, '-')} | görsel: {'var' if m['gorsel'] else 'YOK'} | {u}")
        print(f"   BAŞLIK: {b}")
        print(f"   ÖZET: {ozet_olustur(m['govde'], b, 5, ad)}")

for adres in ("https://selcuk-hoo.github.io/haber-ozetleri/",
              "https://selcuk--hoo-github-io.translate.goog/haber-ozetleri/?_x_tr_sl=en&_x_tr_tl=tr&_x_tr_hl=tr&_x_tr_pto=wapp"):
    try:
        yanit = urllib.request.urlopen(urllib.request.Request(adres, headers={"User-Agent": "Mozilla/5.0"}), timeout=30)
        s = yanit.read().decode("utf-8", "replace")
        ust = re.search(r'data-etiket="([^"]*haber[^"]*)"', s) or re.search(r"(\d{4}-\d\d-\d\d \d\d:\d\d TRT)", s)
        print(f"\n{adres[:60]}…\n   HTTP {yanit.status} cache-control={yanit.headers.get('cache-control')} age={yanit.headers.get('age')}")
        print("   html:", re.search(r"<html[^>]*>", s).group(0)[:120], "| üst satır:", ust.group(1) if ust else "-")
        print("   başlık:", (re.search(r"<title>([^<]*)", s) or [None, "-"])[1][:80])
    except Exception as e:
        print("\n", adres[:60], "HATA:", e)
