"""GEÇİCİ teşhis: The Verge ham metinleri (başlık tekrarı)."""

import sys

sys.path.insert(0, "scripts")
import besleme  # noqa: E402

urls, _ = besleme.besleme_ogeleri("https://www.theverge.com/rss/index.xml", 12)
for url in urls:
    s = besleme.makale_getir(url) or {}
    govde = s.get("govde", "")
    baslik = s.get("baslik", "")
    i = govde.find(baslik[:40]) if baslik else -1
    print(f"[TESHIS] HAM verge | {baslik!r} | etiket {s.get('etiketler', [])[:4]}")
    print(f"[TESHIS]   BAS {govde[:300]!r}")
    print(f"[TESHIS]   TEKRAR@{i} {govde[max(0, i - 150):i + 500]!r}")
