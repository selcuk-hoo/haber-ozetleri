#!/usr/bin/env python3
"""Haber kaynaklarından özet sayfasını (dist/index.html) üretir.

GitHub Actions'ta çalışıp statik bir HTML üretir. Başlık ve özetler
üretim sırasında Türkçeye çevrilir (ceviri.py); bakım yolları için
depodaki CLAUDE.md'ye bakın.

Modüller:
  ayarlar.py  kaynaklar, haber sayıları, eşikler (elle değiştirilen her şey)
  besleme.py  kaynaklardan haber adreslerini ve makale metinlerini çekme
  ozet.py     özet üretimi ve kaynağa özgü temizlik kuralları
  tarih.py    tarih ayrıştırma/biçimlendirme
  takip.py    haberlerin ilk görülme anı ve içerik güncellemeleri
  arsiv.py    "Older news" arşivi (sayfadan düşen haberlerin başlıkları)
  ceviri.py   başlık/özetlerin Türkçeye çevrilmesi (Google Çeviri, önbellekli)
  sayfa.py    HTML sayfası, robots.txt, sitemap.xml (CSS/JS: web/)
  model.py    modüller arasında taşınan Makale / KaynakBolumu / ArsivKaydi

Gereksinim: requirements.txt (sürümler sabit)
"""

import os
import re
from dataclasses import replace
from datetime import datetime, timezone

from courlan import normalize_url

from arsiv import arsivi_guncelle, arsivi_kaydet, arsivi_yukle, eski_haberler
from ayarlar import (
    ARSIV_DOSYASI, ATLANAN_BOLUMLER, CEVIRI_DOSYASI, CIKTI, CLAUDE_KATEGORILERI, ESKI_HABER_ESIGI, HARIC_BESLEMELER, K,
    KATEGORI_OZET_CUMLE, KATEGORI_SAYISI, KAYNAK_SAYISI, KAYNAKLAR, N, TAKIP_DOSYASI, TURKCE_KAYNAKLAR,
)
from besleme import ATLANAN_ADRES, besleme_listesi, besleme_ogeleri, makale_getir
import claude_ceviri
from ceviri import CALISTIRMA_BASINA_CAGRI, Cevirmen, onbellegi_kaydet, onbellegi_yukle
from model import ArsivKaydi, Ceviriler, KaynakBolumu, Makale
from olaylar import tekrar_mi
from ozet import atlanacak_mi, basligi_temizle, haber_ayiklanir_mi, ozet_olustur
from sayfa import sayfa_olustur, yan_dosyalari_yaz
from takip import Takip, takibi_kaydet, takibi_yukle
from tarih import ILK_GORULME_DOSYASI, guvenilir_tarih, sira_zamani, tarihi_ayristir


# Haberin tarihini ve bunun tahmini olup olmadığını döner. Sayfa ya da
# besleme güvenilir bir tarih vermiyorsa (CNN, Al Jazeera gibi gerçek
# RSS'i olmayan kaynaklarda görülüyor) haberi ilk gördüğümüz an
# kullanılır (bkz. takip.py). Bu gerçek yayın saati değil; sayfada "~" ile
# gösterilir.
def _tarih_bul(sayfa_tarihi: str, besleme_tarihi: str, url: str, takip: Takip) -> tuple[str, bool]:
    tarih = guvenilir_tarih(sayfa_tarihi, besleme_tarihi)
    if tarih:
        return tarih, False
    return takip.ilk_gorulme(url), True


def _cok_eski_mi(tarih: str) -> bool:
    zaman = tarihi_ayristir(tarih)
    if zaman is None or zaman.tzinfo is None:
        return False
    return datetime.now(timezone.utc) - zaman > ESKI_HABER_ESIGI


