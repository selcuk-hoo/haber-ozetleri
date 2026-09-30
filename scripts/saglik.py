"""Sitenin sağlık takibi: süren sorunlar için uyarı metni.

Site sessizce bozulabiliyor: bir kaynak düzenini değiştirip haber
getirmez olur, Google Çeviri saatlerce 429 verir, Claude anahtarının
(`claude setup-token`) süresi dolar. Her çalıştırma birkaç sinyal üretir:
True sorun var, False yok, None bilinmiyor (ör. Claude'a gidecek metin
yoktu; sayaç değişmez). Bir sorun ESIK çalıştırma üst üste sürerse uyarı
metni yazılır; iş akışı bunu depoda bir kayıt (issue) olarak açar, sorunlar
geçince kaydı kapatır (bkz. haber.yml). Sayaçlar arşiv gibi gh-pages'te
(saglik.json) durur.
"""

import json
import os
from pathlib import Path

ESIK = 6  # ardışık çalıştırma (~3 saat)


def aciklama(ad: str) -> str:
    if ad.startswith("kaynak:"):
        return f"**{ad[7:]}** hiç haber getirmiyor (besleme adresi ya da sayfa düzeni değişmiş olabilir)."
    return {
        "google": "**Google Çeviri** duruyor (429 ya da erişim hatası); çevrilemeyen yeni haberler sayfada"
                  " gösterilmiyor ya da Claude yedeğiyle çevriliyor.",
        "claude": "**Claude çevirisi** çalışmıyor. Anahtarın süresi dolmuş olabilir: `claude setup-token` ile yeni"
                  " anahtar alıp deponun `CLAUDE_CODE_OAUTH_TOKEN` gizli değişkenini güncelleyin. Bu sürede Yemek, Gezi"
                  " ve Sanat & Kültür Google'la çevriliyor.",
    }.get(ad, ad)


def saglik_guncelle(yol: Path, sinyaller: dict[str, bool | None]) -> list[str]:
    """Sayaçları günceller, ESIK'i aşan sorunların açıklamalarını döndürür."""
    try:
        sayaclar = json.loads(yol.read_text(encoding="utf-8"))
        if not isinstance(sayaclar, dict):
            sayaclar = {}
    except (FileNotFoundError, json.JSONDecodeError):
        sayaclar = {}
    yeni = {}
    for ad, sorun in sinyaller.items():
        onceki = int(sayaclar.get(ad, 0))
        yeni[ad] = onceki if sorun is None else (onceki + 1 if sorun else 0)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(yeni, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return [f"{aciklama(ad)} ({n} çalıştırmadır)" for ad, n in sorted(yeni.items()) if n >= ESIK]


def uyari_yaz(yol: Path, sorunlar: list[str]) -> None:
    """Sorun yoksa dosya boş kalır (iş akışı açık kaydı kapatır)."""
    if not sorunlar:
        yol.write_text("", encoding="utf-8")
        return
    sahip = os.environ.get("GITHUB_REPOSITORY_OWNER")
    satirlar = ["Sitede birkaç saattir süren sorunlar var:", ""] + [f"- {s}" for s in sorunlar]
    satirlar += ["", "Sorunlar geçince bu kayıt kendiliğinden kapanır."]
    if sahip:
        satirlar += ["", f"@{sahip}"]
    yol.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
