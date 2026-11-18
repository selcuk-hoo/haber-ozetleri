"""Geçici teşhis: CNN'in World bölümünden gelecek haberler (başlık, tarih)."""
import sys

sys.path.insert(0, "scripts")
from besleme import anasayfa_baglantilari, makale_getir  # noqa: E402

DESEN = r"(?:https://edition\.cnn\.com)?/20\d\d/\d\d/\d\d/[a-z\-]+/[^\"'#?\s<>]+"
for adres in ("https://edition.cnn.com/world", "https://www.cnn.com/world"):
    urller = anasayfa_baglantilari(adres, DESEN, 40)
    print(f"[TESHIS] {adres}: {len(urller)} bağlantı")
    if not urller:
        continue
    for url in urller[:24]:
        s = makale_getir(url)
        if not s:
            print(f"[TESHIS]   ✗ {url}")
            continue
        print(f"[TESHIS]   {(s.get('tarih') or '')[:16]} | {url.split('/')[6]} | {s.get('baslik','')[:100]}")
    break
