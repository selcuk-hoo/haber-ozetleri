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


def _cagir(model: str, parca: dict) -> dict[str, str]:
    cevap = gemini_ceviri.metin_uret(model, TALIMAT, json.dumps(parca, ensure_ascii=False))
    return claude_ceviri.cevabi_ayikla(cevap)


def ozetle(cevirmen, makaleler: list, cagir=None) -> int:
    """Özeti olmayan (ya da kaynağı değişmiş) haberlerin özetini yazdırıp
    önbelleğe kaydeder; en yeniler önce gelmeli. Kaydedilen özet sayısı döner."""
    bekleyen = {f"y{i}": m for i, m in enumerate(
        m for m in makaleler if m.uzun and cevirmen.yz_ozeti(m.url, m.uzun) is None)}
    if not bekleyen:
        return 0
    if cagir is None:
        if not gemini_ceviri.kullanilabilir_mi():
            return 0
        cagir = _cagir
    girdi = {k: {"baslik": m.baslik, "metin": m.uzun} for k, m in bekleyen.items()}
    sonuc = gemini_ceviri.toplu_cevir(girdi, cagir=cagir)
    alinan = sum(cevirmen.yz_ozeti_kaydet(bekleyen[k].url, bekleyen[k].uzun, oz)
                 for k, oz in sonuc.items() if isinstance(oz, str))
    print(f"Gemini özeti: {alinan}/{len(bekleyen)} haber; kullanım: {gemini_ceviri.kullanim_ozeti()}")
    for k in list(sonuc)[:2]:
        print(f"  {bekleyen[k].baslik[:100]}\n  → {str(sonuc[k])[:300]}")
    return alinan
