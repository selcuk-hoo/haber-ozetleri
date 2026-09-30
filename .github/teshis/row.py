"""GEÇİCİ teşhis: Rest of World beslemesi (öğe sayısı, tarihler, metin, özet)."""
import sys
from collections import Counter

sys.path.insert(0, "scripts")
import feedparser  # noqa: E402

from besleme import besleme_ogeleri, makale_getir  # noqa: E402
from ozet import basligi_temizle, ozet_olustur  # noqa: E402

for adres in ["https://restofworld.org/feed/latest/", "https://restofworld.org/feed/"]:
    f = feedparser.parse(adres, agent="Mozilla/5.0")
    print(f"[TESHIS] {adres} durum={getattr(f, 'status', '?')} öğe={len(f.entries)} hata={f.bozo_exception if f.bozo else ''}")
    gunler = Counter((e.get("published") or "")[:16] for e in f.entries)
    print(f"[TESHIS]   günler: {dict(gunler)}")
    for e in f.entries[:20]:
        print(f"[TESHIS]   {e.get('published','')[:25]} | {e.get('title','')[:90]} | {e.get('link','')[:90]}")

urls, tarihler = besleme_ogeleri("https://restofworld.org/feed/latest/", 12)
print(f"[TESHIS] besleme_ogeleri: {len(urls)} url")
for url in urls[:6]:
    s = makale_getir(url)
    if s is None:
        print(f"[TESHIS] YOK {url}")
        continue
    b = basligi_temizle(s["baslik"], "restofworld.org")
    o = ozet_olustur(s["govde"], b, 5, "restofworld.org")
    print(f"[TESHIS] --- {url}\n[TESHIS] başlık: {b}\n[TESHIS] tarih: {s['tarih']} / besleme: {tarihler.get(url,'')}\n[TESHIS] görsel: {s['gorsel'][:90]}\n[TESHIS] govde: {len(s['govde'])} karakter\n[TESHIS] özet: {o}")
