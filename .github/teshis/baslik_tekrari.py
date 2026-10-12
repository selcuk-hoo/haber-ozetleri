"""GEÇİCİ teşhis: başlık tekrarı.
1) The Art Newspaper "Comment |" yazısında başlık neden kırpılmıyor?
2) Gemini özetine "başlığı tekrarlama" kuralı: aynı haberlerde yeni talimatla tek istek."""
import json
import re
import sys

sys.path.insert(0, "scripts")
import gemini_ceviri  # noqa: E402
import gemini_ozet  # noqa: E402
from ayarlar import YZ_OZET_CUMLE  # noqa: E402
from besleme import makale_getir  # noqa: E402
from ozet import basligi_temizle, ozet_olustur  # noqa: E402

# 1) The Art Newspaper
url = "https://www.theartnewspaper.com/2026/10/09/comment-mark-wallinger-latest-work-making-big-ideas-accessible"
s = makale_getir(url)
if s:
    b = basligi_temizle(s["baslik"], "theartnewspaper.com")
    print(f"[TESHIS] TAN ham başlık: {s['baslik']!r}")
    print(f"[TESHIS] TAN temiz başlık: {b!r}")
    print(f"[TESHIS] TAN gövde başı: {s['govde'][:400]!r}")
    print(f"[TESHIS] TAN özet: {ozet_olustur(s['govde'], b, 5, 'theartnewspaper.com')[:400]!r}")
else:
    print("[TESHIS] TAN alınamadı")

# 2) Gemini özeti, yeni talimat
YENI = gemini_ozet.TALIMAT.replace(
    "başlama; okur ilk cümlede haberi öğrensin.",
    "başlama. Başlık okura özetin hemen üstünde gösteriliyor: ilk cümlede başlığı ne aynen ne de\n"
    "başka sözcüklerle yeniden söyle; başlıktaki bilgiyi bilinen say, ayrıntı (kim, ne zaman, nerede,\n"
    "kaç), bağlam, gerekçe ya da sonuçla devam et.")
assert YENI != gemini_ozet.TALIMAT
veri = json.load(open(".github/teshis/baslik_ornekler.json"))
haberler = [(r, "tekrar") for r in veri["tekrar"]] + [(r, "diger") for r in veri["diger"]]
girdi, bilgi = {}, {}
for i, ((u, kaynak, tr_b, tr_o), tur) in enumerate(haberler):
    s = makale_getir(u)
    if not s:
        print(f"[TESHIS] alınamadı {u}")
        continue
    b = basligi_temizle(s["baslik"], kaynak)
    uzun = ozet_olustur(s["govde"], b, YZ_OZET_CUMLE, kaynak)[:2000]
    if not uzun:
        continue
    girdi[f"y{i}"] = {"baslik": b, "metin": uzun}
    bilgi[f"y{i}"] = (tur, kaynak, tr_b, tr_o, b)
cevap = gemini_ceviri.metin_uret("gemini-flash-lite-latest", YENI, json.dumps(girdi, ensure_ascii=False))
sonuc = json.loads(re.search(r"\{.*\}", cevap, re.S).group(0))
for k, (tur, kaynak, tr_b, tr_o, en_b) in bilgi.items():
    print(f"\n[TESHIS] ==== {tur} | {kaynak}\n[TESHIS] EN B : {en_b}\n[TESHIS] TR B : {tr_b}"
          f"\n[TESHIS] ESKİ : {tr_o}\n[TESHIS] YENİ : {sonuc.get(k, '<YOK>')}")
