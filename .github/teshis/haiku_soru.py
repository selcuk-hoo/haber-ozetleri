"""GEÇİCİ: soru başlıklı haberlerin özetini Haiku 5.5'e yazdırıp Gemini'ninkiyle karşılaştır."""
import json, sys
sys.path.insert(0, "scripts")
import claude_ceviri
import gemini_ozet
from ayarlar import YZ_OZET_CUMLE
from besleme import makale_getir
from ozet import basligi_temizle, ozet_olustur

liste = json.load(open(".github/teshis/haiku_soru_liste.json"))
onbellek = json.load(open("dist/ceviri.json"))
girdi, kimlikler = {}, {}
for i, (url, ad) in enumerate(liste):
    s = makale_getir(url)
    if not s:
        print(f"[TESHIS] alinamadi {url}")
        continue
    baslik = basligi_temizle(s["baslik"], ad)
    k = f"y{i}"
    girdi[k] = {"baslik": baslik, "metin": ozet_olustur(s["govde"], baslik, YZ_OZET_CUMLE, ad)[:2000]}
    kimlikler[k] = url
sistem = gemini_ozet.TALIMAT + gemini_ozet.SORU_EKI
sonuc = {}
anahtarlar = list(girdi)
for parca in (anahtarlar[:1], anahtarlar[1:]):
    try:
        cevap = claude_ceviri.metin_uret("Aşağıdaki JSON nesnesindeki haberleri kurallara göre özetle.",
                                         json.dumps({k: girdi[k] for k in parca}, ensure_ascii=False), sistem)
        sonuc.update(claude_ceviri.cevabi_ayikla(cevap))
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] hata: {hata}")
    print(f"[TESHIS] {len(parca)} haberlik cagri sonrasi kullanim: {claude_ceviri.kullanim_ozeti()} {claude_ceviri.kullanim}")
for k, url in kimlikler.items():
    kayit = onbellek.get(url, {})
    print(f"[TESHIS] ### {kayit.get('b', girdi[k]['baslik'])}")
    print(f"[TESHIS] GEMINI: {kayit.get('y', '')}")
    print(f"[TESHIS] HAIKU : {sonuc.get(k, '(yok)')}")
