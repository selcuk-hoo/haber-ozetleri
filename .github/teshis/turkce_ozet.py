"""GEÇİCİ teşhis: Türkçe kaynaklarda eski özet (ilk 5 cümle) ve Gemini özeti yan yana."""
import json
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, "scripts")
import gemini_ceviri  # noqa: E402
from ayarlar import KAYNAKLAR, TURKCE_KAYNAKLAR, YZ_OZET_CUMLE  # noqa: E402
from besleme import makale_getir  # noqa: E402
from haber_uret import kaynak_haberleri  # noqa: E402
from ozet import basligi_temizle, ozet_olustur  # noqa: E402
from takip import Takip  # noqa: E402

TALIMAT = """Sen bir Türk haber sitesinin editörüsün. Her metin bir Türkçe haberin ilk paragraflarıdır.
Her biri için 2-3 cümlelik Türkçe bir özet yaz: haberin asıl bilgisini ver (ne oldu, kim, nerede,
neden önemli) ve metinde varsa haberin son durumunu, sonucunu ya da son gelişmeyi de özete koy.
Metinde aynı olay iki kez anlatılıyorsa yalnız bir kez yaz; başlığı yeniden söyleme. Yalnız metindeki
bilgiyi kullan; yorum ve tahmin ekleme; sayı, isim ve tarihleri değiştirme; "iddia edildi", "öne
sürüldü" gibi kayıtları koru. Metinde sayfa kalıntısı (künye, abonelik çağrısı, yazar adı) varsa alma.
Girdi: {"kimlik": {"baslik": "...", "metin": "..."}, ...}
Yalnız JSON döndür: {"kimlik": "Türkçe özet", ...}"""

takip = Takip({}, datetime.now(timezone.utc))
girdi, bilgi = {}, {}
for kategori, ad, adres in KAYNAKLAR:
    if ad not in TURKCE_KAYNAKLAR:
        continue
    try:
        haberler = kaynak_haberleri(kategori, ad, adres, takip)[:3]
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] {ad} alınamadı: {hata!r}")
        continue
    for m in haberler:
        s = makale_getir(m.url)
        if not s:
            continue
        b = basligi_temizle(s["baslik"], ad)
        uzun = ozet_olustur(s["govde"], b, YZ_OZET_CUMLE, ad)[:2000]
        k = f"h{len(girdi)}"
        girdi[k] = {"baslik": b, "metin": uzun}
        bilgi[k] = (ad, b, m.ozet, len(s["govde"]), len(uzun))
cevap = gemini_ceviri.metin_uret("gemini-flash-lite-latest", TALIMAT, json.dumps(girdi, ensure_ascii=False))
sonuc = json.loads(re.search(r"\{.*\}", cevap, re.S).group(0))
for k, (ad, b, eski, boy, uboy) in bilgi.items():
    print(f"\n[TESHIS] ==== {ad} | metin {boy} harf, Gemini'ye giden {uboy}\n[TESHIS] BASLIK: {b}"
          f"\n[TESHIS] ESKI : {eski}\n[TESHIS] YENI : {sonuc.get(k, '<YOK>')}")
