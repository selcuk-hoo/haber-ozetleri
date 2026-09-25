"""GEÇİCİ teşhis: translate.goog adresi gerçek tarayıcıda asıl siteye yönleniyor mu?"""
from playwright.sync_api import sync_playwright

URL = ("https://selcuk--hoo-github-io.translate.goog/haber-ozetleri/"
       "?_x_tr_sl=en&_x_tr_tl=tr&_x_tr_hl=tr&_x_tr_pto=wapp")
with sync_playwright() as p:
    for ad, ayar in (("masaüstü", {}), ("mobil", p.devices["Pixel 7"])):
        tarayici = p.chromium.launch()
        sayfa = tarayici.new_context(locale="tr-TR", **ayar).new_page()
        olaylar = []
        sayfa.on("console", lambda m: olaylar.append("KONSOL " + m.text[:200]))
        sayfa.on("pageerror", lambda e: olaylar.append("HATA " + str(e)[:200]))
        sayfa.on("framenavigated", lambda f: olaylar.append("GEÇİŞ " + f.url[:150]) if f == sayfa.main_frame else None)
        try:
            sayfa.goto(URL, wait_until="load", timeout=60000)
        except Exception as e:
            olaylar.append("goto: " + str(e)[:200])
        sayfa.wait_for_timeout(10000)
        print(f"\n== {ad}: son adres {sayfa.url}")
        try:
            print("   bilgi:", sayfa.evaluate("""() => ({
              host: location.hostname,
              dataDil: document.documentElement.getAttribute('data-dil'),
              lang: document.documentElement.lang,
              ust: (document.querySelector('.meta span') || {getAttribute(){return null}}).getAttribute('data-etiket'),
              betik: document.scripts.length,
            })"""))
        except Exception as e:
            print("   evaluate:", e)
        for o in olaylar[:25]:
            print("  ", o)
        tarayici.close()
