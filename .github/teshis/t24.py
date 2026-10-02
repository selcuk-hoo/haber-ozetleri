"""GEÇİCİ teşhis: T24 ana sayfa bağlantıları ve kaynak_haberleri sonucu."""

import collections
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
import besleme  # noqa: E402
import haber_uret  # noqa: E402
from ayarlar import ANASAYFA_KAYNAKLARI  # noqa: E402
from takip import Takip  # noqa: E402
from trafilatura import fetch_url  # noqa: E402

ana = fetch_url("https://t24.com.tr/") or ""
print(f"[TESHIS] anasayfa: {len(ana)} bayt")
tum = re.findall(r'href=["\'](?:https://t24\.com\.tr)?(/[a-z0-9-]+/[^"\'#?\s<>]+,\d+)', ana)
print(f"[TESHIS] ,ID biçimli bağlantılar: {len(tum)}; bölümler: "
      f"{collections.Counter(t.split('/')[1] for t in tum).most_common(10)}")
adaylar = besleme.anasayfa_baglantilari("https://t24.com.tr/", ANASAYFA_KAYNAKLARI["t24.com.tr"], 24)
print(f"[TESHIS] haber bağlantısı: {len(adaylar)}")
for u in adaylar[:24]:
    print(f"[TESHIS]    {u}")
ayiklanan: set[str] = set()
makaleler = haber_uret.kaynak_haberleri("Gündem", "t24.com.tr", "https://t24.com.tr/",
                                        Takip({}, datetime.now(timezone.utc)), ayiklanan)
print(f"[TESHIS] kaynak_haberleri: {len(makaleler)} haber, ayıklanan {len(ayiklanan) // 2}")
for m in makaleler:
    print(f"[TESHIS] - {m.baslik} | {m.tarih} {'(tahmini)' if m.tahmini else ''}")
    print(f"[TESHIS]   {m.ozet[:420]}")
