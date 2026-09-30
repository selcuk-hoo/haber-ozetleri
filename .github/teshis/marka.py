"""GEÇİCİ teşhis: markalar.markalari_koruyarak gerçek Google çevirisiyle (8 istek)."""
import sys
import time

sys.path.insert(0, "scripts")
from ceviri import google_cevir  # noqa: E402
from markalar import markalari_koruyarak  # noqa: E402

for cumle in [
    "The open-source AI platforms vying to become China’s Hugging Face",
    "Anthropic CEO Amodei to have dinner with Trump at White House",
    "Researchers at Anthropic found that the model could deceive its users.",
    "The company was founded by former employees of Hugging Face and Google.",
    "“Not everyone is able to use a VPN all the time,” Xu Yong told Rest of World.",
    "According to The Verge, the phone will launch next month.",
    "AMD buys Li Fei-Fei’s World Labs for US$8.2b, escalating rivalry with Nvidia",
    "Microsoft’s new Surface Mouse has haptic feedback and a customizable button",
]:
    try:
        print(f"[TESHIS] {cumle}\n[TESHIS]   → {markalari_koruyarak(cumle, google_cevir)}")
    except Exception as hata:  # noqa: BLE001
        print(f"[TESHIS] HATA {hata!r}")
    time.sleep(2)
