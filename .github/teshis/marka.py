"""GEÇİCİ teşhis: marka adlarını Google çevirisinden koruma yöntemleri.
Az istek: 5 cümle x 4 yöntem, 2 sn arayla."""
import sys
import time

sys.path.insert(0, "scripts")
from ceviri import google_cevir  # noqa: E402

ZWSP, WJ = "​", "⁠"
cumleler = [
    ("The open-source AI platforms vying to become China’s Hugging Face", ["Hugging Face"]),
    ("Anthropic CEO Amodei to have dinner with Trump at White House", ["Anthropic"]),
    ("AMD buys Li Fei-Fei’s World Labs for US$8.2b, escalating rivalry with Nvidia", ["World Labs"]),
    ("Microsoft’s new Surface Mouse has haptic feedback and a customizable button", ["Surface Mouse"]),
    ("Anthropic's new model beats OpenAI and Hugging Face rivals in a benchmark", ["Anthropic", "Hugging Face"]),
]


def boz(ad, ayrac):
    # Kelimeler ayraçla birleşir; tek kelimede ilk harften sonra ayraç.
    return ayrac.join(ad.split(" ")) if " " in ad else ad[0] + ayrac + ad[1:]


yontemler = {
    "düz": lambda c, adlar: c,
    "zwsp": lambda c, adlar: _uygula(c, adlar, lambda a: boz(a, ZWSP)),
    "wj": lambda c, adlar: _uygula(c, adlar, lambda a: boz(a, WJ)),
    "yertutucu": lambda c, adlar: _uygula(c, adlar, lambda a: "X" + str(adlar.index(a) + 1) + "Q"),
}


def _uygula(c, adlar, donustur):
    for a in adlar:
        c = c.replace(a, donustur(a))
    return c


for cumle, adlar in cumleler:
    for ad, yontem in yontemler.items():
        girdi = yontem(cumle, adlar)
        try:
            cikti = google_cevir(girdi)
        except Exception as hata:  # noqa: BLE001
            cikti = f"HATA {hata!r}"
        temiz = cikti.replace(ZWSP, "").replace(WJ, "")
        print(f"[TESHIS] {ad:9} | {temiz} | ham={cikti!r}")
        time.sleep(2)
    print("[TESHIS]")
