""""Older news" arşivi: sayfadan düşen haberlerin başlıkları.

Her çalıştırmada sayfadaki haberler arşive eklenir (ya da güncellenir),
yayın tarihi ARSIV_SURESI'nden eski olanlar düşer. Sayfanın "Older news"
görünümü arşivde olup o an kart olarak gösterilmeyen haberleri listeler.
Dosya yayınlanan sitenin yanında (gh-pages) tutulur; böylece main'e her
yarım saatte bir arşiv commit'i düşmez (bkz. workflow).
"""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ayarlar import ARSIV_SURESI
from model import ArsivKaydi, KaynakBolumu
from tarih import tarihi_ayristir


def arsivi_yukle(yol: Path) -> list[ArsivKaydi]:
    try:
        ham = json.loads(yol.read_text(encoding="utf-8"))
        return [ArsivKaydi(**k) for k in ham]
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        # İlk çalıştırma ya da bozuk/eski biçimli dosya: boş başla.
        return []


def arsivi_kaydet(yol: Path, kayitlar: list[ArsivKaydi]) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps([asdict(k) for k in kayitlar], ensure_ascii=False) + "\n", encoding="utf-8")


# Süre ve sıralama için: yayın tarihi, o yoksa arşive giriş anı.
def referans_zamani(k: ArsivKaydi) -> datetime:
    zaman = tarihi_ayristir(k.tarih) or tarihi_ayristir(k.eklendi)
    if zaman is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return zaman if zaman.tzinfo else zaman.replace(tzinfo=timezone.utc)


# Aynı haber birden fazla kategoride olabildiği için anahtar (kategori, url).
def arsivi_guncelle(
    onceki: list[ArsivKaydi], kategoriler: dict[str, list[KaynakBolumu]], simdi: datetime
) -> list[ArsivKaydi]:
    kayitlar = {(k.kategori, k.url): k for k in onceki}
    simdi_metni = simdi.strftime("%Y-%m-%dT%H:%M:%S%z")
    for kategori, bolumler in kategoriler.items():
        for b in bolumler:
            for m in b.makaleler:
                eski = kayitlar.get((kategori, m.url))
                kayitlar[(kategori, m.url)] = ArsivKaydi(
                    kategori, m.kaynak, m.baslik, m.url, m.tarih, m.tahmini,
                    eski.eklendi if eski else simdi_metni,
                )
    guncel = [k for k in kayitlar.values() if simdi - referans_zamani(k) <= ARSIV_SURESI]
    guncel.sort(key=referans_zamani, reverse=True)
    return guncel


# Arşivde olup şu an kart olarak gösterilmeyen haberler. Artık
# KAYNAKLAR'da olmayan bir kaynağın kayıtları menüde karşılığı
# olmayacağı için gösterilmez (süresi dolunca arşivden de düşer).
def eski_haberler(arsiv: list[ArsivKaydi], kategoriler: dict[str, list[KaynakBolumu]]) -> list[ArsivKaydi]:
    sayfadakiler = {(kat, m.url) for kat, bolumler in kategoriler.items() for b in bolumler for m in b.makaleler}
    kaynaklar = {(kat, b.ad) for kat, bolumler in kategoriler.items() for b in bolumler}
    return [
        k for k in arsiv
        if (k.kategori, k.url) not in sayfadakiler and (k.kategori, k.kaynak) in kaynaklar
    ]
