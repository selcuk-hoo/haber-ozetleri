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
import os
import sys

import claude_ceviri
import gemini_ceviri
from ayarlar import TURKCE_KAYNAKLAR

TALIMAT = """Sen bir Türk haber sitesinin editörüsün. Her metin bir haberin ilk paragrafları
(İngilizce). Her biri için Türkçe 2-3 cümlelik bir özet yaz (özetin tamamı Türkçe olsun): haberin asıl bilgisini
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


# Başlığı soru olan haberler (22.10.2026): genel talimattaki "cevabı özete
# koy" kuralı Flash-Lite'ta tutmuyordu; soru başlıklı 118 özetin çoğu haberin
# girişini anlatıp soruyu cevapsız bırakıyordu (Al Jazeera "Meta neden 25
# milyar dolar ceza aldı?": cevap, Cambridge Analytica, metnin ilk cümlesinde
# olduğu hâlde özette yoktu). Bu haberler ayrı istekte, bu ekle gider.
SORU_EKI = """
BU İSTEKTEKİ BÜTÜN BAŞLIKLAR BİRER SORU. Özetin ilk cümlesi başlıktaki soruya metnin verdiği
cevabı doğrudan versin: "neden" diye soruyorsa sebebi, "ne", "neler", "kim" diye soruyorsa onları
adıyla say, evet/hayır sorusuysa metnin vardığı sonucu söyle. Haberin öteki bilgisi ondan sonra
gelir. Metin soruyu açıkça cevaplamıyorsa cevap uydurma; ama bunu da yazma: "kesin bir cevap yok",
"metinde yanıtlanmıyor" gibi sözler özete girmez. Metnin verdiği bilgiyi doğal bir haber özeti
gibi yaz."""


# Soru başlıklı haberlerin özetini Haiku 5.5 yazar (22.10.2026, kullanıcının
# kararı); olmazsa Gemini. SORU_EKI'yle Gemini'de 16 özetin ~8'i soruyu
# cevaplıyor, 3'ünde bozuk sözcük vardı ("Güney Africalı", "Avrupa Union");
# aynı 17 haberde Haiku cevabı daha çok veriyordu (Çin'in rolü: zirveye
# Shenzhen'de ev sahipliği), bozuk sözcük yoktu. Kusuru: hemen her özete
# "Metne göre…" diye başlıyor, metnin neyi anlatmadığını yazıyor, 3-4 cümle
# yazıyordu; bu ek onun için. Kullanım: 17 haber ~12 bin girdi + ~9 bin
# çıktı token (düşünme payı); günde ~25 haber, haftalık limitin ~%1-2'si.
CLAUDE_EKI = """
Okura "metin", "metne göre", "haberde", "yazı" diye söz etme; bilgiyi doğrudan ver. Metin soruyu
cevaplamıyorsa bunu yazma ("kesin bir cevap yok", "yanıtlanmıyor" gibi sözler özete girmez); metnin
verdiği bilgiyi yorum katmadan, doğal bir haber özeti gibi yaz. Metnin neyi anlatmadığını ya da nerede
bittiğini yazma. Özet en çok 3 cümle olsun. İngilizce terim bırakma."""
CLAUDE_PARCA = 10  # bir çağrıdaki haber sayısı
CLAUDE_EN_FAZLA = 30  # çalıştırma başına; kalanlar Gemini'ye


def _cagir(model: str, parca: dict, talimat: str = TALIMAT) -> dict[str, str]:
    cevap = gemini_ceviri.metin_uret(model, talimat, json.dumps(parca, ensure_ascii=False))
    return claude_ceviri.cevabi_ayikla(cevap)


def _claude_cagir(parca: dict, talimat: str) -> dict[str, str]:
    return claude_ceviri.cevabi_ayikla(claude_ceviri.metin_uret(
        "Aşağıdaki JSON nesnesindeki haberleri kurallara göre özetle.",
        json.dumps(parca, ensure_ascii=False), talimat))


def claude_kullanilir() -> bool:
    # Deneme dalında (CEVIRI_KAPALI) kapalı: önbellek orada kaydedilmediği
    # için her çalıştırmada aynı haberler yeniden yazdırılırdı.
    return claude_ceviri.kullanilabilir_mi() and not os.environ.get("CEVIRI_KAPALI")


def _claude_ile(girdi: dict, cagir) -> dict:
    sonuc: dict = {}
    kimlikler = list(girdi)[:CLAUDE_EN_FAZLA]
    for i in range(0, len(kimlikler), CLAUDE_PARCA):
        parca = {k: girdi[k] for k in kimlikler[i:i + CLAUDE_PARCA]}
        claude_ceviri.durum["denendi"] = True
        try:
            sonuc.update(claude_ceviri._parcayi_cevir(parca, cagir))
        except Exception as hata:  # noqa: BLE001 - Claude olmazsa Gemini var
            print(f"Claude özeti alınamadı ({hata!r}); kalanlar Gemini'ye", file=sys.stderr)
            claude_ceviri.durum["hata"] = repr(hata)[:300]
            break
    return sonuc


def ozetle(cevirmen, makaleler: list, cagir=None, claude_cagir=None) -> int:
    """Özeti olmayan (ya da kaynağı değişmiş) haberlerin özetini yazdırıp
    önbelleğe kaydeder; en yeniler önce gelmeli. Türkçe kaynaklar ayrı istekle,
    kendi talimatıyla gider; soru başlıklılar önce Claude'a (Haiku). Kaydedilen
    özet sayısı döner."""
    gemini_var = cagir is not None or gemini_ceviri.kullanilabilir_mi()
    claude_var = claude_cagir is not None or claude_kullanilir()
    if not (gemini_var or claude_var):
        return 0
    toplam = 0
    for turkce, soru in ((False, False), (False, True), (True, False), (True, True)):
        bekleyen = {f"y{i}": m for i, m in enumerate(
            m for m in makaleler
            if (m.kaynak in TURKCE_KAYNAKLAR) == turkce and cevirmen.soru_mu(m.baslik) == soru
            and m.uzun and cevirmen.yz_ozeti(m.url, m.uzun, soru) is None)}
        if not bekleyen:
            continue
        talimat = (TALIMAT_TR if turkce else TALIMAT) + (SORU_EKI if soru else "")
        girdi = {k: {"baslik": m.baslik, "metin": m.uzun} for k, m in bekleyen.items()}
        etiket = ("Türkçe kaynaklar" if turkce else "yabancı kaynaklar") + (", soru başlıklı" if soru else "")
        if soru and claude_var:
            istek = claude_cagir or (lambda parca, t=talimat + CLAUDE_EKI: _claude_cagir(parca, t))
            sonuc = _claude_ile(girdi, istek)
            kaydedilen = [k for k, oz in sonuc.items() if isinstance(oz, str)
                          and cevirmen.yz_ozeti_kaydet(bekleyen[k].url, bekleyen[k].uzun, oz, soru, "c")]
            print(f"Claude özeti ({etiket}): {len(kaydedilen)}/{len(bekleyen)} haber;"
                  f" kullanım: {claude_ceviri.kullanim_ozeti()}")
            for k in kaydedilen[:5]:
                print(f"  {bekleyen[k].baslik[:100]}\n  → {sonuc[k][:300]}")
            toplam += len(kaydedilen)
            girdi = {k: v for k, v in girdi.items() if k not in kaydedilen}
            if not girdi:
                continue
        if not gemini_var:
            continue
        if cagir is not None:
            istek = cagir
        else:
            istek = lambda model, parca, t=talimat: _cagir(model, parca, t)  # noqa: E731
        sonuc = gemini_ceviri.toplu_cevir(girdi, cagir=istek)
        alinan = sum(cevirmen.yz_ozeti_kaydet(bekleyen[k].url, bekleyen[k].uzun, oz, soru)
                     for k, oz in sonuc.items() if isinstance(oz, str))
        print(f"Gemini özeti ({etiket}): {alinan}/{len(girdi)} haber; kullanım: {gemini_ceviri.kullanim_ozeti()}")
        for k in list(sonuc)[:5 if soru else 2]:
            print(f"  {bekleyen[k].baslik[:100]}\n  → {str(sonuc[k])[:300]}")
        toplam += alinan
    return toplam