# Bir kaynağın en yeni haberlerini çekip özetler. takip tüm kaynaklar
# arasında paylaşılıyor; burada güncellenir. Başlığı ya da sayfa etiketi
# yüzünden atlanan yazıların adresleri ayiklanan'a eklenir (arşivden de
# çıksınlar diye: arşiv kayıtlarında etiket yok).
def kaynak_haberleri(kategori: str, ad: str, adres: str, takip: Takip,
                     ayiklanan: set[str] | None = None) -> list[Makale]:
    sayi = KAYNAK_SAYISI.get(ad, KATEGORI_SAYISI.get(kategori, N))
    # Video sayfaları atlanıp eski haberler elendiğinde yerleri
    # sonrakilerle dolsun diye iki katı aday alınıyor; hedef sayıya
    # ulaşınca durulduğu için fazladan sayfa ancak gerekirse çekiliyor.
    # Bölüm atlanan (bkz. ATLANAN_BOLUMLER) ya da başlığa göre haber
    # ayıklanan (ozet.KAYNAK_KURALLARI "haber_at") kaynakta adayların çoğu
    # elenebildiği için daha fazla aday alınıyor.
    atlanan_bolum = ATLANAN_BOLUMLER.get((kategori, ad))
    aday_sayisi = sayi * (4 if atlanan_bolum or haber_ayiklanir_mi(ad) else 2)
    urls, besleme_tarihleri = besleme_ogeleri(adres, aday_sayisi)
    if not urls:
        # Gerçek bir besleme yok (anasayfa/site haritası kaynağı, ör. CNN,
        # Al Jazeera) — site haritası yoluna düş; tarih bilgisi olmaz.
        urls = besleme_listesi(adres, aday_sayisi)
    haric: set[str] = set()
    for besleme in HARIC_BESLEMELER.get((kategori, ad), []):
        haric.update(besleme_ogeleri(besleme, 50)[0])

    makaleler: list[Makale] = []
    for url in urls:
        if len(makaleler) >= sayi:
            break
        if url in haric or (atlanan_bolum and re.search(atlanan_bolum, url)):
            continue
        if ATLANAN_ADRES.search(url):
            continue
        sonuc = makale_getir(url)
        if sonuc is None:
            continue
        baslik = basligi_temizle(sonuc["baslik"], ad)
        if atlanacak_mi(baslik, ad, sonuc.get("etiketler", ())):
            if ayiklanan is not None:
                ayiklanan.update({url, _normal(url)})
            continue
        ozet = ozet_olustur(sonuc["govde"], baslik, KATEGORI_OZET_CUMLE.get(kategori, K), ad)
        if not ozet:
            continue
        normal_url = _normal(url)

        tarih, tahmini = _tarih_bul(sonuc["tarih"], besleme_tarihleri.get(normal_url, ""), normal_url, takip)
        if _cok_eski_mi(tarih):
            continue
        # Aynı haberin ikinci adresi (bkz. olaylar.tekrar_mi): besleme en
        # yeniden eskiye sıralı olduğu için ilk görülen (yeni olan) kalır.
        if any(tekrar_mi(baslik, tarih, m.baslik, m.tarih) for m in makaleler):
            continue
        takip.gor(normal_url, baslik, ozet, "" if tahmini else tarih)
        makaleler.append(Makale(ad, baslik, url, ozet, sonuc["gorsel"], tarih, tahmini))
    takip.kaynak_bitti(ad)
    # Güncellenme anı kaynak bitince (toplu değişiklik denetiminden sonra)
    # belli oluyor.
    return [replace(m, guncellendi=takip.guncellendi(_normal(m.url))) for m in makaleler]


def _normal(url: str) -> str:
    try:
        return normalize_url(url)
    except Exception:  # noqa: BLE001
        return url


