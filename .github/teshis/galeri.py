"""GEÇİCİ teşhis: Guardian galerisinin gerçek metni (Photograph künyesi)."""
import sys
sys.path.insert(0, "scripts")
from besleme import makale_getir  # noqa: E402
m = makale_getir("https://www.theguardian.com/artanddesign/gallery/2026/oct/03/barking-beautiful-the-2026-dog-photography-awards-in-pictures")
t = m["govde"] if m else ""
i = t.find("Brockman")
print("[TESHIS]", repr(t[:300]))
print("[TESHIS]", repr(t[max(0, i - 200):i + 400]))
