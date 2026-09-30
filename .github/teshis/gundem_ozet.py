"""GEÇİCİ teşhis: yeni Gündem kaynaklarının temizlenmiş özetleri."""

import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
import haber_uret  # noqa: E402
from takip import Takip  # noqa: E402

for ad, adres in [
    ("bbc.com/turkce", "https://feeds.bbci.co.uk/turkce/rss.xml"),
    ("dw.com/tr", "https://rss.dw.com/rdf/rss-tur-all"),
    ("africanews.com", "https://www.africanews.com/feed/rss"),
    ("mercopress.com", "https://en.mercopress.com/rss/"),
    ("aa.com.tr", "https://www.aa.com.tr/en/rss/default?cat=turkiye"),
]:
    ayiklanan: set[str] = set()
    makaleler = haber_uret.kaynak_haberleri("Gündem", ad, adres, Takip({}, datetime.now(timezone.utc)), ayiklanan)
    print(f"[TESHIS] == {ad}: {len(makaleler)} haber, {len(ayiklanan) // 2} ayıklanan")
    for m in makaleler:
        print(f"[TESHIS]   {m.tarih[:16]} {m.baslik}")
        print(f"[TESHIS]     {m.ozet[:420]}")
