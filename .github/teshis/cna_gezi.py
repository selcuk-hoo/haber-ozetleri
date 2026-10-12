"""GEÇİCİ teşhis: CNA Asya beslemesinde "weekend escapes" etiketli yazı var mı?"""
import re
import sys

sys.path.insert(0, "scripts")
from ayarlar import ATLANAN_BOLUMLER, CNA_ASYA  # noqa: E402
from besleme import besleme_ogeleri, makale_getir  # noqa: E402

urls, tarihler = besleme_ogeleri(CNA_ASYA, 60)
print(f"[TESHIS] besleme: {len(urls)} öğe")
atlanan = ATLANAN_BOLUMLER[("Gündem", "channelnewsasia.com")]
bolum = {}
for u in urls:
    m = re.search(r"channelnewsasia\.com/([^/]+)/", u)
    bolum[m.group(1) if m else "?"] = bolum.get(m.group(1) if m else "?", 0) + 1
print(f"[TESHIS] bölümler: {bolum}")
# Gezi için ilk 12 aday, bölümü atlanmayanlar
ilk = [u for u in urls[:12]]
print(f"[TESHIS] Gezi'nin baktığı ilk 12 adres:")
for u in ilk:
    print(f"[TESHIS]   {u}")
sayac = 0
for u in urls:
    if re.search(atlanan, u):
        continue
    s = makale_getir(u)
    if not s:
        print(f"[TESHIS] ALINAMADI {u}")
        continue
    sayac += 1
    print(f"[TESHIS] {u.split('.com/')[-1][:70]} | etiketler={list(s.get('etiketler', ()))[:8]}")
    if sayac >= 25:
        break
