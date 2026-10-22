"""Çok kaynaklı olayların haberlerini sayfada tutma (22.10.2026, kullanıcının isteği).

Sayfada her kaynağın son N haberi durur; hızlı yazan kaynakta (Al Jazeera
günde ~54 haber, 7 yer) bir haber ~3 saatte düşüyordu, önemli olsa da.
"Önemli" = en az iki kaynağın yazdığı olay (olay süzgecinin grupları; Manşet
adayları da buradan). Böyle bir olayın haberleri, olay ilk görüldükten
sonra TUTMA_SURESI boyunca kaynağın N'lik sırası dolsa da sayfada kalır.
Ölçüm (22.10.2026, Gündem): son 12 saatin 14 çok kaynaklı olayının 5'i
sayfadan tamamen düşmüştü (Merkez Bankası faiz indirimi, 5 kaynaklı
Shamonda virüsü); kural ~22 haber ekler, çoğu var olan kartın ilgili
haberi olur. Kullanıcı 24 saati fazla buldu, 12 saat.

Kayıt dist/tutulan.json'da: {url: {"kategori", "kaynak", "ilk"}}.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

TUTMA_SURESI = timedelta(hours=12)


def yukle(yol: Path) -> dict[str, dict]:
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
        return veri if isinstance(veri, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def kaynak_icin(kayit: dict[str, dict], kategori: str, kaynak: str, simdi: datetime) -> list[str]:
    """Bu kaynağın süresi dolmamış tutulan haberleri (en yeni olay önce)."""
    sinir = (simdi - TUTMA_SURESI).isoformat()
    secilen = [(v["ilk"], u) for u, v in kayit.items()
               if v.get("kategori") == kategori and v.get("kaynak") == kaynak and v.get("ilk", "") >= sinir]
    return [u for _, u in sorted(secilen, reverse=True)]


def guncelle(kayit: dict[str, dict], olaylar: list[tuple[str, list]], simdi: datetime) -> dict[str, dict]:
    """olaylar: [(kategori, [Makale, ...])], olay süzgecinin grupları (öncü
    dahil). Çok kaynaklı olayların haberleri eklenir (ilk görülme anı
    korunur), süresi dolanlar atılır."""
    sinir = (simdi - TUTMA_SURESI).isoformat()
    yeni = {u: v for u, v in kayit.items() if v.get("ilk", "") >= sinir}
    for kategori, uyeler in olaylar:
        if len({m.kaynak for m in uyeler}) < 2:
            continue
        # Olaydaki haberlerden biri zaten kayıtlıysa olayın ilk anı odur.
        ilk = min([yeni[m.url]["ilk"] for m in uyeler if m.url in yeni] or [simdi.isoformat()])
        for m in uyeler:
            yeni.setdefault(m.url, {"kategori": kategori, "kaynak": m.kaynak, "ilk": ilk})
    return yeni


def kaydet(yol: Path, kayit: dict[str, dict]) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(kayit, ensure_ascii=False) + "\n", encoding="utf-8")