# CLAUDE_KATEGORILERI'ndeki haberlerin Claude çevirisi olmayan başlık ve
# özetleri Claude'a çevirtilip önbelleğe yazılır; ardından gelen olağan
# çeviri döngüsü bunları önbellekte bulur. Claude yoksa ya da başarısız
# olursa bu haberler de Google'a gider.
def claude_ile_cevir(cevirmen: Cevirmen, kategori: str, makaleler: list[Makale], tum_karsilastirma: bool = False) -> None:
    if not makaleler:
        return
    if not claude_ceviri.kullanilabilir_mi():
        print("Claude çevirisi kullanılamıyor (CLAUDE_CODE_OAUTH_TOKEN ya da claude CLI yok); Google kullanılıyor")
        return
    bekleyen: dict[str, tuple[str, str, str]] = {}  # kimlik → (tür, url, İngilizce)
    for m in makaleler:
        for tur, metin in (("b", m.baslik), ("o", m.ozet)):
            if cevirmen.claude_gerekli_mi(tur, m.url, metin):
                bekleyen[f"{tur}{len(bekleyen)}"] = (tur, m.url, metin)
    if not bekleyen:
        return
    onceki = {k: cevirmen.onbellek.get(url, {}).get(tur) for k, (tur, url, _) in bekleyen.items()}
    sonuc = claude_ceviri.toplu_cevir({k: metin for k, (_, _, metin) in bekleyen.items()}, kategori=kategori)
    for kimlik, ceviri in sonuc.items():
        tur, url, metin = bekleyen[kimlik]
        cevirmen.claude_kaydet(tur, url, metin, ceviri)
    print(f"Claude çevirisi ({kategori}): {len(sonuc)}/{len(bekleyen)} metin")
    # Karşılaştırma için: birkaç başlık ve özetin İngilizcesi, önceki
    # (Google) çevirisi ve Claude çevirisi. Deneme dalında hepsi, tam.
    basliklar = [k for k in sonuc if k.startswith("b")]
    ozetler = [k for k in sonuc if k.startswith("o")]
    ornekler = basliklar + ozetler if tum_karsilastirma else basliklar[:6] + ozetler[:2]
    for kimlik in ornekler:
        uzunluk = None if tum_karsilastirma else 110 if kimlik.startswith("b") else 400
        print(f"  EN : {bekleyen[kimlik][2][:uzunluk]}")
        if onceki[kimlik]:
            print(f"  G  : {onceki[kimlik][:uzunluk]}")
        print(f"  C  : {sonuc[kimlik][:uzunluk]}")


# Sayfadaki başlık/özetleri ve eski haber başlıklarını Türkçeye çevirir
# (önbellekten ya da Google'dan). Öncelik sayfadaki en yeni haberlerde;
# çalıştırma başına çağrı sınırı dolarsa kalanlar sonraki çalıştırmaya
# kalır.
def cevir(kategoriler: dict[str, list[KaynakBolumu]], eski: list[ArsivKaydi]) -> Ceviriler:
    # Deneme dalındaki çalıştırmalar yayınlamıyor ve çevirilerini
    # kaydetmiyor; Google'a gitmeleri yalnız sitenin istek sınırını (429)
    # tüketiyordu. Orada yalnız önbellekteki çeviriler kullanılır.
    kapali = os.environ.get("CEVIRI_KAPALI") == "1"
    cevirmen = Cevirmen(onbellegi_yukle(CEVIRI_DOSYASI), cagri_siniri=0 if kapali else CALISTIRMA_BASINA_CAGRI)
    if kapali:
        print("Google çevirisi kapalı (deneme dalı): yalnız önbellekteki çeviriler")
    makaleler = sorted(
        (m for bolumler in kategoriler.values() for b in bolumler for m in b.makaleler),
        key=sira_zamani,
        reverse=True,
    )
    for kat in sorted(CLAUDE_KATEGORILERI):
        claude_ile_cevir(cevirmen, kat, [
            m for b in kategoriler.get(kat, []) for m in b.makaleler if m.kaynak not in TURKCE_KAYNAKLAR
        ], tum_karsilastirma=kapali)
    for m in makaleler:
        if m.kaynak in TURKCE_KAYNAKLAR:
            cevirmen.turkce_kaynak(m.url, m.baslik, m.ozet)
            continue
        cevirmen.baslik(m.url, m.baslik)
        cevirmen.ozet(m.url, m.ozet)
    for k in eski:
        if k.kaynak in TURKCE_KAYNAKLAR:
            cevirmen.turkce_kaynak(k.url, k.baslik)
        else:
            cevirmen.baslik(k.url, k.baslik)
    onbellegi_kaydet(CEVIRI_DOSYASI, cevirmen.onbellek, {m.url for m in makaleler} | {k.url for k in eski})
    cevrilen = sum(cevirmen.ceviriler.cevrildi_mi(m.url) for m in makaleler)
    print(
        f"Çeviri: {cevrilen}/{len(makaleler)} haber Türkçe, {cevirmen.yeni} yeni çeviri"
        + (f" (+{cevirmen.claude} Claude)" if cevirmen.claude else "")
        + (f", {cevirmen.eskimis} metinde önceki çeviri" if cevirmen.eskimis else "")
        + (" (Google çevirisi durdu; çevrilemeyen yeni haberler bu yayında gösterilmiyor)" if cevirmen.durdu else "")
    )
    for m in makaleler[:3]:
        print(f"  {m.baslik[:70]}  →  {cevirmen.ceviriler.baslik(m.url, '(çevrilmedi)')[:70]}")
    turkce = [m for m in makaleler if m.kaynak in TURKCE_KAYNAKLAR]
    if turkce:
        ingilizcesi = [m for m in turkce if m.url in cevirmen.ceviriler.ingilizceler]
        print(f"Türkçe kaynak: {len(turkce)} haber, {len(ingilizcesi)} tanesinin İngilizcesi gruplamada")
        for m in ingilizcesi[:2]:
            print(f"  {m.baslik[:70]}  →  {cevirmen.ceviriler.ingilizceler[m.url][0][:70]}")
    return cevirmen.ceviriler


