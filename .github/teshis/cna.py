import sys
sys.path.insert(0, "scripts")
from besleme import besleme_ogeleri, makale_getir
from ayarlar import CNA_ASYA

urls, tarihler = besleme_ogeleri(CNA_ASYA, 14)
print(f"[TESHIS] oge sayisi: {len(urls)}")
for u in urls:
    s = makale_getir(u)
    if not s:
        print(f"[TESHIS] {u} -> None"); continue
    print(f"[TESHIS] {u}\n[TESHIS]  tarih={s['tarih']!r} besleme={tarihler.get(u)!r}\n[TESHIS]  baslik={s['baslik']!r}\n[TESHIS]  etiketler={s['etiketler']}\n[TESHIS]  govde={s['govde'][:350]!r}")
