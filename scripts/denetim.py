"""İçerik denetimi: sayfadaki başlık ve özetlerde gözden kaçan sorunlar.

Sağlık takibi (saglik.py) teknik arızaları yakalıyordu (kaynak haber
getirmiyor, çeviri duruyor); içerik hataları ancak okur fark edince
düzeliyordu. Her çalıştırmada sayfaya girecek metinler burada taranır
(yapay zekâ yok, maliyetsiz): özet kalıntısı (altyazı, abonelik çağrısı,
adres), çevrilmeden kalmış İngilizce, çok kısa özet, başlığı tekrarlayan
özet. Bulgu ESIK çalıştırma sürerse (aynı haber sayfada kaldıkça) sağlık
kaydına örnekleriyle yazılır; düzeltmesi çoğu zaman ozet.py'ye bir kural
(bkz. CLAUDE.md "Özette kalıntı var").

İlk taramada (03.10.2026) bulunanlar: Guardian galerisinde "Fotoğraf:
Katie Brockman" altyazısı; Gemini'nin çevirmeden geri verdiği Ars Technica
özeti (İngilizce kalmıştı).
"""

import re

from model import Ceviriler, KaynakBolumu

# Kalıntı kalıpları: haber metninde kendiliğinden geçmesi pek olası olmayan
# sayfa öğeleri. "abonelik", "reklam" gibi sıradan sözcükler bilerek yok
# (TV aboneliği, reklam sektörü haberleri yanlış alarm veriyordu).
KALINTI = re.compile(
    r"(?i)\b(?:share this (?:article|story)|share on (?:facebook|twitter|x)\b|advertisement\b|"
    r"sign up (?:for|to) (?:our|the) newsletter|subscribe to (?:our|the)\b|read more:|click here\b|"
    r"accept (?:all )?cookies|enable javascript|getty images|image caption|all rights reserved|"
    r"abone ol(?:un|mak için)?\b|haberin devamı|bültenimize)"
    r"|(?<![\w’'])(?:Fotoğraf|Photograph|Photo|Görsel):\s*[A-ZÇĞİÖŞÜ]"
    r"|https?://|www\.\w|©"
)
# İngilizce kalmış metin: sık İngilizce sözcükler çok, Türkçe harf az.
INGILIZCE = re.compile(r"(?i)\b(?:the|and|of|to|with|is|are|was|for|that|this|has|have)\b")
EN_KISA = 50  # bundan kısa özet bilgi vermiyor
EN_COK_ORNEK = 10  # sağlık kaydına yazılan örnek


def _ingilizce_mi(metin: str) -> bool:
    turkce_harf = len(re.findall(r"[çğıöşüÇĞİÖŞÜ]", metin))
    return len(INGILIZCE.findall(metin)) >= 4 and turkce_harf < len(metin) / 80


def sorun(baslik: str, ozet: str, cevrilmis: bool) -> str | None:
    """Bir kartın sorunu (yoksa None). cevrilmis: metin İngilizceden
    çevrilmiş olmalıydı (Türkçe kaynak değil)."""
    eslesme = KALINTI.search(f"{baslik}\n{ozet}")
    if eslesme:
        return f"kalıntı “{eslesme.group(0).strip()}”"
    if cevrilmis and _ingilizce_mi(ozet):
        return "çevrilmemiş İngilizce"
    if len(ozet.strip()) < EN_KISA:
        return f"çok kısa özet ({len(ozet.strip())} harf)"
    if len(baslik) > 20 and ozet.startswith(baslik[:40]):
        return "özet başlığı tekrarlıyor"
    return None


def denetle(kategoriler: dict[str, list[KaynakBolumu]], ceviri: Ceviriler,
            turkce_kaynaklar: frozenset[str] | set[str]) -> list[str]:
    """Sayfaya girecek kartların sorunları: "Kategori / kaynak: “başlık” — sorun".
    Çevirisi olmayan kart Türkçe sayfada gösterilmediği için taranmaz."""
    bulgular = []
    for kat, bolumler in kategoriler.items():
        for b in bolumler:
            for m in b.makaleler:
                turkce = m.kaynak in turkce_kaynaklar
                if not turkce and not ceviri.cevrildi_mi(m.url):
                    continue
                baslik = m.baslik if turkce else ceviri.baslik(m.url, m.baslik)
                ozet = m.ozet if turkce else ceviri.ozet(m.url, m.ozet)
                neden = sorun(baslik, ozet, not turkce)
                if neden:
                    bulgular.append(f"{kat} / {m.kaynak}: “{baslik[:80]}” — {neden}")
    return bulgular


# Yalnız loga yazılan hafif bulgular (sağlık kaydı açtırmaz): kısa özet
# çoğu zaman yazının soruyla açılmasından ("Kuzey Kore DMZ'yi zorluyor
# mu?"), kural gerektirmiyor.
HAFIF = ("çok kısa özet",)


def ciddi(bulgular: list[str]) -> list[str]:
    return [b for b in bulgular if not any(f"— {h}" in b for h in HAFIF)]


def ayrinti(bulgular: list[str]) -> str:
    """Sağlık kaydı için örnek listesi (Markdown)."""
    satirlar = [f"  - {b}" for b in bulgular[:EN_COK_ORNEK]]
    if len(bulgular) > EN_COK_ORNEK:
        satirlar.append(f"  - … ve {len(bulgular) - EN_COK_ORNEK} haber daha")
    return "\n".join(satirlar)
