"""GEÇİCİ teşhis: her kaynağın beslemesindeki en yeni haberler sayfada var mı?"""
import html, re, subprocess, sys
sys.path.insert(0, "scripts")
from ayarlar import KAYNAKLAR
from besleme import ATLANAN_ADRES, besleme_listesi, besleme_ogeleri, makale_getir

sayfa = subprocess.run(["git", "show", "FETCH_HEAD:index.html"], capture_output=True, text=True).stdout
sayfadakiler = {html.unescape(u) for u in re.findall(r'data-url="([^"]*)"', sayfa)}
for kategori, ad, adres in KAYNAKLAR:
    urls, tarihler = besleme_ogeleri(adres, 20)
    yol = "besleme"
    if not urls:
        urls, yol = besleme_listesi(adres, 20), "site haritası"
    print(f"\n== {kategori} / {ad} ({yol}, {len(urls)} aday)")
    for u in urls[:6]:
        if u in sayfadakiler:
            durum = "sayfada"
        elif ATLANAN_ADRES.search(u):
            durum = "video, atlandı"
        else:
            durum = "EKSİK: " + ("makale alınamadı" if not makale_getir(u) else "alınabiliyor")
        print(f"   {tarihler.get(u, '-'):26} {durum:28} {u[:95]}")
