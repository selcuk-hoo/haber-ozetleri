"""GEÇİCİ teşhis: T24 (yalnız Türkiye bölümleri) kaynak_haberleri sonucu."""

import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
import besleme  # noqa: E402
import haber_uret  # noqa: E402
from ayarlar import ANASAYFA_KAYNAKLARI  # noqa: E402
from takip import Takip  # noqa: E402

adaylar = besleme.anasayfa_baglantilari("https://t24.com.tr/", ANASAYFA_KAYNAKLARI["t24.com.tr"], 40)
print(f"[TESHIS] aday bağlantı: {len(adaylar)}")
ayiklanan: set[str] = set()
makaleler = haber_uret.kaynak_haberleri("Gündem", "t24.com.tr", "https://t24.com.tr/",
                                        Takip({}, datetime.now(timezone.utc)), ayiklanan)
print(f"[TESHIS] kaynak_haberleri: {len(makaleler)} haber")
for m in makaleler:
    print(f"[TESHIS] - {m.baslik} | {m.tarih}")
    print(f"[TESHIS]   {m.ozet[:380]}")
