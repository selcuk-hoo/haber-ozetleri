"""GEÇİCİ teşhis: Quanta ve Ars Technica metinleri, yeni ayıklamalar."""

import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
import besleme  # noqa: E402
import haber_uret  # noqa: E402
from takip import Takip  # noqa: E402

urls, _ = besleme.besleme_ogeleri("https://feeds.arstechnica.com/arstechnica/index", 14)
for url in urls:
    s = besleme.makale_getir(url) or {}
    print(f"[TESHIS] HAM ars | {s.get('baslik', '')[:70]} | {s.get('govde', '')[:700]!r}")

for kategori, ad, adres in [("Bilim", "quantamagazine.org", "https://www.quantamagazine.org/feed/"),
                            ("Teknoloji", "arstechnica.com", "https://feeds.arstechnica.com/arstechnica/index"),
                            ("Bilim", "phys.org", "https://phys.org/rss-feed/"),
                            ("Teknoloji", "theverge.com", "https://www.theverge.com/rss/index.xml")]:
    ayiklanan: set[str] = set()
    makaleler = haber_uret.kaynak_haberleri(kategori, ad, adres, Takip({}, datetime.now(timezone.utc)), ayiklanan)
    print(f"[TESHIS] ===== {ad}: {len(makaleler)} haber, ayıklanan {len(ayiklanan) // 2}")
    for u in sorted(ayiklanan):
        if u.startswith("http"):
            print(f"[TESHIS]   AYIKLANDI {u}")
    for m in makaleler:
        print(f"[TESHIS] - {m.baslik}\n[TESHIS]   {m.ozet}")
