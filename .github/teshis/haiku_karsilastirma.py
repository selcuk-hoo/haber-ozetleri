"""GEÇİCİ teşhis: Sonnet ile Haiku 5.5'i aynı işlerde karşılaştırır.
1) Yemek, Gezi, Sanat & Kültür çevirisi (aynı gerçek metinler),
2) Manşet puanlaması (dünya + Türkiye) ve derleme (aynı olaylar)."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "scripts")
import claude_ceviri  # noqa: E402
import manset  # noqa: E402
from ayarlar import CLAUDE_HARIC_KAYNAKLAR, KAYNAKLAR, MANSET_OLAYLARI_DOSYASI  # noqa: E402
from haber_uret import kaynak_haberleri  # noqa: E402
from takip import Takip  # noqa: E402

MODELLER = {"S": "sonnet", "H": "claude-haiku-5-5"}
HABER_KATEGORI = 6  # kategori başına


def model_sec(kod):
    os.environ["CLAUDE_CEVIRI_MODELI"] = MODELLER[kod]
    for k in claude_ceviri.kullanim:
        claude_ceviri.kullanim[k] = 0.0 if k == "maliyet" else 0


def ceviri_denemesi():
    takip = Takip({}, datetime.now(timezone.utc))
    for kategori in ("Yemek", "Gezi", "Sanat & Kültür"):
        makaleler = []
        kaynaklar = [(ad, adres) for k, ad, adres in KAYNAKLAR
                     if k == kategori and (k, ad) not in CLAUDE_HARIC_KAYNAKLAR]
        for ad, adres in kaynaklar:
            try:
                makaleler += kaynak_haberleri(kategori, ad, adres, takip)[:2]
            except Exception as hata:  # noqa: BLE001
                print(f"[TESHIS] {ad} alınamadı: {hata!r}")
            if len(makaleler) >= HABER_KATEGORI:
                break
        makaleler = makaleler[:HABER_KATEGORI]
        metinler = {}
        for i, m in enumerate(makaleler):
            metinler[f"b{i}"] = m.baslik
            metinler[f"o{i}"] = m.ozet
        sonuclar = {}
        for kod in MODELLER:
            model_sec(kod)
            sonuclar[kod] = claude_ceviri.toplu_cevir(metinler, kategori=kategori)
            print(f"[TESHIS] KULLANIM {kategori} {MODELLER[kod]}: {claude_ceviri.kullanim_ozeti()}")
        for i, m in enumerate(makaleler):
            print(f"\n[TESHIS] ==== {kategori} | {m.kaynak} | {m.url}")
            for tur in "bo":
                k = f"{tur}{i}"
                print(f"[TESHIS] EN: {metinler[k]}")
                for kod in MODELLER:
                    print(f"[TESHIS] {kod} : {sonuclar[kod].get(k, '<YOK>')}")


def manset_denemesi():
    kayit = manset.yukle(Path(MANSET_OLAYLARI_DOSYASI))
    simdi = datetime.now(timezone.utc)
    baski = manset.baski_ani(simdi)
    secilen = manset.adaylar(kayit.get("olaylar", []), baski)
    tr_secilen = manset.tr_adaylar(kayit.get("olaylar", []), baski)
    print(f"\n[TESHIS] MANŞET baskı {baski}, {len(secilen)} dünya + {len(tr_secilen)} Türkiye adayı")
    puanlar, tr_puanlar = {}, {}
    for kod in MODELLER:
        model_sec(kod)
        try:
            puanlar[kod] = manset.puanla(secilen) if secilen else []
            tr_puanlar[kod] = (manset.puanla(tr_secilen, None, manset.TR_PUAN_TALIMATI, manset.MANSET_TR_AGIRLIKLAR)
                               if tr_secilen else [])
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] {kod} puanlama hatası: {hata!r}")
            puanlar.setdefault(kod, [None] * len(secilen))
            tr_puanlar.setdefault(kod, [None] * len(tr_secilen))
        print(f"[TESHIS] KULLANIM puanlama {MODELLER[kod]}: {claude_ceviri.kullanim_ozeti()}")
    for ad, liste, p in (("DÜNYA", secilen, puanlar), ("TÜRKİYE", tr_secilen, tr_puanlar)):
        print(f"\n[TESHIS] --- {ad} puanları (S / H)")
        for i, o in enumerate(liste):
            ps = [(p[kod][i] or {}) for kod in MODELLER]
            print(f"[TESHIS] {ps[0].get('puan', '-')!s:>5} / {ps[1].get('puan', '-')!s:>5}  "
                  f"{o['uyeler'][0]['baslik'][:90]}")
            for kod, d in zip(MODELLER, ps):
                print(f"[TESHIS]      {kod}: {d.get('gerekce', '(elendi/yok)')[:250]}")
    # Derleme: Sonnet puanına göre en yüksek 2 dünya + 1 Türkiye olayı, iki modele de.
    sirali = sorted(range(len(secilen)), key=lambda i: -((puanlar["S"][i] or {}).get("puan") or 0))[:2]
    tr_sirali = sorted(range(len(tr_secilen)), key=lambda i: -((tr_puanlar["S"][i] or {}).get("puan") or 0))[:1]
    olaylar = [secilen[i] for i in sirali] + [{**tr_secilen[i], "tur": "turkiye"} for i in tr_sirali]
    for kod in MODELLER:
        model_sec(kod)
        try:
            derlenen = manset.derle(olaylar)
        except Exception as hata:  # noqa: BLE001
            print(f"[TESHIS] {kod} derleme hatası: {hata!r}")
            continue
        print(f"\n[TESHIS] --- DERLEME {MODELLER[kod]} ({claude_ceviri.kullanim_ozeti()})")
        for d in derlenen:
            print(f"[TESHIS] # {d['baslik']}\n[TESHIS]   {d['ozet']}")


if __name__ == "__main__":
    if not claude_ceviri.kullanilabilir_mi():
        print("[TESHIS] Claude kullanılamıyor")
        sys.exit(0)
    ceviri_denemesi()
    manset_denemesi()
