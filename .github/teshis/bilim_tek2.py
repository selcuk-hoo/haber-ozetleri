"""GEÇİCİ teşhis: The Verge ve Ars Technica temizlenmiş özetleri."""

import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
import haber_uret  # noqa: E402
from takip import Takip  # noqa: E402

for kategori, ad, adres in [("Teknoloji", "theverge.com", "https://www.theverge.com/rss/index.xml"),
                            ("Teknoloji", "arstechnica.com", "https://feeds.arstechnica.com/arstechnica/index")]:
    ayiklanan: set[str] = set()
    makaleler = haber_uret.kaynak_haberleri(kategori, ad, adres, Takip({}, datetime.now(timezone.utc)), ayiklanan)
    print(f"[TESHIS] ===== {ad}: {len(makaleler)} haber")
    for u in sorted(ayiklanan):
        if u.startswith("http"):
            print(f"[TESHIS]   AYIKLANDI {u}")
    for m in makaleler:
        print(f"[TESHIS] - {m.baslik}\n[TESHIS]   {m.ozet}")