def uret() -> None:
    simdi = datetime.now(timezone.utc)
    takip = Takip(takibi_yukle(TAKIP_DOSYASI, ILK_GORULME_DOSYASI), simdi)
    kategoriler: dict[str, list[KaynakBolumu]] = {}
    ayiklanan: set[str] = set()

    for kategori, ad, adres in KAYNAKLAR:
        makaleler = kaynak_haberleri(kategori, ad, adres, takip, ayiklanan)
        kategoriler.setdefault(kategori, []).append(KaynakBolumu(ad, adres, makaleler))
        print(f"{kategori} / {ad}: {len(makaleler)} haber")

    takibi_kaydet(TAKIP_DOSYASI, takip.kayitlar, simdi)
    print(f"Takip: {len(takip.kayitlar)} kayıt, {len(takip.guncellenen)} haber güncellendi")
    for url in takip.guncellenen[:10]:
        print(f"  güncellendi: {url}")
    if takip.toplu_degisen_kaynaklar:
        print("  toplu değişiklik (güncelleme sayılmadı): " + ", ".join(takip.toplu_degisen_kaynaklar))

    # Arşivdeki eski kayıtların başlıkları da güncel kurallarla temizlenir.
    # Başlığına (ozet.KAYNAK_KURALLARI "haber_at"), adresine
    # (ATLANAN_BOLUMLER) ya da bu turda sayfa etiketine ("etiket_at") göre
    # artık alınmayan haberler arşivden de çıkar.
    onceki = [
        replace(k, baslik=basligi_temizle(k.baslik, k.kaynak)) for k in arsivi_yukle(ARSIV_DOSYASI)
        if not atlanacak_mi(basligi_temizle(k.baslik, k.kaynak), k.kaynak)
        and not re.search(ATLANAN_BOLUMLER.get((k.kategori, k.kaynak)) or r"(?!)", k.url)
        and k.url not in ayiklanan and _normal(k.url) not in ayiklanan
    ]
    arsiv = arsivi_guncelle(onceki, kategoriler, datetime.now(timezone.utc))
    arsivi_kaydet(ARSIV_DOSYASI, arsiv)
    eski = eski_haberler(arsiv, kategoriler)
    print(f"Arşiv: {len(arsiv)} kayıt, {len(eski)} eski haber")

    ceviri = cevir(kategoriler, eski)

    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(sayfa_olustur(kategoriler, eski, ceviri), encoding="utf-8")
    yan_dosyalari_yaz(CIKTI.parent)

    toplam = sum(len(b.makaleler) for bolumler in kategoriler.values() for b in bolumler)
    print(f"Bitti: {CIKTI} ({toplam} haber)")


if __name__ == "__main__":
    uret()
