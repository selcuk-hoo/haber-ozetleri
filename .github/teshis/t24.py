"""GEÇİCİ teşhis: T24 anasayfa haberlerinin başlangıç etiketleri (bölüm /
yazar satırı) ve diğer bölüm bağlantılarının türü."""

import collections
import re
import sys

sys.path.insert(0, "scripts")
import besleme  # noqa: E402
from trafilatura import fetch_url  # noqa: E402

ana = fetch_url("https://t24.com.tr/") or ""
haber = besleme.anasayfa_baglantilari("https://t24.com.tr/", r"(?:https://t24\.com\.tr)?/haber/[^\"'#?\s<>]+,\d+", 60)
print(f"[TESHIS] /haber/ bağlantısı: {len(haber)}")
etiketler = collections.Counter()
for u in haber:
    s = besleme.makale_getir(u)
    if not s:
        print(f"[TESHIS] ALINAMADI {u[-60:]}")
        continue
    bas = " ".join(s["govde"].split())[:90]
    kisa = " ".join(bas.split()[:3])
    etiketler[kisa] += 1
    print(f"[TESHIS] {s['baslik'][:70]!r} || {bas!r}")
print(f"[TESHIS] ilk üç kelime sayımı: {etiketler.most_common(25)}")
# Öteki bölüm bağlantıları (/gundem/, /ekonomi/ …) haber mi?
bolumler = collections.defaultdict(list)
for m in re.finditer(r'href=["\'](?:https://t24\.com\.tr)?(/([a-z0-9-]+)/[^"\'#?\s<>]+,\d+)', ana):
    bolumler[m.group(2)].append(m.group(1))
for ad in ("gundem", "ekonomi", "politika", "dunya", "medya", "foto-haber", "basinda-bugun"):
    for yol in bolumler.get(ad, [])[:2]:
        s = besleme.makale_getir("https://t24.com.tr" + yol)
        print(f"[TESHIS] /{ad}/ {yol[:70]} -> {'-' if not s else (s['baslik'][:50], ' '.join(s['govde'].split())[:70])}")
