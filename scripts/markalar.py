"""Marka ve yayın adlarını Google çevirisinden korumak.

Google sıradan kelimelerden oluşan adları bazen çeviriyor: "Hugging Face"
→ "Sarılma Yüzü", "Anthropic" → "Antropik", "World Labs" → "Dünya
Laboratuvarları", "told Rest of World" → "Dünyanın geri kalanına söyledi".
Tutarlı da değil: aynı ad bir cümlede korunup ötekinde çevriliyor.

Çeviriden önce her ad "X1Q", "X2Q"… yer tutucusuyla değiştirilir (Google
bunlara dokunmuyor, 5 denemede 5), çeviriden sonra geri yazılır. Google
Türkçe eki yer tutucuya göre seçtiği için ("X1Q'su", "X1Q'nun") ek, adın
okunuşuna göre yeniden çekimlenir: "Hugging Face'i", "Anthropic'in",
"World Labs'ta". Yer tutucu çeviride kaybolursa metin düz çevrilir.

Listeye yalnız Google'ın gerçekten çevirdiği ya da çevirebileceği
(sıradan kelimelerden oluşan) adlar girer; "Apple Butter", "Oval Office"
gibi sıradan kullanımları bozmamak için gerekirse kalıp bağlamlıdır.
"""

import re
from typing import Callable

# Kalıp → okunuşunun sonu (Türkçe ek uyumu için: son ünlü ve son ses).
MARKALAR: dict[str, str] = {
    r"Anthropic": "ik",
    r"Hugging Face": "eys",
    r"World Labs": "labz",
    r"Thinking Machines(?: Lab)?": "inz",
    r"Safe Superintelligence": "ns",
    r"Perplexity": "ti",
    r"Scale AI": "ay",
    r"Figure AI": "ay",
    r"Stability AI": "ay",
    # Microsoft'un ürünleri; yalnız "Surface" değil ürünün tam adı
    # ("a rough surface" etkilenmesin, "Mouse" da "Fare" olmasın).
    r"Surface (?:Pro|Studio|Duo|Go)": "o",
    r"Surface Laptop": "op",
    r"Surface Book": "uk",
    r"Surface Mouse": "aus",
    r"Surface Keyboard": "ord",
    r"Surface Headphones": "onz",
    r"Surface (?:Earbuds|Hub)": "ab",
    r"Surface Pen": "en",
    # Yazılarda kaynak olarak geçen yayın adları ("told Rest of World").
    r"Rest of World": "örld",
    r"The Verge": "örc",
    r"The Art Newspaper": "ır",
    r"Lonely Planet": "ıt",
    r"Bon Appétit": "i",
    r"Aeon": "on",
    r"Lit(?:erary)? Hub": "ab",
}
_KALIPLAR = [(re.compile(rf"(?<![\w-]){k}(?![\w-])"), okunus) for k, okunus in MARKALAR.items()]

_UNLULER = "aeıioöuü"
_KALIN = "aıou"
_YUVARLAK = "oöuü"
_SERT = "fstkçşhp"


def markali_mi(metin: str) -> bool:
    return any(k.search(metin) for k, _ in _KALIPLAR)


def _ek_cekimle(ek: str, okunus: str) -> str:
    """Google'ın ünlüyle biten, son ünlüsü "u" olan yer tutucuya ("X1Q",
    "kyu") eklediği eki adın okunuşuna uyarlar."""
    unluyle_biter = okunus[-1] in _UNLULER
    # Ünlüyle biten köke gelen kaynaştırma ünsüzü, ünsüzle biten adda düşer:
    # "su" (iyelik) → "i", "nun" (ilgi) → "in", "yu"/"ya"/"yla" → "i"/"e"/"le".
    if not unluyle_biter and len(ek) > 1 and (ek[0] == "y" or (ek[0] in "sn" and ek[1] in _UNLULER)):
        ek = ek[1:]
    son_unlu = next((h for h in reversed(okunus) if h in _UNLULER), "e")
    onceki = okunus[-1]
    sonuc = []
    for h in ek:
        if h in "ae":
            h = "a" if son_unlu in _KALIN else "e"
        elif h in "ıiuü":
            kalin, yuvarlak = son_unlu in _KALIN, son_unlu in _YUVARLAK
            h = ("u" if yuvarlak else "ı") if kalin else ("ü" if yuvarlak else "i")
        elif h in "dt":
            h = "t" if onceki in _SERT else "d"
        if h in _UNLULER:
            son_unlu = h
        sonuc.append(h)
        onceki = h
    return "".join(sonuc)


def markalari_koruyarak(metin: str, cevir: Callable[[str], str]) -> str:
    bulunan: list[tuple[str, str]] = []  # (ad, okunuş)

    def degistir(eslesme: re.Match, okunus: str) -> str:
        ad = eslesme.group(0)
        if (ad, okunus) not in bulunan:
            bulunan.append((ad, okunus))
        return f"X{bulunan.index((ad, okunus)) + 1}Q"

    korunan = metin
    for kalip, okunus in _KALIPLAR:
        korunan = kalip.sub(lambda e, o=okunus: degistir(e, o), korunan)
    if not bulunan:
        return cevir(metin)
    ceviri = cevir(korunan)
    for i, (ad, okunus) in enumerate(bulunan, 1):
        yer = re.compile(rf"X{i}Q(?:(['’])?([a-zçğıöşü]+))?", re.IGNORECASE)
        if not yer.search(ceviri):
            # Google yer tutucuyu bozmuş: düz çeviri.
            return cevir(metin)
        ceviri = yer.sub(lambda e: ad + ("'" + _ek_cekimle(e.group(2).lower(), okunus) if e.group(2) else ""), ceviri)
    return ceviri
