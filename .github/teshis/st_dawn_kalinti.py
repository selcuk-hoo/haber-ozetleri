"""GEÇİCİ teşhis: Straits Times ve Dawn: üretim koduyla çekilen haberlerin metin başı/sonu (kalıntı var mı)."""
import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
from ayarlar import KAYNAKLAR, YZ_OZET_CUMLE  # noqa: E402
from besleme import makale_getir  # noqa: E402
from haber_uret import kaynak_haberleri  # noqa: E402
from ozet import basligi_temizle, ozet_olustur  # noqa: E402
from takip import Takip  # noqa: E402

takip = Takip({}, datetime.now(timezone.utc))
for kategori, ad, adres in KAYNAKLAR:
    if ad in ("straitstimes.com", "dawn.com"):
        haberler = kaynak_haberleri(kategori, ad, adres, takip)
        print(f"[TESHIS] ==== {ad}: {len(haberler)} haber (hedef 3)")
        for m in haberler:
            print(f"[TESHIS] -- {m.baslik}\n[TESHIS]    tarih={m.tarih} ilk5={m.ozet[:260]}")
            s = makale_getir(m.url)
            uzun = ozet_olustur(s["govde"], basligi_temizle(s["baslik"], ad), YZ_OZET_CUMLE, ad)
            print(f"[TESHIS]    HAM BAS: {s['govde'][:200]!r}\n[TESHIS]    HAM SON: {s['govde'][-200:]!r}")
