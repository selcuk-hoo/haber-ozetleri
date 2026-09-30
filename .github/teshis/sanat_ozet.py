"""GEÇİCİ teşhis: yeni Sanat & Kültür kaynaklarının temizlenmiş özetleri."""

import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
import haber_uret  # noqa: E402
from takip import Takip  # noqa: E402

for ad, adres in [("aeon.co", "https://aeon.co/feed.rss"), ("lithub.com", "https://lithub.com/feed/")]:
    ayiklanan: set[str] = set()
    makaleler = haber_uret.kaynak_haberleri("Sanat & Kültür", ad, adres, Takip({}, datetime.now(timezone.utc)), ayiklanan)
    print(f"[TESHIS] == {ad}: {len(makaleler)} haber, ayıklanan: {sorted(ayiklanan)[:6]}")
    for m in makaleler:
        print(f"[TESHIS]   {m.tarih[:16]} {m.baslik} | görsel {'var' if m.gorsel else 'yok'}")
        print(f"[TESHIS]     {m.ozet[:600]}")
