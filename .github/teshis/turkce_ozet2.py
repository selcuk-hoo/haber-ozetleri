"""GEÇİCİ teşhis: Türkçe kaynak özeti (uzun metin) + denetçi, gerçek haberlerde."""
import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
import ceviri_denetcisi  # noqa: E402
import gemini_ozet  # noqa: E402
from ayarlar import KAYNAKLAR, TURKCE_KAYNAKLAR  # noqa: E402
from ceviri import Cevirmen  # noqa: E402
from haber_uret import kaynak_haberleri  # noqa: E402
from takip import Takip  # noqa: E402

takip = Takip({}, datetime.now(timezone.utc))
makaleler = []
for kategori, ad, adres in KAYNAKLAR:
    if ad in TURKCE_KAYNAKLAR and kategori == "Gündem":
        try:
            makaleler += kaynak_haberleri(kategori, ad, adres, takip)[:4]
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] {ad} alınamadı: {hata!r}")
uzunlu = [m for m in makaleler if m.uzun]
print(f"[TESHIS] {len(makaleler)} haber, {len(uzunlu)} tanesinde uzun metin (kısalar eski yöntemle)")
c = Cevirmen({}, lambda m: "G " + m, 0, bekleme=0)
alinan = gemini_ozet.ozetle(c, uzunlu)
print(f"[TESHIS] özet alınan: {alinan}/{len(uzunlu)}")
sayac = ceviri_denetcisi.denetle(c, [(m.url, m.baslik, m.ozet, m.uzun) for m in uzunlu], turkce=True)
print(f"[TESHIS] denetim: {sayac}")
for m in uzunlu:
    print(f"\n[TESHIS] ==== {m.kaynak} | {m.baslik}\n[TESHIS] METIN SONU: ...{m.uzun[-350:]}"
          f"\n[TESHIS] OZET: {c.yz_ozeti(m.url, m.uzun) or '<YOK: eski yöntem>'}")
