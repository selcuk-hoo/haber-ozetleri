"""Yapay zekâ özeti (Gündem, Teknoloji, Bilim; 05.10.2026'dan beri).

"İlk K cümlenin çevirisi" uzun yazılarda girişte kalıyordu: anekdotla
açılan yazının özeti başlıktaki soruya varmıyordu (SCMP "Ne pahasına?"
veri merkezi yazısı). Gemini Flash-Lite metnin ilk YZ_OZET_CUMLE
cümlesinden 2-3 cümlelik Türkçe özet yazar: önce haberin asıl bilgisi.

Deneme (03.10.2026, 10 gerçek haber): hikâyeyle açılan yazılarda belirgin
iyi; düz haberde aşağı yukarı aynı ama daha kısa, biraz ayrıntı kaybı;
bir anlam hatası ("informal settlement" → "seyyar sokak"). Kullanıcı
canlıya alınmasını istedi. Anlam hatalarını ceviri_denetcisi.py yakalar.

Özet önbellekte "y"/"yh" ile durur (bkz. Cevirmen.yz_ozeti); kaynak metin
değişince yeniden yazılır. Gemini olmazsa ya da geçersiz özet dönerse o
haberde eski yöntem (ilk K cümlenin çevirisi) kullanılır. İstekler
çeviriyle aynı model zincirinden (gemini_ceviri.MODELLER) gider; Flash-Lite
günde 500 istek, özet çalıştırma başına çoğunlukla tek istek.
"""

import json

import claude_ceviri
import gemini_ceviri
from ayarlar import TURKCE_KAYNAKLAR

TALIMAT = """Sen bir Türk haber sitesinin editörüsün. Her metin bir haberin ilk paragrafları
(İngilizce). Her biri için Türkçe 2-3 cümlelik bir özet yaz: haberin asıl bilgisini
ver (ne oldu, kim, nerede, neden önemli). Sahne kuran giriş, anekdot ya da alıntıyla
başlama; okur ilk cümlede haberi öğrensin. Başlık bir soru soruyorsa metnin verdiği
cevabı özete koy. Yalnız metindeki bilgiyi kullan, yorum ve tahmin ekleme; sayı,
isim ve tarihleri değiştirme; "reportedly", "allegedly" gibi kesinlik kayıtlarını
koru ("bildirildi", "iddia edildi"); kişi, kurum ve yayın adlarını çevirme; ülke ve
şehir adlarının Türkçede yerleşik biçimini kullan; ABD başkanı için "ABD Başkanı" de.
Yalnız Türk alfabesiyle, yazım kurallarına uygun yaz. Metin içinde tırnak gerekirse
“ ” kullan. Metinde sayfa kalıntısı (künye, tarih satırı, etkinlik duyurusu, yazar
adı) varsa özete alma.
Girdi: {"kimlik": {"baslik": "...", "metin": "..."}, ...}
Yalnız JSON döndür: {"kimlik": "Türkçe özet", ...}"""


# Türkçe kaynaklar (13.10.2026): metin zaten Türkçe, çeviri yok; yalnız özet.
# Haberin sonu (son durum, sonuç) özete girsin, giriş paragrafıyla aynı olay
# iki kez anlatılıyorsa bir kez yazılsın (Euronews Türkçe, BBC Türkçe: giriş
# paragrafı + aynı olayın ayrıntılı anlatımı).
TALIMAT_TR = """Sen bir Türk haber sitesinin editörüsün. Her metin bir Türkçe haberin ilk paragraflarıdır.
Her biri için 2-3 cümlelik Türkçe bir özet yaz: haberin asıl bilgisini ver (ne oldu, kim, nerede,
neden önemli) ve metinde varsa haberin son durumunu, sonucunu ya da son gelişmeyi de özete koy.
Metinde aynı olay iki kez anlatılıyorsa yalnız bir kez yaz. Özet başlığın altında gösterilecek:
ilk cümlede başlığı olduğu gibi tekrar etme. Yalnız metindeki bilgiyi kullan; yorum ve tahmin ekleme;
sayı, isim ve tarihleri değiştirme; "iddia edildi", "öne sürüldü" gibi kayıtları koru. Yalnız Türk
alfabesiyle, yazım kurallarına uygun yaz (özel adlar kaynaktaki gibi). Metinde sayfa kalıntısı
(künye, abonelik çağrısı, yazar adı) varsa özete alma.
Girdi: {"kimlik": {"baslik": "...", "metin": "..."}, ...}
Yalnız JSON döndür: {"kimlik": "Türkçe özet", ...}"""


def _cagir(model: str, parca: dict, talimat: str = TALIMAT) -> dict[str, str]:
    cevap = gemini_ceviri.metin_uret(model, talimat, json.dumps(parca, ensure_ascii=False))
    return claude_ceviri.cevabi_ayikla(cevap)


def ozetle(cevirmen, makaleler: list, cagir=None) -> int:
    """Özeti olmayan (ya da kaynağı değişmiş) haberlerin özetini yazdırıp
    önbelleğe kaydeder; en yeniler önce gelmeli. Türkçe kaynaklar ayrı istekle,
    kendi talimatıyla gider. Kaydedilen özet sayısı döner."""
    if cagir is None and not gemini_ceviri.kullanilabilir_mi():
        return 0
    toplam = 0
    for turkce in (False, True):
        bekleyen = {f"y{i}": m for i, m in enumerate(
            m for m in makaleler
            if (m.kaynak in TURKCE_KAYNAKLAR) == turkce and m.uzun and cevirmen.yz_ozeti(m.url, m.uzun) is None)}
        if not bekleyen:
            continue
        if cagir is not None:
            istek = cagir
        else:
            talimat = TALIMAT_TR if turkce else TALIMAT
            istek = lambda model, parca, t=talimat: _cagir(model, parca, t)  # noqa: E731
        girdi = {k: {"baslik": m.baslik, "metin": m.uzun} for k, m in bekleyen.items()}
        sonuc = gemini_ceviri.toplu_cevir(girdi, cagir=istek)
        alinan = sum(cevirmen.yz_ozeti_kaydet(bekleyen[k].url, bekleyen[k].uzun, oz)
                     for k, oz in sonuc.items() if isinstance(oz, str))
        etiket = "Türkçe kaynaklar" if turkce else "yabancı kaynaklar"
        print(f"Gemini özeti ({etiket}): {alinan}/{len(bekleyen)} haber; kullanım: {gemini_ceviri.kullanim_ozeti()}")
        for k in list(sonuc)[:2]:
            print(f"  {bekleyen[k].baslik[:100]}\n  → {str(sonuc[k])[:300]}")
        toplam += alinan
    return toplam
